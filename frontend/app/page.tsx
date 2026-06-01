"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  getPipelineStats,
  getPriceChanges,
  searchProducts,
  Product,
  Stats,
  TopMover,
} from "@/lib/api";

// ─────────────────────────────────────────
// Вспомогательные компоненты
// ─────────────────────────────────────────

function MetricCard({ label, value, sub, accent }: {
  label: string; value: string; sub?: string; accent?: "green" | "red" | "blue";
}) {
  const color = accent === "green" ? "text-emerald-400"
    : accent === "red" ? "text-red-400"
    : accent === "blue" ? "text-blue-400"
    : "text-white";
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">{label}</div>
      <div className={`text-2xl font-semibold ${color}`}>{value}</div>
      {sub && <div className="text-xs text-gray-500 mt-1">{sub}</div>}
    </div>
  );
}

function CategoryChip({ label, active, onClick }: {
  label: string; active: boolean; onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1 rounded-full text-sm font-medium border transition-all ${
        active
          ? "bg-blue-600 border-blue-500 text-white"
          : "bg-transparent border-gray-700 text-gray-400 hover:border-gray-500 hover:text-gray-200"
      }`}
    >
      {label}
    </button>
  );
}

function PriceChangeBadge({ pct }: { pct: string | null }) {
  if (!pct) return <span className="text-gray-600 text-sm">—</span>;
  const val = parseFloat(pct);
  const isUp = val > 0;
  return (
    <span className={`text-sm font-semibold ${isUp ? "text-red-400" : "text-emerald-400"}`}>
      {isUp ? "+" : ""}{val.toFixed(1)}%
    </span>
  );
}

// ─────────────────────────────────────────
// Главная страница
// ─────────────────────────────────────────
export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [allMovers, setAllMovers] = useState<TopMover[]>([]);
  const [filteredMovers, setFilteredMovers] = useState<TopMover[]>([]);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Product[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [loading, setLoading] = useState(true);

  // Загрузка данных
  useEffect(() => {
    getPipelineStats().then(setStats).catch(console.error);
    getPriceChanges(undefined).then((data) => {
      setAllMovers(data);
      setFilteredMovers(data);
      setLoading(false);
    }).catch(console.error);
  }, []);

  // Фильтрация по категории
  useEffect(() => {
    if (!activeCategory) {
      setFilteredMovers(allMovers);
    } else {
      setFilteredMovers(allMovers.filter(m => m.category === activeCategory));
    }
  }, [activeCategory, allMovers]);

  // Поиск с дебаунсом
  useEffect(() => {
    if (searchQuery.length < 2) {
      setSearchResults([]);
      setShowDropdown(false);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const results = await searchProducts(searchQuery);
        setSearchResults(results);
        setShowDropdown(true);
      } catch (e) {
        console.error(e);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const formatLastUpdate = (iso: string | null) => {
    if (!iso) return "—";
    const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
    if (diff < 60) return `${diff} мин назад`;
    if (diff < 1440) return `${Math.floor(diff / 60)} ч назад`;
    return `${Math.floor(diff / 1440)} д назад`;
  };

  const topGainer = [...allMovers].filter(m => m.price_change_pct && parseFloat(m.price_change_pct) > 0)
    .sort((a, b) => parseFloat(b.price_change_pct!) - parseFloat(a.price_change_pct!))[0];
  const topLoser = [...allMovers].filter(m => m.price_change_pct && parseFloat(m.price_change_pct) < 0)
    .sort((a, b) => parseFloat(a.price_change_pct!) - parseFloat(b.price_change_pct!))[0];

  return (
    <div className="flex flex-col gap-6">

      {/* Заголовок */}
      <div>
        <h1 className="text-2xl font-semibold text-white">Dashboard</h1>
        <p className="text-gray-400 text-sm mt-1">Цены на GPU, CPU, RAM — США и Европа</p>
      </div>

      {/* Метрики */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard
          label="Отслеживается"
          value={stats ? `${stats.tracked_products}` : "—"}
          sub="GPU · CPU · RAM"
          accent="blue"
        />
        <MetricCard
          label="Обновлено"
          value={stats ? formatLastUpdate(stats.last_collected_at) : "—"}
          sub={`${stats?.total_price_records ?? 0} записей`}
        />
        <MetricCard
          label="Макс. рост (7д)"
          value={topGainer ? `+${parseFloat(topGainer.price_change_pct!).toFixed(1)}%` : "—"}
          sub={topGainer?.product_name?.split(" ").slice(-2).join(" ")}
          accent="red"
        />
        <MetricCard
          label="Макс. падение (7д)"
          value={topLoser ? `${parseFloat(topLoser.price_change_pct!).toFixed(1)}%` : "—"}
          sub={topLoser?.product_name?.split(" ").slice(-2).join(" ")}
          accent="green"
        />
      </div>

      {/* Поиск */}
      <div className="relative">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onFocus={() => searchResults.length > 0 && setShowDropdown(true)}
          onBlur={() => setTimeout(() => setShowDropdown(false), 200)}
          placeholder="Найти продукт: RTX 4090, Ryzen 9, DDR5..."
          className="w-full bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors"
        />
        {showDropdown && searchResults.length > 0 && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-gray-900 border border-gray-700 rounded-xl overflow-hidden z-50 shadow-xl">
            {searchResults.map((product) => (
              <Link
                key={product.product_id}
                href={`/product/${product.product_id}`}
                className="flex items-center gap-3 px-4 py-3 hover:bg-gray-800 transition-colors"
              >
                <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                  product.category === "GPU" ? "bg-blue-900 text-blue-300"
                  : product.category === "CPU" ? "bg-green-900 text-green-300"
                  : "bg-purple-900 text-purple-300"
                }`}>
                  {product.category}
                </span>
                <span className="text-white text-sm">{product.name}</span>
                {product.msrp_usd && (
                  <span className="ml-auto text-gray-400 text-xs">MSRP ${product.msrp_usd}</span>
                )}
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Фильтры */}
      <div className="flex flex-wrap gap-2">
        {["GPU", "CPU", "RAM"].map((cat) => (
          <CategoryChip
            key={cat}
            label={cat}
            active={activeCategory === cat}
            onClick={() => setActiveCategory(activeCategory === cat ? null : cat)}
          />
        ))}
      </div>

      {/* Список продуктов */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-800">
          <h2 className="text-sm font-medium text-gray-300">
            Все продукты
            {activeCategory && <span className="text-gray-500 ml-2">· {activeCategory}</span>}
          </h2>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16 text-gray-500 text-sm">
            Загрузка...
          </div>
        ) : filteredMovers.length === 0 ? (
          <div className="flex items-center justify-center py-16 text-gray-600 text-sm">
            Нет данных
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left text-gray-500 font-normal px-5 py-3">Продукт</th>
                <th className="text-left text-gray-500 font-normal px-3 py-3">Категория</th>
                <th className="text-right text-gray-500 font-normal px-3 py-3">Цена</th>
                <th className="text-right text-gray-500 font-normal px-5 py-3">Изм. 7д</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {filteredMovers.map((mover, i) => (
                <tr
                  key={`${mover.product_id}-${i}`}
                  className="hover:bg-gray-800/50 transition-colors cursor-pointer"
                  onClick={() => window.location.href = `/product/${mover.product_id}`}
                >
                  <td className="px-5 py-3">
                    <span className="text-white font-medium">{mover.product_name}</span>
                  </td>
                  <td className="px-3 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                      mover.category === "GPU" ? "bg-blue-900 text-blue-300"
                      : mover.category === "CPU" ? "bg-green-900 text-green-300"
                      : "bg-purple-900 text-purple-300"
                    }`}>
                      {mover.category}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-right text-white">
                    {mover.current_price
                      ? `$${parseFloat(mover.current_price).toLocaleString("en-US", { minimumFractionDigits: 2 })}`
                      : "—"}
                  </td>
                  <td className="px-5 py-3 text-right">
                    <PriceChangeBadge pct={mover.price_change_pct} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
