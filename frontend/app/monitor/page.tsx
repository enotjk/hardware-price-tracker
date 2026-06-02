"use client";

import { useState, useEffect } from "react";
import { getPipelines, getPipelineStats, getDagRuns, Pipeline, Stats } from "@/lib/api";

// ─────────────────────────────────────────
// Компоненты
// ─────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { label: string; className: string }> = {
    success: { label: "✅ success", className: "bg-emerald-900 text-emerald-400" },
    failed:  { label: "❌ failed",  className: "bg-red-900 text-red-400" },
    running: { label: "⏳ running", className: "bg-blue-900 text-blue-400" },
  };
  const c = config[status] ?? { label: status, className: "bg-gray-800 text-gray-400" };
  return (
    <span className={`text-xs px-2 py-0.5 rounded font-medium ${c.className}`}>
      {c.label}
    </span>
  );
}

function StatCard({ label, value, sub, accent }: {
  label: string; value: string | number; sub?: string; accent?: string;
}) {
  const color = accent === "green" ? "text-emerald-400"
    : accent === "red"    ? "text-red-400"
    : accent === "blue"   ? "text-blue-400"
    : accent === "amber"  ? "text-amber-400"
    : "text-white";
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">{label}</div>
      <div className={`text-2xl font-semibold ${color}`}>{value}</div>
      {sub && <div className="text-xs text-gray-500 mt-1">{sub}</div>}
    </div>
  );
}

