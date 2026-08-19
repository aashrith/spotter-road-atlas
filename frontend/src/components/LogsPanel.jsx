/** Driver's Daily Logs card: day tabs, the duty grid, remarks, print. */
import { useState } from "react";
import LogSheet, { fmtHours } from "./LogSheet.jsx";
import { PrintIcon } from "./icons.jsx";

function tabDate(date) {
  return new Date(`${date}T00:00:00`).toLocaleDateString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function clock(hour) {
  const h = Math.floor(hour + 1e-9);
  const m = Math.round((hour - h) * 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

function remarksFor(sheet) {
  return sheet.segments.filter(
    (seg) =>
      seg.note &&
      seg.note !== "Off duty" &&
      (seg.status === "on_duty" ||
        seg.status === "sleeper_berth" ||
        seg.note.includes("rest") ||
        seg.note.includes("restart"))
  );
}

export default function LogsPanel({ sheets, trip }) {
  const [active, setActive] = useState(0);
  const sheet = sheets[active];

  return (
    <section className="panel logs-card">
      <div className="logs-header no-print">
        <h2 className="card-title">Driver&rsquo;s Daily Logs</h2>
        <button className="ghost-button" onClick={() => window.print()}>
          <PrintIcon /> Print log sheets
        </button>
      </div>

      <div className="log-tabs no-print" role="tablist">
        {sheets.map((s, i) => (
          <button
            key={s.date}
            role="tab"
            aria-selected={i === active}
            className={i === active ? "log-tab log-tab-active" : "log-tab"}
            onClick={() => setActive(i)}
          >
            <strong>Day {i + 1}</strong>
            <span>{tabDate(s.date)}</span>
          </button>
        ))}
      </div>

      {/* On screen only the active day; in print, every day. */}
      {sheets.map((s, i) => (
        <article
          key={s.date}
          className={`log-day ${i === active ? "" : "log-day-hidden"}`}
        >
          <div className="log-day-meta">
            <span className="log-day-count">
              Day {i + 1} of {sheets.length}
            </span>
            <span className="log-day-extra">
              {tabDate(s.date)} · {Math.round(s.miles_driven)} mi driven ·{" "}
              {trip.pickup.query} → {trip.dropoff.query}
            </span>
          </div>

          <LogSheet sheet={s} />

          <div className="remarks">
            <h3>Remarks</h3>
            {remarksFor(s).length === 0 ? (
              <p className="muted">No duty changes this day.</p>
            ) : (
              <ul>
                {remarksFor(s).map((seg, j) => (
                  <li key={j}>
                    <span className="remark-time">{clock(seg.start_hour)}</span>
                    {seg.note}
                    <span className="remark-duration">
                      {fmtHours(seg.end_hour - seg.start_hour)} h
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </article>
      ))}
    </section>
  );
}
