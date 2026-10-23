import { useState } from "react";
import { fetchMeta } from "./api";
import { AccuracyView } from "./components/AccuracyView";
import { ForecastView } from "./components/ForecastView";
import { Status } from "./components/Status";
import { useAsync } from "./useAsync";

type Tab = "decision" | "accuracy";

export default function App() {
  const meta = useAsync((signal) => fetchMeta(signal), []);
  const [tab, setTab] = useState<Tab>("decision");
  const [cutoffHour, setCutoffHour] = useState<number | null>(null);

  return (
    <div className="shell">
      <header className="top">
        <div>
          <h1>WindWatch</h1>
          <p className="tagline">Day-ahead wind forecasts for the GB power desk. January 2026 pilot.</p>
        </div>
      </header>

      <Status state={meta}>
        {(m) => {
          const hour = cutoffHour ?? m.default_cutoff_hour;
          return (
            <>
              <div className="toolbar">
                <nav className="tabs" role="tablist" aria-label="Views">
                  <button role="tab" type="button" aria-selected={tab === "decision"} onClick={() => setTab("decision")}>
                    Decision view
                  </button>
                  <button role="tab" type="button" aria-selected={tab === "accuracy"} onClick={() => setTab("accuracy")}>
                    Forecast accuracy
                  </button>
                </nav>
                <label className="cutoff">
                  Buy decided at
                  <select value={hour} onChange={(e) => setCutoffHour(Number(e.target.value))} aria-label="Decision hour on the previous day">
                    {Array.from({ length: 24 }, (_, h) => (
                      <option key={h} value={h}>
                        {String(h).padStart(2, "0")}:00 UK, day before
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <main>{tab === "decision" ? <ForecastView meta={m} cutoffHour={hour} /> : <AccuracyView meta={m} cutoffHour={hour} />}</main>
            </>
          );
        }}
      </Status>

      <footer>Data: Elexon BMRS (FUELHH actual wind, WINDFOR wind forecast). All times are UK local time.</footer>
    </div>
  );
}
