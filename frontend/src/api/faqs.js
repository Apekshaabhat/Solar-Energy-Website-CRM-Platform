import apiClient from "./client";

export const faqsApi = {
  async getFaqs(params = {}) {
    const query = new URLSearchParams();
    if (params.page) query.append("page", params.page);
    if (params.limit) query.append("limit", params.limit);
    if (params.search) query.append("search", params.search);
    if (params.category && params.category !== "All Categories") {
      query.append("category", params.category);
    }
    if (params.is_active !== undefined) {
      query.append("is_active", params.is_active);
    }

    const queryString = query.toString();
    const url = `/faqs${queryString ? `?${queryString}` : ""}`;
    return await apiClient(url);
  },

  async getFaq(id) {
    return await apiClient(`/faqs/${id}`);
  },

  async createFaq(data) {
    return await apiClient("/faqs", {
      method: "POST",
      body: data,
    });
  },

  async updateFaq(id, data) {
    return await apiClient(`/faqs/${id}`, {
      method: "PATCH",
      body: data,
    });
  },

  async deleteFaq(id) {
    return await apiClient(`/faqs/${id}`, {
      method: "DELETE",
    });
  },
};

export default faqsApi;
