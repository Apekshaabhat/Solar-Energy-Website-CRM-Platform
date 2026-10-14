import { apiRequest, unwrapData } from "./api";
import { toProject, toProjectPayload } from "./mappers";

export const projectService = {
  async getProjects(params = {}) {
    const response = await apiRequest("/projects", { params });
    return (unwrapData(response) || []).map(toProject);
  },

  async getProject(id) {
    const response = await apiRequest(`/projects/${id}`);
    return toProject(unwrapData(response));
  },

  async createProject(payload) {
    const response = await apiRequest("/projects", {
      method: "POST",
      body: toProjectPayload(payload),
    });
    return toProject(unwrapData(response));
  },

  async updateProject(id, payload) {
    const response = await apiRequest(`/projects/${id}`, {
      method: "PATCH",
      body: toProjectPayload(payload),
    });
    return toProject(unwrapData(response));
  },

  async startProject(id) {
    const response = await apiRequest(`/projects/${id}/start`, {
      method: "POST",
    });
    return toProject(unwrapData(response));
  },

  async holdProject(id) {
    const response = await apiRequest(`/projects/${id}/hold`, {
      method: "POST",
    });
    return toProject(unwrapData(response));
  },

  async resumeProject(id) {
    const response = await apiRequest(`/projects/${id}/resume`, {
      method: "POST",
    });
    return toProject(unwrapData(response));
  },

  async completeProject(id, payload = {}) {
    const actualCost = payload.actualCost ?? payload.actual_cost;
    const query = actualCost ? `?actual_cost=${actualCost}` : "";
    const response = await apiRequest(`/projects/${id}/complete${query}`, {
      method: "POST",
    });
    return toProject(unwrapData(response));
  },

  async cancelProject(id) {
    const response = await apiRequest(`/projects/${id}/cancel`, {
      method: "POST",
    });
    return toProject(unwrapData(response));
  },

  async deleteProject(id) {
    const response = await apiRequest(`/projects/${id}`, { method: "DELETE" });
    return unwrapData(response);
  },

  async getProjectRelatedData(id) {
    const response = await apiRequest(`/projects/${id}/related-data`);
    return unwrapData(response);
  },
};
