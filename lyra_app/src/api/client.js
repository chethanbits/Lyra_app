/**
 * Lyra app – API client for the Lyra prod backend (/day, /range, /heatmap).
 * Set VITE_API_URL in .env or it defaults to http://localhost:8000
 */
export const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/** Test API connection (e.g. /health). Returns { ok, status, data }. */
export async function testConnection() {
  try {
    const res = await fetch(`${BASE}/health`, { headers: { Accept: 'application/json' } });
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, data };
  } catch (e) {
    return { ok: false, status: 0, error: e.message };
  }
}

async function request(path, params = {}) {
  const url = new URL(path, BASE);
  Object.entries(params).forEach(([k, v]) => {
    if (v != null && v !== '') url.searchParams.set(k, String(v));
  });
  const res = await fetch(url.toString(), { headers: { Accept: 'application/json' } });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

/** Lyra prod backend: one day (panchanga + alignment score + summary). */
export function getDay(opts) {
  const { date, lat, lon, tz = 5.5, region = 'NORTH_INDIA', place_name } = opts || {};
  return request('/day', { date, lat, lon, tz, region, place_name });
}

/** Lyra prod backend: date range (list of DayResult). */
export function getRange(opts) {
  const { start, end, lat, lon, tz = 5.5, region = 'NORTH_INDIA', place_name } = opts || {};
  return request('/range', { start, end, lat, lon, tz, region, place_name });
}

/** Lyra prod backend: heatmap (lightweight list for calendar). */
export function getHeatmap(opts) {
  const { start, end, lat, lon, tz = 5.5, region = 'NORTH_INDIA', place_name } = opts || {};
  return request('/heatmap', { start, end, lat, lon, tz, region, place_name });
}

/** Profile mode: one day with birth details (Tara Bala, personal alignment). */
export function getProfileDay(opts) {
  const {
    date,
    lat,
    lon,
    tz = 5.5,
    birth_date,
    birth_time,
    pob_lat,
    pob_lon,
    pob_tz = 5.5,
    pob_name,
    region = 'NORTH_INDIA',
    anchor,
    ayanamsa,
    place_name,
  } = opts || {};
  return request('/p/day', {
    date,
    lat,
    lon,
    tz,
    birth_date,
    birth_time,
    pob_lat,
    pob_lon,
    pob_tz,
    pob_name,
    region,
    anchor,
    ayanamsa,
    place_name,
  });
}

// Legacy (api_exploration) – keep if you still need them
export const api = {
  getDay,
  getRange,
  getHeatmap,
  getProfileDay,
  geocode: (city) => request('/geocode', { city }),
  panchangDetailed: (opts) => request('/panchang-detailed', opts),
  planetPositions: (opts) => request('/planet-positions', { ...opts, second: 0 }),
  dasha: (opts) => request('/dasha', { ...opts, second: 0 }),
  transits: (year, lat, lon, tz) => request('/transits', { year, lat, lon, tz }),
};

export default api;
