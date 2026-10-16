import React, { useState, useEffect } from "react";
import {
  Building2,
  Bell,
  Lock,
  Palette,
  Mail,
  MessageSquare,
  Zap,
  Shield,
  CheckCircle2,
  RefreshCw,
  AlertCircle,
  X,
} from "lucide-react";
import { settingsService } from "../../services/settingsService";
import { useAuth } from "../../context/AuthContext";

// Reusable toggle row component
function ToggleRow({ icon: Icon, title, desc, checked, onChange, disabled }) {
  return (
    <div className={`flex items-center justify-between py-3.5 border-b border-gray-100 dark:border-[#293227] last:border-0 ${disabled ? "opacity-60" : ""}`}>
      <div className="flex items-start gap-3.5 pr-4">
        {Icon && (
          <div className="w-9 h-9 rounded-full bg-[#EFF3EC] dark:bg-[#1C2A21] text-[#1F5C3E] dark:text-[#4ADE80] flex items-center justify-center shrink-0 mt-0.5">
            <Icon className="w-4.5 h-4.5" />
          </div>
        )}
        <div>
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white">{title}</h4>
          {desc && <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 leading-relaxed">{desc}</p>}
        </div>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => !disabled && onChange(!checked)}
        className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/40 ${
          checked ? "bg-[#1F5C3E]" : "bg-gray-200 dark:bg-[#293227]"
        } ${disabled ? "cursor-not-allowed" : ""}`}
      >
        <span
          className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out ${
            checked ? "translate-x-5" : "translate-x-0"
          }`}
        />
      </button>
    </div>
  );
}

