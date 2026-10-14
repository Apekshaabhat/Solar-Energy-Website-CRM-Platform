import React, { useState, useEffect, useCallback } from "react";
import {
  Settings2,
  Search,
  Eye,
  Trash2,
  SunMedium,
  Zap,
  Clock,
  Sprout,
  X,
  Calculator,
  TrendingUp,
} from "lucide-react";
import { calculatorsApi } from "../../api/calculators";

function getPropertyTypeBadge(type) {
  switch (type) {
    case "Residential":
      return "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800/50";
    case "Commercial":
      return "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800/50";
    case "Industrial":
      return "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950/60 dark:text-purple-300 dark:border-purple-800/50";
    default:
      return "bg-gray-50 text-gray-700 border-gray-200 dark:bg-gray-900 dark:text-gray-300 dark:border-gray-800";
  }
}

export default function Calculators() {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [propertyFilter, setPropertyFilter] = useState("All");

  const [selectedSubmission, setSelectedSubmission] = useState(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const [settings, setSettings] = useState({
    electricityRate: 8,
    generationPerKW: 120,
    installationCostPerKW: 55000,
    billOffsetPercent: 85,
  });

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [subRes, setRes] = await Promise.all([
        calculatorsApi.getSubmissions({
          search: searchQuery.trim() || undefined,
          calculator_type: propertyFilter !== "All" ? propertyFilter : undefined,
        }),
        calculatorsApi.getSettings().catch(() => null),
      ]);

      const items = Array.isArray(subRes) ? subRes : subRes?.items || [];
      setSubmissions(items);

      if (setRes) {
        setSettings({
          electricityRate: setRes.electricity_rate ?? setRes.electricityRate ?? 8,
          generationPerKW: setRes.generation_per_kw ?? setRes.generationPerKW ?? 120,
          installationCostPerKW: setRes.installation_cost_per_kw ?? setRes.installationCostPerKW ?? 55000,
          billOffsetPercent: setRes.bill_offset_percent ?? setRes.billOffsetPercent ?? 85,
        });
      }
    } catch (err) {
      setError(err.message || "Failed to load calculator submissions.");
    } finally {
      setLoading(false);
    }
  }, [searchQuery, propertyFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const totalSubmissions = submissions.length;
  const avgSystemSize =
    totalSubmissions > 0
      ? (
          submissions.reduce(
            (acc, curr) => acc + (curr.system_size_kw || curr.systemSizeKW || 0),
            0
          ) / totalSubmissions
        ).toFixed(1)
      : "0.0";

  const avgAnnualSavings =
    totalSubmissions > 0
      ? Math.round(
          submissions.reduce(
            (acc, curr) => acc + (curr.annual_savings || curr.annualSavings || 0),
            0
          ) / totalSubmissions
        )
      : 0;

  const handleSaveSettings = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await calculatorsApi.updateSettings({
        electricity_rate: Number(settings.electricityRate),
        generation_per_kw: Number(settings.generationPerKW),
        installation_cost_per_kw: Number(settings.installationCostPerKW),
        bill_offset_percent: Number(settings.billOffsetPercent),
      });
      setIsSettingsOpen(false);
    } catch (err) {
      setError(err.message || "Failed to update calculator settings.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white tracking-tight">
            Calculators
          </h1>
          <p className="text-sm sm:text-base text-gray-500 dark:text-gray-400 mt-1">
            Savings estimates submitted through the public calculator.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setIsSettingsOpen(true)}
          className="inline-flex items-center gap-2 border border-[#1F5C3E] text-[#1F5C3E] dark:border-[#4ADE80] dark:text-[#4ADE80] hover:bg-[#1F5C3E]/10 px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors cursor-pointer self-start sm:self-auto"
        >
          <Settings2 className="w-4 h-4" />
          <span>Calculation Settings</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/20 border border-red-200 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-2xl p-4 sm:p-5 shadow-sm">
          <div className="flex items-center justify-between text-gray-500 dark:text-gray-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">
              Total Submissions
            </span>
            <div className="w-8 h-8 rounded-full bg-[#EFF3EC] dark:bg-[#1C2A21] text-[#1F5C3E] dark:text-[#4ADE80] flex items-center justify-center">
              <Calculator className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">
            {totalSubmissions}
          </p>
        </div>

        <div className="bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-2xl p-4 sm:p-5 shadow-sm">
          <div className="flex items-center justify-between text-gray-500 dark:text-gray-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">
              Avg System Size
            </span>
            <div className="w-8 h-8 rounded-full bg-[#EFF3EC] dark:bg-[#1C2A21] text-[#1F5C3E] dark:text-[#4ADE80] flex items-center justify-center">
              <SunMedium className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">
            {avgSystemSize} <span className="text-sm font-normal text-gray-500 dark:text-gray-400">kW</span>
          </p>
        </div>

        <div className="bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-2xl p-4 sm:p-5 shadow-sm">
          <div className="flex items-center justify-between text-gray-500 dark:text-gray-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">
              Avg Annual Savings
            </span>
            <div className="w-8 h-8 rounded-full bg-[#EFF3EC] dark:bg-[#1C2A21] text-[#1F5C3E] dark:text-[#4ADE80] flex items-center justify-center">
              <Zap className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">
            ₹{avgAnnualSavings.toLocaleString("en-IN")}
          </p>
        </div>

        <div className="bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-2xl p-4 sm:p-5 shadow-sm">
          <div className="flex items-center justify-between text-gray-500 dark:text-gray-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">
              Recent Activity
            </span>
            <div className="w-8 h-8 rounded-full bg-[#EFF3EC] dark:bg-[#1C2A21] text-[#1F5C3E] dark:text-[#4ADE80] flex items-center justify-center">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">
            {totalSubmissions}
          </p>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500 pointer-events-none" />
          <input
            type="text"
            placeholder="Search by name or phone..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-xl text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30 transition-colors"
          />
        </div>

        <div className="w-full sm:w-56">
          <select
            value={propertyFilter}
            onChange={(e) => setPropertyFilter(e.target.value)}
            className="w-full px-3.5 py-2.5 bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-xl text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30 transition-colors cursor-pointer"
          >
            <option value="All">All Property Types</option>
            <option value="Residential">Residential</option>
            <option value="Commercial">Commercial</option>
            <option value="Industrial">Industrial</option>
          </select>
        </div>
      </div>

      <div className="bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-2xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto no-scrollbar">
          <table className="w-full text-left text-sm border-collapse min-w-[720px]">
            <thead>
              <tr className="bg-gray-50/80 dark:bg-[#0E1712]/80 border-b border-gray-200 dark:border-[#293227] text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <th className="py-3.5 px-5">Name</th>
                <th className="py-3.5 px-4">Phone / Contact</th>
                <th className="py-3.5 px-4">Property Type</th>
                <th className="py-3.5 px-4">Monthly Bill</th>
                <th className="py-3.5 px-4">System Size</th>
                <th className="py-3.5 px-4">Date</th>
                <th className="py-3.5 px-5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-[#293227]/60 text-gray-800 dark:text-gray-200">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-gray-500 text-sm">
                    Loading submissions...
                  </td>
                </tr>
              ) : submissions.length > 0 ? (
                submissions.map((sub) => {
                  const pType = sub.property_type || sub.propertyType || "Residential";
                  const bill = sub.monthly_bill ?? sub.monthlyBill ?? 0;
                  const kw = sub.system_size_kw ?? sub.systemSizeKW ?? 0;
                  const dt = sub.created_at ? new Date(sub.created_at).toLocaleDateString() : (sub.date || "—");

                  return (
                    <tr key={sub.id} className="hover:bg-gray-50/70 dark:hover:bg-[#152019]/60 transition-colors">
                      <td className="py-3.5 px-5 font-semibold text-gray-900 dark:text-white">
                        {sub.name || sub.customer_name || "Lead Submission"}
                      </td>
                      <td className="py-3.5 px-4 text-gray-600 dark:text-gray-300">
                        {sub.phone || sub.contact || "—"}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${getPropertyTypeBadge(pType)}`}>
                          {pType}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-gray-900 dark:text-white font-medium">
                        ₹{Number(bill).toLocaleString("en-IN")}
                      </td>
                      <td className="py-3.5 px-4 text-gray-900 dark:text-white font-medium">
                        {kw} kW
                      </td>
                      <td className="py-3.5 px-4 text-gray-500 dark:text-gray-400 text-xs">
                        {dt}
                      </td>
                      <td className="py-3.5 px-5 text-right">
                        <button
                          type="button"
                          onClick={() => setSelectedSubmission(sub)}
                          title="View Submission Details"
                          className="p-1.5 text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white rounded-lg hover:bg-gray-100 dark:hover:bg-[#293227] transition-colors cursor-pointer"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-gray-500 dark:text-gray-400 text-sm">
                    No submissions found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {selectedSubmission && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-2xl p-6 w-full max-w-lg shadow-2xl space-y-6">
            <div className="flex items-start justify-between border-b border-gray-100 dark:border-[#293227] pb-4">
              <div>
                <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                  {selectedSubmission.name || "Calculator Submission"}
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${getPropertyTypeBadge(selectedSubmission.property_type || selectedSubmission.propertyType || "Residential")}`}>
                    {selectedSubmission.property_type || selectedSubmission.propertyType || "Residential"}
                  </span>
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Contact: {selectedSubmission.phone || selectedSubmission.contact || "—"}
                </p>
              </div>

              <button
                type="button"
                onClick={() => setSelectedSubmission(null)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 p-1 rounded-lg transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3.5">
              <div className="bg-[#EFF3EC] dark:bg-[#1C2A21] border border-[#1F5C3E]/20 dark:border-[#4ADE80]/20 rounded-xl p-3.5">
                <div className="flex items-center gap-2 text-xs font-semibold text-[#1F5C3E] dark:text-[#4ADE80] mb-1">
                  <SunMedium className="w-4 h-4" />
                  <span>Recommended System</span>
                </div>
                <p className="text-lg font-bold text-gray-900 dark:text-white">
                  {selectedSubmission.system_size_kw || selectedSubmission.systemSizeKW || 0} kW
                </p>
              </div>

              <div className="bg-[#EFF3EC] dark:bg-[#1C2A21] border border-[#1F5C3E]/20 dark:border-[#4ADE80]/20 rounded-xl p-3.5">
                <div className="flex items-center gap-2 text-xs font-semibold text-[#1F5C3E] dark:text-[#4ADE80] mb-1">
                  <Zap className="w-4 h-4" />
                  <span>Annual Savings</span>
                </div>
                <p className="text-lg font-bold text-gray-900 dark:text-white">
                  ₹{Number(selectedSubmission.annual_savings || selectedSubmission.annualSavings || 0).toLocaleString("en-IN")}
                </p>
              </div>

              <div className="bg-[#EFF3EC] dark:bg-[#1C2A21] border border-[#1F5C3E]/20 dark:border-[#4ADE80]/20 rounded-xl p-3.5">
                <div className="flex items-center gap-2 text-xs font-semibold text-[#1F5C3E] dark:text-[#4ADE80] mb-1">
                  <Clock className="w-4 h-4" />
                  <span>Payback Period</span>
                </div>
                <p className="text-lg font-bold text-gray-900 dark:text-white">
                  {((selectedSubmission.payback_period_years || selectedSubmission.paybackPeriodYears) ?? 4.5)} yrs
                </p>
              </div>

              <div className="bg-[#EFF3EC] dark:bg-[#1C2A21] border border-[#1F5C3E]/20 dark:border-[#4ADE80]/20 rounded-xl p-3.5">
                <div className="flex items-center gap-2 text-xs font-semibold text-[#1F5C3E] dark:text-[#4ADE80] mb-1">
                  <Sprout className="w-4 h-4" />
                  <span>CO₂ Offset / yr</span>
                </div>
                <p className="text-lg font-bold text-gray-900 dark:text-white">
                  {((selectedSubmission.system_size_kw || selectedSubmission.systemSizeKW || 0) * 1.2).toFixed(1)} tons
                </p>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => setSelectedSubmission(null)}
                className="bg-[#1F5C3E] hover:bg-[#184931] text-white text-sm font-medium rounded-xl px-5 py-2.5 transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {isSettingsOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-2xl p-6 w-full max-w-md shadow-2xl space-y-5">
            <div className="flex items-start justify-between border-b border-gray-100 dark:border-[#293227] pb-3">
              <div>
                <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                  Calculation Settings
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                  These values control how the public calculator estimates savings.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsSettingsOpen(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 p-1 rounded-lg transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveSettings} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                  Electricity Rate (₹ / unit)
                </label>
                <input
                  type="number"
                  min="1"
                  step="0.5"
                  value={settings.electricityRate}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      electricityRate: parseFloat(e.target.value) || 0,
                    })
                  }
                  className="w-full px-3.5 py-2.5 bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] rounded-xl text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                  Generation per kW (units / month)
                </label>
                <input
                  type="number"
                  min="1"
                  value={settings.generationPerKW}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      generationPerKW: parseInt(e.target.value, 10) || 0,
                    })
                  }
                  className="w-full px-3.5 py-2.5 bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] rounded-xl text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                  Installation Cost per kW (₹)
                </label>
                <input
                  type="number"
                  min="1000"
                  step="1000"
                  value={settings.installationCostPerKW}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      installationCostPerKW: parseInt(e.target.value, 10) || 0,
                    })
                  }
                  className="w-full px-3.5 py-2.5 bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] rounded-xl text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                  Bill Offset (%)
                </label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={settings.billOffsetPercent}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      billOffsetPercent: parseInt(e.target.value, 10) || 0,
                    })
                  }
                  className="w-full px-3.5 py-2.5 bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] rounded-xl text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-100 dark:border-[#293227]">
                <button
                  type="button"
                  onClick={() => setIsSettingsOpen(false)}
                  className="px-4 py-2.5 text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-[#293227] rounded-xl transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="bg-[#1F5C3E] hover:bg-[#184931] text-white text-sm font-medium rounded-xl px-4 py-2.5 transition-colors shadow-sm cursor-pointer disabled:opacity-60"
                >
                  {saving ? "Saving..." : "Save Settings"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
