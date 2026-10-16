import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  Search,
  Plus,
  Pencil,
  Trash2,
  X,
  Users as UsersIcon,
  UserCheck,
  UserX,
  Mail,
  RefreshCw,
  Eye,
  Shield,
  AlertCircle,
  CheckCircle2,
  Copy,
  Link as LinkIcon,
} from "lucide-react";
import { userService } from "../../services/userService";
import { useAuth } from "../../context/AuthContext";

// Helper to extract initials from full name
function getInitials(name, email) {
  if (name) {
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }
  if (email) return email.substring(0, 2).toUpperCase();
  return "U";
}

// Role badge styling
function getRoleBadge(role) {
  switch (role) {
    case "Admin":
      return "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950/60 dark:text-purple-300 dark:border-purple-800/50";
    case "Manager":
      return "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800/50";
    case "Sales Rep":
      return "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800/50";
    case "Support":
      return "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800/50";
    case "Customer":
      return "bg-teal-50 text-teal-700 border-teal-200 dark:bg-teal-950/60 dark:text-teal-300 dark:border-teal-800/50";
    default:
      return "bg-gray-50 text-gray-700 border-gray-200 dark:bg-gray-900 dark:text-gray-300 dark:border-gray-800";
  }
}

export default function Users() {
  const { user: currentUser, isAdmin, isManager } = useAuth();

  const [users, setUsers] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedRole, setSelectedRole] = useState("ALL");
  const [selectedStatus, setSelectedStatus] = useState("ALL");

  // Notifications
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Modals
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [inviteResult, setInviteResult] = useState(null);

  // Form states
  const [inviteForm, setInviteForm] = useState({
    name: "",
    email: "",
    role: "Sales Rep",
    phone: "",
    notes: "",
  });

  const [editForm, setEditForm] = useState({
    name: "",
    role: "Sales Rep",
    status: "Active",
    phone: "",
  });

  const [submitting, setSubmitting] = useState(false);

  // Fetch users and metrics
  const loadData = useCallback(async () => {
    setLoading(true);
    setErrorMsg("");
    try {
      const [userList, statsData] = await Promise.all([
        userService.getUsers(),
        userService.getStats().catch(() => null),
      ]);
      setUsers(Array.isArray(userList) ? userList : []);
      if (statsData) setStats(statsData);
    } catch (err) {
      setErrorMsg(err.message || "Failed to load users from the server.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Dismiss notifications automatically
  useEffect(() => {
    if (successMsg) {
      const timer = setTimeout(() => setSuccessMsg(""), 4500);
      return () => clearTimeout(timer);
    }
  }, [successMsg]);

  // Filter users
  const filteredUsers = useMemo(() => {
    return users.filter((u) => {
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        (u.name && u.name.toLowerCase().includes(q)) ||
        (u.email && u.email.toLowerCase().includes(q)) ||
        (u.role && u.role.toLowerCase().includes(q));

      const matchesRole = selectedRole === "ALL" || u.role === selectedRole;
      const matchesStatus = selectedStatus === "ALL" || u.status === selectedStatus;

      return matchesSearch && matchesRole && matchesStatus;
    });
  }, [users, searchQuery, selectedRole, selectedStatus]);

  // Open invite modal
  const handleOpenInvite = () => {
    setInviteResult(null);
    setInviteForm({
      name: "",
      email: "",
      role: "Sales Rep",
      phone: "",
      notes: "",
    });
    setIsInviteModalOpen(true);
  };

  // Submit invite
  const handleSubmitInvite = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMsg("");
    try {
      const result = await userService.inviteUser(inviteForm);
      setSuccessMsg(`Invitation created for ${inviteForm.email}`);
      setInviteResult(result);
      await loadData();
    } catch (err) {
      setErrorMsg(err.message || "Failed to send user invitation.");
    } finally {
      setSubmitting(false);
    }
  };

  // Open edit modal
  const handleOpenEdit = (user) => {
    setSelectedUser(user);
    setEditForm({
      name: user.name || "",
      role: user.role || "Sales Rep",
      status: user.status || "Active",
      phone: user.phone || "",
    });
    setIsEditModalOpen(true);
  };

  // Submit edit
  const handleSubmitEdit = async (e) => {
    e.preventDefault();
    if (!selectedUser) return;
    setSubmitting(true);
    setErrorMsg("");
    try {
      await userService.updateUser(selectedUser.id, editForm);
      setSuccessMsg(`User ${selectedUser.name || selectedUser.email} updated successfully.`);
      setIsEditModalOpen(false);
      setSelectedUser(null);
      await loadData();
    } catch (err) {
      setErrorMsg(err.message || "Failed to update user.");
    } finally {
      setSubmitting(false);
    }
  };

  // Toggle active/inactive
  const handleToggleStatus = async (user) => {
    const nextStatus = user.status === "Active" ? "Inactive" : "Active";
    const actionLabel = nextStatus === "Active" ? "activate" : "deactivate";
    if (!window.confirm(`Are you sure you want to ${actionLabel} ${user.name || user.email}?`)) {
      return;
    }

    try {
      await userService.updateUser(user.id, { status: nextStatus });
      setSuccessMsg(`User ${user.name || user.email} is now ${nextStatus}.`);
      await loadData();
    } catch (err) {
      setErrorMsg(err.message || `Failed to ${actionLabel} user.`);
    }
  };

  // Delete user
  const handleDeleteUser = async (user) => {
    if (
      !window.confirm(
        `Are you sure you want to delete ${user.name || user.email}? This will remove the account or clear safe relationships.`
      )
    ) {
      return;
    }

    try {
      await userService.deleteUser(user.id);
      setSuccessMsg(`User ${user.name || user.email} was removed.`);
      await loadData();
    } catch (err) {
      setErrorMsg(err.message || "Failed to delete user.");
    }
  };

  // View Details
  const handleOpenDetails = async (user) => {
    try {
      const detailed = await userService.getUser(user.id);
      setSelectedUser(detailed);
      setIsDetailModalOpen(true);
    } catch (err) {
      setErrorMsg(err.message || "Failed to fetch detailed profile.");
    }
  };

  // Backfill Customer Links
  const handleBackfillCustomers = async () => {
    if (!window.confirm("Run customer reconciliation to match users with CRM customer records?")) {
      return;
    }
    try {
      const res = await userService.backfillCustomers();
      setSuccessMsg(
        `Reconciliation complete: ${res.matched} accounts matched, ${res.unresolved} unresolved.`
      );
      await loadData();
    } catch (err) {
      setErrorMsg(err.message || "Reconciliation failed.");
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white tracking-tight">
            User Management
          </h1>
          <p className="text-sm sm:text-base text-gray-500 dark:text-gray-400 mt-1">
            Manage authenticated team members, roles, statuses, and customer logins.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {isAdmin && (
            <button
              type="button"
              onClick={handleBackfillCustomers}
              title="Reconcile user accounts with customer records"
              className="inline-flex items-center gap-2 px-3.5 py-2.5 rounded-xl border border-gray-200 dark:border-[#293227] bg-white dark:bg-[#17221B] text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-[#202E24] text-sm font-medium transition cursor-pointer"
            >
              <LinkIcon className="w-4 h-4 text-[#1F5C3E]" />
              <span className="hidden md:inline">Reconcile Accounts</span>
            </button>
          )}

          <button
            type="button"
            onClick={loadData}
            title="Refresh Users"
            className="p-2.5 rounded-xl border border-gray-200 dark:border-[#293227] bg-white dark:bg-[#17221B] text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-[#202E24] transition cursor-pointer"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-[#1F5C3E]" : ""}`} />
          </button>

          {isAdmin && (
            <button
              type="button"
              onClick={handleOpenInvite}
              className="inline-flex items-center justify-center gap-2 bg-[#1F5C3E] hover:bg-[#184931] text-white text-sm font-medium rounded-xl px-4 py-2.5 transition-colors shadow-sm cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>Invite User</span>
            </button>
          )}
        </div>
      </div>

      {/* Notifications */}
      {errorMsg && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/50 text-red-700 dark:text-red-300 text-sm">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <p className="flex-1 font-medium">{errorMsg}</p>
          <button
            onClick={() => setErrorMsg("")}
            className="text-red-500 hover:text-red-700 p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {successMsg && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900/50 text-[#1F5C3E] dark:text-emerald-300 text-sm">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <p className="flex-1 font-medium">{successMsg}</p>
          <button
            onClick={() => setSuccessMsg("")}
            className="text-emerald-600 hover:text-emerald-800 p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-2xl p-4 sm:p-5 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                Total Users
              </span>
              <div className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 text-[#1F5C3E] flex items-center justify-center">
                <UsersIcon className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white mt-2">
              {stats.totalUsers}
            </p>
          </div>

          <div className="bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-2xl p-4 sm:p-5 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                Active Users
              </span>
              <div className="w-8 h-8 rounded-lg bg-green-50 dark:bg-green-950/60 text-green-600 flex items-center justify-center">
                <UserCheck className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white mt-2">
              {stats.activeUsers}
            </p>
          </div>

          <div className="bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-2xl p-4 sm:p-5 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                Pending Invitations
              </span>
              <div className="w-8 h-8 rounded-lg bg-amber-50 dark:bg-amber-950/60 text-amber-600 flex items-center justify-center">
                <Mail className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white mt-2">
              {stats.invitedUsers}
            </p>
          </div>

          <div className="bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-2xl p-4 sm:p-5 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                Inactive Accounts
              </span>
              <div className="w-8 h-8 rounded-lg bg-gray-50 dark:bg-gray-900 text-gray-600 flex items-center justify-center">
                <UserX className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white mt-2">
              {stats.inactiveUsers}
            </p>
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500 pointer-events-none" />
          <input
            type="text"
            placeholder="Search by name, email, or role..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-xl text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30 focus:border-[#1F5C3E] transition-colors"
          />
        </div>

        <div className="flex items-center gap-2.5">
          <select
            value={selectedRole}
            onChange={(e) => setSelectedRole(e.target.value)}
            className="px-3 py-2 bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-xl text-sm text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30 focus:border-[#1F5C3E]"
          >
            <option value="ALL">All Roles</option>
            <option value="Admin">Admin</option>
            <option value="Manager">Manager</option>
            <option value="Sales Rep">Sales Rep</option>
            <option value="Support">Support</option>
            <option value="Customer">Customer</option>
          </select>

          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="px-3 py-2 bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-xl text-sm text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30 focus:border-[#1F5C3E]"
          >
            <option value="ALL">All Statuses</option>
            <option value="Active">Active</option>
            <option value="Invited">Invited</option>
            <option value="Inactive">Inactive</option>
          </select>
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-2xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto no-scrollbar">
          <table className="w-full text-left text-sm border-collapse min-w-[720px]">
            <thead>
              <tr className="bg-gray-50/80 dark:bg-[#0E1712]/80 border-b border-gray-200 dark:border-[#293227] text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <th className="py-3.5 px-5">User</th>
                <th className="py-3.5 px-4">Email</th>
                <th className="py-3.5 px-4">Role</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4">Created</th>
                <th className="py-3.5 px-5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-[#293227]/60 text-gray-800 dark:text-gray-200">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-gray-500 dark:text-gray-400">
                    <div className="flex items-center justify-center gap-2">
                      <RefreshCw className="w-5 h-5 animate-spin text-[#1F5C3E]" />
                      <span>Loading database users...</span>
                    </div>
                  </td>
                </tr>
              ) : filteredUsers.length > 0 ? (
                filteredUsers.map((user) => (
                  <tr
                    key={user.id}
                    className="hover:bg-gray-50/70 dark:hover:bg-[#152019]/60 transition-colors"
                  >
                    <td className="py-3.5 px-5">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-[#EFF3EC] dark:bg-[#1C2A21] text-[#1F5C3E] dark:text-[#4ADE80] font-semibold flex items-center justify-center text-xs shrink-0 border border-[#1F5C3E]/20 dark:border-[#4ADE80]/20">
                          {getInitials(user.name, user.email)}
                        </div>
                        <div>
                          <span className="font-semibold text-gray-900 dark:text-white block">
                            {user.name || "Unnamed Account"}
                          </span>
                          {user.customer_id && (
                            <span className="inline-flex items-center gap-1 text-[11px] text-[#1F5C3E] font-medium">
                              <LinkIcon className="w-3 h-3" /> Customer Linked
                            </span>
                          )}
                        </div>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 text-gray-600 dark:text-gray-300">
                      {user.email}
                    </td>

                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${getRoleBadge(
                          user.role
                        )}`}
                      >
                        {user.role}
                      </span>
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="inline-flex items-center gap-2">
                        <span
                          className={`w-2 h-2 rounded-full shrink-0 ${
                            user.status === "Active"
                              ? "bg-emerald-500"
                              : user.status === "Invited"
                              ? "bg-amber-500 animate-pulse"
                              : "bg-gray-400 dark:bg-gray-500"
                          }`}
                        />
                        <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                          {user.status}
                        </span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 text-xs text-gray-500 dark:text-gray-400">
                      {user.created_at ? new Date(user.created_at).toLocaleDateString() : "—"}
                    </td>

                    <td className="py-3.5 px-5 text-right">
                      <div className="inline-flex items-center justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => handleOpenDetails(user)}
                          title="View Details"
                          className="p-1.5 text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white rounded-lg hover:bg-gray-100 dark:hover:bg-[#293227] transition cursor-pointer"
                        >
                          <Eye className="w-4 h-4" />
                        </button>

                        {(isAdmin || (isManager && user.role !== "Admin")) && (
                          <button
                            type="button"
                            onClick={() => handleOpenEdit(user)}
                            title="Edit User"
                            className="p-1.5 text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white rounded-lg hover:bg-gray-100 dark:hover:bg-[#293227] transition cursor-pointer"
                          >
                            <Pencil className="w-4 h-4" />
                          </button>
                        )}

                        {isAdmin && (
                          <button
                            type="button"
                            onClick={() => handleToggleStatus(user)}
                            title={user.status === "Active" ? "Deactivate Account" : "Activate Account"}
                            className={`p-1.5 rounded-lg transition cursor-pointer ${
                              user.status === "Active"
                                ? "text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-950/40"
                                : "text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/40"
                            }`}
                          >
                            {user.status === "Active" ? (
                              <UserX className="w-4 h-4" />
                            ) : (
                              <UserCheck className="w-4 h-4" />
                            )}
                          </button>
                        )}

                        {isAdmin && (
                          <button
                            type="button"
                            onClick={() => handleDeleteUser(user)}
                            title="Delete user"
                            className="p-1.5 text-gray-400 hover:text-red-600 dark:text-gray-500 dark:hover:text-red-400 rounded-lg hover:bg-red-50 dark:hover:bg-red-950/40 transition cursor-pointer"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-gray-500 dark:text-gray-400 text-sm">
                    No users matching the filters found in database.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* INVITE USER MODAL */}
      {isInviteModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-2xl p-6 w-full max-w-lg shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-gray-100 dark:border-[#293227] pb-3">
              <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <Mail className="w-5 h-5 text-[#1F5C3E]" />
                Invite New User
              </h3>
              <button
                type="button"
                onClick={() => setIsInviteModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {inviteResult ? (
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 text-emerald-800 dark:text-emerald-200 text-sm">
                  <p className="font-semibold">{inviteResult.message}</p>
                  <p className="text-xs mt-1 text-emerald-700 dark:text-emerald-300">
                    Expires at: {new Date(inviteResult.expires_at).toLocaleString()}
                  </p>
                </div>

                {inviteResult.activation_url && (
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">
                      Single-Use Activation URL (Direct Distribution):
                    </label>
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        readOnly
                        value={inviteResult.activation_url}
                        className="w-full text-xs p-2.5 rounded-lg border border-gray-200 dark:border-[#293227] bg-gray-50 dark:bg-[#0E1712] text-gray-800 dark:text-gray-200"
                      />
                      <button
                        type="button"
                        onClick={() => {
                          navigator.clipboard.writeText(inviteResult.activation_url);
                          setSuccessMsg("Activation link copied to clipboard!");
                        }}
                        className="p-2.5 rounded-lg bg-[#1F5C3E] text-white hover:bg-[#184931]"
                        title="Copy activation link"
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                    </div>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400">
                      Notice: SMTP email delivery requires configuring `SMTP_HOST` in `.env`. Send this secure link to the invited user to complete setup.
                    </p>
                  </div>
                )}

                <div className="flex justify-end pt-3">
                  <button
                    type="button"
                    onClick={() => {
                      setIsInviteModalOpen(false);
                      setInviteResult(null);
                    }}
                    className="px-5 py-2.5 bg-[#1F5C3E] text-white rounded-xl text-sm font-medium hover:bg-[#184931]"
                  >
                    Done
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleSubmitInvite} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                    Full Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Jane Doe"
                    value={inviteForm.name}
                    onChange={(e) => setInviteForm({ ...inviteForm, name: e.target.value })}
                    className="w-full px-3.5 py-2.5 bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] rounded-xl text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30 focus:border-[#1F5C3E]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                    Email Address <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="email"
                    required
                    placeholder="e.g. jane@solara.com"
                    value={inviteForm.email}
                    onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })}
                    className="w-full px-3.5 py-2.5 bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] rounded-xl text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30 focus:border-[#1F5C3E]"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                      Role <span className="text-red-500">*</span>
                    </label>
                    <select
                      value={inviteForm.role}
                      onChange={(e) => setInviteForm({ ...inviteForm, role: e.target.value })}
                      className="w-full px-3.5 py-2.5 bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] rounded-xl text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30 focus:border-[#1F5C3E]"
                    >
                      {isAdmin && <option value="Admin">Admin</option>}
                      <option value="Manager">Manager</option>
                      <option value="Sales Rep">Sales Rep</option>
                      <option value="Support">Support</option>
                      <option value="Customer">Customer</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                      Phone Number
                    </label>
                    <input
                      type="tel"
                      placeholder="+1 (555) 000-0000"
                      value={inviteForm.phone}
                      onChange={(e) => setInviteForm({ ...inviteForm, phone: e.target.value })}
                      className="w-full px-3.5 py-2.5 bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] rounded-xl text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30 focus:border-[#1F5C3E]"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                    Invitation Notes / Department
                  </label>
                  <textarea
                    rows={2}
                    placeholder="Optional onboarding notes..."
                    value={inviteForm.notes}
                    onChange={(e) => setInviteForm({ ...inviteForm, notes: e.target.value })}
                    className="w-full px-3.5 py-2 bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] rounded-xl text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30 focus:border-[#1F5C3E]"
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-100 dark:border-[#293227]">
                  <button
                    type="button"
                    onClick={() => setIsInviteModalOpen(false)}
                    className="px-4 py-2.5 text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-[#293227] rounded-xl transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="bg-[#1F5C3E] hover:bg-[#184931] text-white text-sm font-medium rounded-xl px-4 py-2.5 transition shadow-sm"
                  >
                    {submitting ? "Creating Invite..." : "Generate & Send Invitation"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* EDIT USER MODAL */}
      {isEditModalOpen && selectedUser && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-2xl p-6 w-full max-w-md shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-gray-100 dark:border-[#293227] pb-3">
              <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                Edit User ({selectedUser.email})
              </h3>
              <button
                type="button"
                onClick={() => setIsEditModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmitEdit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  value={editForm.name}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                  className="w-full px-3.5 py-2.5 bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] rounded-xl text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30 focus:border-[#1F5C3E]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                  Phone Number
                </label>
                <input
                  type="tel"
                  value={editForm.phone}
                  onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })}
                  className="w-full px-3.5 py-2.5 bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] rounded-xl text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30 focus:border-[#1F5C3E]"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                    Role
                  </label>
                  <select
                    value={editForm.role}
                    disabled={!isAdmin}
                    onChange={(e) => setEditForm({ ...editForm, role: e.target.value })}
                    className="w-full px-3.5 py-2.5 bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] rounded-xl text-sm text-gray-900 dark:text-white disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30 focus:border-[#1F5C3E]"
                  >
                    <option value="Admin">Admin</option>
                    <option value="Manager">Manager</option>
                    <option value="Sales Rep">Sales Rep</option>
                    <option value="Support">Support</option>
                    <option value="Customer">Customer</option>
                  </select>
                  {!isAdmin && (
                    <p className="text-[10px] text-gray-500 mt-1">Only Admin can alter roles.</p>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                    Status
                  </label>
                  <select
                    value={editForm.status}
                    disabled={!isAdmin && selectedUser.role === "Admin"}
                    onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
                    className="w-full px-3.5 py-2.5 bg-white dark:bg-[#0E1712] border border-gray-200 dark:border-[#293227] rounded-xl text-sm text-gray-900 dark:text-white disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-[#1F5C3E]/30 focus:border-[#1F5C3E]"
                  >
                    <option value="Active">Active</option>
                    <option value="Invited">Invited</option>
                    <option value="Inactive">Inactive</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-100 dark:border-[#293227]">
                <button
                  type="button"
                  onClick={() => setIsEditModalOpen(false)}
                  className="px-4 py-2.5 text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-[#293227] rounded-xl transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="bg-[#1F5C3E] hover:bg-[#184931] text-white text-sm font-medium rounded-xl px-4 py-2.5 transition shadow-sm"
                >
                  {submitting ? "Saving..." : "Save Changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* VIEW DETAILS MODAL */}
      {isDetailModalOpen && selectedUser && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-[#17221B] border border-gray-200 dark:border-[#293227] rounded-2xl p-6 w-full max-w-lg shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-gray-100 dark:border-[#293227] pb-3">
              <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <Shield className="w-5 h-5 text-[#1F5C3E]" />
                User Account Details
              </h3>
              <button
                type="button"
                onClick={() => setIsDetailModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3.5 text-sm">
              <div className="flex justify-between py-1.5 border-b border-gray-100 dark:border-[#293227]">
                <span className="text-gray-500">ID:</span>
                <span className="font-mono text-xs font-semibold text-gray-800 dark:text-gray-200">
                  {selectedUser.id}
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-gray-100 dark:border-[#293227]">
                <span className="text-gray-500">Full Name:</span>
                <span className="font-semibold text-gray-900 dark:text-white">
                  {selectedUser.name || "—"}
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-gray-100 dark:border-[#293227]">
                <span className="text-gray-500">Email:</span>
                <span className="text-gray-800 dark:text-gray-200 font-medium">
                  {selectedUser.email}
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-gray-100 dark:border-[#293227]">
                <span className="text-gray-500">Role:</span>
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${getRoleBadge(selectedUser.role)}`}>
                  {selectedUser.role}
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-gray-100 dark:border-[#293227]">
                <span className="text-gray-500">Status:</span>
                <span className="font-semibold text-gray-900 dark:text-white">
                  {selectedUser.status}
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-gray-100 dark:border-[#293227]">
                <span className="text-gray-500">Phone:</span>
                <span className="text-gray-800 dark:text-gray-200">
                  {selectedUser.phone || "—"}
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-gray-100 dark:border-[#293227]">
                <span className="text-gray-500">Linked Customer ID:</span>
                <span className="font-mono text-xs text-[#1F5C3E]">
                  {selectedUser.customer_id || "None (Staff / Independent)"}
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-gray-100 dark:border-[#293227]">
                <span className="text-gray-500">Created At:</span>
                <span className="text-gray-800 dark:text-gray-200 text-xs">
                  {selectedUser.created_at ? new Date(selectedUser.created_at).toLocaleString() : "—"}
                </span>
              </div>
            </div>

            <div className="flex justify-end pt-3">
              <button
                type="button"
                onClick={() => setIsDetailModalOpen(false)}
                className="px-5 py-2.5 bg-[#1F5C3E] text-white rounded-xl text-sm font-medium hover:bg-[#184931]"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
