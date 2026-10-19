import { apiRequest, clearAuthSession, setAuthSession, unwrapData } from "./api";

export const authService = {
  async login(credentials) {
    const session = await apiRequest("/auth/login", {
      method: "POST",
      body: {
        email: credentials.email,
        password: credentials.password,
        remember_me: credentials.rememberMe ?? false,
      },
      auth: false,
    });
    setAuthSession(session.access_token, session.user);
    return session;
  },

  async register(payload) {
    const response = await apiRequest("/auth/register", {
      method: "POST",
      body: {
        name: payload.name ?? payload.fullName,
        email: payload.email,
        password: payload.password,
        phone: payload.phone,
        role: payload.role ?? "Customer",
      },
      auth: false,
    });
    return unwrapData(response);
  },

  async me() {
    const response = await apiRequest("/auth/me");
    return unwrapData(response);
  },

  async updateProfile(payload) {
    const response = await apiRequest("/auth/profile", {
      method: "PATCH",
      body: {
        name: payload.name ?? payload.fullName,
        email: payload.email,
        phone: payload.phone,
      },
    });
    return unwrapData(response);
  },

  async changePassword(payload) {
    const response = await apiRequest("/auth/change-password", {
      method: "POST",
      body: {
        current_password: payload.currentPassword,
        new_password: payload.newPassword,
        confirm_password: payload.confirmPassword,
      },
    });
    return unwrapData(response);
  },

  async forgotPassword(email) {
    const response = await apiRequest("/auth/forgot-password", {
      method: "POST",
      body: { email },
      auth: false,
    });
    return unwrapData(response);
  },

  async activateAccount(payload) {
    const response = await apiRequest("/auth/activate", {
      method: "POST",
      body: {
        token: payload.token,
        password: payload.password,
        confirm_password: payload.confirmPassword ?? payload.confirm_password,
      },
      auth: false,
    });
    return unwrapData(response);
  },

  async logout() {
    try {
      await apiRequest("/auth/logout", { method: "POST" });
    } finally {
      clearAuthSession();
    }
  },
};
