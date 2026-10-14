export function toLead(row) {
  return {
    ...row,
    propertyType: row.property_type ?? row.propertyType,
    estimatedValue: row.estimated_value ?? row.estimatedValue,
    assignedUserId: row.assigned_user_id ?? row.assignedUserId,
    customerId: row.customer_id ?? row.customerId,
    createdAt: row.date ?? row.createdAt ?? row.created_at,
  };
}

export function toLeadPayload(form) {
  return {
    name: form.name,
    contact: form.contact,
    email: form.email || undefined,
    phone: form.phone || undefined,
    location: form.location,
    property_type: form.propertyType ?? form.property_type ?? "Residential",
    source: form.source ?? "Website",
    status: form.status ?? "New",
    notes: form.notes || undefined,
    estimated_value: form.estimatedValue ?? form.estimated_value,
    assigned_user_id: form.assignedUserId ?? form.assigned_user_id,
    customer_id: form.customerId ?? form.customer_id,
  };
}

export function toCustomer(row) {
  return {
    ...row,
    propertyType: row.property_type ?? row.propertyType,
    totalProjects: row.total_projects ?? row.totalProjects ?? 0,
    customerSince: row.customer_since ?? row.customerSince,
  };
}

export function toCustomerPayload(form) {
  return {
    name: form.name,
    contact: form.contact,
    email: form.email || undefined,
    phone: form.phone || undefined,
    location: form.location,
    property_type: form.propertyType ?? form.property_type ?? "Residential",
    status: form.status ?? "Active",
    customer_since: form.customerSince ?? form.customer_since,
  };
}

export function toSurvey(row) {
  return {
    ...row,
    customerName: row.customer_name ?? row.customerName,
    propertyType: row.property_type ?? row.propertyType,
    surveyDate: row.survey_date ?? row.surveyDate,
    timeSlot: row.time_slot ?? row.timeSlot,
    assignedTo: row.assigned_to ?? row.assignedTo,
    customerId: row.customer_id ?? row.customerId,
    leadId: row.lead_id ?? row.leadId,
    projectId: row.project_id ?? row.projectId,
    assignedUserId: row.assigned_user_id ?? row.assignedUserId,
    roofInformation: row.roof_information ?? row.roofInformation,
    capacityEstimate: row.capacity_estimate ?? row.capacityEstimate,
  };
}

export function toSurveyPayload(form) {
  return {
    customer_name: form.customerName ?? form.customer_name,
    location: form.location,
    property_type: form.propertyType ?? form.property_type ?? "Residential",
    survey_date: form.surveyDate ?? form.survey_date,
    time_slot: form.timeSlot ?? form.time_slot ?? "10:00 AM",
    assigned_to: form.assignedTo ?? form.assigned_to ?? "Rahul",
    status: form.status ?? "Scheduled",
    customer_id: form.customerId ?? form.customer_id,
    lead_id: form.leadId ?? form.lead_id,
    project_id: form.projectId ?? form.project_id,
    assigned_user_id: form.assignedUserId ?? form.assigned_user_id,
    roof_information: form.roofInformation ?? form.roof_information,
    capacity_estimate: form.capacityEstimate ?? form.capacity_estimate,
    notes: form.notes,
  };
}

export function toProject(row) {
  return {
    ...row,
    capacityKW: row.capacity_kw ?? row.capacityKW,
    customerId: row.customer_id ?? row.customerId,
    sourceLeadId: row.source_lead_id ?? row.sourceLeadId,
    assignedUserId: row.assigned_user_id ?? row.assignedUserId,
    customerName: row.customer_name ?? row.customerName,
    imageUrl: row.image_url ?? row.imageUrl,
    isPublic: row.is_public ?? row.isPublic,
    estimatedCost: row.estimated_cost ?? row.estimatedCost,
    actualCost: row.actual_cost ?? row.actualCost,
    startDate: row.start_date ?? row.startDate,
    completionDate: row.completion_date ?? row.completionDate,
  };
}

export function toProjectPayload(form) {
  return {
    name: form.name,
    category: form.category,
    location: form.location,
    capacity: form.capacity,
    capacity_kw: form.capacityKW ?? form.capacity_kw,
    status: form.status ?? "In Progress",
    customer_id: form.customerId ?? form.customer_id,
    source_lead_id: form.sourceLeadId ?? form.source_lead_id,
    assigned_user_id: form.assignedUserId ?? form.assigned_user_id,
    image_url: form.imageUrl ?? form.image_url,
    is_public: form.isPublic ?? form.is_public ?? true,
    estimated_cost: form.estimatedCost ?? form.estimated_cost,
    actual_cost: form.actualCost ?? form.actual_cost,
    start_date: form.startDate ?? form.start_date,
    completion_date: form.completionDate ?? form.completion_date,
  };
}

