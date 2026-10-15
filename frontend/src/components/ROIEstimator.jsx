import React, { useState } from "react";
import {
  ArrowRight,
  ShieldCheck,
  IndianRupee,
  CalendarClock,
  PiggyBank,
  TrendingUp,
  CheckCircle2,
} from "lucide-react";
import Eyebrow from "./Eyebrow";
import { calculatorsApi } from "../api/calculators";

export default function ROIEstimator(props) {
  const theme = props.t || props.theme || {
    bg: "#FFFFFF",
    bgAlt: "#FBFAF6",
    card: "#FFFFFF",
    border: "#E2E8F0",
    text: "#0F172A",
    textMuted: "#475569",
    textFaint: "#94A3B8",
    green: "#1F5C3E",
    greenHover: "#184931",
    greenSoft: "#EFF3EC",
    input: "#FFFFFF",
  };

  const [systemSize, setSystemSize] = useState("5");
  const [monthlySavings, setMonthlySavings] = useState("6000");
  const [subsidy, setSubsidy] = useState("78000");
  const [calculated, setCalculated] = useState(false);
  const [results, setResults] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleCalculate = async (e) => {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const estimate = await calculatorsApi.estimateROI({
        system_size_kw: Number(systemSize) || 0,
        monthly_savings: Number(monthlySavings) || 0,
        subsidy: Number(subsidy) || 0,
      });
      setResults({
        netInvestment: estimate.net_investment ?? estimate.netInvestment,
        paybackYears: estimate.payback_years ?? estimate.paybackYears,
        lifetimeSavings: estimate.lifetime_savings ?? estimate.lifetimeSavings,
        roiPercent: estimate.roi_percent ?? estimate.roiPercent,
      });
      setCalculated(true);
    } catch (err) {
      setError(err.message || "Unable to estimate ROI right now.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="py-12 sm:py-16 lg:py-20 transition-colors duration-200"
      style={{ backgroundColor: theme.bg }}
    >
      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-8 xl:px-10">
        {/* Header Section */}
        <div>
          <Eyebrow text="ROI Estimator" theme={theme} />
          <h1
            className="text-4xl sm:text-5xl lg:text-[54px] font-semibold leading-[1.15] tracking-tight max-w-4xl"
            style={{ color: theme.text }}
          >
            See the real return on your solar investment.
          </h1>
          <p
            className="mt-4 text-base sm:text-lg lg:text-xl leading-relaxed max-w-3xl"
            style={{ color: theme.textMuted }}
          >
            Calculate your payback timeframe, 25-year net utility savings, and overall return on investment percentage.
          </p>
        </div>

        {/* 2-Column Layout (3/2 split -> 7 cols / 5 cols) */}
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

              {/* Field 1: System Size */}
              <div className="flex flex-col space-y-2">
                <label
                  className="text-sm font-medium"
                  style={{ color: theme.text }}
                >
                  System size (kW)
                </label>
                <input
                  type="number"
                  placeholder="e.g. 5"
                  value={systemSize}
                  onChange={(e) => setSystemSize(e.target.value)}
                  required
                  min="1"
                  step="0.5"
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

              {/* Field 2: Expected Monthly Savings */}
              <div className="flex flex-col space-y-2">
                <label
                  className="text-sm font-medium"
                  style={{ color: theme.text }}
                >
                  Expected monthly savings (₹)
                </label>
                <input
                  type="number"
                  placeholder="e.g. 6000"
                  value={monthlySavings}
                  onChange={(e) => setMonthlySavings(e.target.value)}
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

              {/* Field 3: Government Subsidy */}
              <div className="flex flex-col space-y-2">
                <label
                  className="text-sm font-medium"
                  style={{ color: theme.text }}
                >
                  Government subsidy (₹, optional)
                </label>
                <input
                  type="number"
                  placeholder="e.g. 78000"
                  value={subsidy}
                  onChange={(e) => setSubsidy(e.target.value)}
                  min="0"
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

              {/* Estimate Button */}
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full inline-flex items-center justify-center gap-2.5 font-medium text-base px-7 py-4 rounded-full text-white transition-all duration-200 mt-2 focus:outline-none cursor-pointer"
                style={{ backgroundColor: theme.green }}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.backgroundColor = theme.greenHover)
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.backgroundColor = theme.green)
                }
              >
                <span>{isSubmitting ? "Estimating..." : "Estimate My ROI"}</span>
                <ArrowRight className="w-5 h-5" />
              </button>

              {/* Trust Badge */}
              <div
                className="flex items-center justify-center gap-2 text-xs sm:text-sm pt-1"
                style={{ color: theme.textFaint }}
              >
                <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>
                  Based on a 25-year panel lifespan and average install costs.
                </span>
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
                <div
                  className="w-12 h-12 rounded-2xl flex items-center justify-center mb-6"
                  style={{
                    backgroundColor: theme.greenSoft,
                    color: theme.green,
                  }}
                >
                  <TrendingUp className="w-6 h-6" />
                </div>

                <h3
                  className="text-2xl font-semibold tracking-tight"
                  style={{ color: theme.text }}
                >
                  Why ROI matters
                </h3>
                <p
                  className="mt-3 text-sm sm:text-base leading-relaxed"
                  style={{ color: theme.textMuted }}
                >
                  Solar energy is a fixed-cost capital investment that protects you from inflation and annual utility tariff hikes. Most rooftop systems pay for themselves within 3–5 years.
                </p>

                <ul
                  className="mt-6 space-y-3 text-sm font-medium"
                  style={{ color: theme.text }}
                >
                  {[
                    "Hedge against 6-8% annual grid inflation",
                    "PM Surya Ghar subsidy deduction included",
                    "25-year linear performance warranty",
                    "Tax-free wealth generation",
                  ].map((item, idx) => (
                    <li key={idx} className="flex items-center gap-2.5">
                      <CheckCircle2
                        className="w-5 h-5 flex-shrink-0"
                        style={{ color: theme.green }}
                      />
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
                <div
                  className="flex items-center justify-between border-b pb-4 mb-6"
                  style={{ borderColor: theme.border }}
                >
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-emerald-700">
                      Calculated Results
                    </span>
                    <h3
                      className="text-2xl font-bold tracking-tight"
                      style={{ color: theme.text }}
                    >
                      Your Estimated Return
                    </h3>
                  </div>
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center text-white"
                    style={{ backgroundColor: theme.green }}
                  >
                    <TrendingUp className="w-5 h-5" />
                  </div>
                </div>

                {/* 2x2 Grid of Result Boxes */}
                <div className="grid grid-cols-2 gap-4">
                  {/* Box 1: Net Investment */}
                  <div
                    className="p-4 rounded-2xl border shadow-sm flex flex-col justify-between"
                    style={{
                      backgroundColor: theme.card,
                      borderColor: theme.border,
                    }}
                  >
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center mb-2"
                      style={{
                        backgroundColor: theme.greenSoft,
                        color: theme.green,
                      }}
                    >
                      <IndianRupee className="w-4 h-4" />
                    </div>
                    <div>
                      <div
                        className="text-xl font-bold tracking-tight"
                        style={{ color: theme.text }}
                      >
                        ₹{results.netInvestment.toLocaleString("en-IN")}
                      </div>
                      <div
                        className="text-xs font-medium mt-0.5"
                        style={{ color: theme.textFaint }}
                      >
                        Net Investment
                      </div>
                    </div>
                  </div>

                  {/* Box 2: Payback Period */}
                  <div
                    className="p-4 rounded-2xl border shadow-sm flex flex-col justify-between"
                    style={{
                      backgroundColor: theme.card,
                      borderColor: theme.border,
                    }}
                  >
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center mb-2"
                      style={{
                        backgroundColor: theme.greenSoft,
                        color: theme.green,
                      }}
                    >
                      <CalendarClock className="w-4 h-4" />
                    </div>
                    <div>
                      <div
                        className="text-xl font-bold tracking-tight"
                        style={{ color: theme.text }}
                      >
                        {results.paybackYears} yrs
                      </div>
                      <div
                        className="text-xs font-medium mt-0.5"
                        style={{ color: theme.textFaint }}
                      >
                        Payback Period
                      </div>
                    </div>
                  </div>

                  {/* Box 3: 25-Year Net Savings */}
                  <div
                    className="p-4 rounded-2xl border shadow-sm flex flex-col justify-between"
                    style={{
                      backgroundColor: theme.card,
                      borderColor: theme.border,
                    }}
                  >
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center mb-2"
                      style={{
                        backgroundColor: theme.greenSoft,
                        color: theme.green,
                      }}
                    >
                      <PiggyBank className="w-4 h-4" />
                    </div>
                    <div>
                      <div
                        className="text-xl font-bold tracking-tight"
                        style={{ color: theme.text }}
                      >
                        ₹{results.lifetimeSavings.toLocaleString("en-IN")}
                      </div>
                      <div
                        className="text-xs font-medium mt-0.5"
                        style={{ color: theme.textFaint }}
                      >
                        25-Yr Net Savings
                      </div>
                    </div>
                  </div>

                  {/* Box 4: Total ROI */}
                  <div
                    className="p-4 rounded-2xl border shadow-sm flex flex-col justify-between"
                    style={{
                      backgroundColor: theme.card,
                      borderColor: theme.border,
                    }}
                  >
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center mb-2"
                      style={{
                        backgroundColor: theme.greenSoft,
                        color: theme.green,
                      }}
                    >
                      <TrendingUp className="w-4 h-4" />
                    </div>
                    <div>
                      <div
                        className="text-xl font-bold tracking-tight text-emerald-600"
                      >
                        {results.roiPercent}%
                      </div>
                      <div
                        className="text-xs font-medium mt-0.5"
                        style={{ color: theme.textFaint }}
                      >
                        Total ROI
                      </div>
                    </div>
                  </div>
                </div>

                {/* Disclaimer */}
                <p
                  className="mt-6 text-xs leading-relaxed"
                  style={{ color: theme.textMuted }}
                >
                  Estimates account for 0.5% annual panel degradation. Actual returns depend on local utility net-metering policies.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
