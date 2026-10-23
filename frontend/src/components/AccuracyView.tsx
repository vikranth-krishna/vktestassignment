import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fetchAccuracy } from "../api";
import { describeBias, describeRange, fmtDay, fmtMW, fmtNum, fmtPct, fmtSignedMW } from "../format";
import type { Accuracy, Meta } from "../types";
import { useAsync } from "../useAsync";
import { Kpi } from "./Kpi";
import { Status } from "./Status";

interface Props {
  meta: Meta;
  cutoffHour: number;
}

export function AccuracyView({ meta, cutoffHour }: Props) {
  const state = useAsync(
    (signal) => fetchAccuracy(meta.first_delivery_day, meta.last_delivery_day, cutoffHour, signal),
    [meta.first_delivery_day, meta.last_delivery_day, cutoffHour],
  );

  return (
    <section aria-labelledby="accuracy-heading">
      <div className="section-head">
        <div>
          <h2 id="accuracy-heading">How good were the forecasts?</h2>
          <p className="lede">
            Every delivery hour in January 2026, scored against metered wind output. Error is forecast minus actual, so a
            positive number means the forecast was too optimistic.
          </p>
        </div>
      </div>
      <Status state={state}>{(data) => <AccuracyDetail data={data} />}</Status>
    </section>
  );
}

function AccuracyDetail({ data }: { data: Accuracy }) {
  const o = data.overall;
  if (!o.n) return <div className="status">No scored hours in this range.</div>;

  const dayData = data.by_day.map((d) => ({ day: String(Number(d.date.slice(8))), label: fmtDay(d.date), mae: d.mae_mw }));
  const horizonData = data.by_horizon.map((h) => ({ lead: `${h.from_h}-${h.to_h} h`, mae: h.mae_mw, bias: h.bias_mw, n: h.n }));
  const hourData = data.by_hour.map((h) => ({ hour: `${String(h.hour).padStart(2, "0")}:00`, mae: h.mae_mw }));
  const histData = data.histogram.map((b) => ({ bucket: `${(b.from_mw / 1000).toFixed(0)} to ${(b.to_mw / 1000).toFixed(0)} GW`, count: b.count }));
  const mwTick = (v: number) => `${v / 1000} GW`;

  return (
    <>
      <div className="kpi-grid">
        <Kpi label="Mean absolute error" value={fmtMW(o.mae_mw)} hint={`${fmtPct(o.mape_pct)} of actual output, on ${o.n} hours`} />
        <Kpi label="Root mean square error" value={fmtMW(o.rmse_mw)} hint="Penalises large misses more" />
        <Kpi label="Bias (forecast minus actual)" value={fmtSignedMW(o.bias_mw)} tone={Math.abs(o.bias_mw ?? 0) > 500 ? "warn" : "default"} hint="Persistent direction of the error" />
        <Kpi label="Bad day error (90th percentile)" value={fmtMW(o.p90_abs_error_mw)} hint="9 in 10 hours missed by less than this" />
      </div>

      <div className="callout">
        <strong>Reading for the buying team.</strong> {describeBias(o.bias_mw)} Removing that average bias alone would take
        the typical miss from {fmtMW(o.mae_mw)} to about {fmtMW(o.mae_bias_removed_mw)} (measured on the same January data, so
        treat it as an upper bound on the gain). In 80% of hours the actual output was {describeRange(-(o.error_p90_mw ?? 0), -(o.error_p10_mw ?? 0))}.
      </div>

      <div className="grid-2">
        <ChartCard title="Error by day" note="Mean absolute error for each January delivery day (day of month along the bottom). Hover a bar for the date.">
          <BarChart data={dayData} margin={{ top: 8, right: 8, bottom: 4, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" />
            <XAxis dataKey="day" tick={{ fontSize: 11 }} interval={1} />
            <YAxis tickFormatter={mwTick} tick={{ fontSize: 12 }} width={64} />
            <Tooltip
              formatter={(v: unknown) => fmtMW(Number(v))}
              labelFormatter={(_: unknown, items: { payload?: { label?: string } }[]) => items[0]?.payload?.label ?? ""}
            />
            <Bar dataKey="mae" name="Mean absolute error" fill="var(--accent)" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ChartCard>

        <ChartCard title="Error by lead time" note="How the error grows the further ahead the forecast was published. A day-ahead decision at 09:00 works with forecasts roughly 15 to 40 hours old.">
          <LineChart data={horizonData} margin={{ top: 8, right: 8, bottom: 4, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" />
            <XAxis dataKey="lead" tick={{ fontSize: 11 }} />
            <YAxis tickFormatter={mwTick} tick={{ fontSize: 12 }} width={64} />
            <Tooltip formatter={(v: unknown) => fmtMW(Number(v))} />
            <Legend />
            <Line dataKey="mae" name="Mean absolute error" stroke="var(--accent)" strokeWidth={2.5} dot />
            <Line dataKey="bias" name="Bias" stroke="var(--warm)" strokeWidth={2} strokeDasharray="5 4" dot />
          </LineChart>
        </ChartCard>

        <ChartCard title="Error by hour of day" note="Mean absolute error for each UK clock hour, across the month.">
          <BarChart data={hourData} margin={{ top: 8, right: 8, bottom: 4, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" />
            <XAxis dataKey="hour" tick={{ fontSize: 11 }} interval={2} />
            <YAxis tickFormatter={mwTick} tick={{ fontSize: 12 }} width={64} />
            <Tooltip formatter={(v: unknown) => fmtMW(Number(v))} />
            <Bar dataKey="mae" name="Mean absolute error" fill="var(--accent-2)" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ChartCard>

        <ChartCard title="Spread of errors" note="Number of hours at each error size. Bars right of zero are hours where the forecast was too high.">
          <BarChart data={histData} margin={{ top: 8, right: 8, bottom: 4, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" />
            <XAxis dataKey="bucket" tick={{ fontSize: 10 }} interval={1} />
            <YAxis tick={{ fontSize: 12 }} width={40} />
            <Tooltip formatter={(v: unknown) => `${fmtNum(Number(v))} hours`} />
            <Bar dataKey="count" name="Hours" fill="var(--warm)" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ChartCard>
      </div>

      <details className="card glossary">
        <summary>How these numbers are worked out</summary>
        <ul>
          <li>Forecasts come from the WINDFOR dataset and actuals from FUELHH (wind only), both from Elexon.</li>
          <li>The forecast for each hour is the latest run published at or before the decision time on the previous day.</li>
          <li>WINDFOR is hourly and FUELHH is half-hourly, so only the on-the-hour actuals are scored.</li>
          <li>Mean absolute error is the average size of the miss. Root mean square error weights large misses more. Bias is the average signed miss.</li>
        </ul>
      </details>
    </>
  );
}

function ChartCard({ title, note, children }: { title: string; note: string; children: React.ReactElement }) {
  return (
    <div className="card">
      <h3>{title}</h3>
      <div className="chart">
        <ResponsiveContainer width="100%" height={260}>
          {children}
        </ResponsiveContainer>
      </div>
      <p className="note">{note}</p>
    </div>
  );
}