export function toActivity(row) {
  return {
    ...row,
    entityType: row.entity_type ?? row.entityType,
    entityId: row.entity_id ?? row.entityId,
    customerId: row.customer_id ?? row.customerId,
    customerName: row.customer_name ?? row.customerName,
    createdAt: row.created_at ?? row.createdAt,
  };
}

export function toBlog(row) {
  return {
    ...row,
    coverImage: row.cover_image ?? row.coverImage,
    readTime: row.read_time ?? row.readTime,
    authorId: row.author_id ?? row.authorId,
  };
}

export function toBlogPayload(form) {
  return {
    title: form.title,
    slug: form.slug || undefined,
    category: form.category ?? "Guides",
    status: form.status ?? "Draft",
    author: form.author || undefined,
    date: form.date || undefined,
    excerpt: form.excerpt || undefined,
    content: form.content || undefined,
    cover_image: (form.coverImage ?? form.cover_image) || undefined,
    read_time: (form.readTime ?? form.read_time) || undefined,
  };
}

export function toFaqPayload(form) {
  return {
    question: form.question,
    answer: form.answer,
    category: form.category ?? "General",
    display_order: form.displayOrder ?? form.display_order ?? 0,
    is_published: form.isPublished ?? form.is_published ?? true,
  };
}

export function toFaq(row) {
  return {
    ...row,
    displayOrder: row.display_order ?? row.displayOrder,
    isPublished: row.is_published ?? row.isPublished,
  };
}

export function toCalculatorSubmission(row) {
  return {
    ...row,
    propertyType: row.property_type ?? row.propertyType,
    monthlyBill: row.monthly_bill ?? row.monthlyBill,
    roofArea: row.roof_area ?? row.roofArea,
    systemSizeKW: row.system_size_kw ?? row.systemSizeKW,
    annualSavings: row.annual_savings ?? row.annualSavings,
    paybackYears: row.payback_years ?? row.paybackYears,
    co2Tons: row.co2_tons ?? row.co2Tons,
  };
}

export function toCalculatorPayload(form) {
  return {
    name: form.name,
    phone: form.phone,
    email: form.email || undefined,
    property_type: form.propertyType ?? form.property_type ?? "Residential",
    monthly_bill: Number(form.monthlyBill ?? form.monthly_bill),
    roof_area: Number(form.roofArea ?? form.roof_area),
    system_size_kw: Number(form.systemSizeKW ?? form.system_size_kw),
    annual_savings: Number(form.annualSavings ?? form.annual_savings),
    payback_years: form.paybackYears ?? form.payback_years,
    co2_tons: form.co2Tons ?? form.co2_tons,
  };
}

export function toCalculatorSettings(row) {
  return {
    ...row,
    electricityRate: row.electricity_rate ?? row.electricityRate,
    generationPerKW: row.generation_per_kw ?? row.generationPerKW,
    installationCostPerKW: row.installation_cost_per_kw ?? row.installationCostPerKW,
    billOffsetPercent: row.bill_offset_percent ?? row.billOffsetPercent,
  };
}

export function toCalculatorSettingsPayload(form) {
  return {
    electricity_rate: form.electricityRate ?? form.electricity_rate,
    generation_per_kw: form.generationPerKW ?? form.generation_per_kw,
    installation_cost_per_kw: form.installationCostPerKW ?? form.installation_cost_per_kw,
    bill_offset_percent: form.billOffsetPercent ?? form.bill_offset_percent,
  };
}

export function toSystemSettings(row) {
  return {
    ...row,
    companyName: row.company_name ?? row.companyName,
    supportEmail: row.support_email ?? row.supportEmail,
    emailNotifications: row.email_notifications ?? row.emailNotifications,
    smsNotifications: row.sms_notifications ?? row.smsNotifications,
    leadAlerts: row.lead_alerts ?? row.leadAlerts,
    twoFactorAuth: row.two_factor_auth ?? row.twoFactorAuth,
  };
}

export function toSystemSettingsPayload(form) {
  return {
    company_name: form.companyName ?? form.company_name,
    support_email: form.supportEmail ?? form.support_email,
    email_notifications: form.emailNotifications ?? form.email_notifications,
    sms_notifications: form.smsNotifications ?? form.sms_notifications,
    lead_alerts: form.leadAlerts ?? form.lead_alerts,
    two_factor_auth: form.twoFactorAuth ?? form.two_factor_auth,
  };
}
