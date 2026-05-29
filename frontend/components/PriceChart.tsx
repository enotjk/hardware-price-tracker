"use client";

import { useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import { PriceHistory } from "@/lib/api";

// ─────────────────────────────────────────
// Цвета источников
// ─────────────────────────────────────────
const SOURCE_COLORS: Record<string, string> = {
  "eBay US":      "#3b82f6",  // синий
  "eBay Germany": "#10b981",  // зелёный
  "Amazon US":    "#f59e0b",  // оранжевый
  "Amazon DE":    "#f97316",  // тёмно-оранжевый
  "Newegg US":    "#8b5cf6",  // фиолетовый
};

const PERIOD_OPTIONS = [
  { label: "7д",  days: 7 },
  { label: "14д", days: 14 },
  { label: "30д", days: 30 },
  { label: "90д", days: 90 },
];

// ─────────────────────────────────────────
// Типы
// ─────────────────────────────────────────
interface PriceChartProps {
  data: PriceHistory[];
  msrp?: number | null;
  onPeriodChange?: (days: number) => void;
  isLoading?: boolean;
}

interface ChartDataPoint {
  date: string;
  [source: string]: number | string | null;
}

// ─────────────────────────────────────────
// Кастомный Tooltip
// ─────────────────────────────────────────
const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-3 shadow-xl">
      <p className="text-gray-400 text-xs mb-2">{label}</p>
      {payload.map((entry: any) => (
        <div key={entry.name} className="flex items-center gap-2 text-sm">
          <span
            className="w-2 h-2 rounded-full flex-shrink-0"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-gray-300">{entry.name}:</span>
          <span className="text-white font-medium">
            ${Number(entry.value).toLocaleString("en-US", { minimumFractionDigits: 2 })}
          </span>
        </div>
      ))}
    </div>
  );
};

// ─────────────────────────────────────────
// Трансформация данных для recharts
// ─────────────────────────────────────────
function transformData(data: PriceHistory[]): {
  chartData: ChartDataPoint[];
  sources: string[];
} {
  // Группируем по дате
  const byDate: Record<string, Record<string, number>> = {};
  const sourcesSet = new Set<string>();

  for (const point of data) {
    const date = point.date_id;
    const source = point.display_name;
    const price = parseFloat(point.price_usd);

    if (!byDate[date]) byDate[date] = {};
    // Если несколько записей за день — берём минимальную цену
    if (!byDate[date][source] || price < byDate[date][source]) {
      byDate[date][source] = price;
    }
    sourcesSet.add(source);
  }

  const chartData = Object.entries(byDate)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, prices]) => ({
      date,
      ...prices,
    }));

  return { chartData, sources: Array.from(sourcesSet) };
}

