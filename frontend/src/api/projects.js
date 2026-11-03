import apiClient from "./client";
import { toProject } from "../services/mappers";

export const projectsApi = {
  async getProjects(params = {}) {
    const query = new URLSearchParams();
    if (params.page) query.append("page", params.page);
    if (params.limit) query.append("limit", params.limit);
    if (params.search) query.append("search", params.search);
    if (params.status && !["All Projects", "All Status", "All Statuses"].includes(params.status)) {
      query.append("status", params.status);
    }
    if (params.system_capacity && params.system_capacity !== "All Capacities") {
      query.append("system_capacity", params.system_capacity);
    }

    const queryString = query.toString();
    const url = `/projects${queryString ? `?${queryString}` : ""}`;
    const response = await apiClient(url);
    if (Array.isArray(response)) {
      return response.map(toProject);
    }
    if (response && Array.isArray(response.items)) {
      response.items = response.items.map(toProject);
    }
    return response;
  },

  async getProject(id) {
    const response = await apiClient(`/projects/${id}`);
    return response ? toProject(response) : response;
  },

  async createProject(data) {
    return await apiClient("/projects", {
      method: "POST",
      body: data,
    });
  },

  async updateProject(id, data) {
    return await apiClient(`/projects/${id}`, {
      method: "PATCH",
      body: data,
    });
  },

  async deleteProject(id) {
    return await apiClient(`/projects/${id}`, {
      method: "DELETE",
    });
  },

  async startProject(id) {
    return await apiClient(`/projects/${id}/start`, {
      method: "POST",
    });
  },

  async holdProject(id, reason = "") {
    return await apiClient(`/projects/${id}/hold`, {
      method: "POST",
      body: { reason },
    });
  },

  async resumeProject(id) {
    return await apiClient(`/projects/${id}/resume`, {
      method: "POST",
    });
  },

  async completeProject(id) {
    return await apiClient(`/projects/${id}/complete`, {
      method: "POST",
    });
  },

  async cancelProject(id, reason = "") {
    return await apiClient(`/projects/${id}/cancel`, {
      method: "POST",
      body: { reason },
    });
  },
};

export default projectsApi;
