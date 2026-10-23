import type { Accuracy, DayForecast, Meta } from "./types";

async function getJson<T>(path: string, params: Record<string, string | number> = {}, signal?: AbortSignal): Promise<T> {
  const qs = new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)])).toString();
  const res = await fetch(qs ? `${path}?${qs}` : path, { signal });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* body was not JSON, keep the status text */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const fetchMeta = (signal?: AbortSignal) => getJson<Meta>("/api/meta", {}, signal);

export const fetchForecast = (deliveryDay: string, cutoffHour: number, signal?: AbortSignal) =>
  getJson<DayForecast>("/api/forecast", { delivery_day: deliveryDay, cutoff_hour: cutoffHour }, signal);

export const fetchAccuracy = (firstDay: string, lastDay: string, cutoffHour: number, signal?: AbortSignal) =>
  getJson<Accuracy>("/api/accuracy", { first_day: firstDay, last_day: lastDay, cutoff_hour: cutoffHour }, signal);
