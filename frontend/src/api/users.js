import apiClient from "./client";

export const usersApi = {
  async getUsers(params = {}) {
    const query = new URLSearchParams();
    if (params.page) query.append("page", params.page);
    if (params.limit) query.append("limit", params.limit);
    if (params.search) query.append("search", params.search);
    if (params.role && params.role !== "All Roles") query.append("role", params.role);
    if (params.status && params.status !== "All Status") query.append("status", params.status);

    const queryString = query.toString();
    const url = `/users${queryString ? `?${queryString}` : ""}`;
    return await apiClient(url);
  },

  async getUser(id) {
    return await apiClient(`/users/${id}`);
  },

  async createUser(data) {
    return await apiClient("/users", {
      method: "POST",
      body: data,
    });
  },

  async updateUser(id, data) {
    return await apiClient(`/users/${id}`, {
      method: "PATCH",
      body: data,
    });
  },

  async deleteUser(id) {
    return await apiClient(`/users/${id}`, {
      method: "DELETE",
    });
  },
};

export default usersApi;
