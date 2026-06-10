/**
 * Driver's Daily Log grid drawn as SVG in the FMCSA paper-log layout:
 * four duty rows, 24 hour columns with 15-minute ticks, a continuous
 * status line and per-status totals. Dark-themed on screen; print
 * styles flip it to paper (see styles.css).
 */
const ROWS = [
  { key: "off_duty", label: "1. Off Duty" },
  { key: "sleeper_berth", label: "2. Sleeper Berth" },
  { key: "driving", label: "3. Driving" },
  { key: "on_duty", label: "4. On Duty (not driving)" },
];

const GRID = {
  left: 150,
  top: 34,
  hourWidth: 34,
  rowHeight: 40,
};
const GRID_W = GRID.hourWidth * 24;
const GRID_H = GRID.rowHeight * ROWS.length;
const TOTALS_X = GRID.left + GRID_W + 14;
const SVG_W = TOTALS_X + 64;
const SVG_H = GRID.top + GRID_H + 16;

const STATUS_ROW = Object.fromEntries(ROWS.map((row, i) => [row.key, i]));

const x = (hour) => GRID.left + hour * GRID.hourWidth;
const rowMidY = (i) => GRID.top + i * GRID.rowHeight + GRID.rowHeight / 2;

function hourLabel(h) {
  if (h === 0 || h === 24) return "Mid";
  if (h === 12) return "Noon";
  return h > 12 ? h - 12 : h;
}

function buildStatusPath(segments) {
  if (!segments.length) return "";
  let d = "";
  segments.forEach((seg, i) => {
    const y = rowMidY(STATUS_ROW[seg.status]);
    d += i === 0 ? `M ${x(seg.start_hour)} ${y}` : ` L ${x(seg.start_hour)} ${y}`;
    d += ` L ${x(seg.end_hour)} ${y}`;
  });
  return d;
}

export function fmtHours(value) {
  const h = Math.floor(value + 1e-9);
  const m = Math.round((value - h) * 60);
  return `${h}:${String(m).padStart(2, "0")}`;
}

export default function LogSheet({ sheet }) {
  return (
    <svg
      viewBox={`0 0 ${SVG_W} ${SVG_H}`}
      className="log-grid"
      role="img"
      aria-label={`Duty status grid for ${sheet.date}`}
    >
      {/* hour labels */}
      {Array.from({ length: 25 }, (_, h) => (
        <text
          key={`hl-${h}`}
          x={x(h)}
          y={GRID.top - 10}
          textAnchor="middle"
          className="svg-hour-label"
        >
          {hourLabel(h)}
        </text>
      ))}
      <text
        x={TOTALS_X + 24}
        y={GRID.top - 10}
        textAnchor="middle"
        className="svg-hour-label svg-total-head"
      >
        Total
      </text>

      {/* row bands, labels and totals */}
      {ROWS.map((row, i) => {
        const yTop = GRID.top + i * GRID.rowHeight;
        return (
          <g key={row.key}>
            <rect
              x={GRID.left}
              y={yTop}
              width={GRID_W}
              height={GRID.rowHeight}
              className={i % 2 ? "svg-band-alt" : "svg-band"}
            />
            <text
              x={GRID.left - 10}
              y={yTop + GRID.rowHeight / 2 + 4}
              textAnchor="end"
              className="svg-row-label"
            >
              {row.label}
            </text>
            <text
              x={TOTALS_X + 24}
              y={yTop + GRID.rowHeight / 2 + 4}
              textAnchor="middle"
              className="svg-total"
            >
              {fmtHours(sheet.totals[row.key] || 0)}
            </text>
          </g>
        );
      })}

      {/* vertical ticks: hours full height, halves & quarters shorter */}
      {Array.from({ length: 24 * 4 + 1 }, (_, q) => {
        const hour = q / 4;
        const tickX = x(hour);
        const isHour = q % 4 === 0;
        const isHalf = q % 2 === 0;
        return ROWS.map((row, r) => {
          const yTop = GRID.top + r * GRID.rowHeight;
          const len = isHour
            ? GRID.rowHeight
            : isHalf
              ? GRID.rowHeight * 0.45
              : GRID.rowHeight * 0.28;
          return (
            <line
              key={`t-${q}-${r}`}
              x1={tickX}
              y1={yTop}
              x2={tickX}
              y2={yTop + len}
              className={isHour ? "svg-tick-hour" : "svg-tick"}
            />
          );
        });
      })}

      {/* frame */}
      {ROWS.map((_, i) => (
        <line
          key={`rl-${i}`}
          x1={GRID.left}
          y1={GRID.top + i * GRID.rowHeight}
          x2={GRID.left + GRID_W}
          y2={GRID.top + i * GRID.rowHeight}
          className="svg-frame"
        />
      ))}
      <rect
        x={GRID.left}
        y={GRID.top}
        width={GRID_W}
        height={GRID_H}
        fill="none"
        className="svg-frame"
      />

      {/* the duty status line */}
      <path d={buildStatusPath(sheet.segments)} className="svg-status-glow" />
      <path d={buildStatusPath(sheet.segments)} className="svg-status-line" />
    </svg>
  );
}
