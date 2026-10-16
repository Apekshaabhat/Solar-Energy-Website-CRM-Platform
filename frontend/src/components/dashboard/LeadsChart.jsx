import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

function CustomTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-forest-950 dark:bg-[#0A0F0B] border border-transparent dark:border-[#293227] text-white text-xs rounded-lg px-3 py-2 shadow-lg">
        <p className="font-semibold">{payload[0].value} Leads</p>
        <p className="text-white/60">{label}</p>
      </div>
    );
  }
  return null;
}

export default function LeadsChart({ data = [] }) {
  const chartData = Array.isArray(data) ? data : [];
  const hasData = chartData.length > 0;

  return (
    <div className="bg-white dark:bg-[#17221B] rounded-2xl border border-line dark:border-[#293227] p-5 sm:p-6 flex-1 min-w-0 transition-colors">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-ink-900 dark:text-[#F3F6F1]">Leads Overview</h3>
        <select className="text-sm border border-line dark:border-[#293227] rounded-lg px-3 py-1.5 text-ink-600 dark:text-[#F3F6F1] bg-white dark:bg-[#17221B] focus:outline-none transition-colors">
          <option className="dark:bg-[#17221B] dark:text-[#F3F6F1]">Last 30 Days</option>
          <option className="dark:bg-[#17221B] dark:text-[#F3F6F1]">Last 7 Days</option>
          <option className="dark:bg-[#17221B] dark:text-[#F3F6F1]">Last 90 Days</option>
        </select>
      </div>

      <div className="h-72">
        {hasData ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="leadsFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#24b368" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#24b368" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} stroke="#293227" opacity={0.3} />
              <XAxis
                dataKey="date"
                tickLine={false}
                axisLine={false}
                tick={{ fill: "#8a978f", fontSize: 12 }}
                interval="preserveStartEnd"
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tick={{ fill: "#8a978f", fontSize: 12 }}
                width={30}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="leads"
                stroke="#1e9e5a"
                strokeWidth={2.5}
                fill="url(#leadsFill)"
                dot={{ r: 3, fill: "#1e9e5a", strokeWidth: 0 }}
                activeDot={{ r: 5 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center text-center p-6 border border-dashed border-line dark:border-[#293227] rounded-xl">
            <p className="text-sm font-medium text-ink-700 dark:text-[#F3F6F1]">No lead volume recorded in this period</p>
            <p className="text-xs text-ink-400 dark:text-[#8A968C] mt-1">
              New leads will automatically be tracked and charted on this timeline.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
