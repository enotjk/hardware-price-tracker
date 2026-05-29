"use client";

import { useState, useEffect, useCallback } from "react";
import PriceChart from "@/components/PriceChart";
import {
  getProducts,
  searchProducts,
  getPriceHistory,
  getCurrentPrices,
  getPipelineStats,
  getPriceChanges,
  Product,
  PriceHistory,
  CurrentPrice,
  Stats,
  TopMover,
} from "@/lib/api";

// ─────────────────────────────────────────
// Вспомогательные компоненты
// ─────────────────────────────────────────

function MetricCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: "green" | "red" | "blue";
}) {
  const accentClass =
    accent === "green"
      ? "text-emerald-400"
      : accent === "red"
      ? "text-red-400"
      : accent === "blue"
      ? "text-blue-400"
      : "text-white";

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">{label}</div>
      <div className={`text-2xl font-semibold ${accentClass}`}>{value}</div>
      {sub && <div className="text-xs text-gray-500 mt-1">{sub}</div>}
    </div>
  );
}

function CategoryChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
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

const FLAG: Record<string, string> = {
  US: "🇺🇸",
  DE: "🇩🇪",
  UK: "🇬🇧",
};

// ─────────────────────────────────────────
// Главная страница
// ─────────────────────────────────────────

export default function DashboardPage() {
  // ── State ──
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Product[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [activeBrand, setActiveBrand] = useState<string | null>(null);

  const [priceHistory, setPriceHistory] = useState<PriceHistory[]>([]);
  const [currentPrices, setCurrentPrices] = useState<CurrentPrice[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [topMovers, setTopMovers] = useState<TopMover[]>([]);
  const [historyDays, setHistoryDays] = useState(30);

  const [loadingHistory, setLoadingHistory] = useState(false);
  const [loadingPrices, setLoadingPrices] = useState(false);

  // ── Загрузка статистики и топ-муверов при старте ──
  useEffect(() => {
    getPipelineStats().then(setStats).catch(console.error);
    getPriceChanges().then(setTopMovers).catch(console.error);
  }, []);

  // ── Поиск с дебаунсом ──
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

  // ── Загрузка данных при выборе продукта ──
  const loadProductData = useCallback(
    async (product: Product, days: number) => {
      setLoadingHistory(true);
      setLoadingPrices(true);
      try {
        const [history, prices] = await Promise.all([
          getPriceHistory(product.product_id, days),
          getCurrentPrices(product.product_id),
        ]);
        setPriceHistory(history);
        setCurrentPrices(prices);
      } catch (e) {
        console.error(e);
      } finally {
        setLoadingHistory(false);
        setLoadingPrices(false);
      }
    },
    []
  );

  const handleSelectProduct = (product: Product) => {
    setSelectedProduct(product);
    setSearchQuery(product.name);
    setShowDropdown(false);
    loadProductData(product, historyDays);
  };

  const handlePeriodChange = (days: number) => {
    setHistoryDays(days);
    if (selectedProduct) loadProductData(selectedProduct, days);
  };

  // ── Форматирование времени ──
  const formatLastUpdate = (iso: string | null) => {
    if (!iso) return "—";
    const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
    if (diff < 60) return `${diff} мин назад`;
    if (diff < 1440) return `${Math.floor(diff / 60)} ч назад`;
    return `${Math.floor(diff / 1440)} д назад`;
  };

  // ── Best price ──
  const bestPrice = currentPrices.length
    ? Math.min(...currentPrices.map((p) => parseFloat(p.price_usd)))
    : null;

  // ── Топ рост/падение ──
  const topGainer = topMovers
    .filter((m) => m.price_change_pct && parseFloat(m.price_change_pct) > 0)
    .sort((a, b) => parseFloat(b.price_change_pct!) - parseFloat(a.price_change_pct!))[0];
  const topLoser = topMovers
    .filter((m) => m.price_change_pct && parseFloat(m.price_change_pct) < 0)
    .sort((a, b) => parseFloat(a.price_change_pct!) - parseFloat(b.price_change_pct!))[0];

  return (
    <div className="flex flex-col gap-6">

      {/* ── Заголовок ── */}
      <div>
        <h1 className="text-2xl font-semibold text-white">Dashboard</h1>
        <p className="text-gray-400 text-sm mt-1">Цены на GPU, CPU, RAM — США и Европа</p>
      </div>

      {/* ── Метрики ── */}
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
          value={
            topGainer
              ? `+${parseFloat(topGainer.price_change_pct!).toFixed(1)}%`
              : "—"
          }
          sub={topGainer?.product_name?.split(" ").slice(-2).join(" ")}
          accent="green"
        />
        <MetricCard
          label="Макс. падение (7д)"
          value={
            topLoser
              ? `${parseFloat(topLoser.price_change_pct!).toFixed(1)}%`
              : "—"
          }
          sub={topLoser?.product_name?.split(" ").slice(-2).join(" ")}
          accent="red"
        />
      </div>

      {/* ── Поиск + фильтры ── */}
      <div className="flex flex-col gap-3">

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

          {/* Dropdown */}
          {showDropdown && searchResults.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-gray-900 border border-gray-700 rounded-xl overflow-hidden z-50 shadow-xl">
              {searchResults.map((product) => (
                <button
                  key={product.product_id}
                  onMouseDown={() => handleSelectProduct(product)}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-800 transition-colors text-left"
                >
                  <span
                    className={`text-xs px-2 py-0.5 rounded font-medium ${
                      product.category === "GPU"
                        ? "bg-blue-900 text-blue-300"
                        : product.category === "CPU"
                        ? "bg-green-900 text-green-300"
                        : "bg-purple-900 text-purple-300"
                    }`}
                  >
                    {product.category}
                  </span>
                  <span className="text-white text-sm">{product.name}</span>
                  {product.msrp_usd && (
                    <span className="ml-auto text-gray-400 text-xs">
                      MSRP ${product.msrp_usd}
                    </span>
                  )}
                </button>
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
          <div className="w-px bg-gray-700 mx-1" />
          {["NVIDIA", "AMD", "Intel"].map((brand) => (
            <CategoryChip
              key={brand}
              label={brand}
              active={activeBrand === brand}
              onClick={() => setActiveBrand(activeBrand === brand ? null : brand)}
            />
          ))}
        </div>
      </div>

      {/* ── Основной контент ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* График — занимает 2/3 ширины */}
        <div className="lg:col-span-2 bg-gray-900 border border-gray-800 rounded-xl p-5">
          {selectedProduct ? (
            <>
              <div className="mb-4">
                <div className="text-lg font-medium text-white">{selectedProduct.name}</div>
                <div className="text-sm text-gray-400 mt-0.5">
                  {selectedProduct.category}
                  {selectedProduct.msrp_usd && ` · MSRP $${selectedProduct.msrp_usd}`}
                </div>
              </div>
              <PriceChart
                data={priceHistory}
                msrp={selectedProduct.msrp_usd ? parseFloat(selectedProduct.msrp_usd) : undefined}
                onPeriodChange={handlePeriodChange}
                isLoading={loadingHistory}
              />
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-64 gap-3">
              <div className="text-gray-500 text-4xl">📊</div>
              <div className="text-gray-400 text-sm">
                Найди продукт через поиск чтобы увидеть график цены
              </div>
            </div>
          )}
        </div>

        {/* Таблица текущих цен — 1/3 ширины */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="text-sm font-medium text-gray-300 mb-4">
            Текущие цены
          </div>

          {selectedProduct && currentPrices.length > 0 ? (
            <div className="flex flex-col gap-2">
              {currentPrices.map((price) => (
                <div
                  key={`${price.source_name}-${price.region}`}
                  className="flex items-center justify-between p-3 bg-gray-800 rounded-lg"
                >
                  <div>
                    <div className="flex items-center gap-1.5 text-sm text-gray-200">
                      <span>{FLAG[price.region] ?? "🌍"}</span>
                      <span>{price.display_name}</span>
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5">{price.date_id}</div>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <span className="text-white font-medium text-sm">
                      ${parseFloat(price.price_usd).toLocaleString("en-US", {
                        minimumFractionDigits: 2,
                      })}
                    </span>
                    {bestPrice !== null &&
                      parseFloat(price.price_usd) === bestPrice && (
                        <span className="text-xs bg-emerald-900 text-emerald-400 px-1.5 py-0.5 rounded">
                          best
                        </span>
                      )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-48 text-gray-600 text-sm">
              {selectedProduct ? "Загрузка..." : "Выбери продукт"}
            </div>
          )}
        </div>
      </div>

      {/* ── Движение цен ── */}
      {topMovers.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="text-sm font-medium text-gray-300 mb-4">
            Движение цен (7 дней)
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {topMovers.slice(0, 9).map((mover) => {
              const pct = mover.price_change_pct
                ? parseFloat(mover.price_change_pct)
                : null;
              const isUp = pct !== null && pct > 0;
              return (
                <button
                  key={mover.product_id}
                  onClick={() =>
                    handleSelectProduct({
                      product_id: mover.product_id,
                      name: mover.product_name,
                      brand: mover.brand,
                      category: mover.category,
                      model_number: null,
                      msrp_usd: null,
                    })
                  }
                  className="flex items-center justify-between p-3 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors text-left"
                >
                  <div>
                    <div className="text-sm text-white font-medium truncate max-w-[150px]">
                      {mover.product_name}
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5">{mover.category} · {mover.brand}</div>
                  </div>
                  {pct !== null ? (
                    <span
                      className={`text-sm font-semibold ${
                        isUp ? "text-red-400" : "text-emerald-400"
                      }`}
                    >
                      {isUp ? "+" : ""}
                      {pct.toFixed(1)}%
                    </span>
                  ) : (
                    <span className="text-gray-600 text-sm">—</span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
