/** Trip planner with HOS schedule and ELD daily logs. */
import { useState } from "react";
import { planTrip } from "../api.js";
import TripForm from "../components/TripForm.jsx";
import TripMap from "../components/TripMap.jsx";
import ItineraryList from "../components/ItineraryList.jsx";
import LogsPanel from "../components/LogsPanel.jsx";
import {
  RouteIcon,
  ClockIcon,
  CalendarIcon,
  CycleIcon,
  TruckIcon,
  SteerIcon,
  GridIcon,
} from "../components/icons.jsx";

function fmtArrival(dt) {
  return new Date(dt).toLocaleString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

function Stat({ Icon, label, value, caption, pink }) {
  return (
    <div className="stat">
      <span className={`stat-icon ${pink ? "stat-icon-pink" : ""}`}>
        <Icon />
      </span>
      <div className="stat-body">
        <span className="stat-label">{label}</span>
        <span className={`stat-value ${pink ? "stat-pink" : "stat-teal"}`}>
          {value}
        </span>
        {caption && <span className="stat-caption">{caption}</span>}
      </div>
    </div>
  );
}

export default function TripPlannerPage() {
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(payload) {
    setLoading(true);
    setError(null);
    try {
      setPlan(await planTrip(payload));
    } catch (err) {
      setPlan(null);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const cycleLeft = plan
    ? Math.max(0, 70 - plan.trip.cycle_used_after_hours).toFixed(1)
    : null;

  return (
    <div className="app">
      <aside className={`sidebar no-print${plan ? " sidebar-compact" : ""}`}>
        <header className="sidebar-header">
          <span className="app-icon" aria-hidden="true">
            <TruckIcon />
          </span>
          <h1>trip planner &amp; ELD logs</h1>
          <p>
            Plan routes, optimize stops, and generate driver&rsquo;s daily
            logs compliant with HOS regulations (70hrs/8days).
          </p>
        </header>

        <section className="panel">
          <h2>Plan Your Trip</h2>
          <TripForm onSubmit={handleSubmit} loading={loading} />
          {error && <p className="route-status error">{error}</p>}
          {plan && !error && (
            <p className="route-status success">
              Trip planned — {plan.daily_logs.length} log{" "}
              {plan.daily_logs.length === 1 ? "sheet" : "sheets"} drawn.
            </p>
          )}
        </section>

        <section className="panel info-panel">
          <h3>Assumptions</h3>
          <ul className="steps-list">
            <li>
              <span className="step-icon"><SteerIcon /></span>
              Property-carrying driver, 70hrs/8days
            </li>
            <li>
              <span className="step-icon"><ClockIcon /></span>
              No adverse driving conditions
            </li>
            <li>
              <span className="step-icon"><RouteIcon /></span>
              Fueling at least every 1,000 miles
            </li>
            <li>
              <span className="step-icon"><CalendarIcon /></span>
              1 hour for pickup and drop-off
            </li>
          </ul>
        </section>

        <section className="panel info-panel">
          <h3>How it works</h3>
          <ul className="steps-list">
            <li>
              <span className="step-icon"><RouteIcon /></span>
              We calculate the best route
            </li>
            <li>
              <span className="step-icon"><ClockIcon /></span>
              Insert required breaks, 10-hr rests &amp; 34-hr restarts
            </li>
            <li>
              <span className="step-icon"><GridIcon /></span>
              Generate ELD logs (classic paper grid)
            </li>
          </ul>
        </section>
      </aside>

      <main className="main">
        {!plan ? (
          <div className="main-empty no-print">
            <p>
              Enter your trip — you&rsquo;ll get the route, every required
              stop and printable ELD log sheets.
            </p>
          </div>
        ) : (
          <>
            <div className="stats-bar no-print">
              <Stat
                Icon={RouteIcon}
                label="Total distance"
                value={`${Math.round(plan.trip.total_distance_miles).toLocaleString()} mi`}
                caption="Approx."
              />
              <Stat
                Icon={ClockIcon}
                label="Drive time"
                value={`${plan.trip.driving_hours} h`}
                caption="Est. driving"
              />
              <Stat
                Icon={CalendarIcon}
                label="Arrives"
                value={fmtArrival(plan.trip.arrival_time)}
                caption="Local time"
              />
              <Stat
                Icon={CycleIcon}
                label="Cycle after trip"
                value={`${cycleLeft} / 70 h`}
                caption="Remaining"
                pink
              />
            </div>

            <div className="map-shell no-print">
              <TripMap plan={plan} />
            </div>

            <div className="below-map">
              <ItineraryList stops={plan.stops} trip={plan.trip} />
              <LogsPanel sheets={plan.daily_logs} trip={plan.trip} />
            </div>
          </>
        )}
      </main>
    </div>
  );
}
