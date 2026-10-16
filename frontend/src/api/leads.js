import apiClient from "./client";

export const leadsApi = {
  async getLeads(params = {}) {
    const query = new URLSearchParams();
    if (params.page) query.append("page", params.page);
    if (params.limit) query.append("limit", params.limit);
    if (params.search) query.append("search", params.search);
    if (params.status && !["All Leads", "All Status", "All Statuses"].includes(params.status)) {
      query.append("status", params.status);
    }
    if (params.property_type && params.property_type !== "All Property Types") {
      query.append("property_type", params.property_type);
    }
    if (params.location && params.location !== "All Locations") {
      query.append("location", params.location);
    }
    if (params.source && params.source !== "All Sources") {
      query.append("source", params.source);
    }

    const queryString = query.toString();
    const url = `/leads${queryString ? `?${queryString}` : ""}`;
    return await apiClient(url);
  },

  async getLead(id) {
    return await apiClient(`/leads/${id}`);
  },

  async createLead(data) {
    return await apiClient("/leads", {
      method: "POST",
      body: data,
    });
  },

  async updateLead(id, data) {
    return await apiClient(`/leads/${id}`, {
      method: "PATCH",
      body: data,
    });
  },

  async deleteLead(id) {
    return await apiClient(`/leads/${id}`, {
      method: "DELETE",
    });
  },

  async contactLead(id) {
    return await apiClient(`/leads/${id}/contact`, {
      method: "POST",
    });
  },

  async scheduleSurvey(id, data) {
    return await apiClient(`/leads/${id}/schedule-survey`, {
      method: "POST",
      body: data,
    });
  },

  async convertLead(id, data = {}) {
    return await apiClient(`/leads/${id}/convert`, {
      method: "POST",
      body: data,
    });
  },

  async cancelLead(id, reason = "") {
    return await apiClient(`/leads/${id}/cancel`, {
      method: "POST",
      body: { reason },
    });
  },

  async getRelatedData(id) {
    return await apiClient(`/leads/${id}/related-data`);
  },
};

export default leadsApi;
