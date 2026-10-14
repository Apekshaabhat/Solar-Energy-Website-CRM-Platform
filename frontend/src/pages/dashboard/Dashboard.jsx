import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown, RefreshCw } from "lucide-react";
import StatCard from "../../components/dashboard/StatCard";
import LeadsChart from "../../components/dashboard/LeadsChart";
import SourceDonut from "../../components/dashboard/SourceDonut";
import RecentLeads from "../../components/dashboard/RecentLeads";
import QuickActions from "../../components/dashboard/QuickActions";
import RecentActivity from "../../components/dashboard/RecentActivity";
import PromoBanner from "../../components/dashboard/PromoBanner";
import { statCards as defaultStatCards } from "../../data/dashboardData";
import { dashboardService } from "../../services/dashboardService";
import { useDashboardData } from "../../context/DashboardDataContext";

const cardRouteMap = {
  1: "/dashboard/leads",
  2: "/dashboard/site-surveys",
  3: "/dashboard/projects",
  4: "/dashboard/projects",
};

export default function Dashboard() {
  const navigate = useNavigate();
  const { refreshToken } = useDashboardData();
  const [summary, setSummary] = useState(null);
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadDashboard() {
    setLoading(true);
    setError("");
    try {
      const [sumData, actData] = await Promise.all([
        dashboardService.getSummary(),
        dashboardService.getActivities(10),
      ]);
      setSummary(sumData);
      setActivities(Array.isArray(actData) ? actData : []);
    } catch (err) {
      setError(err.message || "Failed to load dashboard data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, [refreshToken]);

  const cards = summary?.statCards || summary?.stats || defaultStatCards;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-ink-900 dark:text-[#F3F6F1]">Dashboard</h1>
          <p className="text-ink-600 dark:text-[#B9C4BB] mt-1 text-sm sm:text-base">
            Welcome back! Real-time CRM metrics and solar workflow tracking.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={loadDashboard}
            disabled={loading}
            className="flex items-center gap-2 text-sm font-medium border border-line dark:border-[#293227] rounded-lg px-3 py-2.5 bg-white dark:bg-[#17221B] text-ink-900 dark:text-[#F3F6F1] hover:bg-[#f4f6f4] dark:hover:bg-[#1f2d24] transition-colors cursor-pointer"
            title="Refresh CRM Data"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-leaf-600" : "text-ink-400"}`} />
            Refresh
          </button>
          <button
            type="button"
            className="flex items-center gap-2 text-sm font-medium border border-line dark:border-[#293227] rounded-lg px-4 py-2.5 bg-white dark:bg-[#17221B] text-ink-900 dark:text-[#F3F6F1] focus:outline-none transition-colors"
          >
            Last 30 Days
            <ChevronDown className="w-4 h-4 text-ink-400 dark:text-[#8A968C]" />
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 dark:bg-red-950/20 px-4 py-3 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {cards.map((card, idx) => (
          <StatCard
            key={card.id || idx}
            {...card}
            onClick={() => {
              const target = cardRouteMap[card.id] || cardRouteMap[idx + 1];
              if (target) navigate(target);
            }}
          />
        ))}
      </div>

      <div className="flex flex-col lg:flex-row gap-4">
        <LeadsChart data={summary?.leadsOverview || summary?.trends} />
        <SourceDonut data={summary?.leadsBySource || summary?.sources} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2">
          <RecentLeads leads={summary?.recentLeads || summary?.leads} />
        </div>
        <div className="space-y-4">
          <QuickActions />
          <RecentActivity items={activities.length > 0 ? activities : summary?.recentActivity} />
        </div>
      </div>

      <PromoBanner />
    </div>
  );
}