// Прогресс-бар расхода RapidAPI лимита
function ApiLimitBar({ used, limit = 100 }: { used: number; limit?: number }) {
  const pct = Math.min(Math.round((used / limit) * 100), 100);
  const color = pct >= 80 ? "bg-red-500" : pct >= 50 ? "bg-amber-500" : "bg-emerald-500";
  return (
    <div className="mt-2">
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>RapidAPI лимит (месяц)</span>
        <span className={pct >= 80 ? "text-red-400" : pct >= 50 ? "text-amber-400" : "text-emerald-400"}>
          {used} / {limit}
        </span>
      </div>
      <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function formatTime(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("ru-RU", {
    day: "2-digit", month: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

function formatDuration(start: string | null, end: string | null) {
  if (!start || !end) return "—";
  const sec = Math.floor((new Date(end).getTime() - new Date(start).getTime()) / 1000);
  if (sec < 60) return `${sec}с`;
  return `${Math.floor(sec / 60)}м ${sec % 60}с`;
}

function formatLastUpdate(iso: string | null) {
  if (!iso) return "—";
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (diff < 60) return `${diff} мин назад`;
  if (diff < 1440) return `${Math.floor(diff / 60)} ч назад`;
  return `${Math.floor(diff / 1440)} д назад`;
}

// ─────────────────────────────────────────
// Карточка DAG (расширенная для Amazon)
// ─────────────────────────────────────────
function PipelineCard({
  p,
  selected,
  onClick,
}: {
  p: Pipeline;
  selected: boolean;
  onClick: () => void;
}) {
  const isAmazon = p.dag_id === "dag_amazon";

  return (
    <button
      onClick={onClick}
      className={`text-left p-4 bg-gray-900 border rounded-xl transition-all w-full ${
        selected ? "border-blue-500" : "border-gray-800 hover:border-gray-600"
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-white font-medium text-sm">{p.dag_id}</span>
          {isAmazon && (
            <span className="text-xs px-1.5 py-0.5 rounded bg-amber-900/60 text-amber-400 font-medium">
              RapidAPI
            </span>
          )}
        </div>
        <StatusBadge status={p.status} />
      </div>

      <div className="flex flex-col gap-1 text-xs text-gray-500">
        <div className="flex justify-between">
          <span>Последний запуск</span>
          <span className="text-gray-400">{formatTime(p.started_at)}</span>
        </div>
        <div className="flex justify-between">
          <span>Длительность</span>
          <span className="text-gray-400">{formatDuration(p.started_at, p.finished_at)}</span>
        </div>
        <div className="flex justify-between">
          <span>Записей вставлено</span>
          <span className="text-emerald-400 font-medium">{p.records_inserted ?? 0}</span>
        </div>
        {/* Запросы API — только для Amazon */}
        {isAmazon && p.api_requests_used != null && (
          <div className="flex justify-between">
            <span>Запросов API</span>
            <span className="text-amber-400 font-medium">{p.api_requests_used}</span>
          </div>
        )}
        {p.error_message && (
          <div className="mt-1 text-red-400 truncate">{p.error_message}</div>
        )}
      </div>

      {/* Прогресс-бар лимита — только у Amazon */}
      {isAmazon && typeof (p as any).monthly_requests !== "undefined" && (
        <ApiLimitBar used={(p as any).monthly_requests} />
      )}
    </button>
  );
}

// ─────────────────────────────────────────
// Главный компонент
// ─────────────────────────────────────────
export default function MonitorPage() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [selectedDag, setSelectedDag] = useState<string | null>(null);
  const [dagRuns, setDagRuns] = useState<Pipeline[]>([]);
  const [lastRefresh, setLastRefresh] = useState(new Date());

  const loadData = async () => {
    try {
      const [p, s] = await Promise.all([getPipelines(), getPipelineStats()]);
      setPipelines(p);
      setStats(s);
      setLastRefresh(new Date());
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => { loadData(); }, []);
  useEffect(() => {
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);
  useEffect(() => {
    if (!selectedDag) return;
    getDagRuns(selectedDag).then(setDagRuns).catch(console.error);
  }, [selectedDag]);

  const amazonRequests = (stats as any)?.amazon_requests_this_month ?? 0;

  return (
    <div className="flex flex-col gap-6">

      {/* Заголовок */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">ETL Monitor</h1>
          <p className="text-gray-400 text-sm mt-1">Статус пайплайнов сбора данных</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-600">
            Обновлено: {lastRefresh.toLocaleTimeString("ru-RU")}
          </span>
          <button
            onClick={loadData}
            className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-sm text-gray-300 transition-colors"
          >
            ↻ Обновить
          </button>
        </div>
      </div>

      {/* Статистика */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-7 gap-3">
        <StatCard label="Записей в БД"      value={stats?.total_price_records ?? "—"} accent="blue" />
        <StatCard label="Сырых записей"      value={stats?.total_raw_records ?? "—"} />
        <StatCard label="Продуктов"          value={stats?.tracked_products ?? "—"} sub="отслеживается" />
        <StatCard label="Последнее обновление" value={formatLastUpdate(stats?.last_collected_at ?? null)} />
        <StatCard label="Успешных запусков"  value={stats?.successful_runs ?? "—"} accent="green" />
        <StatCard label="Ошибок"             value={stats?.failed_runs ?? "—"} accent={stats?.failed_runs ? "red" : undefined} />
        {/* Новая карточка — лимит RapidAPI */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 col-span-2 md:col-span-1">
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Amazon API</div>
          <div className="text-2xl font-semibold text-amber-400">{amazonRequests}</div>
          <div className="text-xs text-gray-500 mt-1">запросов в месяц</div>
          <ApiLimitBar used={amazonRequests} limit={100} />
        </div>
      </div>

      {/* Карточки DAGов */}
      <div>
        <div className="text-sm font-medium text-gray-400 mb-3 uppercase tracking-wide">
          Пайплайны
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {pipelines.length === 0 ? (
            <div className="col-span-3 text-center text-gray-600 py-8 text-sm">
              Нет данных о запусках
            </div>
          ) : (
            pipelines.map((p) => (
              <PipelineCard
                key={p.dag_id}
                p={p}
                selected={selectedDag === p.dag_id}
                onClick={() => setSelectedDag(selectedDag === p.dag_id ? null : p.dag_id)}
              />
            ))
          )}
        </div>
      </div>

      {/* История запусков */}
      {selectedDag && dagRuns.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="text-sm font-medium text-gray-300 mb-4">
            История запусков — <span className="text-blue-400">{selectedDag}</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left text-gray-500 font-normal pb-3">Статус</th>
                  <th className="text-left text-gray-500 font-normal pb-3">Запуск</th>
                  <th className="text-left text-gray-500 font-normal pb-3">Длительность</th>
                  <th className="text-right text-gray-500 font-normal pb-3">Получено</th>
                  <th className="text-right text-gray-500 font-normal pb-3">Вставлено</th>
                  {selectedDag === "dag_amazon" && (
                    <th className="text-right text-gray-500 font-normal pb-3">API запросов</th>
                  )}
                  <th className="text-left text-gray-500 font-normal pb-3">Ошибка</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {dagRuns.map((run, i) => (
                  <tr key={i} className="hover:bg-gray-800/40 transition-colors">
                    <td className="py-3"><StatusBadge status={run.status} /></td>
                    <td className="py-3 text-gray-400">{formatTime(run.started_at)}</td>
                    <td className="py-3 text-gray-400">{formatDuration(run.started_at, run.finished_at)}</td>
                    <td className="py-3 text-right text-gray-300">{run.records_fetched ?? 0}</td>
                    <td className="py-3 text-right text-emerald-400 font-medium">{run.records_inserted ?? 0}</td>
                    {selectedDag === "dag_amazon" && (
                      <td className="py-3 text-right text-amber-400 font-medium">
                        {(run as any).api_requests_used ?? "—"}
                      </td>
                    )}
                    <td className="py-3 text-red-400 text-xs max-w-[200px] truncate">
                      {run.error_message ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Индикатор актуальности */}
      <div className="flex items-center gap-2 text-xs text-gray-600">
        {stats?.last_collected_at &&
        Date.now() - new Date(stats.last_collected_at).getTime() < 12 * 60 * 60 * 1000 ? (
          <>
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-emerald-600">Данные актуальны</span>
          </>
        ) : (
          <>
            <span className="w-2 h-2 rounded-full bg-yellow-500" />
            <span className="text-yellow-600">Данные устарели — последнее обновление более 12 часов назад</span>
          </>
        )}
        <span className="ml-auto">Автообновление каждые 30 сек</span>
      </div>
    </div>
  );
}