import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Download, MoreVertical, Pencil, CheckCircle2, UserCheck, Play, XCircle, AlertCircle } from "lucide-react";
import PageHeader from "../../components/dashboard/PageHeader";
import Tabs from "../../components/dashboard/Tabs";
import FilterBar from "../../components/dashboard/FilterBar";
import StatusBadge from "../../components/dashboard/StatusBadge";
import Pagination from "../../components/dashboard/Pagination";
import Modal from "../../components/dashboard/Modal";
import { FormField, TextInput, SelectInput } from "../../components/dashboard/FormField";
import { surveyTabOrder } from "../../data/dashboardData";
import { todayISO } from "../../utils/dashboardDate";
import { surveyService } from "../../services/surveyService";
import { useDashboardData } from "../../context/DashboardDataContext";

const tabFilterMap = {
  "All Surveys": null,
  Scheduled: "Scheduled",
  "In Progress": "In Progress",
  Completed: "Completed",
  Cancelled: "Cancelled",
};

const timeSlots = [
  "09:00 AM",
  "10:00 AM",
  "10:30 AM",
  "11:00 AM",
  "11:30 AM",
  "01:00 PM",
  "02:00 PM",
  "03:00 PM",
  "04:00 PM",
];

const surveyors = ["Rahul", "Priya", "Karan", "Neha"];

const emptyForm = {
  customerId: "",
  customerName: "",
  location: "",
  propertyType: "Residential",
  surveyDate: todayISO(),
  timeSlot: timeSlots[0],
  assignedTo: surveyors[0],
  status: "Scheduled",
  roofInformation: "",
  capacityEstimate: "",
  notes: "",
};

