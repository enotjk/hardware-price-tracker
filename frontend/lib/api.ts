/**
 * API клиент для запросов к FastAPI бэкенду
 * Все запросы идут через этот файл — легко менять базовый URL
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─────────────────────────────────────────
// Типы данных (соответствуют Pydantic схемам)
// ─────────────────────────────────────────

export interface Product {
  product_id: string;
  name: string;
  brand: string;
  category: string;
  model_number: string | null;
  msrp_usd: string | null;
  tdp_watts?: number | null;
  vram_gb?: number | null;
  cores?: number | null;
  release_date?: string | null;
}

export interface PriceHistory {
  date_id: string;
  price_usd: string;
  price_original: string;
  currency: string;
  source_name: string;
  display_name: string;
  region: string;
}

export interface CurrentPrice {
  product_id: string;
  source_name: string;
  display_name: string;
  region: string;
  price_usd: string;
  date_id: string;
  collected_at: string | null;
}

export interface TopMover {
  product_id: string;
  product_name: string;
  brand: string;
  category: string;
  current_price: string | null;
  previous_price: string | null;
  price_change_pct: string | null;
  price_change_abs: string | null;
}

export interface Pipeline {
  dag_id: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  records_fetched: number | null;
  records_inserted: number | null;
  error_message: string | null;
}

export interface Stats {
  total_price_records: number;
  total_raw_records: number;
  tracked_products: number;
  last_collected_at: string | null;
  successful_runs: number;
  failed_runs: number;
}

export interface CurrentPrice {
  product_id: string;
  source_name: string;
  display_name: string;
  region: string;
  price_usd: string;
  date_id: string;
  collected_at: string | null;
  product_url: string | null;
}

// ─────────────────────────────────────────
// Базовый fetch с обработкой ошибок
// ─────────────────────────────────────────

async function apiFetch<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_URL}${endpoint}`, {
    headers: { "Content-Type": "application/json" },
    next: { revalidate: 0 }, // отключаем кеш Next.js — используем свой в FastAPI
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

// ─────────────────────────────────────────
// API функции
// ─────────────────────────────────────────

// Products
export const getProducts = (category?: string, brand?: string) => {
  const params = new URLSearchParams();
  if (category) params.append("category", category);
  if (brand) params.append("brand", brand);
  const query = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<Product[]>(`/products${query}`);
};

export const searchProducts = (q: string) =>
  apiFetch<Product[]>(`/products/search?q=${encodeURIComponent(q)}`);

export const getProduct = (productId: string) =>
  apiFetch<Product>(`/products/${productId}`);

// Prices
export const getPriceHistory = (productId: string, days = 30) =>
  apiFetch<PriceHistory[]>(`/prices/history/${productId}?days=${days}`);

export const getCurrentPrices = (productId: string) =>
  apiFetch<CurrentPrice[]>(`/prices/current/${productId}`);

export const getTopMovers = (limit = 10) =>
  apiFetch<TopMover[]>(`/prices/top-movers?limit=${limit}`);

export const getPriceChanges = (category?: string) => {
  const query = category ? `?category=${category}` : "";
  return apiFetch<TopMover[]>(`/prices/changes${query}`);
};

// Pipelines
export const getPipelines = () =>
  apiFetch<Pipeline[]>(`/pipelines`);

export const getPipelineStats = () =>
  apiFetch<Stats>(`/pipelines/stats`);

export const getDagRuns = (dagId: string) =>
  apiFetch<Pipeline[]>(`/pipelines/${dagId}/runs`);
