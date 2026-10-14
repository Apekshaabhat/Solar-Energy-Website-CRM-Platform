import React, { useState } from 'react';
import { MapPin, Phone, Mail, Send, CheckCircle2 } from 'lucide-react';
import Eyebrow from './Eyebrow';
import CtaBanner from './CtaBanner';
import { leadsApi } from '../api/leads';

export default function ContactPage({ theme }) {
  const [formData, setFormData] = useState({
    fullName: '',
    phone: '',
    email: '',
    location: '',
    message: '',
  });

  const [submitted, setSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      await leadsApi.createLead({
        name: formData.fullName,
        contact: formData.phone || formData.email,
        phone: formData.phone,
        email: formData.email,
        location: formData.location,
        propertyType: 'Residential',
        source: 'Website',
        notes: formData.message,
      });
      setSubmitted(true);
      setTimeout(() => {
        setSubmitted(false);
        setFormData({ fullName: '', phone: '', email: '', location: '', message: '' });
      }, 4000);
    } catch (err) {
      setError(err.message || 'Unable to send your message right now.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="transition-colors duration-200" style={{ backgroundColor: theme.bg }}>
      
      {/* Header Section */}
      <section className="py-12 sm:py-16 lg:py-20">
        <div className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-8 xl:px-10">
          
          <Eyebrow text="Get in touch" theme={theme} />
          
          <h1
            className="text-4xl sm:text-5xl lg:text-[54px] font-semibold leading-[1.15] tracking-tight max-w-4xl"
            style={{ color: theme.text }}
          >
            Let's build your solar future together.
          </h1>

          <p
            className="mt-6 text-base sm:text-lg lg:text-xl leading-relaxed max-w-3xl"
            style={{ color: theme.textMuted }}
          >
            Have questions about rooftop solar installation, financial payback periods, or government subsidies? Our clean energy advisors are ready to assist you. Fill out the form below and we will get back to you within 24 hours.
          </p>

          {/* Two-Column Layout (60/40 Split on Desktop) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 mt-12 sm:mt-16 items-stretch">
            
            {/* LEFT Column: Form (60% width = lg:col-span-7) */}
            <div
              className="lg:col-span-7 rounded-3xl p-6 sm:p-10 border transition-all duration-200"
              style={{
                backgroundColor: theme.card,
                borderColor: theme.border,
              }}
            >
              <h3
                className="text-2xl font-bold tracking-tight mb-6"
                style={{ color: theme.text }}
              >
                Send us a message
              </h3>

              {submitted ? (
                <div
                  className="rounded-2xl p-6 border text-center my-8 flex flex-col items-center justify-center space-y-3"
                  style={{
                    backgroundColor: theme.greenSoft,
                    borderColor: theme.border,
                    color: theme.green,
                  }}
                >
                  <CheckCircle2 className="w-12 h-12" />
                  <h4 className="text-xl font-bold" style={{ color: theme.text }}>
                    Message Sent Successfully!
                  </h4>
                  <p className="text-sm max-w-md" style={{ color: theme.textMuted }}>
                    Thank you for reaching out to SOLARA. Our solar advisor will review your request and contact you within 24 hours.
                  </p>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-6">
                  {error && (
                    <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                      {error}
                    </div>
                  )}
                  
                  {/* 2-Column Input Grid */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                    
                    {/* Full Name */}
                    <div className="flex flex-col space-y-2">
                      <label
                        className="text-sm font-semibold"
                        style={{ color: theme.text }}
                      >
                        Full name
                      </label>
                      <input
                        type="text"
                        name="fullName"
                        required
                        value={formData.fullName}
                        onChange={handleChange}
                        placeholder="e.g. Rahul Verma"
                        className="rounded-xl px-4 py-3 border text-sm font-medium transition-colors focus:outline-none focus:ring-2"
                        style={{
                          backgroundColor: theme.input,
                          borderColor: theme.border,
                          color: theme.text,
                        }}
                      />
                    </div>

                    {/* Phone Number */}
                    <div className="flex flex-col space-y-2">
                      <label
                        className="text-sm font-semibold"
                        style={{ color: theme.text }}
                      >
                        Phone number
                      </label>
                      <input
                        type="tel"
                        name="phone"
                        required
                        value={formData.phone}
                        onChange={handleChange}
                        placeholder="+91 98765 43210"
                        className="rounded-xl px-4 py-3 border text-sm font-medium transition-colors focus:outline-none focus:ring-2"
                        style={{
                          backgroundColor: theme.input,
                          borderColor: theme.border,
                          color: theme.text,
                        }}
                      />
                    </div>

                  </div>

                  {/* Email Address (Full Width) */}
                  <div className="flex flex-col space-y-2">
                    <label
                      className="text-sm font-semibold"
                      style={{ color: theme.text }}
                    >
                      Email address
                    </label>
                    <input
                      type="email"
                      name="email"
                      required
                      value={formData.email}
                      onChange={handleChange}
                      placeholder="rahul@example.com"
                      className="rounded-xl px-4 py-3 border text-sm font-medium transition-colors focus:outline-none focus:ring-2"
                      style={{
                        backgroundColor: theme.input,
                        borderColor: theme.border,
                        color: theme.text,
                      }}
                    />
                  </div>

                  <div className="flex flex-col space-y-2">
                    <label
                      className="text-sm font-semibold"
                      style={{ color: theme.text }}
                    >
                      Location
                    </label>
                    <input
                      type="text"
                      name="location"
                      required
                      value={formData.location}
                      onChange={handleChange}
                      placeholder="e.g. Pune, Maharashtra"
                      className="rounded-xl px-4 py-3 border text-sm font-medium transition-colors focus:outline-none focus:ring-2"
                      style={{
                        backgroundColor: theme.input,
                        borderColor: theme.border,
                        color: theme.text,
                      }}
                    />
                  </div>

                  {/* Message Textarea (5 rows) */}
                  <div className="flex flex-col space-y-2">
                    <label
                      className="text-sm font-semibold"
                      style={{ color: theme.text }}
                    >
                      Message
                    </label>
                    <textarea
                      name="message"
                      rows={5}
                      required
                      value={formData.message}
                      onChange={handleChange}
                      placeholder="Tell us about your rooftop area, monthly energy bills, or specific solar requirements..."
                      className="rounded-xl px-4 py-3 border text-sm font-medium transition-colors focus:outline-none focus:ring-2 resize-y"
                      style={{
                        backgroundColor: theme.input,
                        borderColor: theme.border,
                        color: theme.text,
                      }}
                    />
                  </div>

                  {/* Send Message Button */}
                  <div>
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="inline-flex items-center justify-center gap-2.5 font-medium text-base px-7 py-3.5 rounded-full transition-colors text-white focus:outline-none"
                      style={{ backgroundColor: theme.green }}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = theme.greenHover)}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = theme.green)}
                    >
                      <span>{isSubmitting ? 'Sending...' : 'Send Message'}</span>
                      <Send className="w-4 h-4" />
                    </button>
                  </div>

                  {/* Small Faint Privacy Note */}
                  <p
                    className="text-xs mt-3 leading-normal"
                    style={{ color: theme.textFaint }}
                  >
                    Your information is safe with us. We do not share your data.
                  </p>

                </form>
              )}
            </div>

            {/* RIGHT Column: Stacked Info Cards + Full-Cover Building Map Container (40% width = lg:col-span-5) */}
            <div className="lg:col-span-5 flex flex-col space-y-6">
              
              {/* Card 1: Visit Us */}
              <div
                className="rounded-2xl p-6 border transition-all duration-200 flex items-start gap-4"
                style={{
                  backgroundColor: theme.card,
                  borderColor: theme.border,
                }}
              >
                <div
                  className="w-11 h-11 rounded-full flex items-center justify-center border flex-shrink-0"
                  style={{
                    backgroundColor: theme.greenSoft,
                    borderColor: theme.border,
                    color: theme.green,
                  }}
                >
                  <MapPin className="w-5 h-5 stroke-[2.2]" />
                </div>
                <div>
                  <h4 className="text-base font-bold" style={{ color: theme.text }}>
                    Visit us
                  </h4>
                  <p className="text-sm mt-1 leading-snug" style={{ color: theme.textMuted }}>
                    SOLARA Clean Energy Towers, Plot 42<br />
                    BKC Financial District, Mumbai, MH 400051
                  </p>
                </div>
              </div>

              {/* Card 2: Call Us */}
              <div
                className="rounded-2xl p-6 border transition-all duration-200 flex items-start gap-4"
                style={{
                  backgroundColor: theme.card,
                  borderColor: theme.border,
                }}
              >
                <div
                  className="w-11 h-11 rounded-full flex items-center justify-center border flex-shrink-0"
                  style={{
                    backgroundColor: theme.greenSoft,
                    borderColor: theme.border,
                    color: theme.green,
                  }}
                >
                  <Phone className="w-5 h-5 stroke-[2.2]" />
                </div>
                <div>
                  <h4 className="text-base font-bold" style={{ color: theme.text }}>
                    Call us
                  </h4>
                  <p className="text-sm mt-1 leading-snug" style={{ color: theme.textMuted }}>
                    +91 (022) 5550-1928<br />
                    Mon - Sat: 9:00 AM - 7:00 PM IST
                  </p>
                </div>
              </div>

              {/* Card 3: Email Us */}
              <div
                className="rounded-2xl p-6 border transition-all duration-200 flex items-start gap-4"
                style={{
                  backgroundColor: theme.card,
                  borderColor: theme.border,
                }}
              >
                <div
                  className="w-11 h-11 rounded-full flex items-center justify-center border flex-shrink-0"
                  style={{
                    backgroundColor: theme.greenSoft,
                    borderColor: theme.border,
                    color: theme.green,
                  }}
                >
                  <Mail className="w-5 h-5 stroke-[2.2]" />
                </div>
                <div>
                  <h4 className="text-base font-bold" style={{ color: theme.text }}>
                    Email us
                  </h4>
                  <p className="text-sm mt-1 leading-snug" style={{ color: theme.textMuted }}>
                    contact@solaraenergy.com<br />
                    support@solaraenergy.com
                  </p>
                </div>
              </div>

              {/* Map Container: Full-cover office building photo + floating pill overlay */}
              <div
                className="rounded-2xl border flex-1 min-h-[160px] overflow-hidden relative shadow-sm"
                style={{ borderColor: theme.border }}
              >
                <img
                  src="https://placehold.co/650x240/EFF3EC/1F5C3E?text=SOLARA+Office"
                  alt="SOLARA Regional Office Building"
                  loading="lazy"
                  className="w-full h-full object-cover min-h-[160px]"
                />

                {/* Floating Pill Overlay in Bottom-Left Corner */}
                <div
                  className="absolute bottom-3 left-3 flex items-center gap-1.5 px-3 py-1.5 rounded-full shadow-md text-xs font-semibold border backdrop-blur-sm"
                  style={{
                    backgroundColor: theme.card,
                    color: theme.text,
                    borderColor: theme.border,
                  }}
                >
                  <MapPin className="w-3.5 h-3.5 stroke-[2.2]" style={{ color: theme.green }} />
                  <span>Pune, Maharashtra</span>
                </div>
              </div>

            </div>

          </div>

        </div>
      </section>

      {/* Shared CTA Banner */}
      <CtaBanner theme={theme} />

    </div>
  );
}
