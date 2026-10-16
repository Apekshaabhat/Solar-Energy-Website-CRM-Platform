import React from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  Leaf,
  LayoutDashboard,
  Users2,
  UserSquare2,
  ClipboardCheck,
  FolderKanban,
  Calculator,
  FileText,
  HelpCircle,
  Settings,
  LogOut,
  Users,
} from "lucide-react";
import Topbar from "../components/dashboard/Topbar";
import { useAuth } from "../context/AuthContext";

const ALL_NAV_ITEMS = [
  { label: "Dashboard", icon: LayoutDashboard, to: "/dashboard", roles: ["Admin", "Manager", "Sales Rep", "Support"] },
  { label: "Leads", icon: Users2, to: "/dashboard/leads", roles: ["Admin", "Manager", "Sales Rep", "Support"] },
  { label: "Customers", icon: UserSquare2, to: "/dashboard/customers", roles: ["Admin", "Manager", "Sales Rep", "Support"] },
  { label: "Site Surveys", icon: ClipboardCheck, to: "/dashboard/site-surveys", roles: ["Admin", "Manager", "Sales Rep", "Support"] },
  { label: "Projects", icon: FolderKanban, to: "/dashboard/projects", roles: ["Admin", "Manager", "Sales Rep", "Support"] },
  { label: "Calculators", icon: Calculator, to: "/dashboard/calculators", roles: ["Admin", "Manager", "Sales Rep", "Support"] },
  { label: "Blog Management", icon: FileText, to: "/dashboard/blog", roles: ["Admin", "Manager"] },
  { label: "FAQs", icon: HelpCircle, to: "/dashboard/faqs", roles: ["Admin", "Manager", "Sales Rep", "Support"] },
  { label: "Users", icon: UserSquare2, to: "/dashboard/users", roles: ["Admin", "Manager"] },
];

export default function DashboardLayout() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const userRole = (user?.role || "").toLowerCase();
  const navItems = ALL_NAV_ITEMS.filter((item) => {
    if (!item.roles) return true;
    return item.roles.some((r) => r.toLowerCase() === userRole);
  });
  const canAccessSettings = ["admin", "manager"].includes(userRole);

  return (
    <div className="flex min-h-screen bg-[#FBFAF6] dark:bg-[#0E1712] font-sans transition-colors duration-200">
      {/* Dark Sidebar */}
      <aside className="w-64 min-h-screen bg-[#0E1712] dark:bg-[#0A0F0B] text-white flex flex-col justify-between p-4 flex-shrink-0 border-r border-[#293227] dark:border-[#1C2A21] transition-colors duration-200">
        <div>
          {/* Top Logo + Brand */}
          <div className="flex items-center gap-3 px-2 py-3 mb-6">
            <div className="w-10 h-10 rounded-full bg-[#1F5C3E] flex items-center justify-center flex-shrink-0 shadow-sm">
              <Leaf className="w-5 h-5 text-white" />
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-lg tracking-tight leading-none text-white">SOLARA</span>
              <span className="text-[11px] font-medium tracking-tight text-white/60 mt-1">
                {user?.role ? `${user.role} Dashboard` : "Admin Dashboard"}
              </span>
            </div>
          </div>

          {/* Nav List */}
          <nav className="space-y-1.5">
            {navItems.map(({ label, icon: Icon, to }) => (
              <NavLink
                key={label}
                to={to}
                end={to === "/dashboard"}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                    isActive ? "bg-[#1F5C3E] text-white" : "text-white/70 hover:bg-white/5"
                  }`
                }
              >
                <Icon className="h-4 w-4 flex-shrink-0" />
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Bottom Section */}
        <div className="pt-4 mt-auto border-t border-white/10 space-y-1.5">
          {(isAdmin || isManager) && (
          {canAccessSettings && (
            <NavLink
              to="/dashboard/settings"
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                  isActive ? "bg-[#1F5C3E] text-white" : "text-white/70 hover:bg-white/5"
                }`
              }
            >
              <Settings className="h-4 w-4 flex-shrink-0" />
              <span>Settings</span>
            </NavLink>
          )}

          <button
            type="button"
            onClick={handleLogout}
            onClick={async () => {
              await logout();
              navigate("/login");
            }}
            className="w-full flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-white/70 hover:bg-white/5 transition-colors text-left focus:outline-none cursor-pointer"
          >
            <LogOut className="h-4 w-4 flex-shrink-0" />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 bg-[#FBFAF6] dark:bg-[#0E1712] transition-colors duration-200">
        <Topbar />
        <main className="flex-1 p-6 sm:p-8 bg-[#FBFAF6] dark:bg-[#0E1712] text-ink-900 dark:text-[#F3F6F1] transition-colors duration-200">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
