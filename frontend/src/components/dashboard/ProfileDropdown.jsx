import { useState, useRef, useEffect } from "react";
import { ChevronDown, UserCircle, Settings, LogOut } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

function ProfileDropdown() {
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const menuItems = [
    { label: "My Profile", icon: UserCircle, onClick: () => navigate("/dashboard/profile") },
    { label: "Settings", icon: Settings, onClick: () => navigate("/dashboard/settings") },
    { label: "Logout", icon: LogOut, onClick: handleLogout, danger: true },
  ];

  const initials = user?.name
    ? user.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "U";

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-full px-2 py-1 text-left transition-colors hover:bg-gray-100 dark:hover:bg-white/10 cursor-pointer focus:outline-none"
      >
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#1F5C3E] text-xs font-semibold text-white">
          {initials}
        </span>
        <span className="hidden leading-tight sm:block">
          <span className="block text-sm font-medium text-gray-900 dark:text-white">
            {user?.name || "User"}
          </span>
          <span className="block text-[11px] text-gray-500 dark:text-[#8A968C]">
            {user?.email || ""}
          </span>
        </span>
        <ChevronDown className={`h-4 w-4 text-gray-400 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute right-0 top-full z-30 mt-2 w-52 overflow-hidden rounded-xl border border-gray-100 bg-white py-1.5 shadow-lg dark:border-[#293227] dark:bg-[#17221B]">
          {menuItems.map(({ label, icon: Icon, onClick, danger }) => (
            <button
              key={label}
              type="button"
              onClick={() => { onClick(); setOpen(false); }}
              className={`flex w-full items-center gap-2.5 px-4 py-2.5 text-left text-sm transition-colors cursor-pointer ${
                danger
                  ? "text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-500/10"
                  : "text-gray-700 hover:bg-gray-50 dark:text-gray-200 dark:hover:bg-white/5"
              }`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default ProfileDropdown;
