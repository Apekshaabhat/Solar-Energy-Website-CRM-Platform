import apiClient from "./client";

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
    return await apiClient(url);
  },

  async getCustomer(id) {
    return await apiClient(`/customers/${id}`);
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
