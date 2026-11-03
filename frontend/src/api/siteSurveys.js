import apiClient from "./client";
import { toSurvey } from "../services/mappers";

export const siteSurveysApi = {
  async getSiteSurveys(params = {}) {
    const query = new URLSearchParams();
    if (params.page) query.append("page", params.page);
    if (params.limit) query.append("limit", params.limit);
    if (params.search) query.append("search", params.search);
    if (params.status && !["All Surveys", "All Status", "All Statuses"].includes(params.status)) {
      query.append("status", params.status);
    }

    const queryString = query.toString();
    const url = `/site-surveys${queryString ? `?${queryString}` : ""}`;
    const response = await apiClient(url);
    if (response && Array.isArray(response.items)) {
      response.items = response.items.map(toSurvey);
    } else if (Array.isArray(response)) {
      return response.map(toSurvey);
    }
    return response;
  },

  async exportCSV(params = {}) {
    const query = new URLSearchParams();
    if (params.search) query.append("search", params.search);
    if (params.status && !["All Surveys", "All Status", "All Statuses"].includes(params.status)) {
      query.append("status", params.status);
    }
    const queryString = query.toString();
    const url = `/site-surveys/export${queryString ? `?${queryString}` : ""}`;
    const blob = await apiClient(url, { isBlob: true });
    
    // Trigger browser download
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = `site_surveys_${new Date().toISOString().split("T")[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(downloadUrl);
  },

  async getSiteSurvey(id) {
    const response = await apiClient(`/site-surveys/${id}`);
    return response ? toSurvey(response) : response;
  },

  async createSiteSurvey(data) {
    return await apiClient("/site-surveys", {
      method: "POST",
      body: data,
    });
  },

  async updateSiteSurvey(id, data) {
    return await apiClient(`/site-surveys/${id}`, {
      method: "PATCH",
      body: data,
    });
  },

  async deleteSiteSurvey(id) {
    return await apiClient(`/site-surveys/${id}`, {
      method: "DELETE",
    });
  },

  async startSiteSurvey(id) {
    return await apiClient(`/site-surveys/${id}/start`, {
      method: "POST",
    });
  },

  async completeSiteSurvey(id, data = {}) {
    return await apiClient(`/site-surveys/${id}/complete`, {
      method: "POST",
      body: data,
    });
  },

  async cancelSiteSurvey(id, reason = "") {
    return await apiClient(`/site-surveys/${id}/cancel`, {
      method: "POST",
      body: { reason },
    });
  },
};

export default siteSurveysApi;
