import React, { useState, useEffect, useCallback } from "react";
import {
  Plus,
  Search,
  Pencil,
  Trash2,
  Image as ImageIcon,
  X,
  ChevronLeft,
  ChevronRight,
  FileText,
} from "lucide-react";
import { blogsApi } from "../../api/blogs";

const CATEGORIES = [
  "Guides",
  "Savings",
  "Policy",
  "Maintenance",
  "Technology",
  "Case Study",
];

const ITEMS_PER_PAGE = 5;

const emptyForm = {
  title: "",
  category: "Guides",
  status: "Draft",
  coverImage: "",
  excerpt: "",
  content: "",
};

export default function BlogManagement() {
  const [posts, setPosts] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [selectedStatus, setSelectedStatus] = useState("All");
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingPost, setEditingPost] = useState(null);
  const [formData, setFormData] = useState(emptyForm);

  const loadPosts = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await blogsApi.getBlogs({
        page: currentPage,
        limit: ITEMS_PER_PAGE,
        search: searchQuery.trim(),
        category: selectedCategory !== "All" ? selectedCategory : undefined,
        status: selectedStatus !== "All" ? selectedStatus : undefined,
      });
      const items = Array.isArray(response) ? response : response.items || [];
      setPosts(items);
      setTotalPages(response.meta?.total_pages || response.total_pages || 1);
    } catch (err) {
      setError(err.message || "Failed to load blog posts.");
    } finally {
      setLoading(false);
    }
  }, [currentPage, searchQuery, selectedCategory, selectedStatus]);

  useEffect(() => {
    loadPosts();
  }, [loadPosts]);

  // Modal Handlers
  const handleOpenCreateModal = () => {
    setEditingPost(null);
    setFormData(emptyForm);
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (post) => {
    setEditingPost(post);
    setFormData({
      title: post.title,
      category: post.category || "Guides",
      status: post.status || "Draft",
      coverImage: post.cover_image || post.coverImage || "",
      excerpt: post.excerpt || "",
      content: post.content || "",
    });
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingPost(null);
    setFormData(emptyForm);
  };

  const handleSavePost = async (e) => {
    e.preventDefault();
    if (!formData.title.trim()) return;

    setSaving(true);
    setError("");
    try {
      const payload = {
        title: formData.title.trim(),
        category: formData.category,
        status: formData.status,
        cover_image: formData.coverImage.trim() || undefined,
        excerpt: formData.excerpt.trim() || undefined,
        content: formData.content.trim() || formData.excerpt.trim() || undefined,
      };

      if (editingPost) {
        await blogsApi.updateBlog(editingPost.id, payload);
      } else {
        await blogsApi.createBlog(payload);
      }
      closeModal();
      await loadPosts();
    } catch (err) {
      setError(err.message || "Failed to save blog post.");
    } finally {
      setSaving(false);
    }
  };

  const handleDeletePost = async (id) => {
    if (window.confirm("Are you sure you want to delete this blog post?")) {
      setSaving(true);
      try {
        await blogsApi.deleteBlog(id);
        await loadPosts();
      } catch (err) {
        setError(err.message || "Failed to delete post.");
      } finally {
        setSaving(false);
      }
    }
  };

  const safeCurrentPage = currentPage;

  return (
    <div className="space-y-6">
      {/* Header Row */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">
            Blog Management
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Create, edit, and publish articles for the Solara blog.
          </p>
        </div>
        <button
          type="button"
          onClick={handleOpenCreateModal}
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-full bg-[#1F5C3E] hover:bg-[#184a32] text-white text-sm font-medium shadow-sm transition-colors focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/50 shrink-0 cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>New Post</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
        {/* Search Input */}
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-gray-500 pointer-events-none" />
          <input
            type="text"
            placeholder="Search posts by title..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] text-sm text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30 focus:border-[#1F5C3E] dark:focus:border-[#1F5C3E] transition-colors"
          />
        </div>

        {/* Category Dropdown */}
        <select
          value={selectedCategory}
          onChange={(e) => {
            setSelectedCategory(e.target.value);
            setCurrentPage(1);
          }}
          className="px-3.5 py-2.5 rounded-xl bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30 focus:border-[#1F5C3E] dark:focus:border-[#1F5C3E] transition-colors cursor-pointer"
        >
          <option value="All">All Categories</option>
          {CATEGORIES.map((cat) => (
            <option key={cat} value={cat}>
              {cat}
            </option>
          ))}
        </select>

        {/* Status Dropdown */}
        <select
          value={selectedStatus}
          onChange={(e) => {
            setSelectedStatus(e.target.value);
            setCurrentPage(1);
          }}
          className="px-3.5 py-2.5 rounded-xl bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30 focus:border-[#1F5C3E] dark:focus:border-[#1F5C3E] transition-colors cursor-pointer"
        >
          <option value="All">All Statuses</option>
          <option value="Published">Published</option>
          <option value="Draft">Draft</option>
        </select>
      </div>

      {/* Posts Table Container */}
      <div className="bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-2xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto no-scrollbar">
          <table className="w-full text-left text-sm border-collapse min-w-[700px]">
            <thead>
              <tr className="bg-gray-50/80 dark:bg-[#0E1712]/80 border-b border-gray-200 dark:border-[#293227] text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <th className="py-3.5 px-5">Title</th>
                <th className="py-3.5 px-4">Category</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4">Author</th>
                <th className="py-3.5 px-4">Date</th>
                <th className="py-3.5 px-5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-[#293227]/60 text-gray-800 dark:text-gray-200">
              {posts.length > 0 ? (
                posts.map((post) => (
                  <tr
                    key={post.id}
                    className="hover:bg-gray-50/80 dark:hover:bg-[#152019]/60 transition-colors"
                  >
                    <td className="py-4 px-5 max-w-xs sm:max-w-md">
                      <div className="flex items-center gap-3">
                        {post.cover_image || post.coverImage ? (
                          <img
                            src={post.cover_image || post.coverImage}
                            alt={post.title}
                            className="w-10 h-10 rounded-lg object-cover shrink-0 border border-gray-200 dark:border-[#293227]"
                            onError={(e) => {
                              e.target.style.display = "none";
                            }}
                          />
                        ) : (
                          <div className="w-10 h-10 rounded-lg bg-gray-100 dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] flex items-center justify-center shrink-0">
                            <FileText className="w-5 h-5 text-gray-400 dark:text-gray-500" />
                          </div>
                        )}
                        <div className="min-w-0">
                          <p className="font-semibold text-gray-900 dark:text-white truncate">
                            {post.title}
                          </p>
                          {post.excerpt && (
                            <p className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-xs">
                              {post.excerpt}
                            </p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-4 whitespace-nowrap text-gray-600 dark:text-gray-300">
                      <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-gray-100 dark:bg-[#0E1712] text-gray-700 dark:text-gray-300 border border-gray-200/80 dark:border-[#293227]">
                        {post.category}
                      </span>
                    </td>
                    <td className="py-4 px-4 whitespace-nowrap">
                      {post.status === "Published" ? (
                        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200/60 dark:border-emerald-800/40">
                          Published
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-800/60 text-gray-700 dark:text-gray-300 border border-gray-200/60 dark:border-gray-700/60">
                          Draft
                        </span>
                      )}
                    </td>
                    <td className="py-4 px-4 whitespace-nowrap text-gray-600 dark:text-gray-300">
                      {post.author || "Admin"}
                    </td>
                    <td className="py-4 px-4 whitespace-nowrap text-xs text-gray-500 dark:text-gray-400">
                      {post.created_at ? new Date(post.created_at).toLocaleDateString() : (post.date || "—")}
                    </td>
                    <td className="py-4 px-5 whitespace-nowrap text-right">
                      <div className="inline-flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => handleOpenEditModal(post)}
                          title="Edit post"
                          className="p-1.5 rounded-lg text-gray-500 dark:text-gray-400 hover:text-[#1F5C3E] dark:hover:text-emerald-400 hover:bg-gray-100 dark:hover:bg-[#0E1712] transition-colors cursor-pointer"
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeletePost(post.id)}
                          title="Delete post"
                          className="p-1.5 rounded-lg text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors cursor-pointer"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    colSpan={6}
                    className="py-12 px-4 text-center text-gray-500 dark:text-gray-400 text-sm"
                  >
                    No posts match your filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Container (Only rendered when totalPages > 1) */}
        {totalPages > 1 && (
          <div className="px-5 py-4 border-t border-gray-200 dark:border-[#293227] flex items-center justify-between bg-gray-50/50 dark:bg-[#0E1712]/50">
            <span className="text-xs text-gray-500 dark:text-gray-400">
              Page {safeCurrentPage} of {totalPages}
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={safeCurrentPage === 1}
                onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium border border-gray-200 dark:border-[#293227] bg-white dark:bg-[#17221B] text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-[#0E1712] disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                Previous
              </button>
              <button
                type="button"
                disabled={safeCurrentPage === totalPages}
                onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium border border-gray-200 dark:border-[#293227] bg-white dark:bg-[#17221B] text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-[#0E1712] disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
              >
                Next
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Shared Create / Edit Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 dark:bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div
            className="bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-2xl w-full max-w-lg shadow-xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-gray-200 dark:border-[#293227] flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">
                {editingPost ? "Edit Post" : "Create New Post"}
              </h2>
              <button
                type="button"
                onClick={closeModal}
                className="p-1 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-[#0E1712] transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Form */}
            <form onSubmit={handleSavePost}>
              <div className="p-6 space-y-4 max-h-[70vh] overflow-y-auto">
                {/* Title */}
                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                    Title <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. 10 Ways Solar Lowers Energy Bills"
                    value={formData.title}
                    onChange={(e) =>
                      setFormData((f) => ({ ...f, title: e.target.value }))
                    }
                    className="w-full px-3.5 py-2.5 rounded-xl bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] text-sm text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30 focus:border-[#1F5C3E] dark:focus:border-[#1F5C3E] transition-colors"
                  />
                </div>

                {/* Category & Status */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                      Category
                    </label>
                    <select
                      value={formData.category}
                      onChange={(e) =>
                        setFormData((f) => ({ ...f, category: e.target.value }))
                      }
                      className="w-full px-3.5 py-2.5 rounded-xl bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30 focus:border-[#1F5C3E] dark:focus:border-[#1F5C3E] transition-colors cursor-pointer"
                    >
                      {CATEGORIES.map((cat) => (
                        <option key={cat} value={cat}>
                          {cat}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                      Status
                    </label>
                    <select
                      value={formData.status}
                      onChange={(e) =>
                        setFormData((f) => ({ ...f, status: e.target.value }))
                      }
                      className="w-full px-3.5 py-2.5 rounded-xl bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30 focus:border-[#1F5C3E] dark:focus:border-[#1F5C3E] transition-colors cursor-pointer"
                    >
                      <option value="Draft">Draft</option>
                      <option value="Published">Published</option>
                    </select>
                  </div>
                </div>

                {/* Cover Image URL */}
                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                    Cover Image URL
                  </label>
                  <div className="relative">
                    <ImageIcon className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-gray-500 pointer-events-none" />
                    <input
                      type="text"
                      placeholder="https://example.com/image.jpg"
                      value={formData.coverImage}
                      onChange={(e) =>
                        setFormData((f) => ({ ...f, coverImage: e.target.value }))
                      }
                      className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] text-sm text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30 focus:border-[#1F5C3E] dark:focus:border-[#1F5C3E] transition-colors"
                    />
                  </div>
                </div>

                {/* Excerpt */}
                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                    Excerpt
                  </label>
                  <textarea
                    rows={4}
                    placeholder="Brief summary or hook for the article..."
                    value={formData.excerpt}
                    onChange={(e) =>
                      setFormData((f) => ({ ...f, excerpt: e.target.value }))
                    }
                    className="w-full px-3.5 py-2.5 rounded-xl bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] text-sm text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30 focus:border-[#1F5C3E] dark:focus:border-[#1F5C3E] transition-colors resize-none"
                  />
                </div>
              </div>

              {/* Modal Footer */}
              <div className="px-6 py-4 border-t border-gray-200 dark:border-[#293227] flex items-center justify-end gap-3 bg-gray-50/50 dark:bg-[#0E1712]/50">
                <button
                  type="button"
                  onClick={closeModal}
                  className="px-4 py-2 rounded-xl text-sm font-medium border border-gray-200 dark:border-[#293227] text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-[#0E1712] transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!formData.title.trim()}
                  className="px-4 py-2 rounded-xl text-sm font-medium bg-[#1F5C3E] hover:bg-[#184a32] text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm cursor-pointer"
                >
                  {editingPost ? "Save Changes" : "Publish Post"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
