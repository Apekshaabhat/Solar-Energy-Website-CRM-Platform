import React, { useState } from 'react';
import { Leaf, ChevronDown, Search, ArrowRight, Menu, X, Sun, Moon } from 'lucide-react';
import { useAuth, getDefaultRouteForRole } from '../context/AuthContext';

export default function Header({ theme, isDark, toggleTheme, activePage, currentPage, navigate, setCurrentPage }) {
  const { user, isAuthenticated, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [calculatorsOpen, setCalculatorsOpen] = useState(false);

  const nav = navigate || setCurrentPage;
  const rawCurrent = activePage || currentPage || 'home';
  const current = String(rawCurrent).toLowerCase().trim().replace(/^#\/*/, "").replace(/^\/*/, "");

  const navItems = [
    { id: 'home', label: 'Home' },
    { id: 'about', label: 'About Us' },
    { id: 'services', label: 'Services' },
    { id: 'projects', label: 'Projects' },
    { id: 'calculators', label: 'Calculators', hasDropdown: true },
    { id: 'blog', label: 'Blog' },
    { id: 'contact', label: 'Contact' },
  ];

  const handleNavClick = (id) => {
    if (id) {
      nav(id);
    }
    setMobileMenuOpen(false);
  };

  return (
    <header
      className="sticky top-0 z-50 transition-colors duration-200 border-b"
      style={{
        backgroundColor: theme.bg,
        borderColor: theme.border,
      }}
    >
      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-8 xl:px-10 h-20 flex items-center justify-between">
        
        {/* Left: Circular Dark Green Logo Mark + Wordmark & Tagline */}
        <button
          type="button"
          onClick={() => nav('Home')}
          className="flex items-center gap-3 group focus:outline-none text-left whitespace-nowrap"
        >
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 transition-transform group-hover:scale-105"
            style={{ backgroundColor: theme.green }}
          >
            <Leaf className="w-5 h-5 text-white" />
          </div>
          <div className="flex flex-col">
            <span
              className="font-bold text-xl tracking-tight leading-none"
              style={{ color: theme.text }}
            >
              SOLARA
            </span>
            <span
              className="text-[11px] font-medium tracking-tight mt-0.5"
              style={{ color: theme.textFaint }}
            >
              Clean Energy, Brighter Tomorrow.
            </span>
          </div>
        </button>

        {/* Center: Nav links + Search icon */}
        <div className="hidden xl:flex items-center gap-5">
          <nav className="flex items-center gap-5 text-[15px]">
            {navItems.map((item) => {
              const cur = current.toLowerCase();
              const isActive =
                cur === item.id.toLowerCase() ||
                (item.id === 'about' && cur === 'about us') ||
                (item.id === 'calculators' && ['calculators', 'solar-savings', 'roof-capacity', 'roof-calculator', 'roi-estimator', 'roi'].includes(cur));

              if (item.hasDropdown) {
                return (
                  <div key={item.id} className="relative group">
                    <button
                      type="button"
                      onClick={() => handleNavClick('calculators')}
                      className="font-medium transition-colors py-1 flex items-center gap-1 focus:outline-none whitespace-nowrap"
                      style={{
                        color: isActive ? theme.green : theme.textMuted,
                      }}
                    >
                      {item.label}
                      <ChevronDown
                        className="w-4 h-4 transition-colors"
                        style={{ color: theme.textFaint }}
                      />
                    </button>

                    {/* Submenu */}
                    <div
                      className="absolute top-full left-0 mt-2 w-52 rounded-xl shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 py-2 z-50 border"
                      style={{
                        backgroundColor: theme.card,
                        borderColor: theme.border,
                      }}
                    >
                      <button
                        type="button"
                        onClick={() => handleNavClick('solar-savings')}
                        className="w-full text-left px-4 py-2 text-sm transition-colors whitespace-nowrap cursor-pointer"
                        style={{ color: theme.textMuted }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.backgroundColor = theme.bgAlt;
                          e.currentTarget.style.color = theme.green;
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = 'transparent';
                          e.currentTarget.style.color = theme.textMuted;
                        }}
                      >
                        Solar Savings Calculator
                      </button>
                      <button
                        type="button"
                        onClick={() => handleNavClick('roof-capacity')}
                        className="w-full text-left px-4 py-2 text-sm transition-colors whitespace-nowrap cursor-pointer"
                        style={{ color: theme.textMuted }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.backgroundColor = theme.bgAlt;
                          e.currentTarget.style.color = theme.green;
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = 'transparent';
                          e.currentTarget.style.color = theme.textMuted;
                        }}
                      >
                        Roof Capacity Calculator
                      </button>
                      <button
                        type="button"
                        onClick={() => handleNavClick('roi-estimator')}
                        className="w-full text-left px-4 py-2 text-sm transition-colors whitespace-nowrap cursor-pointer"
                        style={{ color: theme.textMuted }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.backgroundColor = theme.bgAlt;
                          e.currentTarget.style.color = theme.green;
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = 'transparent';
                          e.currentTarget.style.color = theme.textMuted;
                        }}
                      >
                        ROI Estimator
                      </button>
                    </div>
                  </div>
                );
              }

              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => handleNavClick(item.id)}
                  className={`relative py-1 transition-colors whitespace-nowrap ${
                    isActive ? 'font-bold' : 'font-medium'
                  }`}
                  style={{
                    color: isActive ? theme.green : theme.textMuted,
                  }}
                >
                  {item.label}
                  {isActive && (
                    <span
                      className="absolute bottom-[-2px] left-0 right-0 h-[2px] rounded-full"
                      style={{ backgroundColor: theme.green }}
                    />
                  )}
                </button>
              );
            })}
          </nav>

          {/* Search Button */}
          <button
            type="button"
            className="p-2 rounded-full transition-colors focus:outline-none"
            style={{ color: theme.textMuted }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = theme.green;
              e.currentTarget.style.backgroundColor = theme.bgAlt;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = theme.textMuted;
              e.currentTarget.style.backgroundColor = 'transparent';
            }}
            aria-label="Search"
          >
            <Search className="w-4 h-4 stroke-[2.2]" />
          </button>
        </div>

        {/* Right: Theme Toggle, Log In, Sign Up */}
        <div className="flex items-center gap-2.5">
          {/* Circular Theme Toggle Button */}
          <button
            type="button"
            onClick={toggleTheme}
            className="w-10 h-10 rounded-full border flex items-center justify-center transition-all duration-200 focus:outline-none"
            style={{
              borderColor: theme.border,
              backgroundColor: theme.card,
              color: theme.text,
            }}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = theme.green)}
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = theme.border)}
            aria-label="Toggle Theme"
            title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
          >
            {isDark ? (
              <Sun className="w-5 h-5 text-amber-400" />
            ) : (
              <Moon className="w-5 h-5 text-[#1F5C3E]" />
            )}
          </button>

          {isAuthenticated && user ? (
            <div className="hidden xl:flex items-center gap-3">
              <button
                type="button"
                onClick={() => {
                  window.location.href = getDefaultRouteForRole(user.role);
                }}
                className="flex items-center gap-2 px-3.5 py-1.5 rounded-full border transition-all focus:outline-none hover:scale-105"
                style={{
                  borderColor: theme.border,
                  backgroundColor: theme.card,
                }}
              >
                <span
                  className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold text-white"
                  style={{ backgroundColor: theme.green }}
                >
                  {user.name ? user.name.slice(0, 2).toUpperCase() : 'U'}
                </span>
                <span className="text-sm font-medium" style={{ color: theme.text }}>
                  {user.name}
                </span>
                <span
                  className="text-[11px] px-2 py-0.5 rounded-full font-medium"
                  style={{ backgroundColor: theme.greenSoft, color: theme.green }}
                >
                  {user.role}
                </span>
              </button>

              <button
                type="button"
                onClick={async () => {
                  await logout();
                  nav('Login');
                }}
                className="text-xs font-semibold px-2 py-1.5 rounded-lg transition-colors focus:outline-none hover:underline"
                style={{ color: theme.textMuted }}
              >
                Logout
              </button>
            </div>
          ) : (
            <>
              {/* Log In Button (Plain text, green when active) */}
              <button
                type="button"
                onClick={() => nav('Login')}
                className="hidden xl:inline-flex items-center font-medium text-sm transition-colors py-2 px-3 focus:outline-none whitespace-nowrap"
                style={{
                  color: current.toLowerCase() === 'login' ? theme.green : theme.textMuted,
                }}
                onMouseEnter={(e) => {
                  if (current.toLowerCase() !== 'login') {
                    e.currentTarget.style.color = theme.green;
                  }
                }}
                onMouseLeave={(e) => {
                  if (current.toLowerCase() !== 'login') {
                    e.currentTarget.style.color = theme.textMuted;
                  }
                }}
              >
                Log In
              </button>

              {/* Sign Up Button (Filled green pill with right-arrow icon) */}
              <button
                type="button"
                onClick={() => nav('Signup')}
                className="hidden xl:inline-flex items-center justify-center gap-2 font-medium text-sm px-5 py-2.5 rounded-full transition-colors text-white focus:outline-none whitespace-nowrap"
                style={{ backgroundColor: theme.green }}
                onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = theme.greenHover)}
                onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = theme.green)}
              >
                <span>Sign Up</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </>
          )}

          {/* Mobile Menu Toggle Button */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="xl:hidden p-2 rounded-lg transition-colors focus:outline-none"
            style={{ color: theme.text }}
            aria-label="Toggle Navigation Menu"
          >
            {mobileMenuOpen ? (
              <X className="w-6 h-6" />
            ) : (
              <Menu className="w-6 h-6" />
            )}
          </button>
        </div>
      </div>

      {/* Mobile Navigation Dropdown */}
      {mobileMenuOpen && (
        <div
          className="xl:hidden border-b px-4 pt-2 pb-6 space-y-4 transition-colors"
          style={{
            backgroundColor: theme.bg,
            borderColor: theme.border,
          }}
        >
          <nav className="flex flex-col space-y-1 text-base font-medium">
            {navItems.map((item) => {
              const cur = current.toLowerCase();
              const isActive =
                cur === item.id.toLowerCase() ||
                (item.id === 'about' && cur === 'about us') ||
                (item.id === 'calculators' && ['calculators', 'solar-savings', 'roof-capacity', 'roof-calculator', 'roi-estimator', 'roi'].includes(cur));
              if (item.hasDropdown) {
                return (
                  <div key={item.id} className="py-2 border-b" style={{ borderColor: `${theme.border}40` }}>
                    <button
                      type="button"
                      className="w-full flex items-center justify-between text-left whitespace-nowrap"
                      style={{ color: theme.textMuted }}
                      onClick={() => setCalculatorsOpen(!calculatorsOpen)}
                    >
                      <span>Calculators</span>
                      <ChevronDown
                        className={`w-4 h-4 transition-transform duration-200 ${
                          calculatorsOpen ? 'rotate-180' : ''
                        }`}
                      />
                    </button>
                    {calculatorsOpen && (
                      <div className="pl-4 mt-2 space-y-2 text-sm" style={{ color: theme.textFaint }}>
                        <button
                          type="button"
                          onClick={() => handleNavClick('solar-savings')}
                          className="block w-full text-left py-1 whitespace-nowrap cursor-pointer"
                        >
                          Solar Savings Calculator
                        </button>
                        <button
                          type="button"
                          onClick={() => handleNavClick('roof-capacity')}
                          className="block w-full text-left py-1 whitespace-nowrap cursor-pointer"
                        >
                          Roof Capacity Calculator
                        </button>
                        <button
                          type="button"
                          onClick={() => handleNavClick('roi-estimator')}
                          className="block w-full text-left py-1 whitespace-nowrap cursor-pointer"
                        >
                          ROI Estimator
                        </button>
                      </div>
                    )}
                  </div>
                );
              }

              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => handleNavClick(item.id)}
                  className={`w-full text-left py-2.5 border-b transition-colors whitespace-nowrap ${
                    isActive ? 'font-bold' : 'font-medium'
                  }`}
                  style={{
                    color: isActive ? theme.green : theme.textMuted,
                    borderColor: `${theme.border}40`,
                  }}
                >
                  {item.label}
                </button>
              );
            })}

            {isAuthenticated && user ? (
              <div className="py-2 space-y-2">
                <div
                  className="p-3 rounded-xl border flex items-center justify-between"
                  style={{ borderColor: theme.border, backgroundColor: theme.card }}
                >
                  <div className="flex items-center gap-2.5">
                    <span
                      className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold text-white"
                      style={{ backgroundColor: theme.green }}
                    >
                      {user.name ? user.name.slice(0, 2).toUpperCase() : "U"}
                    </span>
                    <div>
                      <p className="text-sm font-semibold" style={{ color: theme.text }}>
                        {user.name}
                      </p>
                      <p className="text-xs" style={{ color: theme.textMuted }}>
                        {user.role}
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      window.location.href = getDefaultRouteForRole(user.role);
                      setMobileMenuOpen(false);
                    }}
                    className="px-3 py-1 rounded-full text-xs font-medium text-white"
                    style={{ backgroundColor: theme.green }}
                  >
                    Dashboard
                  </button>
                </div>

                <button
                  type="button"
                  onClick={async () => {
                    await logout();
                    setMobileMenuOpen(false);
                    nav("Login");
                  }}
                  className="w-full text-left py-2.5 border-b text-sm font-medium transition-colors text-red-600 border-red-100"
                >
                  Logout
                </button>
              </div>
            ) : (
              <>
                {/* Mobile Log In Entry */}
                <button
                  type="button"
                  onClick={() => {
                    nav("Login");
                    setMobileMenuOpen(false);
                  }}
                  className={`w-full text-left py-2.5 border-b transition-colors whitespace-nowrap ${
                    current.toLowerCase() === "login" ? "font-bold" : "font-medium"
                  }`}
                  style={{
                    color: current.toLowerCase() === "login" ? theme.green : theme.textMuted,
                    borderColor: `${theme.border}40`,
                  }}
                >
                  Log In
                </button>

                {/* Mobile Sign Up Entry */}
                <button
                  type="button"
                  onClick={() => {
                    nav("Signup");
                    setMobileMenuOpen(false);
                  }}
                  className={`w-full text-left py-2.5 border-b transition-colors flex items-center justify-between whitespace-nowrap ${
                    current.toLowerCase() === "signup" ? "font-bold" : "font-medium"
                  }`}
                  style={{
                    color: current.toLowerCase() === "signup" ? theme.green : theme.textMuted,
                    borderColor: `${theme.border}40`,
                  }}
                >
                  <span>Sign Up</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </>
            )}
          </nav>

          <div className="pt-2 flex items-center justify-center">
            {/* Mobile Theme Toggle Button */}
            <button
              type="button"
              onClick={toggleTheme}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-full border text-sm font-medium"
              style={{
                backgroundColor: theme.card,
                borderColor: theme.border,
                color: theme.text,
              }}
            >
              {isDark ? (
                <>
                  <Sun className="w-4 h-4 text-amber-400" />
                  <span>Light Mode</span>
                </>
              ) : (
                <>
                  <Moon className="w-4 h-4 text-[#1F5C3E]" />
                  <span>Dark Mode</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </header>
  );
}
