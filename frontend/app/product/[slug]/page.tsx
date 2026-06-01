"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import PriceChart from "@/components/PriceChart";
import {
  getProduct,
  getPriceHistory,
  getCurrentPrices,
  Product,
  PriceHistory,
  CurrentPrice,
} from "@/lib/api";

const FLAG: Record<string, string> = { US: "🇺🇸", DE: "🇩🇪", UK: "🇬🇧" };

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-gray-800 rounded-xl p-4 flex flex-col gap-1">
      <div className="text-xs text-gray-500 uppercase tracking-wide">{label}</div>
      <div className="text-xl font-semibold text-white">{value}</div>
      {sub && <div className="text-xs text-gray-500">{sub}</div>}
    </div>
  );
}

function Breadcrumbs({ product }: { product: Product }) {
  return (
    <nav className="flex items-center gap-2 text-sm text-gray-500">
      <Link href="/" className="hover:text-gray-300 transition-colors">
        Dashboard
      </Link>
      <span>›</span>
      <Link
        href={`/?category=${product.category}`}
        className="hover:text-gray-300 transition-colors"
      >
        {product.category}
      </Link>
      <span>›</span>
      <span className="text-gray-300">{product.model_number ?? product.name}</span>
    </nav>
  );
}

function calcStats(history: PriceHistory[], msrp: number | null) {
  if (!history.length) return null;
  const prices = history.map((h) => parseFloat(h.price_usd));
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const avg = prices.reduce((a, b) => a + b, 0) / prices.length;
  const current = prices[prices.length - 1];
  const vsMsrp = msrp ? ((current - msrp) / msrp) * 100 : null;
  return { min, max, avg, current, vsMsrp };
}

