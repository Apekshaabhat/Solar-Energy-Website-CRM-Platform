import apiClient from "./client";

export const notificationsApi = {
  getNotifications({ limit = 20, offset = 0 } = {}) {
    const query = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    return apiClient(`/notifications?${query.toString()}`);
  },

  getUnreadCount() {
    return apiClient("/notifications/unread-count");
  },

  markAllRead() {
    return apiClient("/notifications/mark-all-read", { method: "PATCH" });
  },

  markRead(id) {
    return apiClient(`/notifications/${id}/read`, { method: "PATCH" });
  },

  dismiss(id) {
    return apiClient(`/notifications/${id}`, { method: "DELETE" });
  },
};

export default notificationsApi;
