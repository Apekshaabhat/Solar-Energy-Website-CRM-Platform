import apiClient from "./client";

export const settingsApi = {
  async getSettings() {
    return await apiClient("/settings");
  },

  async updateSettings(data) {
    return await apiClient("/settings", {
      method: "PUT",
      body: data,
    });
  },
};

export default settingsApi;
