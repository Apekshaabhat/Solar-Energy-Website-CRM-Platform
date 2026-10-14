import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FolderKanban, Pencil, CheckCircle2, UserCheck, IndianRupee, Play, Pause, XCircle, AlertCircle, RotateCcw } from "lucide-react";
import PageHeader from "../../components/dashboard/PageHeader";
import Modal from "../../components/dashboard/Modal";
import StatusBadge from "../../components/dashboard/StatusBadge";
import { FormField, SelectInput, TextInput } from "../../components/dashboard/FormField";
import { projectService } from "../../services/projectService";
import { useDashboardData } from "../../context/DashboardDataContext";

const emptyForm = {
  name: "",
  category: "Residential",
  location: "",
  capacity: "",
  capacityKW: "",
  estimatedCost: "",
  actualCost: "",
  status: "Planning",
  isPublic: true,
};

function toForm(project) {
  return {
    name: project.name || "",
    category: project.category || "Residential",
    location: project.location || "",
    capacity: project.capacity || "",
    capacityKW: project.capacityKW ?? "",
    estimatedCost: project.estimatedCost ?? "",
    actualCost: project.actualCost ?? "",
    status: project.status || "Planning",
    isPublic: Boolean(project.isPublic),
  };
}

export default function Projects() {
  const navigate = useNavigate();
  const { refreshToken, notifyCrmChange } = useDashboardData();
  const [projects, setProjects] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingProject, setEditingProject] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function loadProjects() {
    setLoading(true);
    setError("");
    try {
      const items = await projectService.getProjects();
      setProjects(items);
    } catch (err) {
      setError(err.message || "Unable to load projects.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadProjects();
  }, [refreshToken]);

  // Sequential Workflow 1: Start Project (Planning -> In Progress)
  async function handleStartProject(project) {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      await projectService.startProject(project.id);
      setMessage(`Project '${project.name}' is now In Progress.`);
      notifyCrmChange("projects");
      await loadProjects();
    } catch (err) {
      setError(err.message || "Failed to start project.");
    } finally {
      setSaving(false);
    }
  }

  // Sequential Workflow 2: Complete Project (In Progress -> Completed)
  async function handleCompleteProject(project) {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      await projectService.completeProject(project.id, {
        actualCost: project.estimatedCost,
      });
      setMessage(`Project '${project.name}' marked as Completed.`);
      notifyCrmChange("projects");
      notifyCrmChange("customers");
      await loadProjects();
    } catch (err) {
      setError(err.message || "Failed to complete project.");
    } finally {
      setSaving(false);
    }
  }

  // Sequential Workflow 3: Put on Hold (In Progress -> On Hold)
  async function handleHoldProject(project) {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      await projectService.holdProject(project.id);
      setMessage(`Project '${project.name}' is now On Hold.`);
      notifyCrmChange("projects");
      await loadProjects();
    } catch (err) {
      setError(err.message || "Failed to put project on hold.");
    } finally {
      setSaving(false);
    }
  }

  // Sequential Workflow 4: Resume Project (On Hold -> In Progress)
  async function handleResumeProject(project) {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      await projectService.resumeProject(project.id);
      setMessage(`Project '${project.name}' resumed to In Progress.`);
      notifyCrmChange("projects");
      await loadProjects();
    } catch (err) {
      setError(err.message || "Failed to resume project.");
    } finally {
      setSaving(false);
    }
  }

  // Reverse Workflow 5: Cancel Project (soft transition preserving history)
  async function handleCancelProject(project) {
    if (!window.confirm(`Cancel project '${project.name}'? This will preserve CRM history and re-evaluate the customer status.`)) return;
    setSaving(true);
    setError("");
    setMessage("");
    try {
      await projectService.cancelProject(project.id);
      setMessage(`Project '${project.name}' cancelled. CRM history preserved.`);
      notifyCrmChange("projects");
      notifyCrmChange("customers");
      await loadProjects();
    } catch (err) {
      setError(err.message || "Failed to cancel project.");
    } finally {
      setSaving(false);
    }
  }

  function openEditModal(project) {
    setEditingProject(project);
    setForm(toForm(project));
    setModalOpen(true);
  }

  function handleChange(e) {
    const { name, value, type, checked } = e.target;
    setForm((f) => ({ ...f, [name]: type === "checkbox" ? checked : value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!editingProject) return;
    setSaving(true);
    setError("");
    try {
      await projectService.updateProject(editingProject.id, {
        name: form.name.trim(),
        category: form.category,
        location: form.location.trim(),
        capacity: form.capacity.trim(),
        capacity_kw: form.capacityKW ? Number(form.capacityKW) : undefined,
        estimated_cost: form.estimatedCost ? Number(form.estimatedCost) : undefined,
        actual_cost: form.actualCost ? Number(form.actualCost) : undefined,
        is_public: form.isPublic,
      });
      setMessage("Project details updated.");
      setModalOpen(false);
      setEditingProject(null);
      notifyCrmChange("projects");
      await loadProjects();
    } catch (err) {
      setError(err.message || "Unable to save project details.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Solar Projects"
        subtitle="Manage and track active installations generated automatically from converted leads. Sequential stages: Planning → In Progress → Completed."
      />

      {message && (
        <div className="rounded-xl border border-leaf-200 bg-leaf-50 dark:bg-leaf-950/20 px-4 py-3 text-sm text-leaf-700 dark:text-leaf-300 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          {message}
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 dark:bg-red-950/20 px-4 py-3 text-sm text-red-700 dark:text-red-300 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      <div className="bg-white dark:bg-[#17221B] rounded-2xl border border-line dark:border-[#293227] p-5 sm:p-6 space-y-5">
        <p className="text-sm text-ink-500">
          {loading ? "Loading projects..." : `Total Projects: ${projects.length}`}
        </p>

        <div className="overflow-x-auto no-scrollbar -mx-2">
          <table className="w-full text-sm min-w-[920px]">
            <thead>
              <tr className="text-left text-ink-400 dark:text-[#8A968C] text-xs uppercase tracking-wide border-b border-line dark:border-[#293227]">
                <th className="px-2 pb-3 font-medium">Project ID</th>
                <th className="px-2 pb-3 font-medium">Project Name</th>
                <th className="px-2 pb-3 font-medium">Customer & Source</th>
                <th className="px-2 pb-3 font-medium">Category</th>
                <th className="px-2 pb-3 font-medium">Capacity</th>
                <th className="px-2 pb-3 font-medium">Estimated Value</th>
                <th className="px-2 pb-3 font-medium">Status</th>
                <th className="px-2 pb-3 font-medium text-right">Workflow Actions</th>
              </tr>
            </thead>
            <tbody className="text-ink-800 dark:text-[#F3F6F1]">
              {projects.map((project) => (
                <tr key={project.id} className="border-t border-line dark:border-[#293227] hover:bg-[#f9faf9] dark:hover:bg-[#152019] transition-colors">
                  <td className="px-2 py-3 text-ink-400 font-mono text-xs">#{project.id}</td>
                  <td className="px-2 py-3 font-medium text-ink-900 dark:text-[#F3F6F1]">
                    <div>{project.name}</div>
                    <div className="text-xs text-ink-500 font-normal">{project.location}</div>
                  </td>
                  <td className="px-2 py-3">
                    {project.customerId ? (
                      <button
                        type="button"
                        onClick={() => navigate(`/dashboard/customers?id=${project.customerId}`)}
                        className="inline-flex items-center gap-1 text-xs text-leaf-600 dark:text-leaf-400 hover:underline cursor-pointer font-medium"
                      >
                        <UserCheck className="w-3.5 h-3.5" />
                        {project.customerName || `Customer #${project.customerId}`}
                      </button>
                    ) : (
                      <span className="text-xs text-ink-400">Direct Customer</span>
                    )}
                    {project.sourceLeadId && (
                      <span className="text-[11px] text-ink-400 block mt-0.5">From Lead #{project.sourceLeadId}</span>
                    )}
                  </td>
                  <td className="px-2 py-3 text-ink-600 dark:text-[#B9C4BB]">{project.category}</td>
                  <td className="px-2 py-3 font-medium text-ink-800 dark:text-[#E0E7E1]">{project.capacity}</td>
                  <td className="px-2 py-3 text-ink-700 dark:text-[#B9C4BB]">
                    {project.estimatedCost ? `₹${Number(project.estimatedCost).toLocaleString("en-IN")}` : "—"}
                  </td>
                  <td className="px-2 py-3">
                    <StatusBadge status={project.status} />
                  </td>
                  <td className="px-2 py-3 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      {/* Status = Planning: Start Project | Cancel Project */}
                      {project.status === "Planning" && (
                        <>
                          <button
                            type="button"
                            onClick={() => handleStartProject(project)}
                            disabled={saving}
                            className="inline-flex items-center gap-1 text-xs bg-leaf-600 hover:bg-leaf-700 text-white px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer"
                            title="Start project (transitions Planning -> In Progress)"
                          >
                            <Play className="w-3.5 h-3.5" />
                            Start Project
                          </button>
                          <button
                            type="button"
                            onClick={() => handleCancelProject(project)}
                            disabled={saving}
                            className="inline-flex items-center gap-1 text-xs text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20 border border-red-200 px-2 py-1.5 rounded-lg transition-colors cursor-pointer"
                            title="Cancel project"
                          >
                            <XCircle className="w-3.5 h-3.5" />
                            Cancel
                          </button>
                        </>
                      )}

                      {/* Status = In Progress: Complete | Put On Hold | Cancel */}
                      {project.status === "In Progress" && (
                        <>
                          <button
                            type="button"
                            onClick={() => handleCompleteProject(project)}
                            disabled={saving}
                            className="inline-flex items-center gap-1 text-xs bg-[#1F5C3E] hover:bg-[#184A32] text-white px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer"
                            title="Mark project as Completed"
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            Complete
                          </button>
                          <button
                            type="button"
                            onClick={() => handleHoldProject(project)}
                            disabled={saving}
                            className="inline-flex items-center gap-1 text-xs text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/30 hover:bg-amber-100 border border-amber-200 dark:border-amber-800 px-2 py-1.5 rounded-lg transition-colors cursor-pointer"
                            title="Put project on hold"
                          >
                            <Pause className="w-3.5 h-3.5" />
                            Hold
                          </button>
                          <button
                            type="button"
                            onClick={() => handleCancelProject(project)}
                            disabled={saving}
                            className="inline-flex items-center gap-1 text-xs text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20 border border-red-200 px-2 py-1.5 rounded-lg transition-colors cursor-pointer"
                            title="Cancel project"
                          >
                            <XCircle className="w-3.5 h-3.5" />
                            Cancel
                          </button>
                        </>
                      )}

                      {/* Status = On Hold: Resume | Cancel */}
                      {project.status === "On Hold" && (
                        <>
                          <button
                            type="button"
                            onClick={() => handleResumeProject(project)}
                            disabled={saving}
                            className="inline-flex items-center gap-1 text-xs bg-blue-600 hover:bg-blue-700 text-white px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer"
                            title="Resume project to In Progress"
                          >
                            <RotateCcw className="w-3.5 h-3.5" />
                            Resume
                          </button>
                          <button
                            type="button"
                            onClick={() => handleCancelProject(project)}
                            disabled={saving}
                            className="inline-flex items-center gap-1 text-xs text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20 border border-red-200 px-2 py-1.5 rounded-lg transition-colors cursor-pointer"
                            title="Cancel project"
                          >
                            <XCircle className="w-3.5 h-3.5" />
                            Cancel
                          </button>
                        </>
                      )}

                      {/* Edit Technical Parameters */}
                      <button
                        type="button"
                        onClick={() => openEditModal(project)}
                        className="text-ink-400 hover:text-ink-700 dark:hover:text-[#F3F6F1] p-1.5 rounded-lg hover:bg-line/40 transition-colors"
                        title="Edit project details"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!loading && projects.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-10 text-center text-sm text-ink-500">
                    No projects found. Projects are automatically provisioned when leads are converted.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edit Project Technical Parameters Modal */}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={`Edit Project Details (#${editingProject?.id || ""})`}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <FormField label="Project Name" required>
            <TextInput name="name" value={form.name} onChange={handleChange} required minLength={2} maxLength={150} />
          </FormField>

          <FormField label="Location" required>
            <TextInput name="location" value={form.location} onChange={handleChange} required minLength={2} maxLength={150} />
          </FormField>

          <div className="grid grid-cols-2 gap-3">
            <FormField label="Category">
              <SelectInput name="category" value={form.category} onChange={handleChange} options={["Residential", "Commercial", "Industrial"]} />
            </FormField>

            <FormField label="Capacity">
              <TextInput name="capacity" value={form.capacity} onChange={handleChange} placeholder="e.g. 10 kW" />
            </FormField>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <FormField label="Estimated Cost (₹)">
              <TextInput type="number" name="estimatedCost" value={form.estimatedCost} onChange={handleChange} />
            </FormField>

            <FormField label="Actual Cost (₹)">
              <TextInput type="number" name="actualCost" value={form.actualCost} onChange={handleChange} />
            </FormField>
          </div>

          <div className="flex items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={saving}
              className="bg-[#1F5C3E] hover:bg-[#184A32] dark:bg-[#3FA46A] text-white rounded-lg px-4 py-2.5 text-sm font-medium transition-colors disabled:opacity-60"
            >
              {saving ? "Saving..." : "Save Details"}
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
