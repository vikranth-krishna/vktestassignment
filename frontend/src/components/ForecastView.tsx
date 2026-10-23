import { useMemo, useState } from "react";
import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fetchForecast } from "../api";
import { fmtClock, fmtDay, fmtDayClock, fmtMW, fmtNum, fmtSignedMW, shiftDay } from "../format";
import type { DayForecast, Meta } from "../types";
import { useAsync } from "../useAsync";
import { Kpi } from "./Kpi";
import { Status } from "./Status";

interface Props {
  meta: Meta;
  cutoffHour: number;
}

export function ForecastView({ meta, cutoffHour }: Props) {
  const [day, setDay] = useState("2026-01-15");
  const [reveal, setReveal] = useState(false);
  const state = useAsync((signal) => fetchForecast(day, cutoffHour, signal), [day, cutoffHour]);

  const canPrev = day > meta.first_delivery_day;
  const canNext = day < meta.last_delivery_day;

  return (
    <section aria-labelledby="decision-heading">
      <div className="section-head">
        <div>
          <h2 id="decision-heading">What the desk knew when it had to buy</h2>
          <p className="lede">
            For the chosen delivery day, each hour shows the newest wind forecast that existed at the decision time. Later
            forecast runs are ignored, because they were not available when the buy was placed.
          </p>
        </div>
        <div className="day-picker" role="group" aria-label="Delivery day">
          <button type="button" onClick={() => setDay(shiftDay(day, -1))} disabled={!canPrev} aria-label="Previous day">
            Prev
          </button>
          <input
            type="date"
            value={day}
            min={meta.first_delivery_day}
            max={meta.last_delivery_day}
            onChange={(e) => e.target.value && setDay(e.target.value)}
            aria-label="Delivery day"
          />
          <button type="button" onClick={() => setDay(shiftDay(day, 1))} disabled={!canNext} aria-label="Next day">
            Next
          </button>
        </div>
      </div>

      <Status state={state}>{(data) => <DayDetail data={data} reveal={reveal} onReveal={setReveal} />}</Status>
    </section>
  );
}

function DayDetail({ data, reveal, onReveal }: { data: DayForecast; reveal: boolean; onReveal: (v: boolean) => void }) {
  const s = data.summary;
  const chartData = useMemo(
    () =>
      data.points.map((p) => ({
        hour: fmtClock(p.target),
        forecast: p.forecast_mw,
        band: p.low_mw != null && p.high_mw != null ? [p.low_mw, p.high_mw] : undefined,
        actual: reveal ? p.actual_mw : undefined,
      })),
    [data, reveal],
  );

  if (data.points.length === 0) {
    return <div className="status">No forecast was available at the decision time for this day.</div>;
  }

  return (
    <>
      <div className="decision-bar">
        <div>
          <span className="eyebrow">Decision time</span>
          <strong>{fmtDayClock(data.cutoff)}</strong>
        </div>
        <div>
          <span className="eyebrow">Forecast runs in use</span>
          <strong>{data.forecast_runs_used.map(fmtClock).join(", ")}</strong>
        </div>
        <div>
          <span className="eyebrow">Delivery day</span>
          <strong>{fmtDay(data.delivery_day)}</strong>
        </div>
      </div>

      <div className="kpi-grid">
        <Kpi label="Average wind forecast" value={fmtMW(s.mean_forecast_mw)} />
        <Kpi label="Peak hour" value={fmtMW(s.max_forecast_mw)} />
        <Kpi label="Lowest hour" value={fmtMW(s.min_forecast_mw)} hint="Hardest hour to cover from wind" />
        <Kpi label="Energy for the day" value={`${fmtNum(s.total_forecast_mwh)} MWh`} />
      </div>

      <div className="card">
        <div className="card-head">
          <h3>Hourly wind forecast</h3>
          <label className="switch">
            <input type="checkbox" checked={reveal} onChange={(e) => onReveal(e.target.checked)} />
            Reveal what actually happened
          </label>
        </div>
        <div className="chart" role="img" aria-label="Hourly wind forecast with planning range">
          <ResponsiveContainer width="100%" height={340}>
            <ComposedChart data={chartData} margin={{ top: 8, right: 16, bottom: 4, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" />
              <XAxis dataKey="hour" interval={1} tick={{ fontSize: 12 }} />
              <YAxis tickFormatter={(v: number) => `${v / 1000} GW`} tick={{ fontSize: 12 }} width={64} />
              <Tooltip formatter={(v: unknown) => (Array.isArray(v) ? `${fmtNum(v[0])} to ${fmtNum(v[1])} MW` : fmtMW(Number(v)))} />
              <Legend />
              {data.band && (
                <Area dataKey="band" name="Likely range of actual output" stroke="none" fill="var(--band)" fillOpacity={0.9} />
              )}
              <Line dataKey="forecast" name="Forecast at decision time" stroke="var(--accent)" strokeWidth={2.5} dot={false} />
              {reveal && (
                <Line dataKey="actual" name="Actual generation" stroke="var(--ink)" strokeWidth={2} strokeDasharray="5 4" dot={false} />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <p className="note">
          {data.band
            ? `The shaded range holds the middle 80% of forecast errors from the ${data.band.samples} earlier delivery hours, applied to this forecast. It only uses days before ${fmtDay(data.delivery_day)}.`
            : "No range is shown for this day yet, because there are not enough earlier days to measure the forecast error from."}
        </p>
      </div>

      <details className="card">
        <summary>Hour by hour table</summary>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Hour</th>
                <th>Forecast</th>
                <th>Likely range</th>
                <th>Run published</th>
                <th>Lead time</th>
                {reveal && <th>Actual</th>}
                {reveal && <th>Error</th>}
              </tr>
            </thead>
            <tbody>
              {data.points.map((p) => (
                <tr key={p.target}>
                  <td>{fmtClock(p.target)}</td>
                  <td>{fmtMW(p.forecast_mw)}</td>
                  <td>{p.low_mw != null && p.high_mw != null ? `${fmtNum(p.low_mw)} to ${fmtNum(p.high_mw)}` : "n/a"}</td>
                  <td>{fmtDayClock(p.published)}</td>
                  <td>{p.horizon_h.toFixed(1)} h</td>
                  {reveal && <td>{fmtMW(p.actual_mw)}</td>}
                  {reveal && <td>{fmtSignedMW(p.error_mw)}</td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </>
  );
}
