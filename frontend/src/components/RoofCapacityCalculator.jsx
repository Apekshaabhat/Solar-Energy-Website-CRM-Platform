import React, { useState } from "react";
import {
  ArrowRight,
  ShieldCheck,
  LayoutGrid,
  SunMedium,
  Zap,
  Sprout,
  CheckCircle2,
} from "lucide-react";
import Eyebrow from "./Eyebrow";
import { calculatorsApi } from "../api/calculators";

export default function RoofCapacityCalculator(props) {
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

  const [roofArea, setRoofArea] = useState("800");
  const [shading, setShading] = useState("None");
  const [orientation, setOrientation] = useState("South-facing");
  const [calculated, setCalculated] = useState(false);
  const [results, setResults] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleCalculate = async (e) => {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const estimate = await calculatorsApi.estimateRoofCapacity({
        roof_area: Number(roofArea) || 0,
        shading,
        orientation,
      });
      setResults({
        panelCount: estimate.panel_count ?? estimate.panelCount,
        systemSizeKW: estimate.system_size_kw ?? estimate.systemSizeKW,
        annualGeneration: estimate.annual_generation ?? estimate.annualGeneration,
      });
      setCalculated(true);
    } catch (err) {
      setError(err.message || "Unable to calculate roof capacity right now.");
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
          <Eyebrow text="Roof Capacity Calculator" theme={theme} />
          <h1
            className="text-4xl sm:text-5xl lg:text-[54px] font-semibold leading-[1.15] tracking-tight max-w-4xl"
            style={{ color: theme.text }}
          >
            How many panels can your roof actually hold?
          </h1>
          <p
            className="mt-4 text-base sm:text-lg lg:text-xl leading-relaxed max-w-3xl"
            style={{ color: theme.textMuted }}
          >
            Estimate your roof's usable area, maximum solar panel capacity, and annual power generation based on shading and orientation.
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

              {/* Field 1: Total Roof Area */}
              <div className="flex flex-col space-y-2">
                <label
                  className="text-sm font-medium"
                  style={{ color: theme.text }}
                >
                  Total roof area (sq. ft.)
                </label>
                <input
                  type="number"
                  placeholder="e.g. 800"
                  value={roofArea}
                  onChange={(e) => setRoofArea(e.target.value)}
                  required
                  min="50"
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

              {/* Field 2: Shading Level Toggle */}
              <div className="flex flex-col space-y-2">
                <label
                  className="text-sm font-medium"
                  style={{ color: theme.text }}
                >
                  Shading level
                </label>
                <div className="grid grid-cols-3 gap-3">
                  {["None", "Partial", "Heavy"].map((level) => {
                    const isActive = shading === level;
                    return (
                      <button
                        key={level}
                        type="button"
                        onClick={() => setShading(level)}
                        className="py-3 px-3 rounded-xl border text-sm font-medium transition-all duration-200 focus:outline-none text-center cursor-pointer"
                        style={{
                          backgroundColor: isActive ? theme.greenSoft : theme.input,
                          borderColor: isActive ? theme.green : theme.border,
                          color: isActive ? theme.green : theme.textMuted,
                        }}
                      >
                        {level}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Field 3: Roof Orientation Toggle */}
              <div className="flex flex-col space-y-2">
                <label
                  className="text-sm font-medium"
                  style={{ color: theme.text }}
                >
                  Roof orientation
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {["South-facing", "East/West-facing", "North-facing"].map(
                    (dir) => {
                      const isActive = orientation === dir;
                      return (
                        <button
                          key={dir}
                          type="button"
                          onClick={() => setOrientation(dir)}
                          className="py-3 px-3 rounded-xl border text-sm font-medium transition-all duration-200 focus:outline-none text-center cursor-pointer"
                          style={{
                            backgroundColor: isActive ? theme.greenSoft : theme.input,
                            borderColor: isActive ? theme.green : theme.border,
                            color: isActive ? theme.green : theme.textMuted,
                          }}
                        >
                          {dir}
                        </button>
                      );
                    }
                  )}
                </div>
              </div>

              {/* Calculate Button */}
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
                <span>{isSubmitting ? "Calculating..." : "Calculate Roof Capacity"}</span>
                <ArrowRight className="w-5 h-5" />
              </button>

              {/* Trust Badge */}
              <div
                className="flex items-center justify-center gap-2 text-xs sm:text-sm pt-1"
                style={{ color: theme.textFaint }}
              >
                <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>
                  Estimate only — a site survey confirms the exact layout.
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
                <div className="w-12 h-12 rounded-2xl flex items-center justify-center mb-6" style={{ backgroundColor: theme.greenSoft, color: theme.green }}>
                  <Sprout className="w-6 h-6" />
                </div>

                <h3
                  className="text-2xl font-semibold tracking-tight"
                  style={{ color: theme.text }}
                >
                  Why this matters
                </h3>
                <p
                  className="mt-3 text-sm sm:text-base leading-relaxed"
                  style={{ color: theme.textMuted }}
                >
                  Roof orientation and tree/building shading can reduce your usable rooftop solar capacity by up to 45%. Knowing your true available space ensures you don't over-purchase panels.
                </p>

                <ul
                  className="mt-6 space-y-3 text-sm font-medium"
                  style={{ color: theme.text }}
                >
                  {[
                    "Optimized panel tilt & layout",
                    "Shading loss compensation",
                    "High-efficiency 400W+ module rating",
                    "Free structural feasibility check",
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
                      Your Roof's Potential
                    </h3>
                  </div>
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center text-white"
                    style={{ backgroundColor: theme.green }}
                  >
                    <LayoutGrid className="w-5 h-5" />
                  </div>
                </div>

                {/* 3 Stacked Result Boxes */}
                <div className="space-y-3">
                  {/* Box 1: Panel Count */}
                  <div
                    className="p-4 rounded-2xl border shadow-sm flex items-center justify-between"
                    style={{
                      backgroundColor: theme.card,
                      borderColor: theme.border,
                    }}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className="w-9 h-9 rounded-xl flex items-center justify-center"
                        style={{
                          backgroundColor: theme.greenSoft,
                          color: theme.green,
                        }}
                      >
                        <LayoutGrid className="w-5 h-5" />
                      </div>
                      <span
                        className="text-sm font-medium"
                        style={{ color: theme.textMuted }}
                      >
                        Max Solar Panels
                      </span>
                    </div>
                    <div
                      className="text-2xl font-bold tracking-tight"
                      style={{ color: theme.text }}
                    >
                      {results.panelCount} <span className="text-xs font-normal text-gray-500">panels</span>
                    </div>
                  </div>

                  {/* Box 2: System Size */}
                  <div
                    className="p-4 rounded-2xl border shadow-sm flex items-center justify-between"
                    style={{
                      backgroundColor: theme.card,
                      borderColor: theme.border,
                    }}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className="w-9 h-9 rounded-xl flex items-center justify-center"
                        style={{
                          backgroundColor: theme.greenSoft,
                          color: theme.green,
                        }}
                      >
                        <SunMedium className="w-5 h-5" />
                      </div>
                      <span
                        className="text-sm font-medium"
                        style={{ color: theme.textMuted }}
                      >
                        System Capacity
                      </span>
                    </div>
                    <div
                      className="text-2xl font-bold tracking-tight"
                      style={{ color: theme.text }}
                    >
                      {results.systemSizeKW} <span className="text-xs font-normal text-gray-500">kW</span>
                    </div>
                  </div>

                  {/* Box 3: Annual Generation */}
                  <div
                    className="p-4 rounded-2xl border shadow-sm flex items-center justify-between"
                    style={{
                      backgroundColor: theme.card,
                      borderColor: theme.border,
                    }}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className="w-9 h-9 rounded-xl flex items-center justify-center"
                        style={{
                          backgroundColor: theme.greenSoft,
                          color: theme.green,
                        }}
                      >
                        <Zap className="w-5 h-5" />
                      </div>
                      <span
                        className="text-sm font-medium"
                        style={{ color: theme.textMuted }}
                      >
                        Annual Generation
                      </span>
                    </div>
                    <div
                      className="text-2xl font-bold tracking-tight"
                      style={{ color: theme.text }}
                    >
                      {results.annualGeneration.toLocaleString("en-IN")}{" "}
                      <span className="text-xs font-normal text-gray-500">kWh</span>
                    </div>
                  </div>
                </div>

                {/* Disclaimer */}
                <p
                  className="mt-6 text-xs leading-relaxed"
                  style={{ color: theme.textMuted }}
                >
                  Calculations assume high-efficiency 400W mono-PERC panels. Book a site inspection for detailed engineering blueprints.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
