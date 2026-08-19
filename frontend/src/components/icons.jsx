/** Minimal stroke icon set (currentColor) for chips and labels. */
const base = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round",
  strokeLinejoin: "round",
};

const wrap = (children) => (props) => (
  <svg viewBox="0 0 24 24" width="1em" height="1em" {...base} {...props}>
    {children}
  </svg>
);

export const RouteIcon = wrap(
  <>
    <circle cx="6" cy="19" r="2.4" />
    <circle cx="18" cy="5" r="2.4" />
    <path d="M8.2 17.5h7a3.5 3.5 0 0 0 0-7h-6a3.5 3.5 0 0 1 0-7h6.5" />
  </>
);

export const ClockIcon = wrap(
  <>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 7.5V12l3 2" />
  </>
);

export const CalendarIcon = wrap(
  <>
    <rect x="4" y="5.5" width="16" height="15" rx="2.5" />
    <path d="M4 10h16M8.5 3.5v3.5M15.5 3.5v3.5" />
  </>
);

export const CycleIcon = wrap(
  <>
    <path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3" />
    <path d="M19.8 3.6v3.6h-3.6" />
  </>
);

export const PinIcon = wrap(
  <>
    <path d="M12 21s-6.5-5.4-6.5-10A6.5 6.5 0 0 1 19 11c0 4.6-7 10-7 10z" />
    <circle cx="12" cy="10.6" r="2.2" />
  </>
);

export const FuelIcon = wrap(
  <>
    <rect x="4.5" y="4" width="9" height="16" rx="1.6" />
    <path d="M4.5 9h9M16.5 8.5l2.6 2.6a1.6 1.6 0 0 1 .4 1v5a1.7 1.7 0 0 1-3.4 0v-7" />
  </>
);

export const TruckIcon = wrap(
  <>
    <path d="M2.5 7h10.5v9.5H2.5z" />
    <path d="M13 10h4.4l3 3v3.5H13" />
    <circle cx="6.5" cy="18.4" r="1.9" />
    <circle cx="17" cy="18.4" r="1.9" />
  </>
);

export const BedIcon = wrap(
  <>
    <path d="M3 18.5v-12" />
    <path d="M3 14h18v4.5" />
    <path d="M7.5 14v-3a1.8 1.8 0 0 1 1.8-1.8H19A2 2 0 0 1 21 11v3" />
  </>
);

export const CoffeeIcon = wrap(
  <>
    <path d="M5 9h11v6.5a4 4 0 0 1-4 4H9a4 4 0 0 1-4-4z" />
    <path d="M16 10.5h1.6a2.3 2.3 0 0 1 0 4.6H16M7.6 5.5v1.8M11.5 4.5v2.8" />
  </>
);

export const BoxIcon = wrap(
  <>
    <path d="M12 3.5 20 7.5v9L12 20.5 4 16.5v-9z" />
    <path d="M4 7.5l8 4 8-4M12 11.5v9" />
  </>
);

export const FlagIcon = wrap(
  <>
    <path d="M5.5 21V4" />
    <path d="M5.5 5h12.5l-2.6 3.5L18 12H5.5" />
  </>
);

export const GridIcon = wrap(
  <>
    <rect x="4" y="4" width="16" height="16" rx="2" />
    <path d="M4 9.3h16M4 14.6h16M9.3 4v16M14.6 4v16" />
  </>
);

export const SteerIcon = wrap(
  <>
    <circle cx="12" cy="12" r="8.5" />
    <circle cx="12" cy="12" r="2.4" />
    <path d="M12 3.5v6.1M4.2 14.5l5.6-1.7M19.8 14.5l-5.6-1.7" />
  </>
);

export const PrintIcon = wrap(
  <>
    <path d="M7 8V3.5h10V8" />
    <rect x="4" y="8" width="16" height="8.5" rx="1.8" />
    <path d="M7 13.5h10v7H7z" />
  </>
);
