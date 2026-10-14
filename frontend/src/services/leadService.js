import { apiRequest, unwrapData } from "./api";
import { toLead, toLeadPayload } from "./mappers";

export const leadService = {
  async getLeads(params = {}) {
    const response = await apiRequest("/leads", { params });
    return {
      ...response,
      items: (response.items || []).map(toLead),
      tabCounts: response.tab_counts ?? response.tabCounts ?? {},
    };
  },

  async getLead(id) {
    const response = await apiRequest(`/leads/${id}`);
    return toLead(unwrapData(response));
  },

  async createLead(payload) {
    const response = await apiRequest("/leads", {
      method: "POST",
      body: toLeadPayload(payload),
    });
    return toLead(unwrapData(response));
  },

  async updateLead(id, payload) {
    const response = await apiRequest(`/leads/${id}`, {
      method: "PATCH",
      body: toLeadPayload(payload),
    });
    return toLead(unwrapData(response));
  },

  async deleteLead(id) {
    const response = await apiRequest(`/leads/${id}`, { method: "DELETE" });
    return unwrapData(response);
  },

  async contactLead(id) {
    const response = await apiRequest(`/leads/${id}/contact`, {
      method: "POST",
    });
    return unwrapData(response);
  },

  async scheduleSurvey(id, payload) {
    const response = await apiRequest(`/leads/${id}/schedule-survey`, {
      method: "POST",
      body: payload,
    });
    return unwrapData(response);
  },

  async convertLead(id, payload) {
    const response = await apiRequest(`/leads/${id}/convert`, {
      method: "POST",
      body: payload,
    });
    return unwrapData(response);
  },

  async cancelLead(id, status = "Cancelled") {
    const response = await apiRequest(`/leads/${id}/cancel?status_val=${encodeURIComponent(status)}`, {
      method: "POST",
    });
    return unwrapData(response);
  },

  async getLeadRelatedData(id) {
    const response = await apiRequest(`/leads/${id}/related-data`);
    return unwrapData(response);
  },
};

