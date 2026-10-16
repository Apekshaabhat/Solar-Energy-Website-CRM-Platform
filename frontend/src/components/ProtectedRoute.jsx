import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ShieldAlert } from "lucide-react";

export default function ProtectedRoute({ children, allowedRoles }) {
  const { user, isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-[#FBFAF6]">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-[#1F5C3E] border-t-transparent" />
          <p className="text-sm text-stone-500 font-medium">Verifying authorization...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && (!user?.role || !allowedRoles.includes(user.role))) {
    return (
      <div className="p-8 max-w-xl mx-auto my-12 bg-white rounded-2xl border border-red-200 shadow-sm text-center">
        <div className="w-12 h-12 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto mb-4">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <h2 className="text-xl font-bold text-stone-900 mb-2">Access Restricted</h2>
        <p className="text-stone-600 text-sm mb-6">
          Your current role (<strong>{user?.role || "Unknown"}</strong>) does not have permission to access this resource.
        </p>
        <button
          onClick={() => window.history.back()}
          className="px-5 py-2.5 bg-[#1F5C3E] text-white text-sm font-semibold rounded-lg hover:bg-[#184A32] transition"
        >
          Go Back
        </button>
      </div>
    );
  }

  return children;
}
