import { UserRound, CalendarCheck, CheckCircle2 } from "lucide-react";
import { recentActivity } from "../../data/dashboardData";

const icons = {
  user: UserRound,
  calendar: CalendarCheck,
  check: CheckCircle2,
};

export default function RecentActivity({ items = [] }) {
  const displayItems = items && items.length > 0 ? items : recentActivity;

  return (
    <div className="bg-white dark:bg-[#17221B] rounded-2xl border border-line dark:border-[#293227] p-5 sm:p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-ink-900 dark:text-[#F3F6F1]">Recent Activity</h3>
      </div>

      <ul className="space-y-4">
        {displayItems.slice(0, 7).map((item) => {
          const Icon = icons[item.icon] ?? UserRound;
          const timeLabel = item.time_ago || item.time || "Just now";
          return (
            <li key={item.id} className="flex items-start gap-3">
              <span className={`w-9 h-9 rounded-full grid place-items-center text-white shrink-0 ${item.tint || "bg-[#1F5C3E]"}`}>
                <Icon className="w-[16px] h-[16px]" />
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-ink-900 dark:text-[#F3F6F1]">{item.title}</p>
                <p className="text-xs text-ink-400 dark:text-[#8A968C]">{item.subtitle}</p>
              </div>
              <span className="text-xs text-ink-400 dark:text-[#8A968C] whitespace-nowrap">{timeLabel}</span>
            </li>
          );
        })}
        {displayItems.length === 0 && (
          <li className="text-xs text-ink-400 py-3 text-center">No recent activities recorded yet.</li>
        )}
      </ul>
    </div>
  );
}
