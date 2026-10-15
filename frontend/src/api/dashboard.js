import apiClient from "./client";

export const dashboardApi = {
  async getSummary() {
    return await apiClient("/dashboard/summary");
  },

  async getActivities(limit = 10) {
    return await apiClient(`/dashboard/activities?limit=${limit}`);
  },
};

export default dashboardApi;
