/** Fuel-route optimizer (original assessment): cheapest fuel stops
 *  between two points for a 500-mile-range, 10 MPG vehicle. */
import { useState } from "react";
import { planFuelRoute } from "../api.js";
import MapView from "../components/MapView.jsx";
import {
  RouteIcon,
  ClockIcon,
  FuelIcon,
  CycleIcon,
} from "../components/icons.jsx";

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

export default function FuelRoutePage() {
  const [form, setForm] = useState({ start: "", finish: "" });
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      setResult(await planFuelRoute(form.start.trim(), form.finish.trim()));
    } catch (err) {
      setResult(err.routeContext || null); // a 422 still carries the route
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <header className="sidebar-header">
          <span className="app-icon" aria-hidden="true">⛽</span>
          <h1>spotter-road-atlas</h1>
          <p>
            Find the most cost-effective fuel stops along long-haul routes
            across the USA.
          </p>
        </header>

        <section className="panel">
          <h2>Plan Your Route</h2>
          <form className="route-form" onSubmit={submit}>
            <div className="field">
              <label className="field-label" htmlFor="start">
                Source
              </label>
              <input
                id="start"
                required
                value={form.start}
                placeholder="e.g. Dallas, TX"
                onChange={(e) => setForm({ ...form, start: e.target.value })}
              />
            </div>
            <div className="field">
              <label className="field-label" htmlFor="finish">
                Destination
              </label>
              <input
                id="finish"
                required
                value={form.finish}
                placeholder="e.g. Chicago, IL"
                onChange={(e) => setForm({ ...form, finish: e.target.value })}
              />
            </div>
            <button className="submit-button" disabled={loading}>
              {loading ? "Optimizing…" : "Find Optimal Route"}
            </button>
          </form>
          {error && <p className="route-status error">{error}</p>}
          {result && !error && (
            <p className="route-status success">
              Route planned from {result.start.query} to {result.finish.query}.
            </p>
          )}
        </section>

        <section className="panel info-panel">
          <h3>Assumptions</h3>
          <ul className="info-list">
            <li>Truck range: 500 miles</li>
            <li>Fuel efficiency: 10 MPG</li>
            <li>Vehicle starts with a full tank</li>
          </ul>
        </section>

        <section className="panel info-panel">
          <h3>How it works</h3>
          <ul className="steps-list">
            <li>
              <span className="step-icon" aria-hidden="true">🧭</span>
              We calculate the most efficient route
            </li>
            <li>
              <span className="step-icon" aria-hidden="true">⛽</span>
              Find cost-effective fuel stops within range
            </li>
            <li>
              <span className="step-icon" aria-hidden="true">＄</span>
              Estimate total fuel cost (10 MPG)
            </li>
          </ul>
        </section>
      </aside>

      <main className="main">
        {!result ? (
          <div className="main-empty">
            <p>Enter a source and destination to light up the route.</p>
          </div>
        ) : (
          <FuelResult result={result} />
        )}
      </main>
    </div>
  );
}

function FuelResult({ result }) {
  const route = result.map.features
    .find((f) => f.geometry.type === "LineString")
    .geometry.coordinates.map(([lng, lat]) => [lat, lng]);

  const stops = result.fuel_plan?.stops || [];
  const hours = Math.floor(result.route.duration_hours);
  const minutes = Math.round((result.route.duration_hours - hours) * 60);

  const markers = [
    {
      lat: result.start.lat,
      lng: result.start.lng,
      kind: "start",
      label: { title: "Start", text: result.start.query },
    },
    {
      lat: result.finish.lat,
      lng: result.finish.lng,
      kind: "finish",
      label: { title: "End", text: result.finish.query },
    },
    ...stops.map((stop, i) => ({
      lat: stop.location.lat,
      lng: stop.location.lng,
      kind: "fuel_stop",
      label: {
        title: `Stop ${i + 1}`,
        text: `${stop.city}, ${stop.state}`,
        accent: `$${stop.price_per_gallon.toFixed(2)} / gal`,
      },
      tooltip: `${stop.name} · ${stop.gallons_purchased} gal · $${stop.cost}`,
    })),
  ];

  return (
    <>
      <div className="stats-bar">
        <Stat
          Icon={RouteIcon}
          label="Total distance"
          value={`${Math.round(result.route.distance_miles).toLocaleString()} mi`}
          caption="Approx."
        />
        <Stat
          Icon={ClockIcon}
          label="Est. drive time"
          value={`${hours}h ${minutes}m`}
          caption="Nonstop driving"
        />
        <Stat Icon={FuelIcon} label="Fuel stops" value={stops.length} />
        <Stat
          Icon={CycleIcon}
          label="Est. fuel cost"
          value={
            result.fuel_plan
              ? `$${result.fuel_plan.total_fuel_cost.toLocaleString()}`
              : "—"
          }
          caption="At today's prices"
          pink
        />
      </div>

      <div className="map-shell">
        <MapView route={route} markers={markers} />
      </div>

      {stops.length > 0 && (
        <div className="below-map">
          <aside className="itinerary">
            <h2>Fuel stops</h2>
            <ol>
              {stops.map((stop, i) => (
                <li key={i}>
                  <span className="it-icon">⛽</span>
                  <div>
                    <strong>{stop.name}</strong>
                    <small>
                      {stop.city}, {stop.state} · mile{" "}
                      {Math.round(stop.distance_from_start_miles)} · $
                      {stop.price_per_gallon}/gal · {stop.gallons_purchased}{" "}
                      gal · <b>${stop.cost}</b>
                    </small>
                  </div>
                </li>
              ))}
            </ol>
          </aside>
        </div>
      )}
    </>
  );
}
