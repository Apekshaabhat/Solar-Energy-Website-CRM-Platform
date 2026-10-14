export const statCards = [
  {
    id: "total-leads",
    label: "Total Leads",
    value: "128",
    change: "12% from last month",
    icon: "users",
    tint: "bg-leaf-100 text-leaf-600",
  },
  {
    id: "site-surveys",
    label: "Site Surveys",
    value: "45",
    change: "8% from last month",
    icon: "calendar",
    tint: "bg-blue-50 text-blue-accent",
  },
  {
    id: "ongoing-projects",
    label: "Ongoing Projects",
    value: "18",
    change: "20% from last month",
    icon: "folder",
    tint: "bg-amber-50 text-amber-accent",
  },
  {
    id: "completed-projects",
    label: "Completed Projects",
    value: "62",
    change: "15% from last month",
    icon: "check",
    tint: "bg-leaf-100 text-leaf-600",
  },
];

export const leadsOverview = [
  { date: "Aug 1", leads: 8 },
  { date: "Aug 3", leads: 14 },
  { date: "Aug 5", leads: 11 },
  { date: "Aug 7", leads: 17 },
  { date: "Aug 9", leads: 15 },
  { date: "Aug 11", leads: 19 },
  { date: "Aug 13", leads: 16 },
  { date: "Aug 15", leads: 14 },
  { date: "Aug 17", leads: 20 },
  { date: "Aug 19", leads: 18 },
  { date: "Aug 21", leads: 15 },
  { date: "Aug 23", leads: 24 },
  { date: "Aug 25", leads: 23 },
  { date: "Aug 27", leads: 27 },
  { date: "Aug 29", leads: 30 },
  { date: "Aug 30", leads: 32 },
];

export const leadsBySource = [
  { name: "Website", value: 45, color: "#24b368" },
  { name: "Social Media", value: 20, color: "#f0a94e" },
  { name: "Referral", value: 15, color: "#4a8fe0" },
  { name: "Direct Enquiry", value: 10, color: "#f2c14e" },
  { name: "Calculator", value: 10, color: "#9066e0" },
];

export const quickActions = [
  { id: "add-lead", title: "Add New Lead", subtitle: "Manually add a new lead", icon: "plus", tint: "bg-leaf-600" },
  { id: "schedule-survey", title: "Schedule Site Survey", subtitle: "Book a new site survey", icon: "calendar", tint: "bg-blue-accent" },
  { id: "create-project", title: "Create Project", subtitle: "Add a new solar project", icon: "folder", tint: "bg-amber-accent" },
  { id: "manage-calculators", title: "Manage Calculators", subtitle: "Update calculation settings", icon: "calculator", tint: "bg-violet-accent" },
];

export const recentActivity = [
  { id: 1, title: "New lead from website", subtitle: "Rohan Patil", time: "2 minutes ago", icon: "user", tint: "bg-blue-accent" },
  { id: 2, title: "Site survey scheduled", subtitle: "Sneha Sharma", time: "15 minutes ago", icon: "calendar", tint: "bg-leaf-600" },
  { id: 3, title: "Project marked as completed", subtitle: "Green Tech Solutions", time: "1 hour ago", icon: "check", tint: "bg-leaf-600" },
];

export const leadsTabOrder = ["All Leads", "New", "Contacted", "Site Survey", "Quoted", "Converted", "Cancelled", "Lost"];

export const allLeads = [
  { id: 1, name: "Rohan Patil", contact: "+91 98765 43210", location: "Mumbai", propertyType: "Residential", source: "Website", status: "New", createdAt: "12 Sep 2026" },
  { id: 2, name: "Sneha Sharma", contact: "+91 91234 56789", location: "Pune", propertyType: "Commercial", source: "Google Ads", status: "Contacted", createdAt: "11 Sep 2026" },
  { id: 3, name: "Amit Verma", contact: "+91 99887 66554", location: "Nashik", propertyType: "Residential", source: "Referral", status: "Site Survey", createdAt: "10 Sep 2026" },
  { id: 4, name: "Priya Desai", contact: "+91 97654 32109", location: "Thane", propertyType: "Industrial", source: "Website", status: "Quoted", createdAt: "9 Sep 2026" },
  { id: 5, name: "Karan Mehta", contact: "+91 88990 12345", location: "Mumbai", propertyType: "Residential", source: "Social Media", status: "Converted", createdAt: "8 Sep 2026" },
  { id: 6, name: "Neha Gupta", contact: "+91 98761 23456", location: "Pune", propertyType: "Residential", source: "Website", status: "Lost", createdAt: "7 Sep 2026" },
  { id: 7, name: "Vikram Singh", contact: "+91 90654 77889", location: "Nagpur", propertyType: "Commercial", source: "Google Ads", status: "New", createdAt: "6 Sep 2026" },
  { id: 8, name: "Anjali Kulkarni", contact: "+91 88776 55443", location: "Solapur", propertyType: "Residential", source: "Referral", status: "Contacted", createdAt: "5 Sep 2026" },
];

