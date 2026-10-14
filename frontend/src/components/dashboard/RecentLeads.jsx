import { useNavigate } from "react-router-dom";
import StatusBadge from "./StatusBadge";
import { allLeads } from "../../data/dashboardData";

export default function RecentLeads({ leads = [] }) {
  const navigate = useNavigate();
  const rows = leads && leads.length > 0 ? leads.slice(0, 5) : allLeads.slice(0, 5);
  return (
    <div className="bg-white dark:bg-[#17221B] rounded-2xl border border-line dark:border-[#293227] p-5 sm:p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-ink-900 dark:text-[#F3F6F1]">Recent Leads</h3>
        <button
          type="button"
          onClick={() => navigate("/dashboard/leads")}
          className="text-sm font-medium text-leaf-600 dark:text-leaf-400 hover:text-leaf-700 cursor-pointer"
        >
          View All
        </button>
      </div>

      <div className="overflow-x-auto no-scrollbar -mx-2">
        <table className="w-full text-sm min-w-[640px]">
          <thead>
            <tr className="text-left text-ink-400 dark:text-[#8A968C] text-xs uppercase tracking-wide">
              <th className="px-2 pb-3 font-medium">#</th>
              <th className="px-2 pb-3 font-medium">Name</th>
              <th className="px-2 pb-3 font-medium">Location</th>
              <th className="px-2 pb-3 font-medium">Property Type</th>
              <th className="px-2 pb-3 font-medium">Status</th>
              <th className="px-2 pb-3 font-medium">Created At</th>
              <th className="px-2 pb-3 font-medium text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((lead, i) => (
              <tr key={lead.id} className="border-t border-line dark:border-[#293227]">
                <td className="px-2 py-3 text-ink-400 dark:text-[#8A968C]">{i + 1}</td>
                <td className="px-2 py-3 font-medium text-ink-900 dark:text-[#F3F6F1] whitespace-nowrap">{lead.name}</td>
                <td className="px-2 py-3 text-ink-600 dark:text-[#B9C4BB]">{lead.location}</td>
                <td className="px-2 py-3 text-ink-600 dark:text-[#B9C4BB]">{lead.propertyType}</td>
                <td className="px-2 py-3">
                  <StatusBadge status={lead.status} />
                </td>
                <td className="px-2 py-3 text-ink-600 dark:text-[#B9C4BB] whitespace-nowrap">{lead.createdAt}</td>
                <td className="px-2 py-3 text-right">
                  <button type="button" className="text-leaf-600 dark:text-leaf-400 font-medium hover:underline">
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
