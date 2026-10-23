const TZ = "Europe/London";

const nf0 = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });

export const fmtMW = (n: number | null | undefined): string => (n == null ? "n/a" : `${nf0.format(Math.round(n))} MW`);

export const fmtNum = (n: number | null | undefined): string => (n == null ? "n/a" : nf0.format(Math.round(n)));

/** Adds an explicit plus sign so bias direction is obvious at a glance. */
export const fmtSignedMW = (n: number | null | undefined): string => {
  if (n == null) return "n/a";
  const r = Math.round(n);
  return `${r > 0 ? "+" : r < 0 ? "-" : ""}${nf0.format(Math.abs(r))} MW`;
};

export const fmtPct = (n: number | null | undefined): string => (n == null ? "n/a" : `${n.toFixed(1)}%`);

export const fmtClock = (iso: string): string =>
  new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: TZ, hour12: false }).format(new Date(iso));

export const fmtDayClock = (iso: string): string =>
  new Intl.DateTimeFormat("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: TZ,
    hour12: false,
  }).format(new Date(iso));

export const fmtDay = (isoDate: string): string =>
  new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" }).format(
    new Date(`${isoDate}T00:00:00Z`),
  );

/** Plain-language reading of the bias figure. */
export const describeBias = (bias: number | undefined): string => {
  if (bias == null) return "";
  if (Math.abs(bias) < 50) return "No consistent over or under forecasting.";
  return bias > 0
    ? `Forecasts ran ${nf0.format(Math.round(bias))} MW above actual generation on average, so wind was over-counted.`
    : `Forecasts ran ${nf0.format(Math.round(-bias))} MW below actual generation on average, so wind was under-counted.`;
};

export const shiftDay = (isoDate: string, days: number): string => {
  const d = new Date(`${isoDate}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
};

const sideOf = (offset: number): string => {
  const mw = `${nf0.format(Math.round(Math.abs(offset)))} MW`;
  return offset < 0 ? `${mw} below` : `${mw} above`;
};

/** Words for a range of offsets from a forecast, e.g. "4,306 MW below to 426 MW above the forecast". */
export const describeRange = (low: number, high: number): string => `between ${sideOf(low)} and ${sideOf(high)} the forecast`;
