import apiClient from "./client";

export const calculatorsApi = {
  async estimateSavings(data) {
    return await apiClient("/calculators/savings-estimate", {
      method: "POST",
      body: data,
    });
  },

  async estimateRoofCapacity(data) {
    return await apiClient("/calculators/roof-capacity", {
      method: "POST",
      body: data,
    });
  },

  async estimateROI(data) {
    return await apiClient("/calculators/roi-estimate", {
      method: "POST",
      body: data,
    });
  },

  async getSubmissions(params = {}) {
    const query = new URLSearchParams();
    if (params.page) query.append("page", params.page);
    if (params.limit) query.append("limit", params.limit);
    if (params.search) query.append("search", params.search);
    if (params.calculator_type && params.calculator_type !== "All Types") {
      query.append("calculator_type", params.calculator_type);
    }

    const queryString = query.toString();
    const url = `/calculators/submissions${queryString ? `?${queryString}` : ""}`;
    return await apiClient(url);
  },

  async createSubmission(data) {
    return await apiClient("/calculators/submissions", {
      method: "POST",
      body: data,
    });
  },

  async getSettings() {
    return await apiClient("/calculators/settings");
  },

  async updateSettings(data) {
    return await apiClient("/calculators/settings", {
      method: "PUT",
      body: data,
    });
  },
};

export default calculatorsApi;
