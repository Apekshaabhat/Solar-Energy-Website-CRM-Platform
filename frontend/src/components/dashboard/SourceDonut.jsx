import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";

export default function SourceDonut({ data = [] }) {
  const chartData = Array.isArray(data) ? data : [];
  const total = chartData.reduce((sum, s) => sum + (s.value || 0), 0);
  const hasData = chartData.length > 0 && total > 0;

  return (
    <div className="bg-white dark:bg-[#17221B] rounded-2xl border border-line dark:border-[#293227] p-5 sm:p-6 w-full lg:w-[360px] shrink-0">
      <h3 className="font-semibold text-ink-900 dark:text-[#F3F6F1] mb-4">Leads by Source</h3>

      {hasData ? (
        <div className="flex items-center gap-6">
          <div className="relative w-40 h-40 shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={52}
                  outerRadius={72}
                  paddingAngle={2}
                  stroke="none"
                >
                  {chartData.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-2xl font-bold text-ink-900 dark:text-[#F3F6F1]">{total}</span>
              <span className="text-xs text-ink-400 dark:text-[#8A968C] -mt-0.5">Total Leads</span>
            </div>
          </div>

          <ul className="space-y-2.5 text-sm flex-1">
            {chartData.map((s) => (
              <li key={s.name} className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-2 text-ink-600 dark:text-[#B9C4BB]">
                  <span
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: s.color }}
                  />
                  {s.name}
                </span>
                <span className="font-medium text-ink-900 dark:text-[#F3F6F1]">{s.value}%</span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="h-40 flex flex-col items-center justify-center text-center p-4 border border-dashed border-line dark:border-[#293227] rounded-xl">
          <span className="text-2xl font-bold text-ink-900 dark:text-[#F3F6F1]">0</span>
          <p className="text-xs text-ink-400 dark:text-[#8A968C] mt-1">No lead source data available yet</p>
        </div>
      )}
    </div>
  );
}