export default function ProductPage() {
  const params = useParams();
  const router = useRouter();
  const productId = params.slug as string;

  const [product, setProduct] = useState<Product | null>(null);
  const [history, setHistory] = useState<PriceHistory[]>([]);
  const [currentPrices, setCurrentPrices] = useState<CurrentPrice[]>([]);
  const [days, setDays] = useState(90);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    getProduct(productId)
      .then(setProduct)
      .catch(() => setError(true));
  }, [productId]);

  useEffect(() => {
    if (!product) return;
    setLoading(true);
    Promise.all([
      getPriceHistory(productId, days),
      getCurrentPrices(productId),
    ])
      .then(([hist, prices]) => {
        setHistory(hist);
        setCurrentPrices(prices);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [product, productId, days]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <div className="text-gray-500 text-5xl">404</div>
        <div className="text-gray-400">Продукт не найден</div>
        <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm">
          ← Вернуться на Dashboard
        </Link>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="text-gray-500 text-sm">Загрузка...</div>
      </div>
    );
  }

  const msrp = product.msrp_usd ? parseFloat(product.msrp_usd) : null;
  const stats = calcStats(history, msrp);
  const bestPrice = currentPrices.length
    ? Math.min(...currentPrices.map((p) => parseFloat(p.price_usd)))
    : null;

  return (
    <div className="flex flex-col gap-6">

      {/* Хлебные крошки */}
      <Breadcrumbs product={product} />

      {/* Заголовок продукта */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                product.category === "GPU"
                  ? "bg-blue-900 text-blue-300"
                  : product.category === "CPU"
                  ? "bg-green-900 text-green-300"
                  : "bg-purple-900 text-purple-300"
              }`}>
                {product.category}
              </span>
              <span className="text-gray-400 text-sm">{product.brand}</span>
              {product.release_date && (
                <span className="text-gray-600 text-xs">
                  · {new Date(product.release_date).getFullYear()}
                </span>
              )}
            </div>
            <h1 className="text-2xl font-semibold text-white">{product.name}</h1>
            <div className="flex flex-wrap gap-3 mt-3">
              {product.msrp_usd && (
                <div className="text-sm text-gray-400">
                  MSRP <span className="text-white font-medium">${product.msrp_usd}</span>
                </div>
              )}
              {product.vram_gb && (
                <div className="text-sm text-gray-400">
                  VRAM <span className="text-white font-medium">{product.vram_gb}GB</span>
                </div>
              )}
              {product.tdp_watts && (
                <div className="text-sm text-gray-400">
                  TDP <span className="text-white font-medium">{product.tdp_watts}W</span>
                </div>
              )}
              {product.cores && (
                <div className="text-sm text-gray-400">
                  Cores <span className="text-white font-medium">{product.cores}</span>
                </div>
              )}
            </div>
          </div>

          {bestPrice && (
            <div className="text-right">
              <div className="text-xs text-gray-500 mb-1">Лучшая цена сейчас</div>
              <div className="text-3xl font-bold text-emerald-400">
                ${bestPrice.toLocaleString("en-US", { minimumFractionDigits: 2 })}
              </div>
              {msrp && (
                <div className={`text-xs mt-1 ${bestPrice > msrp ? "text-red-400" : "text-emerald-400"}`}>
                  {bestPrice > msrp ? "+" : ""}
                  {(((bestPrice - msrp) / msrp) * 100).toFixed(1)}% от MSRP
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* График цены */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-sm font-medium text-gray-300 mb-4">История цены</h2>
        <PriceChart
          data={history}
          msrp={msrp ?? undefined}
          onPeriodChange={setDays}
          isLoading={loading}
        />
      </div>

      {/* Статистика */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard
            label="Минимум"
            value={`$${stats.min.toLocaleString("en-US", { minimumFractionDigits: 2 })}`}
            sub={`за ${days} дней`}
          />
          <StatCard
            label="Максимум"
            value={`$${stats.max.toLocaleString("en-US", { minimumFractionDigits: 2 })}`}
            sub={`за ${days} дней`}
          />
          <StatCard
            label="Среднее"
            value={`$${stats.avg.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
            sub={`за ${days} дней`}
          />
          {stats.vsMsrp !== null && (
            <StatCard
              label="Отклонение от MSRP"
              value={`${stats.vsMsrp > 0 ? "+" : ""}${stats.vsMsrp.toFixed(1)}%`}
              sub="текущая цена vs MSRP"
            />
          )}
        </div>
      )}

      {/* Таблица магазинов */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-sm font-medium text-gray-300 mb-4">Сравнение цен по магазинам</h2>

        {currentPrices.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left text-gray-500 font-normal pb-3">Магазин</th>
                  <th className="text-left text-gray-500 font-normal pb-3">Регион</th>
                  <th className="text-right text-gray-500 font-normal pb-3">Цена</th>
                  <th className="text-right text-gray-500 font-normal pb-3">vs MSRP</th>
                  <th className="text-right text-gray-500 font-normal pb-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {currentPrices
                  .sort((a, b) => parseFloat(a.price_usd) - parseFloat(b.price_usd))
                  .map((price) => {
                    const p = parseFloat(price.price_usd);
                    const isBest = bestPrice !== null && p === bestPrice;
                    const diffPct = msrp ? ((p - msrp) / msrp) * 100 : null;

                    return (
                      <tr key={`${price.source_name}-${price.region}`} className="hover:bg-gray-800/50 transition-colors">
                        <td className="py-3">
                          <div className="flex items-center gap-2">
                            <span className="text-white">{price.display_name}</span>
                            {isBest && (
                              <span className="text-xs bg-emerald-900 text-emerald-400 px-1.5 py-0.5 rounded">
                                best
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-3 text-gray-400">
                          {FLAG[price.region] ?? "🌍"} {price.region}
                        </td>
                        <td className="py-3 text-right font-medium text-white">
                          ${p.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                        </td>
                        <td className={`py-3 text-right text-xs ${
                          diffPct === null ? "text-gray-600"
                          : diffPct > 0 ? "text-red-400" : "text-emerald-400"
                        }`}>
                          {diffPct !== null
                            ? `${diffPct > 0 ? "+" : ""}${diffPct.toFixed(1)}%`
                            : "—"}
                        </td>
                        <td className="py-3 text-right">
                          {price.product_url ? (
                            <a
                              href={price.product_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
                            >
                              Открыть →
                            </a>
                          ) : (
                            <span className="text-xs text-gray-600 italic">нет ссылки</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center text-gray-600 py-8 text-sm">
            Данные о ценах пока не собраны
          </div>
        )}
      </div>

      {/* Назад */}
      <div>
        <button
          onClick={() => router.back()}
          className="text-sm text-gray-500 hover:text-gray-300 transition-colors"
        >
          ← Назад
        </button>
      </div>

    </div>
  );
}
