import apiClient, { setToken, setStoredUser, clearAuth } from "./client";

export const authApi = {
  async login(email, password, remember_me = false) {
    const res = await apiClient("/auth/login", {
      method: "POST",
      body: { email, password, remember_me },
    });
    // res contains { access_token, token_type, user }
    if (res?.access_token) {
      setToken(res.access_token, remember_me);
    }
    if (res?.user) {
      setStoredUser(res.user);
    }
    return res;
  },

  async me() {
    const user = await apiClient("/auth/me");
    if (user) {
      setStoredUser(user);
    }
    return user;
  },

  async updateProfile(data) {
    const user = await apiClient("/auth/profile", {
      method: "PATCH",
      body: data,
    });
    if (user) {
      setStoredUser(user);
    }
    return user;
  },

  async changePassword(current_password, new_password, confirm_password) {
    return await apiClient("/auth/change-password", {
      method: "POST",
      body: { current_password, new_password, confirm_password },
    });
  },

  async forgotPassword(email) {
    return await apiClient("/auth/forgot-password", {
      method: "POST",
      body: { email },
    });
  },

  async resetPassword(token, new_password) {
    return await apiClient("/auth/reset-password", {
      method: "POST",
      body: { token, new_password },
    });
  },

  async activate(token, password) {
    return await apiClient("/auth/activate", {
      method: "POST",
      body: { token, password },
    });
  },

  async register({ name, email, password, phone }) {
    return await apiClient("/auth/register", {
      method: "POST",
      body: { name, email, password, phone: phone || null },
    });
  },

  async logout() {
    try {
      await apiClient("/auth/logout", { method: "POST" });
    } catch (err) {
      // Ignore network errors on logout
    } finally {
      clearAuth();
    }
  },
};

export default authApi;
