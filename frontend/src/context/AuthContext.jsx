import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { authService } from "../services/authService";
import { getAuthToken, getStoredUser, clearAuthSession, setAuthSession } from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => getStoredUser());
  const [token, setToken] = useState(() => getAuthToken());
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    const currentToken = getAuthToken();
    if (!currentToken) {
      setUser(null);
      setToken(null);
      setLoading(false);
      return null;
    }

    try {
      const freshUser = await authService.me();
      if (freshUser) {
        setUser(freshUser);
        setToken(currentToken);
        setAuthSession(currentToken, freshUser);
        return freshUser;
      }
    } catch (err) {
      clearAuthSession();
      setUser(null);
      setToken(null);
    } finally {
      setLoading(false);
    }
    return null;
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = async (credentials) => {
    const session = await authService.login(credentials);
    setToken(session.access_token);
    setUser(session.user);
    return session;
  };

  const logout = async () => {
    try {
      await authService.logout();
    } finally {
      setUser(null);
      setToken(null);
    }
  };

  const value = {
    user,
    token,
    isAuthenticated: Boolean(token && user && user.status === "Active"),
    isAdmin: user?.role === "Admin",
    isManager: user?.role === "Manager",
    isStaff: ["Admin", "Manager", "Sales Rep", "Support"].includes(user?.role),
    isCustomer: user?.role === "Customer",
    loading,
    login,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
