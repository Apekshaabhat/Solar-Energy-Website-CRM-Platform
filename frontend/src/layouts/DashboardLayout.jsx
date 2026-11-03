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
  { label: "Dashboard", icon: LayoutDashboard, to: "/dashboard", roles: ["Admin", "Sales Rep"] },
  { label: "Leads", icon: Users2, to: "/dashboard/leads", roles: ["Admin", "Sales Rep"] },
  { label: "Customers", icon: UserSquare2, to: "/dashboard/customers", roles: ["Admin", "Sales Rep"] },
  { label: "Projects", icon: FolderKanban, to: "/dashboard/projects", roles: ["Admin", "Sales Rep"] },
  { label: "Site Surveys", icon: ClipboardCheck, to: "/dashboard/site-surveys", roles: ["Admin", "Sales Rep"] },
  { label: "Calculators", icon: Calculator, to: "/dashboard/calculators", roles: ["Admin"] },
  { label: "Blog Management", icon: FileText, to: "/dashboard/blog", roles: ["Admin"] },
  { label: "FAQs", icon: HelpCircle, to: "/dashboard/faqs", roles: ["Admin", "Sales Rep"] },
  { label: "Sales Management", icon: Users, to: "/dashboard/users", roles: ["Admin"] },
  { label: "My Profile", icon: UserSquare2, to: "/dashboard/profile", roles: ["Admin", "Sales Rep"] },
];

export default function DashboardLayout() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const userRole = (user?.role || "").toLowerCase().trim();
  const isSalesRep = userRole === "sales rep" || userRole === "sales_rep";
  const isAdmin = userRole === "admin";

  const navItems = ALL_NAV_ITEMS.filter((item) => {
    if (!item.roles) return true;
    return item.roles.some((r) => {
      const target = r.toLowerCase();
      if (target === "sales rep" && isSalesRep) return true;
      if (target === "admin" && isAdmin) return true;
      return target === userRole;
    });
  });
  const canAccessSettings = isAdmin;

  return (
    <div className="flex h-screen overflow-hidden bg-[#FBFAF6] dark:bg-[#0E1712] font-sans transition-colors duration-200">
      {/* Dark Sidebar */}
      <aside className="w-64 h-screen sticky top-0 bg-[#0E1712] dark:bg-[#0A0F0B] text-white flex flex-col justify-between p-4 flex-shrink-0 border-r border-[#293227] dark:border-[#1C2A21] transition-colors duration-200 z-30">
        <div className="flex flex-col min-h-0 flex-1">
          {/* Top Logo + Brand */}
          <div className="flex items-center gap-3 px-2 py-3 mb-6 shrink-0">
            <div className="w-10 h-10 rounded-full bg-[#1F5C3E] flex items-center justify-center flex-shrink-0 shadow-sm">
              <Leaf className="w-5 h-5 text-white" />
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-lg tracking-tight leading-none text-white">SOLARA</span>
              <span className="text-[11px] font-medium tracking-tight text-white/60 mt-1">
                {isAdmin ? "Admin Portal" : "Sales Portal"}
              </span>
            </div>
          </div>

          {/* Nav List */}
          <nav className="space-y-1.5 overflow-y-auto flex-1 pr-1">
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
        <div className="pt-4 mt-auto border-t border-white/10 space-y-1.5 shrink-0">
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
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-y-auto bg-[#FBFAF6] dark:bg-[#0E1712] transition-colors duration-200">
        <Topbar />
        <main className="flex-1 p-6 sm:p-8 bg-[#FBFAF6] dark:bg-[#0E1712] text-ink-900 dark:text-[#F3F6F1] transition-colors duration-200">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