export default function SiteSurveys() {
  const navigate = useNavigate();
  const { refreshToken, notifyCrmChange } = useDashboardData();
  const [surveys, setSurveys] = useState([]);
  const [tabCounts, setTabCounts] = useState({});
  const [activeTab, setActiveTab] = useState("All Surveys");
  const [searchValue, setSearchValue] = useState("");
  const [statusFilter, setStatusFilter] = useState("All Status");
  const [surveyorFilter, setSurveyorFilter] = useState("All Surveyors");
  const [propertyFilter, setPropertyFilter] = useState("All Property Types");

  // Edit details modal state
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingSurvey, setEditingSurvey] = useState(null);
  const [form, setForm] = useState(emptyForm);

  // Complete Survey Modal state
  const [completeModalOpen, setCompleteModalOpen] = useState(false);
  const [completingSurvey, setCompletingSurvey] = useState(null);
  const [completeForm, setCompleteForm] = useState({
    roofInformation: "",
    capacityEstimate: "",
    notes: "",
  });

  const [openMenuId, setOpenMenuId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState("");
  const [message, setMessage] = useState("");
  const [loadError, setLoadError] = useState("");

  const tabs = useMemo(
    () =>
      surveyTabOrder.map((label) => ({
        label,
        count: tabCounts[label] ?? 0,
      })),
    [tabCounts]
  );

  async function loadSurveys() {
    setLoading(true);
    setLoadError("");

    try {
      const params = {};
      const trimmedSearch = searchValue.trim();
      if (trimmedSearch) params.search = trimmedSearch;
      if (statusFilter && statusFilter !== "All Status" && statusFilter !== "All Statuses") {
        params.status = statusFilter;
      } else if (tabFilterMap[activeTab]) {
        params.status = tabFilterMap[activeTab];
      }
      if (surveyorFilter && surveyorFilter !== "All Surveyors") params.surveyor = surveyorFilter;
      if (propertyFilter && propertyFilter !== "All Property Types") params.property_type = propertyFilter;

      const response = await surveyService.getSurveys(params);
      const items = Array.isArray(response.items) ? response.items : [];
      setSurveys(items);
      setTabCounts(response.tabCounts ?? response.tab_counts ?? {});
    } catch (err) {
      setSurveys([]);
      setTabCounts({});
      setLoadError(err.message || "Unable to load site surveys.");
    } finally {
      setLoading(false);
    }
  }

  async function handleExport() {
    setExporting(true);
    setExportError("");
    try {
      const params = {};
      const trimmedSearch = searchValue.trim();
      if (trimmedSearch) params.search = trimmedSearch;
      if (statusFilter && statusFilter !== "All Status" && statusFilter !== "All Statuses") {
        params.status = statusFilter;
      } else if (tabFilterMap[activeTab]) {
        params.status = tabFilterMap[activeTab];
      }
      if (surveyorFilter && surveyorFilter !== "All Surveyors") params.surveyor = surveyorFilter;
      if (propertyFilter && propertyFilter !== "All Property Types") params.property_type = propertyFilter;

      const blob = await surveyService.exportSurveys(params);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "site-surveys.csv";
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setExportError(err.message || "Unable to export site surveys.");
    } finally {
      setExporting(false);
    }
  }

  useEffect(() => {
    loadSurveys();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, searchValue, statusFilter, surveyorFilter, propertyFilter, refreshToken]);

  // Sequential Workflow 1: Start Survey (Scheduled -> In Progress)
  async function handleStartSurvey(survey) {
    setSaving(true);
    setLoadError("");
    setMessage("");
    try {
      await surveyService.startSurvey(survey.id);
      setMessage(`Survey #${survey.id} is now In Progress.`);
      notifyCrmChange("site_surveys");
      await loadSurveys();
    } catch (err) {
      setLoadError(err.message || "Failed to start site survey.");
    } finally {
      setSaving(false);
    }
  }

  // Sequential Workflow 2: Open Complete Modal (In Progress -> Completed)
  function openCompleteModal(survey) {
    setCompletingSurvey(survey);
    setCompleteForm({
      roofInformation: survey.roofInformation || "RCC flat roof with south-facing exposure",
      capacityEstimate: survey.capacityEstimate || "10 kW",
      notes: survey.notes || "Technical inspection completed. Roof load assessment verified.",
    });
    setCompleteModalOpen(true);
  }

  async function handleCompleteSubmit(e) {
    e.preventDefault();
    if (!completingSurvey) return;
    setSaving(true);
    setLoadError("");
    setMessage("");
    try {
      await surveyService.completeSurvey(completingSurvey.id, completeForm);
      setMessage(`Survey #${completingSurvey.id} completed! Related lead automatically advanced to Quoted.`);
      setCompleteModalOpen(false);
      setCompletingSurvey(null);
      notifyCrmChange("site_surveys");
      notifyCrmChange("leads");
      await loadSurveys();
    } catch (err) {
      setLoadError(err.message || "Failed to complete site survey.");
    } finally {
      setSaving(false);
    }
  }

  // Reverse Workflow 3: Cancel Survey (soft transition preserving history)
  async function handleCancelSurvey(survey) {
    if (!window.confirm(`Cancel the site survey for ${survey.customerName}? This will preserve historical records and mark the waiting lead as Cancelled.`)) return;
    setSaving(true);
    setLoadError("");
    setMessage("");
    try {
      await surveyService.cancelSurvey(survey.id);
      setMessage(`Survey #${survey.id} cancelled. Historical record preserved.`);
      notifyCrmChange("site_surveys");
      notifyCrmChange("leads");
      notifyCrmChange("customers");
      setOpenMenuId(null);
      await loadSurveys();
    } catch (err) {
      setLoadError(err.message || "Failed to cancel site survey.");
    } finally {
      setSaving(false);
    }
  }

  function openEditModal(survey) {
    setEditingSurvey(survey);
    setForm({
      customerId: survey.customerId || "",
      customerName: survey.customerName || "",
      location: survey.location || "",
      propertyType: survey.propertyType || "Residential",
      surveyDate: survey.surveyDate || todayISO(),
      timeSlot: survey.timeSlot || timeSlots[0],
      assignedTo: survey.assignedTo || surveyors[0],
      status: survey.status || "Scheduled",
      roofInformation: survey.roofInformation || "",
      capacityEstimate: survey.capacityEstimate || "",
      notes: survey.notes || "",
    });
    setEditModalOpen(true);
    setOpenMenuId(null);
  }

  async function handleEditSubmit(e) {
    e.preventDefault();
    if (!editingSurvey) return;
    setSaving(true);
    setLoadError("");
    try {
      await surveyService.updateSurvey(editingSurvey.id, {
        roofInformation: form.roofInformation,
        capacityEstimate: form.capacityEstimate,
        notes: form.notes,
        assignedTo: form.assignedTo,
        surveyDate: form.surveyDate,
        timeSlot: form.timeSlot,
      });
      setMessage("Survey technical details updated.");
      setEditModalOpen(false);
      setEditingSurvey(null);
      notifyCrmChange("site_surveys");
      await loadSurveys();
    } catch (err) {
      setLoadError(err.message || "Failed to update survey details.");
    } finally {
      setSaving(false);
    }
  }

  const filtered = useMemo(() => {
    if (!activeTab || activeTab === "All Surveys") return surveys;
    return surveys.filter((survey) => survey.status === tabFilterMap[activeTab]);
  }, [activeTab, surveys]);

  return (
    <div className="space-y-5">
      <PageHeader
        title="Site Surveys"
        subtitle="Manage and track site assessments scheduled through the lead workflow. Progression: Scheduled → In Progress → Completed."
      />

      {message && (
        <div className="rounded-xl border border-leaf-200 bg-leaf-50 dark:bg-leaf-950/20 px-4 py-3 text-sm text-leaf-700 dark:text-leaf-300 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          {message}
        </div>
      )}

      {loadError && (
        <div className="rounded-xl border border-red-200 bg-red-50 dark:bg-red-950/20 px-4 py-3 text-sm text-red-700 dark:text-red-300 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {loadError}
        </div>
      )}

      <div className="bg-white dark:bg-[#17221B] rounded-2xl border border-line dark:border-[#293227]">
        <div className="px-5 sm:px-6 pt-2">
          <Tabs tabs={tabs} active={activeTab} onChange={setActiveTab} />
        </div>

        <div className="p-5 sm:p-6 space-y-5">
          <div className="flex flex-wrap items-center gap-3 justify-between">
            <div className="flex-1 min-w-[260px]">
              <FilterBar
                searchPlaceholder="Search by customer, location or surveyor..."
                searchValue={searchValue}
                onSearchChange={setSearchValue}
                filters={[
                  {
                    name: "status",
                    label: "Status",
                    value: statusFilter,
                    options: ["All Status", "Scheduled", "In Progress", "Completed", "Cancelled"],
                    onChange: (value) => {
                      setStatusFilter(value);
                      setActiveTab("All Surveys");
                    },
                  },
                  {
                    name: "surveyor",
                    label: "Surveyor",
                    value: surveyorFilter,
                    options: ["All Surveyors", ...surveyors],
                    onChange: setSurveyorFilter,
                  },
                  {
                    name: "propertyType",
                    label: "Property Type",
                    value: propertyFilter,
                    options: ["All Property Types", "Residential", "Commercial", "Industrial"],
                    onChange: setPropertyFilter,
                  },
                ]}
                onApply={() => loadSurveys()}
              />
            </div>
            <button
              type="button"
              onClick={handleExport}
              disabled={exporting}
              className="flex items-center gap-2 text-sm font-medium border border-line dark:border-[#293227] rounded-lg px-4 py-2.5 text-ink-600 dark:text-[#B9C4BB] hover:bg-[#f4f6f4] dark:hover:bg-[#152019] transition-colors disabled:opacity-60 cursor-pointer"
            >
              <Download className="w-4 h-4" />
              {exporting ? "Exporting..." : "Export"}
            </button>
          </div>

          {exportError && <p className="text-sm text-red-600 dark:text-red-300">{exportError}</p>}

          <div className="overflow-x-auto no-scrollbar border border-line dark:border-[#293227] rounded-xl">
            <table className="w-full text-left text-sm">
              <thead className="bg-[#f6f8f6] dark:bg-[#0E1712] text-ink-500 dark:text-[#B9C4BB] font-semibold border-b border-line dark:border-[#293227] text-xs uppercase tracking-wider">
                <tr>
                  <th className="py-3.5 px-4">Customer & CRM Link</th>
                  <th className="py-3.5 px-4">Location</th>
                  <th className="py-3.5 px-4">Property</th>
                  <th className="py-3.5 px-4">Date & Time</th>
                  <th className="py-3.5 px-4">Surveyor</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4 text-right">Workflow Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line dark:divide-[#293227] text-ink-800 dark:text-[#F3F6F1] font-medium">
                {!loading && filtered.length === 0 && (
                  <tr>
                    <td colSpan={7} className="py-10 text-center text-sm text-ink-500">
                      No site surveys found.
                    </td>
                  </tr>
                )}
                {loading && (
                  <tr>
                    <td colSpan={7} className="py-10 text-center text-sm text-ink-500">
                      Loading site surveys...
                    </td>
                  </tr>
                )}
                {!loading && filtered.map((survey) => (
                  <tr key={survey.id} className="hover:bg-[#f9faf9] dark:hover:bg-[#152019] transition-colors">
                    <td className="py-3.5 px-4 font-semibold text-ink-900 dark:text-[#F3F6F1]">
                      <div>{survey.customerName}</div>
                      {survey.customerId && (
                        <button
                          type="button"
                          onClick={() => navigate(`/dashboard/customers?id=${survey.customerId}`)}
                          className="mt-0.5 inline-flex items-center gap-1 text-[11px] font-medium text-leaf-600 dark:text-leaf-400 hover:underline cursor-pointer"
                        >
                          <UserCheck className="w-3 h-3" />
                          Customer #{survey.customerId}
                        </button>
                      )}
                      {survey.leadId && (
                        <span className="text-[11px] text-ink-400 block">From Lead #{survey.leadId}</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-ink-600 dark:text-[#B9C4BB]">{survey.location}</td>
                    <td className="py-3.5 px-4">{survey.propertyType}</td>
                    <td className="py-3.5 px-4 text-ink-600 dark:text-[#B9C4BB] text-xs">
                      {survey.surveyDate} at {survey.timeSlot}
                    </td>
                    <td className="py-3.5 px-4 text-ink-700 dark:text-[#B9C4BB]">{survey.assignedTo}</td>
                    <td className="py-3.5 px-4">
                      <StatusBadge status={survey.status} />
                    </td>
                    <td className="relative py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {/* Status = Scheduled: Start Survey | Cancel Survey */}
                        {survey.status === "Scheduled" && (
                          <>
                            <button
                              type="button"
                              onClick={() => handleStartSurvey(survey)}
                              disabled={saving}
                              className="inline-flex items-center gap-1 text-xs bg-leaf-600 hover:bg-leaf-700 text-white px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer"
                              title="Start survey (moves to In Progress)"
                            >
                              <Play className="w-3.5 h-3.5" />
                              Start Survey
                            </button>
                            <button
                              type="button"
                              onClick={() => handleCancelSurvey(survey)}
                              disabled={saving}
                              className="inline-flex items-center gap-1 text-xs text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20 border border-red-200 px-2 py-1.5 rounded-lg transition-colors cursor-pointer"
                              title="Cancel site survey"
                            >
                              <XCircle className="w-3.5 h-3.5" />
                              Cancel
                            </button>
                          </>
                        )}

                        {/* Status = In Progress: Complete Survey | Cancel Survey */}
                        {survey.status === "In Progress" && (
                          <>
                            <button
                              type="button"
                              onClick={() => openCompleteModal(survey)}
                              disabled={saving}
                              className="inline-flex items-center gap-1 text-xs bg-[#1F5C3E] hover:bg-[#184A32] text-white px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer"
                              title="Complete survey and automatically update Lead to Quoted"
                            >
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              Complete Survey
                            </button>
                            <button
                              type="button"
                              onClick={() => handleCancelSurvey(survey)}
                              disabled={saving}
                              className="inline-flex items-center gap-1 text-xs text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20 border border-red-200 px-2 py-1.5 rounded-lg transition-colors cursor-pointer"
                              title="Cancel site survey"
                            >
                              <XCircle className="w-3.5 h-3.5" />
                              Cancel
                            </button>
                          </>
                        )}

                        {/* Edit Technical Notes Button */}
                        <button
                          type="button"
                          onClick={() => openEditModal(survey)}
                          className="p-1.5 rounded-lg text-ink-400 hover:text-ink-900 dark:hover:text-[#F3F6F1] transition-colors"
                          title="Edit survey notes"
                        >
                          <Pencil className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <Pagination totalItems={filtered.length} itemsPerPage={10} />
        </div>
      </div>

      {/* Complete Site Survey Modal */}
      <Modal
        open={completeModalOpen}
        onClose={() => setCompleteModalOpen(false)}
        title={`Complete Survey for ${completingSurvey?.customerName || ""}`}
        subtitle="Completing this survey will automatically update the related Lead to 'Quoted'."
      >
        <form onSubmit={handleCompleteSubmit} className="space-y-4">
          <FormField label="Roof Information & Structural Condition">
            <TextInput
              name="roofInformation"
              value={completeForm.roofInformation}
              onChange={(e) => setCompleteForm((f) => ({ ...f, roofInformation: e.target.value }))}
              placeholder="e.g. RCC flat roof with south-facing exposure, shadow-free"
            />
          </FormField>

          <FormField label="Recommended System Capacity">
            <TextInput
              name="capacityEstimate"
              value={completeForm.capacityEstimate}
              onChange={(e) => setCompleteForm((f) => ({ ...f, capacityEstimate: e.target.value }))}
              placeholder="e.g. 10 kW"
            />
          </FormField>

          <FormField label="Final Inspection Notes">
            <TextInput
              name="notes"
              value={completeForm.notes}
              onChange={(e) => setCompleteForm((f) => ({ ...f, notes: e.target.value }))}
              placeholder="Technical observations for quote preparation"
            />
          </FormField>

          <div className="flex items-center gap-3 pt-2">
            <button
              type="button"
              onClick={() => setCompleteModalOpen(false)}
              className="flex-1 border border-line dark:border-[#293227] rounded-lg px-4 py-2.5 text-sm font-medium text-ink-600 dark:text-[#B9C4BB] hover:bg-[#f4f6f4] dark:hover:bg-[#152019] transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex-1 bg-[#1F5C3E] hover:bg-[#184A32] text-white rounded-lg px-4 py-2.5 text-sm font-medium transition-colors disabled:opacity-60"
            >
              {saving ? "Completing..." : "Confirm Survey Completion"}
            </button>
          </div>
        </form>
      </Modal>

      {/* Edit Technical Details Modal */}
      <Modal
        open={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        title={`Edit Survey Details (#${editingSurvey?.id || ""})`}
      >
        <form onSubmit={handleEditSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Assigned Surveyor">
              <SelectInput
                name="assignedTo"
                value={form.assignedTo}
                onChange={(e) => setForm((f) => ({ ...f, assignedTo: e.target.value }))}
                options={surveyors}
              />
            </FormField>

            <FormField label="Time Slot">
              <SelectInput
                name="timeSlot"
                value={form.timeSlot}
                onChange={(e) => setForm((f) => ({ ...f, timeSlot: e.target.value }))}
                options={timeSlots}
              />
            </FormField>
          </div>

          <FormField label="Roof Information">
            <TextInput
              name="roofInformation"
              value={form.roofInformation}
              onChange={(e) => setForm((f) => ({ ...f, roofInformation: e.target.value }))}
            />
          </FormField>

          <FormField label="Capacity Estimate">
            <TextInput
              name="capacityEstimate"
              value={form.capacityEstimate}
              onChange={(e) => setForm((f) => ({ ...f, capacityEstimate: e.target.value }))}
            />
          </FormField>

          <FormField label="Notes">
            <TextInput
              name="notes"
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
            />
          </FormField>

          <div className="flex items-center gap-3 pt-2">
            <button
              type="button"
              onClick={() => setEditModalOpen(false)}
              className="flex-1 border border-line dark:border-[#293227] rounded-lg px-4 py-2.5 text-sm font-medium text-ink-600 dark:text-[#B9C4BB] hover:bg-[#f4f6f4] dark:hover:bg-[#152019] transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex-1 bg-[#1F5C3E] hover:bg-[#184A32] text-white rounded-lg px-4 py-2.5 text-sm font-medium transition-colors disabled:opacity-60"
            >
              {saving ? "Saving..." : "Save Details"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}