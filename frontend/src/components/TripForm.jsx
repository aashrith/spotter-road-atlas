import { useState } from "react";
import { PinIcon, ClockIcon, RouteIcon } from "./icons.jsx";

const FIELDS = [
  { name: "current_location", label: "Current location", placeholder: "e.g. Dallas, TX" },
  { name: "pickup_location", label: "Pickup location", placeholder: "e.g. Oklahoma City, OK" },
  { name: "dropoff_location", label: "Dropoff location", placeholder: "e.g. Chicago, IL" },
];

export default function TripForm({ onSubmit, loading }) {
  const [form, setForm] = useState({
    current_location: "",
    pickup_location: "",
    dropoff_location: "",
    current_cycle_used_hours: "0",
    start_time: "",
  });

  function update(field) {
    return (event) => setForm({ ...form, [field]: event.target.value });
  }

  function submit(event) {
    event.preventDefault();
    onSubmit({
      current_location: form.current_location.trim(),
      pickup_location: form.pickup_location.trim(),
      dropoff_location: form.dropoff_location.trim(),
      current_cycle_used_hours: Number(form.current_cycle_used_hours || 0),
      start_time: form.start_time || null,
    });
  }

  return (
    <form className="route-form" onSubmit={submit}>
      {FIELDS.map((field) => (
        <div className="field" key={field.name}>
          <label className="field-label" htmlFor={field.name}>
            {field.label}
          </label>
          <div className="input-wrap">
            <span className="field-icon"><PinIcon /></span>
            <input
              id={field.name}
              required
              value={form[field.name]}
              onChange={update(field.name)}
              placeholder={field.placeholder}
            />
          </div>
        </div>
      ))}
      <div className="field-row">
        <div className="field">
          <label className="field-label" htmlFor="cycle">
            Cycle (hrs)
          </label>
          <div className="input-wrap">
            <span className="field-icon"><ClockIcon /></span>
            <input
              id="cycle"
              type="number"
              min="0"
              max="70"
              step="0.5"
              required
              value={form.current_cycle_used_hours}
              onChange={update("current_cycle_used_hours")}
            />
          </div>
        </div>
        <div className="field">
          <label className="field-label" htmlFor="start">
            Start (optional)
          </label>
          <input
            id="start"
            type="datetime-local"
            value={form.start_time}
            onChange={update("start_time")}
          />
        </div>
      </div>
      <button className="submit-button" disabled={loading}>
        <RouteIcon /> {loading ? "Planning…" : "Plan Trip & Draw Logs"}
      </button>
    </form>
  );
}
