import apiClient from "./client";

export const blogsApi = {
  async getBlogs(params = {}) {
    const query = new URLSearchParams();
    if (params.page) query.append("page", params.page);
    if (params.limit) query.append("limit", params.limit);
    if (params.search) query.append("search", params.search);
    if (params.status && !["All Status", "All Statuses"].includes(params.status)) {
      query.append("status", params.status);
    }
    if (params.category && params.category !== "All Categories") {
      query.append("category", params.category);
    }

    const queryString = query.toString();
    const url = `/blogs${queryString ? `?${queryString}` : ""}`;
    return await apiClient(url);
  },

  async getBlog(idOrSlug) {
    return await apiClient(`/blogs/${idOrSlug}`);
  },

  async createBlog(data) {
    return await apiClient("/blogs", {
      method: "POST",
      body: data,
    });
  },

  async updateBlog(id, data) {
    return await apiClient(`/blogs/${id}`, {
      method: "PATCH",
      body: data,
    });
  },

  async deleteBlog(id) {
    return await apiClient(`/blogs/${id}`, {
      method: "DELETE",
    });
  },
};

export default blogsApi;
