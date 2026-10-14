import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Edit2, Calendar, FolderOpen, Users, Clock, MapPin, Phone, Mail, Building } from "lucide-react";
import PageHeader from "../../components/dashboard/PageHeader";

import StatusBadge from "../../components/dashboard/StatusBadge";
import Pagination from "../../components/dashboard/Pagination";
import Modal from "../../components/dashboard/Modal";
import { FormField, SelectInput, TextInput } from "../../components/dashboard/FormField";
import { customerService } from "../../services/customerService";
import { useDashboardData } from "../../context/DashboardDataContext";

const emptyForm = {
  name: "",
  contact: "",
  email: "",
  location: "",
  propertyType: "Residential",
  status: "Active",
};

function toForm(customer) {
  return {
    name: customer.name || "",
    contact: customer.contact || "",
    email: customer.email || "",
    location: customer.location || "",
    propertyType: customer.propertyType || "Residential",
    status: customer.status || "Active",
  };
}

export default function Customers() {
  const [searchParams] = useSearchParams();
  const { refreshToken, notifyCrmChange } = useDashboardData();
  const [customers, setCustomers] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  // Edit / Create Form Modal
  const [modalOpen, setModalOpen] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState(null);
  const [form, setForm] = useState(emptyForm);

  // Customer 360 Overview Modal
  const [overviewOpen, setOverviewOpen] = useState(false);
  const [overviewCustomer, setOverviewCustomer] = useState(null);
  const [overviewData, setOverviewData] = useState(null);
  const [overviewLoading, setOverviewLoading] = useState(false);
  const [overviewTab, setOverviewTab] = useState("overview");

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function loadCustomers() {
    setLoading(true);
    setError("");
    try {
      const response = await customerService.getCustomers({ page, limit: 10 });
      setCustomers(response.items || []);
      setTotal(response.meta?.total || 0);
      setTotalPages(response.meta?.total_pages || response.meta?.totalPages || 1);
    } catch (err) {
      setError(err.message || "Unable to load customers.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCustomers();
  }, [page, refreshToken]);

  // Handle URL deep linking (e.g. ?id=15)
  useEffect(() => {
    const targetId = searchParams.get("id");
    if (targetId) {
      openCustomerOverview({ id: Number(targetId) });
    }
  }, [searchParams]);

  async function openCustomerOverview(customer) {
    setOverviewCustomer(customer);
    setOverviewOpen(true);
    setOverviewLoading(true);
    setOverviewTab("overview");
    try {
      const data = await customerService.getCustomerOverview(customer.id);
      setOverviewData(data);
      if (data.customer) {
        setOverviewCustomer(data.customer);
      }
    } catch (err) {
      console.error("Failed to load customer overview:", err);
    } finally {
      setOverviewLoading(false);
    }
  }

  function openEditModal(customer) {
    setEditingCustomer(customer);
    setForm(toForm(customer));
    setModalOpen(true);
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
      if (editingCustomer) {
        await customerService.updateCustomer(editingCustomer.id, form);
      }
      notifyCrmChange("customers");
      setModalOpen(false);
      setEditingCustomer(null);
      setForm(emptyForm);
      await loadCustomers();
    } catch (err) {
      setError(err.message || "Unable to save customer.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Customers"
        subtitle="Central customer directory with linked leads, site surveys, and solar projects. Automatically created when leads are contacted."
      />


      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 dark:bg-red-950/20 px-4 py-3 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      <div className="bg-white dark:bg-[#17221B] rounded-2xl border border-line dark:border-[#293227] p-5 sm:p-6 space-y-5">
        <p className="text-sm text-ink-500">
          {loading ? "Loading customers..." : `Showing ${customers.length} of ${total} customers`}
        </p>

        <div className="overflow-x-auto no-scrollbar -mx-2">
          <table className="w-full text-sm min-w-[860px]">
            <thead>
              <tr className="text-left text-ink-400 dark:text-[#8A968C] text-xs uppercase tracking-wide">
                <th className="px-2 pb-3 font-medium">ID</th>
                <th className="px-2 pb-3 font-medium">Name</th>
                <th className="px-2 pb-3 font-medium">Contact</th>
                <th className="px-2 pb-3 font-medium">Location</th>
                <th className="px-2 pb-3 font-medium">Property Type</th>
                <th className="px-2 pb-3 font-medium">Total Projects</th>
                <th className="px-2 pb-3 font-medium">Customer Since</th>
                <th className="px-2 pb-3 font-medium">Status</th>
                <th className="px-2 pb-3 font-medium text-right">Action</th>
              </tr>
            </thead>
            <tbody className="text-ink-800 dark:text-[#F3F6F1]">
              {customers.map((customer, i) => (
                <tr key={customer.id} className="border-t border-line dark:border-[#293227] hover:bg-[#f9faf9] dark:hover:bg-[#152019] transition-colors">
                  <td className="px-2 py-3 text-ink-400 font-mono text-xs">#{customer.id}</td>
                  <td className="px-2 py-3 font-medium text-ink-900 dark:text-[#F3F6F1] whitespace-nowrap">
                    {customer.name}
                  </td>
                  <td className="px-2 py-3 text-ink-600 dark:text-[#B9C4BB] whitespace-nowrap">{customer.contact}</td>
                  <td className="px-2 py-3 text-ink-600 dark:text-[#B9C4BB]">{customer.location}</td>
                  <td className="px-2 py-3 text-ink-600 dark:text-[#B9C4BB]">{customer.propertyType}</td>
                  <td className="px-2 py-3">
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-leaf-50 text-leaf-700 dark:bg-leaf-950/40 dark:text-leaf-300">
                      {customer.totalProjects} {customer.totalProjects === 1 ? "project" : "projects"}
                    </span>
                  </td>
                  <td className="px-2 py-3 text-ink-600 dark:text-[#B9C4BB] whitespace-nowrap">{customer.customerSince}</td>
                  <td className="px-2 py-3">
                    <StatusBadge status={customer.status} />
                  </td>
                  <td className="px-2 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => openCustomerOverview(customer)}
                        className="text-leaf-600 dark:text-leaf-400 font-medium hover:underline text-xs bg-leaf-50 dark:bg-leaf-950/40 px-2.5 py-1 rounded-lg cursor-pointer"
                      >
                        View 360°
                      </button>
                      <button
                        type="button"
                        onClick={() => openEditModal(customer)}
                        className="text-ink-400 hover:text-ink-700 dark:hover:text-[#F3F6F1] p-1"
                        title="Edit Customer"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!loading && customers.length === 0 && (
                <tr>
                  <td colSpan={9} className="py-10 text-center text-sm text-ink-500">
                    No customers found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
      </div>

      {/* Customer 360 Overview Modal */}
      <Modal
        open={overviewOpen}
        onClose={() => setOverviewOpen(false)}
        title={overviewCustomer ? `${overviewCustomer.name} — Customer Record` : "Customer Record"}
        subtitle={`Customer ID: #${overviewCustomer?.id || ""}`}
      >
        <div className="space-y-4">
          {/* Quick Header Summary */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-4 bg-[#f8faf8] dark:bg-[#121c15] rounded-xl border border-line dark:border-[#293227]">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg text-ink-900 dark:text-[#F3F6F1]">{overviewCustomer?.name}</span>
                <StatusBadge status={overviewCustomer?.status || "Active"} />
              </div>
              <div className="flex flex-wrap items-center gap-4 text-xs text-ink-500 dark:text-[#8A968C]">
                <span className="flex items-center gap-1"><Phone className="w-3.5 h-3.5" /> {overviewCustomer?.contact}</span>
                {overviewCustomer?.email && <span className="flex items-center gap-1"><Mail className="w-3.5 h-3.5" /> {overviewCustomer?.email}</span>}
                <span className="flex items-center gap-1"><MapPin className="w-3.5 h-3.5" /> {overviewCustomer?.location}</span>
                <span className="flex items-center gap-1"><Building className="w-3.5 h-3.5" /> {overviewCustomer?.propertyType}</span>
              </div>
            </div>
            <button
              type="button"
              onClick={() => {
                setOverviewOpen(false);
                openEditModal(overviewCustomer);
              }}
              className="inline-flex items-center gap-1.5 text-xs font-medium border border-line dark:border-[#293227] px-3 py-1.5 rounded-lg hover:bg-white dark:hover:bg-[#1b271f] transition-colors"
            >
              <Edit2 className="w-3.5 h-3.5" />
              Edit Info
            </button>
          </div>

          {/* Sub Navigation Tabs */}
          <div className="flex border-b border-line dark:border-[#293227] gap-2 text-xs font-medium">
            <button
              type="button"
              onClick={() => setOverviewTab("overview")}
              className={`pb-2 px-2 border-b-2 transition-colors cursor-pointer ${
                overviewTab === "overview"
                  ? "border-leaf-600 text-leaf-600 dark:text-leaf-400 font-semibold"
                  : "border-transparent text-ink-500 hover:text-ink-800"
              }`}
            >
              Overview & Leads ({overviewData?.leads?.length || 0})
            </button>
            <button
              type="button"
              onClick={() => setOverviewTab("surveys")}
              className={`pb-2 px-2 border-b-2 transition-colors cursor-pointer ${
                overviewTab === "surveys"
                  ? "border-leaf-600 text-leaf-600 dark:text-leaf-400 font-semibold"
                  : "border-transparent text-ink-500 hover:text-ink-800"
              }`}
            >
              Site Surveys ({overviewData?.siteSurveys?.length || 0})
            </button>
            <button
              type="button"
              onClick={() => setOverviewTab("projects")}
              className={`pb-2 px-2 border-b-2 transition-colors cursor-pointer ${
                overviewTab === "projects"
                  ? "border-leaf-600 text-leaf-600 dark:text-leaf-400 font-semibold"
                  : "border-transparent text-ink-500 hover:text-ink-800"
              }`}
            >
              Projects ({overviewData?.projects?.length || 0})
            </button>
            <button
              type="button"
              onClick={() => setOverviewTab("timeline")}
              className={`pb-2 px-2 border-b-2 transition-colors cursor-pointer ${
                overviewTab === "timeline"
                  ? "border-leaf-600 text-leaf-600 dark:text-leaf-400 font-semibold"
                  : "border-transparent text-ink-500 hover:text-ink-800"
              }`}
            >
              Timeline ({overviewData?.activities?.length || 0})
            </button>
          </div>

          {/* Tab Content */}
          {overviewLoading ? (
            <div className="py-8 text-center text-xs text-ink-400">Loading relationship data...</div>
          ) : (
            <div className="min-h-[160px] max-h-[340px] overflow-y-auto pr-1">
              {overviewTab === "overview" && (
                <div className="space-y-4">
                  <div>
                    <h4 className="text-xs font-semibold text-ink-400 uppercase tracking-wider mb-2">Originated Leads</h4>
                    {overviewData?.leads?.length > 0 ? (
                      <div className="divide-y divide-line dark:divide-[#293227] border border-line dark:border-[#293227] rounded-xl overflow-hidden">
                        {overviewData.leads.map((l) => (
                          <div key={l.id} className="p-3 text-xs flex items-center justify-between">
                            <div>
                              <span className="font-semibold text-ink-900 dark:text-[#F3F6F1]">Lead #{l.id}</span>
                              <span className="text-ink-400 ml-2">Source: {l.source}</span>
                              <div className="text-ink-400 text-[11px] mt-0.5">{l.location} • {l.propertyType}</div>
                            </div>
                            <div className="text-right">
                              <StatusBadge status={l.status} />
                              <div className="text-ink-400 text-[11px] mt-1">{l.createdAt}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-ink-400 p-2">Direct customer record (no external lead history).</p>
                    )}
                  </div>
                </div>
              )}

              {overviewTab === "surveys" && (
                <div className="space-y-2">
                  {overviewData?.siteSurveys?.length > 0 ? (
                    overviewData.siteSurveys.map((s) => (
                      <div key={s.id} className="p-3 border border-line dark:border-[#293227] rounded-xl text-xs flex items-center justify-between">
                        <div>
                          <div className="font-semibold text-ink-900 dark:text-[#F3F6F1]">
                            Survey #{s.id} — {s.surveyDate} ({s.timeSlot})
                          </div>
                          <div className="text-ink-500 mt-0.5">
                            Surveyor: {s.assignedTo} • Est: {s.capacityEstimate || "N/A"}
                          </div>
                          {s.roofInformation && <div className="text-ink-400 text-[11px]">Roof: {s.roofInformation}</div>}
                        </div>
                        <StatusBadge status={s.status} />
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-ink-400 py-6 text-center">No site surveys scheduled for this customer.</p>
                  )}
                </div>
              )}

              {overviewTab === "projects" && (
                <div className="space-y-2">
                  {overviewData?.projects?.length > 0 ? (
                    overviewData.projects.map((p) => (
                      <div key={p.id} className="p-3 border border-line dark:border-[#293227] rounded-xl text-xs flex items-center justify-between">
                        <div>
                          <div className="font-semibold text-ink-900 dark:text-[#F3F6F1]">
                            {p.name}
                          </div>
                          <div className="text-ink-500 mt-0.5">
                            Capacity: {p.capacity || `${p.capacityKW} kW`} • Category: {p.category}
                          </div>
                          {p.sourceLeadId && <span className="text-[11px] text-purple-600 dark:text-purple-400">Originated from Lead #{p.sourceLeadId}</span>}
                        </div>
                        <StatusBadge status={p.status} />
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-ink-400 py-6 text-center">No projects assigned to this customer yet.</p>
                  )}
                </div>
              )}

              {overviewTab === "timeline" && (
                <div className="space-y-3">
                  {overviewData?.activities?.length > 0 ? (
                    overviewData.activities.map((a) => (
                      <div key={a.id} className="flex items-start gap-2 text-xs">
                        <Clock className="w-3.5 h-3.5 text-leaf-600 mt-0.5 shrink-0" />
                        <div className="flex-1">
                          <p className="font-medium text-ink-900 dark:text-[#F3F6F1]">{a.title}</p>
                          <p className="text-ink-400 text-[11px]">{new Date(a.createdAt).toLocaleString()}</p>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-ink-400 py-6 text-center">No timeline activity logged.</p>
                  )}
                </div>
              )}
            </div>
          )}

          <div className="flex justify-end pt-2 border-t border-line dark:border-[#293227]">
            <button
              type="button"
              onClick={() => setOverviewOpen(false)}
              className="border border-line dark:border-[#293227] rounded-lg px-4 py-2 text-sm font-medium text-ink-600 dark:text-[#B9C4BB] hover:bg-[#f4f6f4] dark:hover:bg-[#152019] transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </Modal>

      {/* Edit / Create Form Modal */}
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editingCustomer ? "Edit Customer Details" : "Add New Customer"}
        subtitle="Customer records are stored in the PostgreSQL database."
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <FormField label="Full Name" required>
            <TextInput name="name" value={form.name} onChange={handleChange} placeholder="e.g. Rohan Patil" minLength={2} maxLength={150} required />
          </FormField>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormField label="Phone Number" required>
              <TextInput name="contact" value={form.contact} onChange={handleChange} placeholder="+91 98765 43210" minLength={3} maxLength={100} required />
            </FormField>
            <FormField label="Email">
              <TextInput type="email" name="email" value={form.email} onChange={handleChange} maxLength={254} placeholder="customer@example.com" />
            </FormField>
          </div>

          <FormField label="Location" required>
            <TextInput name="location" value={form.location} onChange={handleChange} placeholder="e.g. Mumbai" minLength={2} maxLength={150} required />
          </FormField>

          <div className="grid grid-cols-2 gap-4">
            <FormField label="Property Type">
              <SelectInput name="propertyType" value={form.propertyType} onChange={handleChange} options={["Residential", "Commercial", "Industrial"]} />
            </FormField>

            <FormField label="Status">
              <SelectInput name="status" value={form.status} onChange={handleChange} options={["Active", "Inactive"]} />
            </FormField>
          </div>

          <div className="flex items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={saving}
              className="bg-[#1F5C3E] hover:bg-[#184A32] dark:bg-[#3FA46A] dark:hover:bg-[#4CBE7C] text-white dark:text-[#0E1712] rounded-lg px-4 py-2.5 text-sm font-medium transition-colors disabled:opacity-60"
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
            <button
              type="button"
              onClick={() => setModalOpen(false)}
              className="ml-auto border border-line dark:border-[#293227] rounded-lg px-4 py-2.5 text-sm font-medium text-ink-600 dark:text-[#B9C4BB] hover:bg-[#f4f6f4] dark:hover:bg-[#152019] transition-colors"
            >
              Cancel
            </button>
          </div>

        </form>
      </Modal>
    </div>
  );
}
