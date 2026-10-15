import React, { useState } from 'react';
import { ArrowRight, ShieldCheck, Zap, TrendingUp, Clock, Leaf, CheckCircle2 } from 'lucide-react';
import Eyebrow from './Eyebrow';
import { calculatorsApi } from '../api/calculators';

export default function CalculatorsPage({ theme }) {
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [bill, setBill] = useState('5000');
  const [propertyType, setPropertyType] = useState('Residential');
  const [roofArea, setRoofArea] = useState('800');
  const [calculated, setCalculated] = useState(false);
  const [results, setResults] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [savedNotice, setSavedNotice] = useState('');

  const handleCalculate = async (e) => {
    e.preventDefault();
    setError('');
    setSavedNotice('');
    setIsSubmitting(true);

    try {
      const estimate = await calculatorsApi.estimateSavings({
        monthly_bill: Number(bill) || 0,
        roof_area: Number(roofArea) || 0,
        property_type: propertyType,
      });

      const normalized = {
        systemSizeKW: estimate.system_size_kw ?? estimate.systemSizeKW,
        annualSavings: estimate.annual_savings ?? estimate.annualSavings,
        paybackYears: estimate.payback_years ?? estimate.paybackYears ?? estimate.payback_period_years,
        co2Tons: estimate.co2_tons ?? estimate.co2Tons,
      };

      await calculatorsApi.createSubmission({
        name,
        phone,
        email: email || undefined,
        property_type: propertyType,
        monthly_bill: Number(bill) || 0,
        roof_area: Number(roofArea) || 0,
        system_size_kw: Number(normalized.systemSizeKW) || 0,
        annual_savings: Number(normalized.annualSavings) || 0,
        payback_period_years: Number(normalized.paybackYears) || 0,
        calculator_type: "Solar Savings",
      });

      setResults(normalized);
      setCalculated(true);
      setSavedNotice('Estimate saved. Our solar team can follow up from the CRM.');
    } catch (err) {
      setError(err.message || 'Unable to calculate your savings right now.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="py-12 sm:py-16 lg:py-20 transition-colors duration-200" style={{ backgroundColor: theme.bg }}>
      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-8 xl:px-10">
        
        {/* Header Section */}
        <div>
          <Eyebrow text="Solar Savings Calculator" theme={theme} />
          <h1
            className="text-4xl sm:text-5xl lg:text-[54px] font-semibold leading-[1.15] tracking-tight max-w-4xl"
            style={{ color: theme.text }}
          >
            Find out how much you can save with solar.
          </h1>
          <p
            className="mt-4 text-base sm:text-lg lg:text-xl leading-relaxed max-w-3xl"
            style={{ color: theme.textMuted }}
          >
            Calculate your recommended kilowatt capacity, annual electricity bill savings, and investment payback period in seconds.
          </p>
        </div>

        {/* 2-Column Layout (3/2 split) */}
        <div className="mt-12 grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-start">
          
          {/* LEFT: Form Card (7 cols) */}
          <div
            className="lg:col-span-7 rounded-3xl p-6 sm:p-8 lg:p-10 border shadow-sm transition-colors duration-200"
            style={{
              backgroundColor: theme.card,
              borderColor: theme.border,
            }}
          >
            <form onSubmit={handleCalculate} className="space-y-6">
              {error && (
                <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {error}
                </div>
              )}
              {savedNotice && (
                <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                  {savedNotice}
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="flex flex-col space-y-2">
                  <label className="text-sm font-medium" style={{ color: theme.text }}>
                    Full name
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Rahul Verma"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    className="w-full px-4 py-3.5 rounded-xl border text-base outline-none transition-all duration-200"
                    style={{
                      backgroundColor: theme.input,
                      borderColor: theme.border,
                      color: theme.text,
                    }}
                  />
                </div>

                <div className="flex flex-col space-y-2">
                  <label className="text-sm font-medium" style={{ color: theme.text }}>
                    Phone number
                  </label>
                  <input
                    type="tel"
                    placeholder="+91 98765 43210"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    required
                    className="w-full px-4 py-3.5 rounded-xl border text-base outline-none transition-all duration-200"
                    style={{
                      backgroundColor: theme.input,
                      borderColor: theme.border,
                      color: theme.text,
                    }}
                  />
                </div>
              </div>

              <div className="flex flex-col space-y-2">
                <label className="text-sm font-medium" style={{ color: theme.text }}>
                  Email address
                </label>
                <input
                  type="email"
                  placeholder="rahul@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-4 py-3.5 rounded-xl border text-base outline-none transition-all duration-200"
                  style={{
                    backgroundColor: theme.input,
                    borderColor: theme.border,
                    color: theme.text,
                  }}
                />
              </div>
              
              {/* Field 1: Monthly Electricity Bill */}
              <div className="flex flex-col space-y-2">
                <label className="text-sm font-medium" style={{ color: theme.text }}>
                  Average monthly electricity bill (₹)
                </label>
                <input
                  type="number"
                  placeholder="e.g. 5000"
                  value={bill}
                  onChange={(e) => setBill(e.target.value)}
                  required
                  min="500"
                  className="w-full px-4 py-3.5 rounded-xl border text-base outline-none transition-all duration-200"
                  style={{
                    backgroundColor: theme.input,
                    borderColor: theme.border,
                    color: theme.text,
                  }}
                  onFocus={(e) => (e.target.style.borderColor = theme.green)}
                  onBlur={(e) => (e.target.style.borderColor = theme.border)}
                />
              </div>

              {/* Field 2: Property Type Toggle */}
              <div className="flex flex-col space-y-2">
                <label className="text-sm font-medium" style={{ color: theme.text }}>
                  Property Type
                </label>
                <div className="grid grid-cols-3 gap-3">
                  {['Residential', 'Commercial', 'Industrial'].map((type) => {
                    const isActive = propertyType === type;
                    return (
                      <button
                        key={type}
                        type="button"
                        onClick={() => setPropertyType(type)}
                        className="py-3 px-3 rounded-xl border text-sm font-medium transition-all duration-200 focus:outline-none text-center"
                        style={{
                          backgroundColor: isActive ? theme.greenSoft : theme.input,
                          borderColor: isActive ? theme.green : theme.border,
                          color: isActive ? theme.green : theme.textMuted,
                        }}
                      >
                        {type}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Field 3: Available Roof Area */}
              <div className="flex flex-col space-y-2">
                <label className="text-sm font-medium" style={{ color: theme.text }}>
                  Available roof area (sq. ft.)
                </label>
                <input
                  type="number"
                  placeholder="e.g. 800"
                  value={roofArea}
                  onChange={(e) => setRoofArea(e.target.value)}
                  required
                  min="100"
                  className="w-full px-4 py-3.5 rounded-xl border text-base outline-none transition-all duration-200"
                  style={{
                    backgroundColor: theme.input,
                    borderColor: theme.border,
                    color: theme.text,
                  }}
                  onFocus={(e) => (e.target.style.borderColor = theme.green)}
                  onBlur={(e) => (e.target.style.borderColor = theme.border)}
                />
              </div>

              {/* Calculate Button */}
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full inline-flex items-center justify-center gap-2.5 font-medium text-base px-7 py-4 rounded-full text-white transition-all duration-200 mt-2 focus:outline-none"
                style={{ backgroundColor: theme.green }}
                onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = theme.greenHover)}
                onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = theme.green)}
              >
                <span>{isSubmitting ? 'Calculating...' : 'Calculate My Savings'}</span>
                <ArrowRight className="w-5 h-5" />
              </button>

              {/* Trust Badge */}
              <div className="flex items-center justify-center gap-2 text-xs sm:text-sm pt-1" style={{ color: theme.textFaint }}>
                <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>Your information is safe with us. We do not share your data.</span>
              </div>
            </form>
          </div>

          {/* RIGHT: Results / Info Panel (5 cols) */}
          <div className="lg:col-span-5">
            {!calculated || !results ? (
              <div
                className="rounded-3xl p-6 sm:p-8 border transition-colors duration-200"
                style={{
                  backgroundColor: theme.card,
                  borderColor: theme.border,
                }}
              >
                <div className="h-44 rounded-2xl overflow-hidden mb-6 border" style={{ borderColor: theme.border }}>
                  <img
                    src="/solar-house-hero.jpg"
                    onError={(e) => {
                      e.target.onerror = null;
                      e.target.src = "https://placehold.co/600x400/1F5C3E/FFFFFF?text=SOLARA+Solar+Panels";
                    }}
                    alt="Solar Panels"
                    className="w-full h-full object-cover"
                  />
                </div>

                <h3 className="text-2xl font-semibold tracking-tight" style={{ color: theme.text }}>
                  Clean Energy, Brighter Savings
                </h3>
                <p className="mt-2 text-sm sm:text-base leading-relaxed" style={{ color: theme.textMuted }}>
                  Enter your monthly electricity bill details to generate a customized solar estimation report.
                </p>

                <ul className="mt-6 space-y-3 text-sm font-medium" style={{ color: theme.text }}>
                  {[
                    'Accurate capacity estimates',
                    'Government subsidy included',
                    'Customized for your location',
                    '100% free & zero obligation',
                  ].map((item, idx) => (
                    <li key={idx} className="flex items-center gap-2.5">
                      <CheckCircle2 className="w-5 h-5 flex-shrink-0" style={{ color: theme.green }} />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <div
                className="rounded-3xl p-6 sm:p-8 border transition-all duration-300"
                style={{
                  backgroundColor: theme.greenSoft,
                  borderColor: theme.green,
                }}
              >
                <div className="flex items-center justify-between border-b pb-4 mb-6" style={{ borderColor: theme.border }}>
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-emerald-700">Calculated Results</span>
                    <h3 className="text-2xl font-bold tracking-tight" style={{ color: theme.text }}>
                      Your Solar Potential
                    </h3>
                  </div>
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center text-white"
                    style={{ backgroundColor: theme.green }}
                  >
                    <Zap className="w-5 h-5" />
                  </div>
                </div>

                {/* 2x2 Grid of Stats */}
                <div className="grid grid-cols-2 gap-4">
                  {/* Stat 1 */}
                  <div className="p-4 rounded-2xl border shadow-sm flex flex-col justify-between" style={{ backgroundColor: theme.card, borderColor: theme.border }}>
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-2" style={{ backgroundColor: theme.greenSoft, color: theme.green }}>
                      <Zap className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-2xl font-bold tracking-tight" style={{ color: theme.text }}>
                        {results.systemSizeKW} kW
                      </div>
                      <div className="text-xs font-medium mt-0.5" style={{ color: theme.textFaint }}>
                        Recommended System Size
                      </div>
                    </div>
                  </div>

                  {/* Stat 2 */}
                  <div className="p-4 rounded-2xl border shadow-sm flex flex-col justify-between" style={{ backgroundColor: theme.card, borderColor: theme.border }}>
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-2" style={{ backgroundColor: theme.greenSoft, color: theme.green }}>
                      <TrendingUp className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-2xl font-bold tracking-tight" style={{ color: theme.text }}>
                        ₹{results.annualSavings.toLocaleString('en-IN')}
                      </div>
                      <div className="text-xs font-medium mt-0.5" style={{ color: theme.textFaint }}>
                        Est. Annual Savings
                      </div>
                    </div>
                  </div>

                  {/* Stat 3 */}
                  <div className="p-4 rounded-2xl border shadow-sm flex flex-col justify-between" style={{ backgroundColor: theme.card, borderColor: theme.border }}>
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-2" style={{ backgroundColor: theme.greenSoft, color: theme.green }}>
                      <Clock className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-2xl font-bold tracking-tight" style={{ color: theme.text }}>
                        {results.paybackYears} yrs
                      </div>
                      <div className="text-xs font-medium mt-0.5" style={{ color: theme.textFaint }}>
                        Payback Period
                      </div>
                    </div>
                  </div>

                  {/* Stat 4 */}
                  <div className="p-4 rounded-2xl border shadow-sm flex flex-col justify-between" style={{ backgroundColor: theme.card, borderColor: theme.border }}>
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-2" style={{ backgroundColor: theme.greenSoft, color: theme.green }}>
                      <Leaf className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-2xl font-bold tracking-tight" style={{ color: theme.text }}>
                        {results.co2Tons} tons
                      </div>
                      <div className="text-xs font-medium mt-0.5" style={{ color: theme.textFaint }}>
                        CO₂ Saved / Year
                      </div>
                    </div>
                  </div>
                </div>

                {/* Disclaimer */}
                <p className="mt-6 text-xs leading-relaxed" style={{ color: theme.textMuted }}>
                  This is an estimate for illustration purposes. Book a free site survey for an exact, personalized quote.
                </p>
              </div>
            )}
          </div>

        </div>

      </div>
    </div>
  );
}
