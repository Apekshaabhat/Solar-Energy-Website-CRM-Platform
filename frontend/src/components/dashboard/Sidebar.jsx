import { NavLink, useNavigate } from "react-router-dom";
import {
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
  Leaf,
  Users,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";

export default function Sidebar({ tagline = ["Powering a", "Sustainable Future"] }) {
  const navigate = useNavigate();
  const { user, logout, isAdmin, isManager } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
    } finally {
      navigate("/login");
    }
  };

  const navItems = [
    { label: "Dashboard", icon: LayoutDashboard, to: "/dashboard" },
    ...((isAdmin || isManager) ? [
      { label: "Users", icon: Users, to: "/dashboard/users" }
    ] : []),
    { label: "Leads", icon: Users2, to: "/dashboard/leads" },
    { label: "Customers", icon: UserSquare2, to: "/dashboard/customers" },
    { label: "Site Surveys", icon: ClipboardCheck, to: "/dashboard/site-surveys" },
    { label: "Projects", icon: FolderKanban, to: "/dashboard/projects" },
    { label: "Calculators", icon: Calculator, to: "/dashboard/calculators" },
    { label: "Blog Management", icon: FileText, to: "/dashboard/blog" },
    { label: "FAQs", icon: HelpCircle, to: "/dashboard/faqs" },
  ];

  return (
    <aside className="hidden lg:flex flex-col w-64 shrink-0 bg-[#0E1712] text-white/80 h-screen sticky top-0 border-r border-[#293227]">
      <div className="flex items-center gap-2 px-6 py-6">
        <span className="grid place-items-center w-9 h-9 rounded-full bg-[#1F5C3E]">
          <Leaf className="w-5 h-5 text-white" />
        </span>
        <div className="leading-tight">
          <p className="text-white font-bold text-lg tracking-tight">SOLARA</p>
          <p className="text-[11px] text-white/50">{user?.role || "Clean Energy"} Portal</p>
        </div>
      </div>

      <nav className="flex-1 px-3 mt-2 space-y-1 overflow-y-auto">
        {navItems.map(({ label, icon: Icon, to }) => (
          <NavLink
            key={label}
            to={to}
            end={to === "/dashboard"}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive ? "bg-[#1F5C3E] text-white font-medium" : "hover:bg-white/5 text-white/70"
              }`
            }
          >
            <Icon className="w-[18px] h-[18px]" strokeWidth={2} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-4 pb-3 pt-4">
        <div className="rounded-xl bg-white/5 px-3 py-3 flex items-center gap-2.5">
          <Leaf className="w-5 h-5 text-[#3FA46A] shrink-0" />
          <p className="text-[12px] leading-tight text-white/60">
            {tagline[0]}
            <br />
            {tagline[1]}
          </p>
        </div>
      </div>

      <div className="p-3 border-t border-white/10 space-y-1">
        {(isAdmin || isManager) && (
          <NavLink
            to="/dashboard/settings"
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive ? "bg-[#1F5C3E] text-white font-medium" : "text-white/60 hover:bg-white/5 hover:text-white/90"
              }`
            }
          >
            <Settings className="w-[18px] h-[18px]" />
            Settings
          </NavLink>
        )}
        <button
          type="button"
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/60 hover:bg-white/5 hover:text-white/90 transition-colors cursor-pointer text-left"
        >
          <LogOut className="w-[18px] h-[18px]" />
          Logout
        </button>
      </div>
    </aside>
  );
}
