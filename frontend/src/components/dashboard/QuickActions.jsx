import { useNavigate } from "react-router-dom";
import { Plus, CalendarPlus, FolderPlus, Calculator } from "lucide-react";
import { quickActions } from "../../data/dashboardData";

const icons = {
  plus: Plus,
  calendar: CalendarPlus,
  folder: FolderPlus,
  calculator: Calculator,
};

const routeMap = {
  1: "/dashboard/leads",
  2: "/dashboard/site-surveys",
  3: "/dashboard/projects",
  4: "/dashboard/calculator",
};

export default function QuickActions() {
  const navigate = useNavigate();

  return (
    <div className="bg-white dark:bg-[#17221B] rounded-2xl border border-line dark:border-[#293227] p-5 sm:p-6">
      <h3 className="font-semibold text-ink-900 dark:text-[#F3F6F1] mb-4">Quick Actions</h3>
      <div className="grid grid-cols-2 gap-3">
        {quickActions.map((action) => {
          const Icon = icons[action.icon] ?? Plus;
          return (
            <button
              key={action.id}
              type="button"
              onClick={() => {
                const target = routeMap[action.id] || "/dashboard";
                navigate(target);
              }}
              className="flex flex-col items-start gap-2.5 rounded-xl border border-line dark:border-[#293227] dark:bg-[#152019] p-4 text-left hover:border-leaf-500/40 hover:shadow-sm transition-all cursor-pointer"
            >
              <span className={`w-9 h-9 rounded-lg grid place-items-center text-white ${action.tint}`}>
                <Icon className="w-[18px] h-[18px]" />
              </span>
              <span>
                <span className="block text-sm font-medium text-ink-900 dark:text-[#F3F6F1]">{action.title}</span>
                <span className="block text-xs text-ink-400 dark:text-[#8A968C] mt-0.5">{action.subtitle}</span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
