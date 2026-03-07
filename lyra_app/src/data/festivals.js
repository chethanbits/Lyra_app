/**
 * Festivals & observances keyed by date (YYYY-MM-DD).
 * Uses 15-year holiday database (2010–2024) plus extended/sample data.
 * Used by: main Calendar (Festival / Special Day dots) and Festivals & Observances page.
 */
import { HOLIDAYS_15_YEARS, HOLIDAYS_YEAR_START, HOLIDAYS_YEAR_END } from './holidays15years'

const EXTENDED_BY_DATE = {
  // March 2026 (Phalguna / Chaitra) – sample from boss's images
  '2026-03-03': [
    { name: 'Holika Dahan', type: 'festival' },
    { name: 'Purnima', type: 'purnima' },
  ],
  '2026-03-04': [
    { name: 'Holi (Purnima)', type: 'festival' },
  ],
  '2026-03-13': [
    { name: 'Holika Dahan', type: 'festival' },
  ],
  '2026-03-14': [
    { name: 'Holi (Purnima)', type: 'festival' },
  ],
  '2026-03-09': [
    { name: 'Papmochani Ekadashi', type: 'ekadashi' },
  ],
  '2026-03-16': [
    { name: 'Amavasya', type: 'amavasya' },
  ],
  '2026-03-24': [
    { name: 'Amalaki Ekadashi', type: 'ekadashi' },
  ],
  '2026-03-30': [
    { name: 'Ram Navami', type: 'festival' },
  ],
  '2026-04-01': [
    { name: 'Chaitra Navratri begins', type: 'festival' },
  ],
  '2026-04-09': [
    { name: 'Ram Navami (Chaitra)', type: 'festival' },
  ],
  '2026-04-14': [
    { name: 'Amavasya', type: 'amavasya' },
    { name: 'Solar eclipse (where visible)', type: 'observance' },
  ],
  '2026-05-01': [
    { name: 'Akshaya Tritiya', type: 'festival' },
  ],
  '2026-05-14': [
    { name: 'Amavasya', type: 'amavasya' },
  ],
}

/** Merged: 15-year holidays + extended/sample dates. */
export const FESTIVALS_BY_DATE = {
  ...HOLIDAYS_15_YEARS,
  ...EXTENDED_BY_DATE,
}

/** Holiday database year range (for UI or validation). */
export { HOLIDAYS_YEAR_START, HOLIDAYS_YEAR_END }

/** Get all events for a date. Returns [] if none. */
export function getEventsForDate(dateStr) {
  return FESTIVALS_BY_DATE[dateStr] || []
}

/** Get events in a month. dateStr is YYYY-MM-DD; returns array of { date, events }. */
export function getEventsForMonth(year, monthIndex) {
  const start = `${year}-${String(monthIndex + 1).padStart(2, '0')}-01`
  const prefix = start.slice(0, 7) // YYYY-MM
  const out = []
  Object.entries(FESTIVALS_BY_DATE).forEach(([date, events]) => {
    if (date.startsWith(prefix) && events.length) {
      out.push({ date, events })
    }
  })
  out.sort((a, b) => a.date.localeCompare(b.date))
  return out
}

/** Hindu lunar month names (Chaitra = 1 .. Phalguna = 12). */
export const LUNAR_MONTH_NAMES = [
  'Chaitra', 'Vaishakha', 'Jyestha', 'Ashadha', 'Shravana', 'Bhadrapada',
  'Ashwin', 'Kartik', 'Margashirsha', 'Pausha', 'Magha', 'Phalguna',
]

/** Approximate Vikram Samvat year for a Gregorian year (e.g. 2026 -> 2082). */
export function getVikramSamvatYear(gregorianYear) {
  return gregorianYear + 56
}

/** Rough lunar month for a Gregorian month (0-11). North Indian (Purnimanta) convention. */
export function getLunarMonthLabel(gregorianMonthIndex, gregorianYear) {
  const vs = getVikramSamvatYear(gregorianYear)
  const names = LUNAR_MONTH_NAMES
  const idx = (gregorianMonthIndex + 9) % 12
  return `${names[idx]} ${vs}`
}
