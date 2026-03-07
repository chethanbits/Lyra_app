/**
 * Date format helpers for personal (profile) mode.
 * Store/display: DD-MMM-YYYY (e.g. 15-Jan-1990).
 * API: YYYY-MM-DD.
 */

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** Convert YYYY-MM-DD to DD-MMM-YYYY */
export function toDDMMMYYYY(isoDate) {
  if (!isoDate || typeof isoDate !== 'string') return ''
  const [y, m, d] = isoDate.split('-').map(Number)
  if (!y || !m || !d) return isoDate
  const monthName = MONTHS[m - 1]
  if (!monthName) return isoDate
  const day = String(d).padStart(2, '0')
  return `${day}-${monthName}-${y}`
}

/** Convert DD-MMM-YYYY to YYYY-MM-DD for API */
export function fromDDMMMYYYYToISO(ddMmmYyyy) {
  if (!ddMmmYyyy || typeof ddMmmYyyy !== 'string') return ''
  const trimmed = ddMmmYyyy.trim()
  if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) return trimmed
  const match = trimmed.match(/^(\d{1,2})-([A-Za-z]{3})-(\d{4})$/)
  if (!match) return ''
  const [, day, mon, year] = match
  const mi = MONTHS.findIndex((m) => m.toLowerCase() === mon.toLowerCase()) + 1
  if (mi === 0) return ''
  return `${year}-${String(mi).padStart(2, '0')}-${String(parseInt(day, 10)).padStart(2, '0')}`
}

/** From stored (DD-MMM-YYYY or YYYY-MM-DD) get YYYY-MM-DD for <input type="date"> */
export function storedToInputValue(stored) {
  if (!stored) return ''
  if (/^\d{4}-\d{2}-\d{2}$/.test(stored)) return stored
  return fromDDMMMYYYYToISO(stored)
}
