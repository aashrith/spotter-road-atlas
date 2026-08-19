/** Shared dark map matching the spotter design language:
 *  CARTO dark tiles, teal glow route line, dark labelled pin markers. */
import { useEffect, useMemo } from "react";
import L from "leaflet";
import {
  MapContainer,
  TileLayer,
  Polyline,
  Marker,
  Tooltip,
  useMap,
} from "react-leaflet";

function FitBounds({ positions }) {
  const map = useMap();
  useEffect(() => {
    const bounds = L.latLngBounds(positions);
    if (bounds.isValid()) {
      map.fitBounds(bounds.pad(0.14));
    }
  }, [map, positions]);
  return null;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function markerIcon(marker) {
  const label = marker.label
    ? `<div class="map-marker-label">
         ${marker.label.title ? `<strong>${escapeHtml(marker.label.title)}</strong>` : ""}
         ${marker.label.text ? `<span>${escapeHtml(marker.label.text)}</span>` : ""}
         ${marker.label.accent ? `<em>${escapeHtml(marker.label.accent)}</em>` : ""}
       </div>`
    : "";
  return L.divIcon({
    className: "",
    html: `<div class="map-marker">${label}<div class="map-marker-pin ${marker.kind}"></div></div>`,
    iconSize: [0, 0],
  });
}

export default function MapView({ route, markers }) {
  const icons = useMemo(() => markers.map(markerIcon), [markers]);

  return (
    <div className="map-wrap">
      <MapContainer
        center={route[0]}
        zoom={5}
        scrollWheelZoom
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        <Polyline
          positions={route}
          pathOptions={{
            color: "#2dd4bf",
            weight: 10,
            opacity: 0.18,
            lineCap: "round",
            lineJoin: "round",
          }}
        />
        <Polyline
          positions={route}
          pathOptions={{
            color: "#2dd4bf",
            weight: 4,
            opacity: 0.95,
            lineCap: "round",
            lineJoin: "round",
          }}
        />
        {markers.map((marker, i) => (
          <Marker
            key={i}
            position={[marker.lat, marker.lng]}
            icon={icons[i]}
            zIndexOffset={marker.label ? 300 : 200}
          >
            {marker.tooltip && (
              <Tooltip className="dark-tooltip" direction="top" offset={[0, -12]}>
                {marker.tooltip}
              </Tooltip>
            )}
          </Marker>
        ))}
        <FitBounds positions={route} />
      </MapContainer>
    </div>
  );
}
