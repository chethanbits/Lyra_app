/**
 * Lyra app – API client for the PyJHora wrapper (api_exploration).
 * Set VITE_API_URL in .env or it defaults to http://localhost:8000
 */
export const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/** Test API connection (e.g. /health). Returns { ok, status, error }. */
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

export const api = {
  geocode: (city) => request('/geocode', { city }),
  panchangDetailed: (opts) => request('/panchang-detailed', opts),
  planetPositions: (opts) => request('/planet-positions', { ...opts, second: 0 }),
  dasha: (opts) => request('/dasha', { ...opts, second: 0 }),
  transits: (year, lat, lon, tz) => request('/transits', { year, lat, lon, tz }),
};

export default api;
