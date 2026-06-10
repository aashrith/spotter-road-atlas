const BASE = import.meta.env.VITE_API_URL || "";

async function parse(response) {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(
      body.error || "Something went wrong planning the trip."
    );
    // A 422 from the fuel-route API still carries the drawn route.
    if (body.map) error.routeContext = body;
    throw error;
  }
  return body;
}

export async function planTrip(payload) {
  const response = await fetch(`${BASE}/api/v1/trip-plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parse(response);
}

export async function planFuelRoute(start, finish) {
  const params = new URLSearchParams({ start, finish });
  const response = await fetch(`${BASE}/api/v1/fuel-route?${params}`);
  return parse(response);
}
