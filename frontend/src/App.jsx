import React, { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import DashboardLayout from "./layouts/DashboardLayout";
import Dashboard from "./pages/dashboard/Dashboard";
import Customers from "./pages/dashboard/Customers";
import Leads from "./pages/dashboard/Leads";
import SiteSurveys from "./pages/dashboard/SiteSurveys";
import BlogManagement from "./pages/dashboard/BlogManagement";
import Users from "./pages/dashboard/Users";
import Settings from "./pages/dashboard/Settings";
import MyProfile from "./pages/dashboard/MyProfile";
import Calculators from "./pages/dashboard/Calculators";
import Projects from "./pages/dashboard/Projects";
import Faqs from "./pages/dashboard/Faqs";

// Public site component imports
import Header from "./components/Header";
import HomePage from "./components/HomePage";
import AboutPage from "./components/AboutPage";
import ServicesPage from "./components/ServicesPage";
import ProjectsPage from "./components/ProjectsPage";
import CalculatorsPage from "./components/CalculatorsPage";
import RoofCapacityCalculator from "./components/RoofCapacityCalculator";
import ROIEstimator from "./components/ROIEstimator";
import BlogPage from "./components/BlogPage";
import ContactPage from "./components/ContactPage";
import LoginPage from "./components/LoginPage";
import SignupPage from "./components/SignupPage";
import ForgotPasswordPage from "./components/ForgotPasswordPage";
import { DashboardDataProvider } from "./context/DashboardDataContext";
import { themes } from "./context/ThemeContext";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import ActivatePage from "./components/ActivatePage";

function PublicSite() {
  const [isDark, setIsDark] = useState(false);
  const location = useLocation();

  const getPageFromLocation = (loc) => {
    let hashStr = loc.hash ? loc.hash.replace(/^#\/*/, "") : "";
    let pathStr = loc.pathname ? loc.pathname.replace(/^\/*/, "") : "";
    const page = (hashStr || pathStr).toLowerCase().trim();
    return page || "home";
  };

  const [activePage, setActivePage] = useState(() => getPageFromLocation(location));

  useEffect(() => {
    setActivePage(getPageFromLocation(location));
  }, [location]);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [activePage]);

  const navigate = (page) => {
    if (!page) return;
    const slug = page.toLowerCase().trim().replace(/^#\/*/, "").replace(/^\/*/, "");
    window.location.hash = "/" + slug;
    setActivePage(slug);
  };

  const toggleTheme = () => {
    setIsDark((prev) => !prev);
  };

  const theme = isDark ? themes.dark : themes.light;

  const renderPage = () => {
    switch (activePage) {
      case "about":
      case "about us":
      case "about-us":
        return <AboutPage theme={theme} navigate={navigate} setCurrentPage={navigate} />;
      case "services":
        return <ServicesPage theme={theme} navigate={navigate} setCurrentPage={navigate} />;
      case "projects":
        return <ProjectsPage theme={theme} navigate={navigate} />;
      case "calculators":
      case "solar-savings":
      case "solar-savings-calculator":
        return <CalculatorsPage theme={theme} navigate={navigate} />;
      case "roof-capacity":
      case "roof-calculator":
      case "roof-capacity-calculator":
        return <RoofCapacityCalculator t={theme} theme={theme} />;
      case "roi-estimator":
      case "roi":
        return <ROIEstimator t={theme} theme={theme} />;
      case "blog":
        return <BlogPage theme={theme} navigate={navigate} setCurrentPage={navigate} />;
      case "contact":
        return <ContactPage theme={theme} navigate={navigate} setCurrentPage={navigate} />;
      case "login":
        return <LoginPage theme={theme} />;
      case "signup":
        return <SignupPage theme={theme} navigate={navigate} />;
      case "forgot-password":
      case "forgot password":
        return <ForgotPasswordPage theme={theme} navigate={navigate} />;
      case "home":
      default:
        return <HomePage theme={theme} navigate={navigate} setCurrentPage={navigate} />;
    }
  };

  return (
    <div
      className="min-h-screen font-sans antialiased selection:bg-[#1F5C3E] selection:text-white transition-colors duration-200"
      style={{
        backgroundColor: theme.bg,
        color: theme.text,
      }}
    >
      <style>{`
        html, body { scrollbar-width: none; -ms-overflow-style: none; }
        html::-webkit-scrollbar, body::-webkit-scrollbar { display: none; width: 0; height: 0; }
        * { scrollbar-width: none; -ms-overflow-style: none; }
        *::-webkit-scrollbar { display: none; width: 0; height: 0; }
      `}</style>
      <Header
        theme={theme}
        isDark={isDark}
        toggleTheme={toggleTheme}
        activePage={activePage}
        currentPage={activePage}
        navigate={navigate}
        setCurrentPage={navigate}
      />
      <main>{renderPage()}</main>
    </div>
  );
}

export default function App() {
  const [isDark] = useState(false);
  const theme = isDark ? themes.dark : themes.light;

  return (
    <BrowserRouter>
      <AuthProvider>
        <DashboardDataProvider>
          <Routes>
            {/* Admin Dashboard Protected Nested Routes */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <DashboardLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Dashboard />} />
              <Route path="customers" element={<Customers />} />
              <Route path="leads" element={<Leads />} />
              <Route path="site-surveys" element={<SiteSurveys />} />
              <Route path="projects" element={<Projects />} />
              <Route path="blog" element={<BlogManagement />} />
              <Route path="calculators" element={<Calculators />} />
              <Route path="faqs" element={<Faqs />} />
              <Route
                path="users"
                element={
                  <ProtectedRoute allowedRoles={["Admin", "Manager"]}>
                    <Users />
                  </ProtectedRoute>
                }
              />
              <Route
                path="settings"
                element={
                  <ProtectedRoute allowedRoles={["Admin", "Manager"]}>
                    <Settings />
                  </ProtectedRoute>
                }
              />
              <Route path="profile" element={<MyProfile />} />
            </Route>

            {/* Public Site Routes */}
            <Route path="/login" element={<LoginPage theme={theme} />} />
            <Route path="/activate" element={<ActivatePage theme={theme} />} />
            <Route path="/*" element={<PublicSite />} />
          </Routes>
        </DashboardDataProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