export default function Settings() {
  const { isAdmin, isManager } = useAuth();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const [settings, setSettings] = useState({
    companyName: "SOLARA Energy Solutions",
    supportEmail: "support@solara.com",
    emailNotifications: true,
    smsNotifications: false,
    leadAlerts: true,
    twoFactorAuth: false,
  });

  useEffect(() => {
    async function fetchSettings() {
      setLoading(true);
      setErrorMsg("");
      try {
        const data = await settingsService.getSettings();
        if (data) {
          setSettings({
            companyName: data.companyName ?? "SOLARA Energy Solutions",
            supportEmail: data.supportEmail ?? "support@solara.com",
            emailNotifications: Boolean(data.emailNotifications),
            smsNotifications: Boolean(data.smsNotifications),
            leadAlerts: Boolean(data.leadAlerts),
            twoFactorAuth: Boolean(data.twoFactorAuth),
          });
        }
      } catch (err) {
        setErrorMsg(err.message || "Failed to load system settings.");
      } finally {
        setLoading(false);
      }
    }
    fetchSettings();
  }, []);

  useEffect(() => {
    if (successMsg) {
      const timer = setTimeout(() => setSuccessMsg(""), 4000);
      return () => clearTimeout(timer);
    }
  }, [successMsg]);

  const handleSaveAll = async (e) => {
    if (e) e.preventDefault();
    setSaving(true);
    setErrorMsg("");
    setSuccessMsg("");

    try {
      const updated = await settingsService.updateSettings(settings);
      setSettings((prev) => ({ ...prev, ...updated }));
      setSuccessMsg("Settings saved and persisted successfully.");
    } catch (err) {
      setErrorMsg(err.message || "Failed to persist settings.");
    } finally {
      setSaving(false);
    }
  };

  const updateSettingField = async (field, value) => {
    const updated = { ...settings, [field]: value };
    setSettings(updated);
    setSaving(true);
    try {
      await settingsService.updateSettings(updated);
      setSuccessMsg("Setting preference updated.");
    } catch (err) {
      setErrorMsg(err.message || "Failed to update preference.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="flex items-center gap-2 text-stone-500">
          <RefreshCw className="w-5 h-5 animate-spin text-[#1F5C3E]" />
          <span>Loading system preferences...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white tracking-tight">
            Settings
          </h1>
          <p className="text-sm sm:text-base text-gray-500 dark:text-gray-400 mt-1">
            Configure workspace preferences, communication alerts, and security policies.
          </p>
        </div>
        <button
          type="button"
          onClick={() => handleSaveAll()}
          disabled={saving}
          className="bg-[#1F5C3E] hover:bg-[#184931] text-white text-sm font-medium rounded-xl px-5 py-2.5 transition shadow-sm cursor-pointer disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save All Changes"}
        </button>
      </div>

      {/* Notifications */}
      {errorMsg && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/50 text-red-700 dark:text-red-300 text-sm">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <p className="flex-1 font-medium">{errorMsg}</p>
          <button onClick={() => setErrorMsg("")} className="text-red-500 hover:text-red-700 p-1">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {successMsg && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900/50 text-[#1F5C3E] dark:text-emerald-300 text-sm">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <p className="flex-1 font-medium">{successMsg}</p>
          <button onClick={() => setSuccessMsg("")} className="text-emerald-600 hover:text-emerald-800 p-1">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Cards Stack */}
      <div className="space-y-6">
        {/* Card 1: Company Information */}
        <div className="bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-2xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-5 border-b border-gray-100 dark:border-[#293227] pb-4">
            <div className="w-9 h-9 rounded-full bg-[#EFF3EC] dark:bg-[#1C2A21] text-[#1F5C3E] dark:text-[#4ADE80] flex items-center justify-center shrink-0">
              <Building2 className="w-4.5 h-4.5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                Company Information
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Update your organization details and contact email.
              </p>
            </div>
          </div>

          <form onSubmit={handleSaveAll} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                  Company Name
                </label>
                <input
                  type="text"
                  disabled={!isAdmin}
                  value={settings.companyName}
                  onChange={(e) => setSettings({ ...settings, companyName: e.target.value })}
                  className="w-full px-3.5 py-2.5 bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] rounded-xl text-sm text-gray-900 dark:text-white disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30 focus:border-[#1F5C3E]"
                />
                {!isAdmin && (
                  <p className="text-[11px] text-gray-400 mt-1">Admin access required to change company name.</p>
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                  Support Email
                </label>
                <input
                  type="email"
                  disabled={!isAdmin}
                  value={settings.supportEmail}
                  onChange={(e) => setSettings({ ...settings, supportEmail: e.target.value })}
                  className="w-full px-3.5 py-2.5 bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] rounded-xl text-sm text-gray-900 dark:text-white disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30 focus:border-[#1F5C3E]"
                />
              </div>
            </div>

            {isAdmin && (
              <div className="flex items-center gap-3 pt-2">
                <button
                  type="submit"
                  disabled={saving}
                  className="bg-[#1F5C3E] hover:bg-[#184931] text-white text-sm font-medium rounded-xl px-4 py-2.5 transition shadow-sm cursor-pointer"
                >
                  {saving ? "Saving..." : "Save Company Info"}
                </button>
              </div>
            )}
          </form>
        </div>

        {/* Card 2: Notifications */}
        <div className="bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-2xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4 border-b border-gray-100 dark:border-[#293227] pb-4">
            <div className="w-9 h-9 rounded-full bg-[#EFF3EC] dark:bg-[#1C2A21] text-[#1F5C3E] dark:text-[#4ADE80] flex items-center justify-center shrink-0">
              <Bell className="w-4.5 h-4.5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                Notifications
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Configure system alerts and communication preferences.
              </p>
            </div>
          </div>

          <div className="space-y-1">
            <ToggleRow
              icon={Mail}
              title="Email notifications"
              desc="Receive daily activity summaries and administrative updates via email."
              checked={settings.emailNotifications}
              onChange={(val) => updateSettingField("emailNotifications", val)}
            />
            <ToggleRow
              icon={MessageSquare}
              title="SMS notifications"
              desc="Receive instant text messages for high-priority system events."
              checked={settings.smsNotifications}
              onChange={(val) => updateSettingField("smsNotifications", val)}
            />
            <ToggleRow
              icon={Zap}
              title="New lead alerts"
              desc="Get notified immediately when a new solar lead is submitted or assigned."
              checked={settings.leadAlerts}
              onChange={(val) => updateSettingField("leadAlerts", val)}
            />
          </div>
        </div>

        {/* Card 3: Security */}
        <div className="bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-2xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4 border-b border-gray-100 dark:border-[#293227] pb-4">
            <div className="w-9 h-9 rounded-full bg-[#EFF3EC] dark:bg-[#1C2A21] text-[#1F5C3E] dark:text-[#4ADE80] flex items-center justify-center shrink-0">
              <Lock className="w-4.5 h-4.5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                Security & Authentication Policies
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Manage global authentication protocols and security policies.
              </p>
            </div>
          </div>

          <ToggleRow
            icon={Shield}
            title="Two-factor authentication"
            desc="Enforce multi-factor verification across user sessions (Admin only)."
            checked={settings.twoFactorAuth}
            disabled={!isAdmin}
            onChange={(val) => updateSettingField("twoFactorAuth", val)}
          />
        </div>

        {/* Card 4: Appearance */}
        <div className="bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-2xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-9 h-9 rounded-full bg-[#EFF3EC] dark:bg-[#1C2A21] text-[#1F5C3E] dark:text-[#4ADE80] flex items-center justify-center shrink-0">
              <Palette className="w-4.5 h-4.5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                Appearance
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Customize the look and feel of your dashboard environment.
              </p>
            </div>
          </div>

          <div className="mt-4 p-4 rounded-xl bg-gray-50 dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] text-xs text-gray-600 dark:text-gray-300 leading-relaxed">
            Light and dark themes are managed per user and can be switched dynamically using the sun/moon button in the top navigation bar.
          </div>
        </div>
      </div>
    </div>
  );
}
