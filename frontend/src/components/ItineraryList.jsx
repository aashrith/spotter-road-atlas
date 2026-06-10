import { useState } from "react";
import {
  TruckIcon,
  BoxIcon,
  FlagIcon,
  FuelIcon,
  CoffeeIcon,
  BedIcon,
  CycleIcon,
  PinIcon,
} from "./icons.jsx";

const KIND_META = {
  pickup: { Icon: BoxIcon, tone: "teal" },
  dropoff: { Icon: PinIcon, tone: "pink" },
  fuel: { Icon: FuelIcon, tone: "pink" },
  rest_break: { Icon: CoffeeIcon, tone: "slate" },
  overnight_rest: { Icon: BedIcon, tone: "slate" },
  cycle_restart: { Icon: CycleIcon, tone: "amber" },
};

const COLLAPSED_COUNT = 6;

function fmt(dt) {
  return new Date(dt).toLocaleString(undefined, {
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function Row({ Icon, tone, title, detail }) {
  return (
    <li>
      <span className={`it-chip it-${tone}`}>
        <Icon />
      </span>
      <div>
        <strong>{title}</strong>
        <small>{detail}</small>
      </div>
    </li>
  );
}

export default function ItineraryList({ stops, trip }) {
  const [expanded, setExpanded] = useState(false);

  const rows = [
    {
      Icon: TruckIcon,
      tone: "teal",
      title: `Depart — ${trip.current.query}`,
      detail: fmt(trip.start_time),
    },
    ...stops.map((stop) => {
      const meta = KIND_META[stop.kind] || KIND_META.rest_break;
      return {
        Icon: meta.Icon,
        tone: meta.tone,
        title: stop.note,
        detail: `${fmt(stop.arrival)} → ${fmt(stop.departure)} · mile ${Math.round(
          stop.miles_from_start
        )}`,
      };
    }),
    {
      Icon: FlagIcon,
      tone: "pink",
      title: `Arrive — ${trip.dropoff.query}`,
      detail: fmt(trip.arrival_time),
    },
  ];

  const visible = expanded ? rows : rows.slice(0, COLLAPSED_COUNT);
  const hidden = rows.length - COLLAPSED_COUNT;

  return (
    <section className="panel itinerary-card">
      <h2 className="card-title">Itinerary</h2>
      <ol className="itinerary-list">
        {visible.map((row, i) => (
          <Row key={i} {...row} />
        ))}
      </ol>
      {hidden > 0 && (
        <button
          className="ghost-button itinerary-toggle"
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? "Collapse itinerary" : `View full itinerary (${hidden} more)`}
        </button>
      )}
    </section>
  );
}
