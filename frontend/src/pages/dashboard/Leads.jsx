import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Download, MoreVertical, Plus, Calendar, CheckCircle2, UserCheck, Briefcase } from "lucide-react";
import PageHeader from "../../components/dashboard/PageHeader";
import Tabs from "../../components/dashboard/Tabs";
import FilterBar from "../../components/dashboard/FilterBar";
import StatusBadge from "../../components/dashboard/StatusBadge";
import Pagination from "../../components/dashboard/Pagination";
import Modal from "../../components/dashboard/Modal";
import { FormField, TextInput, SelectInput } from "../../components/dashboard/FormField";
import { leadsTabOrder } from "../../data/dashboardData";
import { leadService } from "../../services/leadService";
import { useDashboardData } from "../../context/DashboardDataContext";
import { todayISO } from "../../utils/dashboardDate";

const tabFilterMap = {
  "All Leads": null,
  New: "New",
  Contacted: "Contacted",
  "Site Survey": "Site Survey",
  Quoted: "Quoted",
  Converted: "Converted",
  Cancelled: "Cancelled",
  Lost: "Lost",
};


const propertyTypeOptions = ["All Property Types", "Residential", "Commercial", "Industrial"];
const locationOptions = ["All Locations", "Mumbai", "Pune", "Nashik", "Thane", "Nagpur", "Solapur"];
const sourceOptions = [
  "All Sources",
  "Website",
  "Calculator",
  "Referral",
  "Cold Call",
  "Ad Campaign",
  "Google Ads",
  "Social Media",
  "Direct Enquiry",
];
const statusOptions = ["All Status", "New", "Contacted", "Site Survey", "Quoted", "Converted", "Cancelled", "Lost"];


const emptyForm = {
  name: "",
  contact: "",
  location: "",
  propertyType: "Residential",
  source: "Website",
  status: "New",
};

function toForm(lead) {
  return {
    name: lead.name || "",
    contact: lead.contact || "",
    location: lead.location || "",
    propertyType: lead.propertyType || "Residential",
    source: lead.source || "Website",
    status: lead.status || "New",
  };
}

