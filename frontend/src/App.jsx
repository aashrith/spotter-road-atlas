import { useState } from "react";
import TripPlannerPage from "./pages/TripPlannerPage.jsx";
import FuelRoutePage from "./pages/FuelRoutePage.jsx";

const TABS = [
  { id: "trip", label: "Trip & ELD Logs" },
  { id: "fuel", label: "Fuel Optimizer" },
];

export default function App() {
  const [tab, setTab] = useState("trip");

  return (
    <>
      <nav className="nav no-print">
        <span className="brand">
          <span className="brand-dots" aria-hidden="true">
            <i /><i /><i />
          </span>
          <span className="brand-name">spotter</span>
        </span>
        <div className="tabs" role="tablist">
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={tab === t.id}
              className={tab === t.id ? "tab tab-active" : "tab"}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </nav>
      {tab === "trip" ? <TripPlannerPage /> : <FuelRoutePage />}
    </>
  );
}
