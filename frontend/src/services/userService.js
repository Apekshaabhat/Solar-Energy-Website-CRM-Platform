import { apiRequest, unwrapData } from "./api";

export const userService = {
  async getUsers(params = {}) {
    const response = await apiRequest("/users", { params });
    return unwrapData(response) || [];
  },

  async getUser(id) {
    const response = await apiRequest(`/users/${id}`);
    return unwrapData(response);
  },

  async inviteUser(payload) {
    const response = await apiRequest("/users/invite", {
      method: "POST",
      body: payload,
    });
    return unwrapData(response);
  },

  async getStats() {
    const response = await apiRequest("/users/stats");
    return unwrapData(response);
  },

  async createUser(payload) {
    const response = await apiRequest("/users", {
      method: "POST",
      body: payload,
    });
    return unwrapData(response);
  },

  async updateUser(id, payload) {
    const response = await apiRequest(`/users/${id}`, {
      method: "PATCH",
      body: payload,
    });
    return unwrapData(response);
  },

  async deleteUser(id) {
    const response = await apiRequest(`/users/${id}`, { method: "DELETE" });
    return unwrapData(response);
  },

  async backfillCustomers() {
    const response = await apiRequest("/users/backfill-customers", {
      method: "POST",
    });
    return unwrapData(response);
  },
};

