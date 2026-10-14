import { apiRequest } from "./api";

export const dashboardService = {
  async getSummary() {
    return apiRequest("/dashboard/summary");
  },

  async getActivities(limit = 10) {
    return apiRequest(`/dashboard/activities?limit=${limit}`);
  },
};