function downloadCsv(filename, rows) {
  const headers = ["Lead Name", "Contact", "Location", "Property", "Source", "Date", "Status", "Customer ID"];
  const values = rows.map((lead) => [
    lead.name,
    lead.contact,
    lead.location,
    lead.propertyType,
    lead.source,
    lead.date || lead.createdAt,
    lead.status,
    lead.customerId || "",
  ]);
  const csv = [headers, ...values]
    .map((row) => row.map((value) => `"${String(value ?? "").replaceAll('"', '""')}"`).join(","))
    .join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8;" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export default function Leads() {
  const navigate = useNavigate();
  const { refreshToken, notifyCrmChange } = useDashboardData();
  const [leads, setLeads] = useState([]);
  const [tabCounts, setTabCounts] = useState({});
  const [activeTab, setActiveTab] = useState("All Leads");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [propertyType, setPropertyType] = useState("All Property Types");
  const [location, setLocation] = useState("All Locations");
  const [source, setSource] = useState("All Sources");
  const [statusFilter, setStatusFilter] = useState("All Status");

  // Lead modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [editingLead, setEditingLead] = useState(null);
  const [form, setForm] = useState(emptyForm);

  // Survey schedule modal state
  const [scheduleModalOpen, setScheduleModalOpen] = useState(false);
  const [surveyLead, setSurveyLead] = useState(null);
  const [surveyForm, setSurveyForm] = useState({
    surveyDate: todayISO(),
    timeSlot: "10:00 AM",
    assignedTo: "Rahul",
    roofInformation: "",
    capacityEstimate: "",
    notes: "",
  });

  // Convert to project modal state
  const [convertModalOpen, setConvertModalOpen] = useState(false);
  const [convertLead, setConvertLead] = useState(null);
  const [convertForm, setConvertForm] = useState({
    projectName: "",
    category: "Residential",
    capacity: "5 kW",
    capacityKW: "5.0",
    estimatedCost: "350000",
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const tabs = useMemo(
    () =>
      leadsTabOrder.map((label) => ({
        label,
        count: tabCounts[label] ?? 0,
      })),
    [tabCounts]
  );

  const loadLeads = useCallback(
    async (targetPage = page) => {
      setLoading(true);
      setError("");
      try {
        const response = await leadService.getLeads({
          page: targetPage,
          limit: 10,
          search,
          property_type: propertyType,
          location,
          source,
          status: tabFilterMap[activeTab] || statusFilter,
        });
        setLeads(response.items || []);
        setTabCounts(response.tabCounts || {});
        setTotal(response.total || 0);
        setTotalPages(response.total_pages || response.totalPages || 1);
      } catch (err) {
        setError(err.message || "Unable to load leads.");
      } finally {
        setLoading(false);
      }
    },
    [activeTab, location, page, propertyType, search, source, statusFilter]
  );

  useEffect(() => {
    loadLeads();
  }, [loadLeads, refreshToken]);

  function updateFilter(setter, value) {
    setter(value);
    setPage(1);
  }

  function openCreateModal() {
    setEditingLead(null);
    setForm(emptyForm);
    setModalOpen(true);
  }

  function openEditModal(lead) {
    setEditingLead(lead);
    setForm(toForm(lead));
    setModalOpen(true);
  }

  function openScheduleModal(lead) {
    setSurveyLead(lead);
    setSurveyForm({
      surveyDate: todayISO(),
      timeSlot: "10:00 AM",
      assignedTo: "Rahul",
      roofInformation: lead.propertyType === "Commercial" ? "Flat RCC Roof" : "Sloped Tile / RCC",
      capacityEstimate: lead.propertyType === "Commercial" ? "25 kW" : "5 kW",
      notes: `Site survey for lead #${lead.id} (${lead.name})`,
    });
    setScheduleModalOpen(true);
  }

  function openConvertModal(lead) {
    setConvertLead(lead);
    setConvertForm({
      projectName: `${lead.name} Solar Project`,
      category: lead.propertyType || "Residential",
      capacity: lead.propertyType === "Commercial" ? "25 kW" : "5 kW",
      capacityKW: lead.propertyType === "Commercial" ? "25.0" : "5.0",
      estimatedCost: lead.propertyType === "Commercial" ? "1200000" : "350000",
    });
    setConvertModalOpen(true);
  }

  async function handleContactLead(lead) {
    setSaving(true);
    setError("");
    setSuccessMsg("");
    try {
      const result = await leadService.contactLead(lead.id);
      setSuccessMsg(`Lead contacted! Customer #${result.lead?.customer_id} linked.`);
      notifyCrmChange("leads");
      await loadLeads(page);
    } catch (err) {
      setError(err.message || "Unable to update lead to Contacted.");
    } finally {
      setSaving(false);
    }
  }

  async function handleScheduleSurveySubmit(e) {
    e.preventDefault();
    if (!surveyLead) return;
    setSaving(true);
    setError("");
    setSuccessMsg("");
    try {
      const res = await leadService.scheduleSurvey(surveyLead.id, {
        survey_date: surveyForm.surveyDate,
        time_slot: surveyForm.timeSlot,
        assigned_to: surveyForm.assignedTo,
        roof_information: surveyForm.roofInformation,
        capacity_estimate: surveyForm.capacityEstimate,
        notes: surveyForm.notes,
      });
      setSuccessMsg(`Site survey #${res.survey?.id} scheduled successfully for ${surveyLead.name}!`);
      setScheduleModalOpen(false);
      setSurveyLead(null);
      notifyCrmChange("site_surveys");
      await loadLeads(page);
    } catch (err) {
      setError(err.message || "Failed to schedule survey.");
    } finally {
      setSaving(false);
    }
  }

  async function handleConvertSubmit(e) {
    e.preventDefault();
    if (!convertLead) return;
    setSaving(true);
    setError("");
    setSuccessMsg("");
    try {
      const res = await leadService.convertLead(convertLead.id, {
        project_name: convertForm.projectName.trim(),
        category: convertForm.category,
        capacity: convertForm.capacity,
        capacity_kw: Number(convertForm.capacityKW) || 0,
        estimated_cost: Number(convertForm.estimatedCost) || 0,
      });
      setSuccessMsg(`Lead converted! Project #${res.project?.id} created.`);
      setConvertModalOpen(false);
      setConvertLead(null);
      notifyCrmChange("projects");
      await loadLeads(page);
    } catch (err) {
      setError(err.message || "Failed to convert lead.");
    } finally {
      setSaving(false);
    }
  }

  function handleChange(e) {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.name.trim() || !form.contact.trim() || !form.location.trim()) return;

    setSaving(true);
    setError("");
    try {
      if (editingLead) {
        await leadService.updateLead(editingLead.id, form);
      } else {
        await leadService.createLead({ ...form, status: "New" });
      }
      notifyCrmChange("leads");
      setModalOpen(false);
      setEditingLead(null);
      setForm(emptyForm);
      setPage(1);
      await loadLeads(1);
    } catch (err) {
      setError(err.message || "Unable to save lead.");
    } finally {
      setSaving(false);
    }
  }

  async function handleCancelLead(lead, statusVal = "Cancelled") {
    const targetStatus = statusVal === "Lost" ? "Lost" : "Cancelled";
    const promptMsg = targetStatus === "Lost"
      ? `Mark lead '${lead.name}' as Lost? CRM history will be preserved.`
      : `Cancel lead '${lead.name}'? CRM history will be preserved.`;
    if (!window.confirm(promptMsg)) return;
    setSaving(true);
    setError("");
    setSuccessMsg("");
    try {
      await leadService.cancelLead(lead.id, targetStatus);
      setSuccessMsg(`Lead '${lead.name}' marked as ${targetStatus}.`);
      notifyCrmChange("leads");
      notifyCrmChange("customers");
      setModalOpen(false);
      setEditingLead(null);
      await loadLeads(page);
    } catch (err) {
      setError(err.message || `Unable to cancel lead.`);
    } finally {
      setSaving(false);
    }
  }


  return (
    <div className="space-y-5">
      <PageHeader
        title="Leads Management"
        subtitle="Manage end-to-end solar lead lifecycle from enquiry to converted project."
        actionLabel="Add New Lead"
        actionIcon={Plus}
        onAction={openCreateModal}
      />

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 dark:bg-red-950/20 px-4 py-3 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {successMsg && (
        <div className="rounded-xl border border-leaf-200 bg-leaf-50 dark:bg-leaf-950/20 px-4 py-3 text-sm text-leaf-700 dark:text-leaf-300 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          {successMsg}
        </div>
      )}

      <div className="bg-white dark:bg-[#17221B] rounded-2xl border border-line dark:border-[#293227]">
        <div className="px-5 sm:px-6 pt-2">
          <Tabs tabs={tabs} active={activeTab} onChange={(tab) => updateFilter(setActiveTab, tab)} />
        </div>

        <div className="p-5 sm:p-6 space-y-5">
          <div className="flex flex-wrap items-center gap-3 justify-between">
            <div className="flex-1 min-w-[260px]">
              <FilterBar
                searchPlaceholder="Search by name, phone, email..."
                searchValue={search}
                onSearchChange={(value) => updateFilter(setSearch, value)}
                onApply={() => loadLeads(1)}
                filters={[
                  { name: "propertyType", label: "Property Type", value: propertyType, onChange: (value) => updateFilter(setPropertyType, value), options: propertyTypeOptions },
                  { name: "location", label: "Location", value: location, onChange: (value) => updateFilter(setLocation, value), options: locationOptions },
                  { name: "source", label: "Source", value: source, onChange: (value) => updateFilter(setSource, value), options: sourceOptions },
                  { name: "status", label: "Status", value: statusFilter, onChange: (value) => updateFilter(setStatusFilter, value), options: statusOptions },
                ]}
              />
            </div>
            <button
              type="button"
              onClick={() => downloadCsv("leads.csv", leads)}
              className="flex items-center gap-2 text-sm font-medium border border-line rounded-lg px-4 py-2.5 text-ink-600 dark:text-[#B9C4BB] hover:bg-[#f4f6f4] dark:hover:bg-[#152019] transition-colors"
            >
              <Download className="w-4 h-4" />
              Export
            </button>
          </div>

          <p className="text-sm text-ink-500">
            {loading ? "Loading leads..." : `Showing ${leads.length} of ${total} leads`}
          </p>

          <div className="overflow-x-auto no-scrollbar border border-line rounded-xl">
            <table className="w-full text-left text-sm">
              <thead className="bg-[#f6f8f6] dark:bg-[#0E1712] text-ink-500 dark:text-[#B9C4BB] font-semibold border-b border-line dark:border-[#293227] text-xs uppercase tracking-wider">
                <tr>
                  <th className="py-3.5 px-4">Lead Name</th>
                  <th className="py-3.5 px-4">Contact</th>
                  <th className="py-3.5 px-4">Location</th>
                  <th className="py-3.5 px-4">Property</th>
                  <th className="py-3.5 px-4">Source</th>
                  <th className="py-3.5 px-4">Date</th>
                  <th className="py-3.5 px-4">Status & CRM Link</th>
                  <th className="py-3.5 px-4 text-right">Workflow Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line dark:divide-[#293227] text-ink-800 dark:text-[#F3F6F1] font-medium">
                {leads.map((lead) => (
                  <tr key={lead.id} className="hover:bg-[#f9faf9] dark:hover:bg-[#152019] transition-colors">
                    <td className="py-3.5 px-4 font-semibold text-ink-900 dark:text-[#F3F6F1]">
                      <div>{lead.name}</div>
                      {lead.customerId && (
                        <button
                          type="button"
                          onClick={() => navigate(`/dashboard/customers?id=${lead.customerId}`)}
                          className="mt-0.5 inline-flex items-center gap-1 text-[11px] font-medium text-leaf-600 dark:text-leaf-400 hover:underline cursor-pointer"
                        >
                          <UserCheck className="w-3 h-3" />
                          Customer #{lead.customerId}
                        </button>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-ink-600 dark:text-[#B9C4BB]">{lead.contact}</td>
                    <td className="py-3.5 px-4 text-ink-600 dark:text-[#B9C4BB]">{lead.location}</td>
                    <td className="py-3.5 px-4">{lead.propertyType}</td>
                    <td className="py-3.5 px-4 text-ink-500 dark:text-[#8A968C]">{lead.source}</td>
                    <td className="py-3.5 px-4 text-ink-500 dark:text-[#8A968C] text-xs">{lead.date || lead.createdAt}</td>
                    <td className="py-3.5 px-4">
                      <div className="flex flex-col items-start gap-1">
                        <StatusBadge status={lead.status} />
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {/* Stage 1: New -> Contact */}
                        {lead.status === "New" && (
                          <>
                            <button
                              type="button"
                              onClick={() => handleContactLead(lead)}
                              disabled={saving}
                              className="inline-flex items-center gap-1 text-xs bg-leaf-600 hover:bg-leaf-700 text-white px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer"
                              title="Contact lead and create/link customer"
                            >
                              <UserCheck className="w-3.5 h-3.5" />
                              Contact
                            </button>
                            <button
                              type="button"
                              onClick={() => handleCancelLead(lead, "Cancelled")}
                              disabled={saving}
                              className="text-xs text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20 border border-red-200 px-2 py-1.5 rounded-lg transition-colors cursor-pointer"
                              title="Cancel lead"
                            >
                              Cancel
                            </button>
                          </>
                        )}

                        {/* Stage 2: Contacted -> Schedule Site Survey */}
                        {lead.status === "Contacted" && (
                          <>
                            <button
                              type="button"
                              onClick={() => openScheduleModal(lead)}
                              disabled={saving}
                              className="inline-flex items-center gap-1 text-xs bg-amber-600 hover:bg-amber-700 text-white px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer"
                              title="Schedule site survey for customer"
                            >
                              <Calendar className="w-3.5 h-3.5" />
                              Schedule Survey
                            </button>
                            <button
                              type="button"
                              onClick={() => handleCancelLead(lead, "Lost")}
                              disabled={saving}
                              className="text-xs text-ink-500 hover:bg-line/40 border border-line px-2 py-1.5 rounded-lg transition-colors cursor-pointer"
                              title="Mark lead as Lost"
                            >
                              Lost
                            </button>
                          </>
                        )}

                        {/* Stage 3: Site Survey (In Progress) -> View Survey Link */}
                        {lead.status === "Site Survey" && (
                          <>
                            <button
                              type="button"
                              onClick={() => navigate("/dashboard/site-surveys")}
                              className="inline-flex items-center gap-1 text-xs bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-800 px-2.5 py-1.5 rounded-lg hover:bg-amber-100 transition-colors cursor-pointer"
                              title="Survey is scheduled/in progress. Complete it on Site Surveys page to advance lead to Quoted."
                            >
                              <Calendar className="w-3.5 h-3.5" />
                              Survey In Progress
                            </button>
                            <button
                              type="button"
                              onClick={() => handleCancelLead(lead, "Cancelled")}
                              disabled={saving}
                              className="text-xs text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20 border border-red-200 px-2 py-1.5 rounded-lg transition-colors cursor-pointer"
                              title="Cancel lead"
                            >
                              Cancel
                            </button>
                          </>
                        )}

                        {/* Stage 4: Quoted -> Convert to Project */}
                        {lead.status === "Quoted" && (
                          <>
                            <button
                              type="button"
                              onClick={() => openConvertModal(lead)}
                              disabled={saving}
                              className="inline-flex items-center gap-1 text-xs bg-purple-600 hover:bg-purple-700 text-white px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer"
                              title="Convert quoted lead to active solar installation project"
                            >
                              <Briefcase className="w-3.5 h-3.5" />
                              Convert to Project
                            </button>
                            <button
                              type="button"
                              onClick={() => handleCancelLead(lead, "Lost")}
                              disabled={saving}
                              className="text-xs text-ink-500 hover:bg-line/40 border border-line px-2 py-1.5 rounded-lg transition-colors cursor-pointer"
                              title="Mark lead as Lost"
                            >
                              Lost
                            </button>
                          </>
                        )}

                        {/* Stage 5: Converted -> View Project Link */}
                        {lead.status === "Converted" && (
                          <button
                            type="button"
                            onClick={() => navigate("/dashboard/projects")}
                            className="inline-flex items-center gap-1 text-xs text-leaf-600 dark:text-leaf-400 border border-leaf-300 dark:border-leaf-700/60 px-2.5 py-1.5 rounded-lg hover:bg-leaf-50 dark:hover:bg-leaf-950/30 transition-colors cursor-pointer font-medium"
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            View Project
                          </button>
                        )}

                        <button
                          type="button"
                          onClick={() => openEditModal(lead)}
                          className="p-1.5 rounded-lg text-ink-400 dark:text-[#8A968C] hover:text-ink-900 dark:hover:text-[#F3F6F1] hover:bg-line/40 transition-colors"
                          aria-label={`Edit ${lead.name}`}
                        >
                          <MoreVertical className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {!loading && leads.length === 0 && (
                  <tr>
                    <td colSpan={8} className="py-10 text-center text-sm text-ink-500">
                      No leads found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </div>
      </div>

      {/* Edit / Create Lead Modal */}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editingLead ? "Lead Details" : "Add New Lead"}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <FormField label="Full Name">
            <TextInput name="name" placeholder="e.g. Rahul Sharma" value={form.name} onChange={handleChange} minLength={2} maxLength={150} required />
          </FormField>

          <FormField label="Contact (Phone / Email)">
            <TextInput name="contact" placeholder="e.g. +91 98765 43210" value={form.contact} onChange={handleChange} minLength={3} maxLength={100} required />
          </FormField>

          <FormField label="Location">
            <TextInput name="location" placeholder="e.g. Pune, Maharashtra" value={form.location} onChange={handleChange} minLength={2} maxLength={150} required />
          </FormField>

          <div className="grid grid-cols-2 gap-3">
            <FormField label="Property Type">
              <SelectInput name="propertyType" value={form.propertyType} onChange={handleChange} options={["Residential", "Commercial", "Industrial"]} />
            </FormField>

            <FormField label="Source">
              <SelectInput name="source" value={form.source} onChange={handleChange} options={sourceOptions.filter((option) => option !== "All Sources")} />
            </FormField>
          </div>

          <div className="flex items-center gap-3 pt-2">
            {editingLead && editingLead.status !== "Converted" && editingLead.status !== "Cancelled" && editingLead.status !== "Lost" && (
              <button
                type="button"
                onClick={() => handleCancelLead(editingLead, "Cancelled")}
                disabled={saving}
                className="inline-flex items-center gap-1.5 border border-red-200 rounded-lg px-4 py-2.5 text-sm font-medium text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20 transition-colors disabled:opacity-50"
              >
                Cancel Lead
              </button>
            )}
            <button
              type="submit"
              disabled={saving}
              className="bg-[#1F5C3E] hover:bg-[#184A32] dark:bg-[#3FA46A] dark:hover:bg-[#4CBE7C] text-white dark:text-[#0E1712] rounded-lg px-4 py-2.5 text-sm font-medium transition-colors disabled:opacity-60"
            >
              {saving ? "Saving..." : "Save Details"}
            </button>
            <button
              type="button"
              onClick={() => setModalOpen(false)}
              className="ml-auto border border-line dark:border-[#293227] rounded-lg px-4 py-2.5 text-sm font-medium text-ink-600 dark:text-[#B9C4BB] hover:bg-[#f4f6f4] dark:hover:bg-[#152019] transition-colors"
            >
              Close
            </button>
          </div>

        </form>
      </Modal>

      {/* Schedule Survey Modal */}
      <Modal
        open={scheduleModalOpen}
        onClose={() => setScheduleModalOpen(false)}
        title={`Schedule Site Survey for ${surveyLead?.name || ""}`}
      >
        <form onSubmit={handleScheduleSurveySubmit} className="space-y-4">
          <p className="text-xs text-ink-500">
            This will schedule a site survey linked to Customer #{surveyLead?.customerId || "Auto-Created"} and advance this lead to "Site Survey".
          </p>

          <div className="grid grid-cols-2 gap-3">
            <FormField label="Survey Date" required>
              <TextInput
                type="date"
                name="surveyDate"
                value={surveyForm.surveyDate}
                onChange={(e) => setSurveyForm((f) => ({ ...f, surveyDate: e.target.value }))}
                required
              />
            </FormField>
            <FormField label="Time Slot" required>
              <SelectInput
                name="timeSlot"
                value={surveyForm.timeSlot}
                onChange={(e) => setSurveyForm((f) => ({ ...f, timeSlot: e.target.value }))}
                options={["09:00 AM", "10:00 AM", "11:30 AM", "01:00 PM", "02:30 PM", "04:00 PM"]}
              />
            </FormField>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <FormField label="Surveyor" required>
              <SelectInput
                name="assignedTo"
                value={surveyForm.assignedTo}
                onChange={(e) => setSurveyForm((f) => ({ ...f, assignedTo: e.target.value }))}
                options={["Rahul", "Priya", "Karan", "Neha"]}
              />
            </FormField>
            <FormField label="Capacity Estimate">
              <TextInput
                name="capacityEstimate"
                placeholder="e.g. 5 kW"
                value={surveyForm.capacityEstimate}
                onChange={(e) => setSurveyForm((f) => ({ ...f, capacityEstimate: e.target.value }))}
              />
            </FormField>
          </div>

          <FormField label="Roof Information">
            <TextInput
              name="roofInformation"
              placeholder="e.g. Flat RCC roof, no shade"
              value={surveyForm.roofInformation}
              onChange={(e) => setSurveyForm((f) => ({ ...f, roofInformation: e.target.value }))}
            />
          </FormField>

          <FormField label="Survey Notes">
            <TextInput
              name="notes"
              placeholder="Customer preferred contact before arrival"
              value={surveyForm.notes}
              onChange={(e) => setSurveyForm((f) => ({ ...f, notes: e.target.value }))}
            />
          </FormField>

          <div className="flex items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={saving}
              className="bg-amber-600 hover:bg-amber-700 text-white rounded-lg px-4 py-2.5 text-sm font-medium transition-colors disabled:opacity-60"
            >
              {saving ? "Scheduling..." : "Confirm Survey"}
            </button>
            <button
              type="button"
              onClick={() => setScheduleModalOpen(false)}
              className="ml-auto border border-line rounded-lg px-4 py-2.5 text-sm font-medium text-ink-600 hover:bg-[#f4f6f4] transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </Modal>

      {/* Convert to Project Modal */}
      <Modal
        open={convertModalOpen}
        onClose={() => setConvertModalOpen(false)}
        title={`Convert Lead to Project: ${convertLead?.name || ""}`}
      >
        <form onSubmit={handleConvertSubmit} className="space-y-4">
          <p className="text-xs text-ink-500">
            This will mark Lead #{convertLead?.id} as Converted, create an active solar Project for Customer #{convertLead?.customerId || "Auto-Created"}, and update your CRM pipeline.
          </p>

          <FormField label="Project Name" required>
            <TextInput
              name="projectName"
              placeholder="e.g. Sharma Residence Rooftop Solar"
              value={convertForm.projectName}
              onChange={(e) => setConvertForm((f) => ({ ...f, projectName: e.target.value }))}
              required
            />
          </FormField>

          <div className="grid grid-cols-2 gap-3">
            <FormField label="Category">
              <SelectInput
                name="category"
                value={convertForm.category}
                onChange={(e) => setConvertForm((f) => ({ ...f, category: e.target.value }))}
                options={["Residential", "Commercial", "Industrial"]}
              />
            </FormField>
            <FormField label="Capacity Display">
              <TextInput
                name="capacity"
                placeholder="e.g. 5 kW"
                value={convertForm.capacity}
                onChange={(e) => setConvertForm((f) => ({ ...f, capacity: e.target.value }))}
                required
              />
            </FormField>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <FormField label="Capacity (kW Numeric)">
              <TextInput
                type="number"
                name="capacityKW"
                step="0.1"
                placeholder="5.0"
                value={convertForm.capacityKW}
                onChange={(e) => setConvertForm((f) => ({ ...f, capacityKW: e.target.value }))}
              />
            </FormField>
            <FormField label="Estimated Cost (₹)">
              <TextInput
                type="number"
                name="estimatedCost"
                step="1000"
                placeholder="350000"
                value={convertForm.estimatedCost}
                onChange={(e) => setConvertForm((f) => ({ ...f, estimatedCost: e.target.value }))}
              />
            </FormField>
          </div>

          <div className="flex items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={saving}
              className="bg-purple-600 hover:bg-purple-700 text-white rounded-lg px-4 py-2.5 text-sm font-medium transition-colors disabled:opacity-60"
            >
              {saving ? "Converting..." : "Convert to Project"}
            </button>
            <button
              type="button"
              onClick={() => setConvertModalOpen(false)}
              className="ml-auto border border-line rounded-lg px-4 py-2.5 text-sm font-medium text-ink-600 hover:bg-[#f4f6f4] transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