// ─────────────────────────────────────────
// Главный компонент
// ─────────────────────────────────────────
export default function PriceChart({
  data,
  msrp,
  onPeriodChange,
  isLoading = false,
}: PriceChartProps) {
  const [activePeriod, setActivePeriod] = useState(30);

  const handlePeriodChange = (days: number) => {
    setActivePeriod(days);
    onPeriodChange?.(days);
  };

  // Тестовые данные если нет реальных
  const displayData = data.length > 0 ? data : MOCK_DATA;
  const { chartData, sources } = transformData(displayData);

  return (
    <div className="flex flex-col gap-4">

      {/* Кнопки периода */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1">
          {PERIOD_OPTIONS.map(({ label, days }) => (
            <button
              key={days}
              onClick={() => handlePeriodChange(days)}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                activePeriod === days
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        {data.length === 0 && (
          <span className="text-xs text-gray-500">тестовые данные</span>
        )}
      </div>

      {/* График */}
      <div className="h-64 w-full">
        {isLoading ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-gray-500 text-sm">Загрузка...</div>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />

              <XAxis
                dataKey="date"
                tick={{ fill: "#6b7280", fontSize: 11 }}
                tickLine={false}
                axisLine={{ stroke: "#374151" }}
                tickFormatter={(val) => {
                  const date = new Date(val);
                  return `${date.getDate()}.${date.getMonth() + 1}`;
                }}
              />

              <YAxis
                tick={{ fill: "#6b7280", fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(val) => `$${val.toLocaleString()}`}
                width={70}
              />

              <Tooltip content={<CustomTooltip />} />

              <Legend
                wrapperStyle={{ paddingTop: "12px" }}
                formatter={(value) => (
                  <span style={{ color: "#9ca3af", fontSize: "12px" }}>{value}</span>
                )}
              />

              {/* Линия MSRP */}
              {msrp && (
                <ReferenceLine
                  y={msrp}
                  stroke="#4b5563"
                  strokeDasharray="6 3"
                  label={{
                    value: `MSRP $${msrp}`,
                    position: "right",
                    fill: "#6b7280",
                    fontSize: 10,
                  }}
                />
              )}

              {/* Линии по источникам */}
              {sources.map((source) => (
                <Line
                  key={source}
                  type="monotone"
                  dataKey={source}
                  stroke={SOURCE_COLORS[source] ?? "#94a3b8"}
                  strokeWidth={2}
                  dot={{ r: 3, fill: SOURCE_COLORS[source] ?? "#94a3b8" }}
                  activeDot={{ r: 5 }}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────
// Тестовые данные для проверки без API
// ─────────────────────────────────────────
const MOCK_DATA: PriceHistory[] = [
  { date_id: "2026-05-20", price_usd: "1849.99", price_original: "1849.99", currency: "USD", source_name: "ebay", display_name: "eBay US", region: "US" },
  { date_id: "2026-05-21", price_usd: "1799.00", price_original: "1799.00", currency: "USD", source_name: "ebay", display_name: "eBay US", region: "US" },
  { date_id: "2026-05-22", price_usd: "1920.00", price_original: "1920.00", currency: "USD", source_name: "ebay", display_name: "eBay US", region: "US" },
  { date_id: "2026-05-23", price_usd: "1875.00", price_original: "1875.00", currency: "USD", source_name: "ebay", display_name: "eBay US", region: "US" },
  { date_id: "2026-05-24", price_usd: "1950.00", price_original: "1950.00", currency: "USD", source_name: "ebay", display_name: "eBay US", region: "US" },
  { date_id: "2026-05-25", price_usd: "1899.00", price_original: "1899.00", currency: "USD", source_name: "ebay", display_name: "eBay US", region: "US" },
  { date_id: "2026-05-26", price_usd: "2093.99", price_original: "2093.99", currency: "USD", source_name: "ebay", display_name: "eBay US", region: "US" },
  { date_id: "2026-05-20", price_usd: "2100.00", price_original: "1805.00", currency: "EUR", source_name: "ebay", display_name: "eBay Germany", region: "DE" },
  { date_id: "2026-05-21", price_usd: "2050.00", price_original: "1762.00", currency: "EUR", source_name: "ebay", display_name: "eBay Germany", region: "DE" },
  { date_id: "2026-05-22", price_usd: "2200.00", price_original: "1890.00", currency: "EUR", source_name: "ebay", display_name: "eBay Germany", region: "DE" },
  { date_id: "2026-05-23", price_usd: "2150.00", price_original: "1847.00", currency: "EUR", source_name: "ebay", display_name: "eBay Germany", region: "DE" },
  { date_id: "2026-05-24", price_usd: "2300.00", price_original: "1976.00", currency: "EUR", source_name: "ebay", display_name: "eBay Germany", region: "DE" },
  { date_id: "2026-05-25", price_usd: "2180.00", price_original: "1873.00", currency: "EUR", source_name: "ebay", display_name: "eBay Germany", region: "DE" },
  { date_id: "2026-05-26", price_usd: "3957.39", price_original: "3399.00", currency: "EUR", source_name: "ebay", display_name: "eBay Germany", region: "DE" },
];
