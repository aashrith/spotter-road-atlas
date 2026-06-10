const form = document.getElementById("route-form");
const startInput = document.getElementById("start");
const finishInput = document.getElementById("finish");
const getStartedButton = document.getElementById("get-started");
const submitButton = document.getElementById("submit-button");
const submitLabel = document.getElementById("submit-label");
const statusNode = document.getElementById("route-status");
const distanceNode = document.getElementById("distance-value");
const etaNode = document.getElementById("eta-value");
const costNode = document.getElementById("cost-value");
const stopsCountNode = document.getElementById("stops-count");

const map = L.map("map", {
  zoomControl: false,
});

L.control
  .zoom({
    position: "topleft",
  })
  .addTo(map);

L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
  maxZoom: 19,
  attribution:
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
}).addTo(map);

const markersLayer = L.layerGroup().addTo(map);
const routeGlowLayer = L.layerGroup().addTo(map);
const routeLayer = L.layerGroup().addTo(map);

map.setView([39.5, -98.35], 4);

function formatDuration(hours) {
  const totalMinutes = Math.round(hours * 60);
  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;
  if (h === 0) {
    return `${m}m`;
  }
  if (m === 0) {
    return `${h}h`;
  }
  return `${h}h ${m}m`;
}

function setStatus(message, tone = "default") {
  statusNode.textContent = message;
  statusNode.className = "route-status";
  if (tone !== "default") {
    statusNode.classList.add(tone);
  }
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  submitLabel.textContent = isLoading ? "Finding Route..." : "Find Optimal Route";
}

function createMarkerIcon(kind, labelHtml) {
  return L.divIcon({
    className: "",
    html: `
      <div class="map-marker">
        <div class="map-marker-label">${labelHtml}</div>
        <div class="map-marker-pin ${kind}"></div>
      </div>
    `,
    iconSize: [0, 0],
    iconAnchor: [0, 0],
  });
}

function resetMetrics() {
  distanceNode.textContent = "--";
  etaNode.textContent = "--";
  stopsCountNode.textContent = "--";
  costNode.textContent = "--";
}

function renderMetrics(data) {
  const stops = data.fuel_plan?.stops ?? [];
  distanceNode.textContent = `${Math.round(data.route.distance_miles).toLocaleString()} mi`;
  etaNode.textContent = formatDuration(data.route.duration_hours);
  stopsCountNode.textContent = String(stops.length);
  costNode.textContent = data.fuel_plan
    ? `$${data.fuel_plan.total_fuel_cost.toFixed(2)}`
    : "--";
}

function renderPartialMetrics(data) {
  distanceNode.textContent = `${Math.round(data.route.distance_miles).toLocaleString()} mi`;
  etaNode.textContent = formatDuration(data.route.duration_hours);
  stopsCountNode.textContent = "--";
  costNode.textContent = "--";
}

function stopByNumber(stops, stopNumber) {
  return stops[stopNumber - 1] || null;
}

function clearMap() {
  markersLayer.clearLayers();
  routeGlowLayer.clearLayers();
  routeLayer.clearLayers();
}

function renderMap(data) {
  clearMap();
  if (!data?.map?.features?.length) {
    return;
  }

  const routeFeature = data.map.features.find(
    (feature) => feature.properties.kind === "route"
  );
  const latlngs = routeFeature.geometry.coordinates.map(([lng, lat]) => [
    lat,
    lng,
  ]);

  L.polyline(latlngs, {
    color: "#2dd4bf",
    weight: 10,
    opacity: 0.18,
    lineCap: "round",
    lineJoin: "round",
  }).addTo(routeGlowLayer);

  L.polyline(latlngs, {
    color: "#2dd4bf",
    weight: 4,
    opacity: 0.95,
    lineCap: "round",
    lineJoin: "round",
  }).addTo(routeLayer);

  for (const feature of data.map.features) {
    const { kind } = feature.properties;
    if (kind === "route") {
      continue;
    }

    const [lng, lat] = feature.geometry.coordinates;
    let labelHtml = "";

    if (kind === "start") {
      labelHtml = `
        <strong>Start</strong>
        <span>${feature.properties.name}</span>
      `;
    } else if (kind === "finish") {
      labelHtml = `
        <strong>End</strong>
        <span>${feature.properties.name}</span>
      `;
    } else if (kind === "fuel_stop") {
      const stop = stopByNumber(data.fuel_plan?.stops ?? [], feature.properties.stop_number);
      const place = stop ? `${stop.city}, ${stop.state}` : feature.properties.name;
      labelHtml = `
        <strong>Stop ${feature.properties.stop_number}</strong>
        <span>${place}</span>
        <em>$${feature.properties.price_per_gallon.toFixed(2)} / gal</em>
      `;
    }

    L.marker([lat, lng], {
      icon: createMarkerIcon(kind, labelHtml),
      zIndexOffset: kind === "fuel_stop" ? 300 : 200,
    }).addTo(markersLayer);
  }

  const bounds = L.latLngBounds(latlngs);
  if (bounds.isValid()) {
    map.fitBounds(bounds.pad(0.14));
  }
}

async function planRoute(start, finish) {
  setLoading(true);
  setStatus("Calculating route and optimizing fuel stops...");

  const params = new URLSearchParams({ start, finish });

  try {
    const response = await fetch(`/api/v1/fuel-route?${params.toString()}`);
    const data = await response.json();

    if (!response.ok) {
      if (data.route && data.map) {
        renderPartialMetrics(data);
        renderMap(data);
      } else {
        resetMetrics();
        clearMap();
      }
      throw new Error(data.error || "Unable to plan route.");
    }

    renderMetrics(data);
    renderMap(data);
    setStatus(
      `Route planned from ${data.start.query} to ${data.finish.query}.`,
      "success"
    );
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    setLoading(false);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  await planRoute(startInput.value.trim(), finishInput.value.trim());
});

getStartedButton.addEventListener("click", () => {
  startInput.focus();
  form.scrollIntoView({ behavior: "smooth", block: "center" });
});

planRoute(startInput.value.trim(), finishInput.value.trim());