export const customers = [
  { id: 1, name: "Rohan Patil", contact: "+91 98765 43210", location: "Mumbai", propertyType: "Residential", totalProjects: 1, customerSince: "12 Sep 2026", status: "Active" },
  { id: 2, name: "Sneha Sharma", contact: "+91 91234 56789", location: "Pune", propertyType: "Commercial", totalProjects: 1, customerSince: "11 Sep 2026", status: "Active" },
  { id: 3, name: "Amit Verma", contact: "+91 99887 66554", location: "Nashik", propertyType: "Residential", totalProjects: 2, customerSince: "2 Aug 2026", status: "Active" },
  { id: 4, name: "Priya Desai", contact: "+91 97654 32109", location: "Thane", propertyType: "Industrial", totalProjects: 1, customerSince: "15 Jul 2026", status: "Inactive" },
  { id: 5, name: "Karan Mehta", contact: "+91 88990 12345", location: "Mumbai", propertyType: "Residential", totalProjects: 1, customerSince: "20 Jun 2026", status: "Active" },
  { id: 6, name: "Neha Gupta", contact: "+91 98761 23456", location: "Pune", propertyType: "Residential", totalProjects: 0, customerSince: "18 Jun 2026", status: "Active" },
  { id: 7, name: "Vikram Singh", contact: "+91 90654 77889", location: "Nagpur", propertyType: "Commercial", totalProjects: 1, customerSince: "5 Jun 2026", status: "Active" },
  { id: 8, name: "Anjali Kulkarni", contact: "+91 88776 55443", location: "Solapur", propertyType: "Residential", totalProjects: 0, customerSince: "28 May 2026", status: "Inactive" },
];

export const surveyTabOrder = ["All Surveys", "Scheduled", "In Progress", "Completed", "Cancelled"];

export const siteSurveys = [
  { id: 1, customerName: "Rohan Patil", location: "Mumbai", propertyType: "Residential", surveyDate: "15 Sep 2026", timeSlot: "10:00 AM", assignedTo: "Rahul", status: "Scheduled" },
  { id: 2, customerName: "Sneha Sharma", location: "Pune", propertyType: "Commercial", surveyDate: "16 Sep 2026", timeSlot: "11:30 AM", assignedTo: "Priya", status: "Completed" },
  { id: 3, customerName: "Amit Verma", location: "Nashik", propertyType: "Residential", surveyDate: "17 Sep 2026", timeSlot: "02:00 PM", assignedTo: "Karan", status: "Scheduled" },
  { id: 4, customerName: "Priya Desai", location: "Thane", propertyType: "Industrial", surveyDate: "18 Sep 2026", timeSlot: "10:30 AM", assignedTo: "Neha", status: "In Progress" },
  { id: 5, customerName: "Karan Mehta", location: "Mumbai", propertyType: "Residential", surveyDate: "19 Sep 2026", timeSlot: "01:00 PM", assignedTo: "Rahul", status: "Completed" },
  { id: 6, customerName: "Neha Gupta", location: "Pune", propertyType: "Residential", surveyDate: "20 Sep 2026", timeSlot: "03:00 PM", assignedTo: "Priya", status: "Scheduled" },
  { id: 7, customerName: "Vikram Singh", location: "Nagpur", propertyType: "Commercial", surveyDate: "21 Sep 2026", timeSlot: "11:00 AM", assignedTo: "Karan", status: "Cancelled" },
  { id: 8, customerName: "Anjali Kulkarni", location: "Solapur", propertyType: "Residential", surveyDate: "22 Sep 2026", timeSlot: "04:00 PM", assignedTo: "Neha", status: "Scheduled" },
];
