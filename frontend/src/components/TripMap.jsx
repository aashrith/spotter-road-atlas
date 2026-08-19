import { useMemo } from "react";
import MapView from "./MapView.jsx";

const REST_TITLES = {
  rest_break: "Rest Stop",
  overnight_rest: "Rest Stop",
  cycle_restart: "34-hr Restart",
};

function near(a, b) {
  return Math.abs(a.lat - b.lat) < 0.005 && Math.abs(a.lng - b.lng) < 0.005;
}

/** "Fuel — PILOT #123 (Memphis, TN)" -> "Memphis, TN" */
function fuelPlace(note) {
  const match = note.match(/\(([^)]+)\)\s*$/);
  return match ? match[1] : note.replace(/^Fuel — /, "");
}

function fmt(dt) {
  return new Date(dt).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function TripMap({ plan }) {
  const route = useMemo(() => {
    const line = plan.map.features.find(
      (f) => f.geometry.type === "LineString"
    );
    return line.geometry.coordinates.map(([lng, lat]) => [lat, lng]);
  }, [plan]);

  const { current, pickup, dropoff } = plan.trip;
  const samePickupDropoff = near(pickup, dropoff);

  const endpoints = [
    {
      lat: current.lat,
      lng: current.lng,
      kind: "current",
      label: { title: "Start", text: current.query },
    },
    samePickupDropoff
      ? {
          lat: pickup.lat,
          lng: pickup.lng,
          kind: "dropoff",
          label: { title: "Pickup & Dropoff", text: pickup.query },
        }
      : null,
    !samePickupDropoff && {
      lat: pickup.lat,
      lng: pickup.lng,
      kind: "pickup",
      label: { title: "Pickup", text: pickup.query },
    },
    !samePickupDropoff && {
      lat: dropoff.lat,
      lng: dropoff.lng,
      kind: "dropoff",
      label: { title: "Drop-off", text: dropoff.query },
    },
  ].filter(Boolean);

  const enRoute = plan.stops
    .filter((s) => !["pickup", "dropoff"].includes(s.kind))
    .map((stop) => ({
      lat: stop.location.lat,
      lng: stop.location.lng,
      kind: stop.kind,
      label:
        stop.kind === "fuel"
          ? { title: "Fuel Stop", text: stop.place || fuelPlace(stop.note) }
          : stop.kind === "overnight_rest" || stop.kind === "cycle_restart"
            ? {
                title: REST_TITLES[stop.kind],
                text:
                  stop.place || `mile ${Math.round(stop.miles_from_start)}`,
              }
            : null, // 30-min breaks: pin + hover tooltip only
      tooltip: `${stop.note} · ${fmt(stop.arrival)}`,
    }));

  return <MapView route={route} markers={[...endpoints, ...enRoute]} />;
}
