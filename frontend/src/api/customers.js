import apiClient from "./client";
import { toCustomer } from "../services/mappers";

export const customersApi = {
  async getCustomers(params = {}) {
    const query = new URLSearchParams();
    if (params.page) query.append("page", params.page);
    if (params.limit) query.append("limit", params.limit);
    if (params.search) query.append("search", params.search);
    if (params.status && !["All Customers", "All Status", "All Statuses"].includes(params.status)) {
      query.append("status", params.status);
    }
    if (params.property_type && params.property_type !== "All Property Types") {
      query.append("property_type", params.property_type);
    }
    if (params.location && params.location !== "All Locations") {
      query.append("location", params.location);
    }

    const queryString = query.toString();
    const url = `/customers${queryString ? `?${queryString}` : ""}`;
    const response = await apiClient(url);
    if (response && Array.isArray(response.items)) {
      response.items = response.items.map(toCustomer);
    } else if (Array.isArray(response)) {
      return response.map(toCustomer);
    }
    return response;
  },

  async getCustomer(id) {
    const response = await apiClient(`/customers/${id}`);
    return response ? toCustomer(response) : response;
  },

  async createCustomer(data) {
    return await apiClient("/customers", {
      method: "POST",
      body: data,
    });
  },

  async updateCustomer(id, data) {
    return await apiClient(`/customers/${id}`, {
      method: "PATCH",
      body: data,
    });
  },

  async deleteCustomer(id) {
    return await apiClient(`/customers/${id}`, {
      method: "DELETE",
    });
  },

  async getCustomerOverview(id) {
    return await apiClient(`/customers/${id}/overview`);
  },
};

export default customersApi;
