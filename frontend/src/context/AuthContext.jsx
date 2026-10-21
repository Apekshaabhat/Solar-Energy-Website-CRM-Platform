import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { Navigate, useLocation } from "react-router-dom";
import authApi from "../api/auth";
import { getToken, getStoredUser, clearAuth } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => getStoredUser());
  const [token, setTokenState] = useState(() => getToken());
  const [isLoading, setIsLoading] = useState(true);

  // Gap 1 & 13: Session Restoration & Inactive Account Verification on App Start
  const checkAuthStatus = useCallback(async () => {
    const currentToken = getToken();
    if (!currentToken) {
      setUser(null);
      setTokenState(null);
      setIsLoading(false);
      return;
    }

    try {
      const me = await authApi.me();
      
      // Reject inactive or disabled accounts on frontend session check
      if (me?.status && me.status.toLowerCase() !== "active") {
        clearAuth();
        setUser(null);
        setTokenState(null);
        return;
      }

      setUser(me);
      setTokenState(currentToken);
    } catch (err) {
      clearAuth();
      setUser(null);
      setTokenState(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuthStatus();

    const handleLogoutEvent = () => {
      setUser(null);
      setTokenState(null);
    };

    window.addEventListener("solara_auth_logout", handleLogoutEvent);
    return () => window.removeEventListener("solara_auth_logout", handleLogoutEvent);
  }, [checkAuthStatus]);

  // Gap 8: Remember Me Duration & Login Handler
  const login = async (email, password, rememberMe) => {
    setIsLoading(true);
    try {
      const res = await authApi.login(email, password, rememberMe);
      const me = res.user || (await authApi.me());

      // Reject login if account is inactive
      if (me?.status && me.status.toLowerCase() !== "active") {
        clearAuth();
        throw new Error("Your account is currently inactive. Please contact support.");
      }

      setUser(me);
      setTokenState(getToken());
      return me;
    } finally {
      setIsLoading(false);
    }
  };

  // Gap 9: Server-side & Client-side Logout
  const logout = async () => {
    setIsLoading(true);
    try {
      await authApi.logout();
    } catch (err) {
      console.warn("Logout error (session cleared locally anyway):", err);
    } finally {
      clearAuth();
      setUser(null);
      setTokenState(null);
      setIsLoading(false);
    }
  };

  const updateUser = (updatedUserData) => {
    setUser((prev) => ({ ...prev, ...updatedUserData }));
  };

  const value = {
    user,
    token,
    isAuthenticated: !!user && !!token,
    isLoading,
    login,
    logout,
    updateUser,
    refreshUser: checkAuthStatus,
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

// Gap 11: Consistent Role-Based Dashboard Routing
export function getDefaultRouteForRole(role = "") {
  if (!role) return "/dashboard";
  const r = role.toLowerCase().trim();
  if (["admin", "manager", "sales rep", "support"].includes(r)) {
    return "/dashboard";
  }
  if (r === "customer") {
    return "/dashboard/customer";
  }
  return "/dashboard";
}

// Protected Route Guard for Authorized Pages
export function ProtectedRoute({ children, allowedRoles }) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-[#0E1712] text-gray-600 dark:text-gray-300">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-[#1F5C3E] border-t-transparent rounded-full animate-spin"></div>
          <p className="text-sm font-medium">Verifying authentication...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && allowedRoles.length > 0 && user?.role) {
    const userRole = user.role.toLowerCase().trim();
    const isAllowed = allowedRoles.some((r) => r.toLowerCase().trim() === userRole);
    if (!isAllowed) {
      return (
        <div className="min-h-[60vh] flex items-center justify-center p-4">
          <div className="p-8 text-center bg-white dark:bg-[#17221B] rounded-2xl shadow-sm border border-gray-100 dark:border-[#293227] max-w-md mx-auto">
            <h2 className="text-xl font-bold text-red-600 dark:text-red-400 mb-2">Access Denied</h2>
            <p className="text-gray-600 dark:text-gray-300 text-sm mb-5">
              Your role ({user.role}) is not authorized to access this page.
            </p>
            <a
              href={getDefaultRouteForRole(user.role)}
              className="inline-block px-5 py-2.5 bg-[#1F5C3E] hover:bg-[#184A32] text-white rounded-full text-sm font-medium transition-colors"
            >
              Return to Authorized Page
            </a>
          </div>
        </div>
      );
    }
  }

  return children;
}

// Public Guard (Prevents logged in users from re-visiting Login/Signup)
export function PublicOnlyRoute({ children }) {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) return null;

  if (isAuthenticated && user?.role) {
    return <Navigate to={getDefaultRouteForRole(user.role)} replace />;
  }

  return children;
}