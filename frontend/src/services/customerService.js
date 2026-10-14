import { apiRequest, unwrapData } from "./api";
import { toCustomer, toCustomerPayload } from "./mappers";

export const customerService = {
  async getCustomers(params = {}) {
    const response = await apiRequest("/customers", { params });
    return {
      ...response,
      items: (response.items || []).map(toCustomer),
    };
  },

  async getCustomer(id) {
    const response = await apiRequest(`/customers/${id}`);
    return toCustomer(unwrapData(response));
  },

  async createCustomer(payload) {
    const response = await apiRequest("/customers", {
      method: "POST",
      body: toCustomerPayload(payload),
    });
    return toCustomer(unwrapData(response));
  },

  async updateCustomer(id, payload) {
    const response = await apiRequest(`/customers/${id}`, {
      method: "PATCH",
      body: toCustomerPayload(payload),
    });
    return toCustomer(unwrapData(response));
  },

  async deleteCustomer(id) {
    const response = await apiRequest(`/customers/${id}`, { method: "DELETE" });
    return unwrapData(response);
  },

  async getCustomerOverview(id) {
    const response = await apiRequest(`/customers/${id}/overview`);
    const data = unwrapData(response) || {};
    return {
      customer: toCustomer(data.customer || {}),
      leads: (data.leads || []).map((l) => ({
        ...l,
        propertyType: l.property_type ?? l.propertyType,
        customerId: l.customer_id ?? l.customerId,
        createdAt: l.date ?? l.createdAt ?? l.created_at,
      })),
      siteSurveys: (data.site_surveys || []).map((s) => ({
        ...s,
        customerName: s.customer_name ?? s.customerName,
        propertyType: s.property_type ?? s.propertyType,
        surveyDate: s.survey_date ?? s.surveyDate,
        timeSlot: s.time_slot ?? s.timeSlot,
        assignedTo: s.assigned_to ?? s.assignedTo,
        customerId: s.customer_id ?? s.customerId,
        leadId: s.lead_id ?? s.leadId,
        projectId: s.project_id ?? s.projectId,
        roofInformation: s.roof_information ?? s.roofInformation,
        capacityEstimate: s.capacity_estimate ?? s.capacityEstimate,
      })),
      projects: (data.projects || []).map((p) => ({
        ...p,
        capacityKW: p.capacity_kw ?? p.capacityKW,
        customerId: p.customer_id ?? p.customerId,
        sourceLeadId: p.source_lead_id ?? p.sourceLeadId,
        customerName: p.customer_name ?? p.customerName,
        estimatedCost: p.estimated_cost ?? p.estimatedCost,
        actualCost: p.actual_cost ?? p.actualCost,
      })),
      activities: (data.activities || []).map((a) => ({
        ...a,
        entityType: a.entity_type ?? a.entityType,
        entityId: a.entity_id ?? a.entityId,
        customerId: a.customer_id ?? a.customerId,
        customerName: a.customer_name ?? a.customerName,
        createdAt: a.created_at ?? a.createdAt,
      })),
    };
  },

  async getCustomerLeads(id) {
    const response = await apiRequest(`/customers/${id}/leads`);
    return (unwrapData(response) || []).map((l) => ({
      ...l,
      propertyType: l.property_type ?? l.propertyType,
      customerId: l.customer_id ?? l.customerId,
      createdAt: l.date ?? l.createdAt ?? l.created_at,
    }));
  },

  async getCustomerSurveys(id) {
    const response = await apiRequest(`/customers/${id}/site-surveys`);
    return (unwrapData(response) || []);
  },

  async getCustomerProjects(id) {
    const response = await apiRequest(`/customers/${id}/projects`);
    return (unwrapData(response) || []);
  },

  async getCustomerActivities(id) {
    const response = await apiRequest(`/customers/${id}/activities`);
    return (unwrapData(response) || []);
  },
};
