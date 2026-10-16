import React, { useState, useEffect } from "react";
import {
  Building2,
  Bell,
  Lock,
  Mail,
  MessageSquare,
  Zap,
  Shield,
  CheckCircle2,
} from "lucide-react";
import { settingsApi } from "../../api/settings";

function ToggleRow({ icon: Icon, title, desc, checked, onChange }) {
  return (
    <div className="flex items-center justify-between py-3.5 border-b border-gray-100 dark:border-[#293227] last:border-0">
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
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/40 ${
          checked ? "bg-[#1F5C3E]" : "bg-gray-200 dark:bg-[#293227]"
        }`}
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
  const [companyInfo, setCompanyInfo] = useState({
    name: "SOLARA Energy Solutions",
    supportEmail: "support@solara.com",
  });
  const [notifications, setNotifications] = useState({
    email: true,
    sms: false,
    leadAlerts: true,
  });
  const [twoFactor, setTwoFactor] = useState(false);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchSettings() {
      setLoading(true);
      try {
        const data = await settingsApi.getSettings();
        if (data) {
          setCompanyInfo({
            name: data.company_name || data.companyName || "SOLARA Energy Solutions",
            supportEmail: data.support_email || data.supportEmail || "support@solara.com",
          });
          setNotifications({
            email: data.email_notifications ?? data.emailNotifications ?? true,
            sms: data.sms_notifications ?? data.smsNotifications ?? false,
            leadAlerts: data.lead_alerts ?? data.leadAlerts ?? true,
          });
          setTwoFactor(data.two_factor_auth ?? data.twoFactorAuth ?? false);
        }
      } catch (err) {
        setError(err.message || "Failed to load system settings.");
      } finally {
        setLoading(false);
      }
    }
    fetchSettings();
  }, []);

  const handleSave = async (e) => {
    if (e) e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await settingsApi.updateSettings({
        company_name: companyInfo.name,
        support_email: companyInfo.supportEmail,
        email_notifications: notifications.email,
        sms_notifications: notifications.sms,
        lead_alerts: notifications.leadAlerts,
        two_factor_auth: twoFactor,
      });
      setNotice(true);
      setTimeout(() => setNotice(false), 3000);
    } catch (err) {
      setError(err.message || "Failed to save settings.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white tracking-tight">
          Settings
        </h1>
        <p className="text-sm sm:text-base text-gray-500 dark:text-gray-400 mt-1">
          Configure your workspace preferences and system parameters.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/20 border border-red-200 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {loading ? (
        <div className="p-12 text-center text-sm text-gray-500">Loading settings...</div>
      ) : (
        <div className="space-y-6">
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

            <form onSubmit={handleSave} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                    Company Name
                  </label>
                  <input
                    type="text"
                    value={companyInfo.name}
                    onChange={(e) => setCompanyInfo({ ...companyInfo, name: e.target.value })}
                    className="w-full px-3.5 py-2.5 bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] rounded-xl text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                    Support Email
                  </label>
                  <input
                    type="email"
                    value={companyInfo.supportEmail}
                    onChange={(e) => setCompanyInfo({ ...companyInfo, supportEmail: e.target.value })}
                    className="w-full px-3.5 py-2.5 bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] rounded-xl text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30"
                  />
                </div>
              </div>

              <div className="flex items-center gap-3 pt-2">
                <button
                  type="submit"
                  disabled={saving}
                  className="bg-[#1F5C3E] hover:bg-[#184931] text-white text-sm font-medium rounded-xl px-4 py-2.5 transition-colors shadow-sm cursor-pointer disabled:opacity-60"
                >
                  {saving ? "Saving..." : "Save Changes"}
                </button>
                {notice && (
                  <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 className="w-4 h-4" />
                    Settings saved successfully!
                  </span>
                )}
              </div>
            </form>
          </div>

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
                checked={notifications.email}
                onChange={(val) => {
                  setNotifications((prev) => ({ ...prev, email: val }));
                }}
              />
              <ToggleRow
                icon={MessageSquare}
                title="SMS notifications"
                desc="Receive instant text messages for high-priority system events."
                checked={notifications.sms}
                onChange={(val) => {
                  setNotifications((prev) => ({ ...prev, sms: val }));
                }}
              />
              <ToggleRow
                icon={Zap}
                title="New lead alerts"
                desc="Get notified immediately when a new solar lead is submitted or assigned."
                checked={notifications.leadAlerts}
                onChange={(val) => {
                  setNotifications((prev) => ({ ...prev, leadAlerts: val }));
                }}
              />
            </div>
          </div>

          <div className="bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-2xl p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-4 border-b border-gray-100 dark:border-[#293227] pb-4">
              <div className="w-9 h-9 rounded-full bg-[#EFF3EC] dark:bg-[#1C2A21] text-[#1F5C3E] dark:text-[#4ADE80] flex items-center justify-center shrink-0">
                <Lock className="w-4.5 h-4.5" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                  Security
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Manage authentication protocols and access protection.
                </p>
              </div>
            </div>

            <ToggleRow
              icon={Shield}
              title="Two-factor authentication"
              desc="Require an authentication code from an authenticator app when logging in."
              checked={twoFactor}
              onChange={(val) => setTwoFactor(val)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
