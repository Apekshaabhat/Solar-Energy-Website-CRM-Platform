import React, { useState, useEffect, useCallback } from "react";
import { Plus, Pencil, Trash2, Search, HelpCircle, CheckCircle2 } from "lucide-react";
import { faqsApi } from "../../api/faqs";
import Modal from "../../components/dashboard/Modal";
import { FormField, TextInput } from "../../components/dashboard/FormField";

const CATEGORIES = ["General", "Installation", "Financial", "Maintenance", "Technical"];

const emptyForm = {
  question: "",
  answer: "",
  category: "General",
  displayOrder: 0,
};

export default function Faqs() {
  const [faqs, setFaqs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("All");

  const [modalOpen, setModalOpen] = useState(false);
  const [editingFaq, setEditingFaq] = useState(null);
  const [form, setForm] = useState(emptyForm);

  const loadFaqs = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await faqsApi.getFaqs({
        search: search.trim() || undefined,
        category: category !== "All" ? category : undefined,
      });
      const items = Array.isArray(response) ? response : response.items || [];
      setFaqs(items);
    } catch (err) {
      setError(err.message || "Failed to load FAQs.");
    } finally {
      setLoading(false);
    }
  }, [search, category]);

  useEffect(() => {
    loadFaqs();
  }, [loadFaqs]);

  const handleOpenCreate = () => {
    setEditingFaq(null);
    setForm(emptyForm);
    setModalOpen(true);
  };

  const handleOpenEdit = (faq) => {
    setEditingFaq(faq);
    setForm({
      question: faq.question || "",
      answer: faq.answer || "",
      category: faq.category || "General",
      displayOrder: faq.display_order ?? faq.displayOrder ?? 0,
    });
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.question.trim() || !form.answer.trim()) return;

    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const payload = {
        question: form.question.trim(),
        answer: form.answer.trim(),
        category: form.category,
        display_order: Number(form.displayOrder) || 0,
      };

      if (editingFaq) {
        await faqsApi.updateFaq(editingFaq.id, payload);
        setSuccess("FAQ updated successfully.");
      } else {
        await faqsApi.createFaq(payload);
        setSuccess("FAQ created successfully.");
      }
      setModalOpen(false);
      await loadFaqs();
    } catch (err) {
      setError(err.message || "Failed to save FAQ.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this FAQ?")) return;
    setSaving(true);
    try {
      await faqsApi.deleteFaq(id);
      setSuccess("FAQ deleted.");
      await loadFaqs();
    } catch (err) {
      setError(err.message || "Failed to delete FAQ.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white tracking-tight">
            FAQs Management
          </h1>
          <p className="text-sm sm:text-base text-gray-500 dark:text-gray-400 mt-1">
            Manage frequently asked questions and support content for solar customers.
          </p>
        </div>
        <button
          type="button"
          onClick={handleOpenCreate}
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-full bg-[#1F5C3E] hover:bg-[#184a32] text-white text-sm font-medium shadow-sm transition-colors cursor-pointer shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>Add New FAQ</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/20 border border-red-200 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {success && (
        <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 text-sm text-emerald-700 dark:text-emerald-300 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          {success}
        </div>
      )}

      <div className="flex flex-col sm:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search FAQs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] text-sm text-gray-900 dark:text-white placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30"
          />
        </div>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30"
        >
          <option value="All">All Categories</option>
          {CATEGORIES.map((cat) => (
            <option key={cat} value={cat}>
              {cat}
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-4">
        {loading ? (
          <div className="p-12 text-center text-sm text-gray-500">Loading FAQs...</div>
        ) : faqs.length > 0 ? (
          faqs.map((faq) => (
            <div
              key={faq.id}
              className="bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-2xl p-5 shadow-sm space-y-2 flex items-start justify-between gap-4"
            >
              <div className="space-y-1.5 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs px-2.5 py-0.5 rounded-md font-semibold bg-gray-100 dark:bg-[#0E1712] text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-[#293227]">
                    {faq.category || "General"}
                  </span>
                  <h3 className="text-base font-bold text-gray-900 dark:text-white">
                    {faq.question}
                  </h3>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
                  {faq.answer}
                </p>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button
                  type="button"
                  onClick={() => handleOpenEdit(faq)}
                  className="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-[#0E1712] transition-colors"
                  title="Edit FAQ"
                >
                  <Pencil className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={() => handleDelete(faq.id)}
                  className="p-1.5 rounded-lg text-red-500 hover:bg-red-50 dark:hover:bg-red-950/20 transition-colors"
                  title="Delete FAQ"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))
        ) : (
          <div className="p-12 text-center text-sm text-gray-500">No FAQs found.</div>
        )}
      </div>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editingFaq ? "Edit FAQ" : "Add FAQ"}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <FormField label="Question" required>
            <TextInput
              name="question"
              value={form.question}
              onChange={(e) => setForm((f) => ({ ...f, question: e.target.value }))}
              placeholder="e.g. How long does a typical installation take?"
              required
            />
          </FormField>

          <FormField label="Answer" required>
            <textarea
              name="answer"
              rows={4}
              value={form.answer}
              onChange={(e) => setForm((f) => ({ ...f, answer: e.target.value }))}
              placeholder="Provide a detailed, clear explanation..."
              required
              className="w-full px-3.5 py-2.5 bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] rounded-xl text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30 resize-none"
            />
          </FormField>

          <div className="grid grid-cols-2 gap-3">
            <FormField label="Category">
              <select
                name="category"
                value={form.category}
                onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
                className="w-full px-3.5 py-2.5 bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] rounded-xl text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30"
              >
                {CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </FormField>

            <FormField label="Display Order">
              <TextInput
                type="number"
                name="displayOrder"
                value={form.displayOrder}
                onChange={(e) => setForm((f) => ({ ...f, displayOrder: e.target.value }))}
              />
            </FormField>
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => setModalOpen(false)}
              className="px-4 py-2.5 border border-gray-200 dark:border-[#293227] rounded-xl text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-[#0E1712]"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2.5 bg-[#1F5C3E] hover:bg-[#184a32] text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-60"
            >
              {saving ? "Saving..." : "Save FAQ"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
