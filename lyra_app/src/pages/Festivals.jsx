import { useMemo, useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { getRange } from '../api/client'
import { getMockRangeResult } from '../data/mockDay'
import {
  getEventsForDate,
  getEventsForMonth,
  getLunarMonthLabel,
} from '../data/festivals'
import './Festivals.css'

const WEEKDAYS = ['Mo', 'Tu', 'We', 'Thu', 'Fri', 'Sat', 'Su']
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

const DEFAULT_LOC = { lat: 28.6139, lon: 77.209, tz: 5.5 }

/** Derive observance type from tithi index (1-30). Returns type string or null. */
function observanceFromTithi(tithiIndex) {
  if (!tithiIndex) return null
  const idx = Number(tithiIndex)
  if (idx === 11 || idx === 26) return 'ekadashi'
  if (idx === 15) return 'purnima'
  if (idx === 30) return 'amavasya'
  return null
}

/** Build merged events for a month: API /range panchanga + static festivals. */
function mergeMonthEvents(rangeResults, year, monthIndex) {
  const prefix = `${year}-${String(monthIndex + 1).padStart(2, '0')}`
  const byDate = {}
  rangeResults.forEach((day) => {
    const date = day.date
    if (!date || !date.startsWith(prefix)) return
    const list = byDate[date] || []
    const tithiIdx = day.panchanga?.tithi?.index
    const obsType = observanceFromTithi(tithiIdx)
    if (obsType) {
      const name = day.panchanga?.tithi?.name || (obsType === 'ekadashi' ? 'Ekadashi' : obsType === 'purnima' ? 'Purnima' : 'Amavasya')
      list.push({ name, type: obsType })
    }
    byDate[date] = list
  })
  const staticEvents = getEventsForMonth(year, monthIndex)
  staticEvents.forEach(({ date, events }) => {
    const list = byDate[date] || []
    events.forEach((e) => {
      const type = e.name && e.name.toLowerCase().includes('eclipse') ? 'eclipse' : e.type
      list.push({ name: e.name, type })
    })
    byDate[date] = list
  })
  const out = []
  Object.entries(byDate).forEach(([date, events]) => {
    if (events.length) out.push({ date, events })
  })
  out.sort((a, b) => a.date.localeCompare(b.date))
  return out
}

/** Vedic tithi code: D/K sequence matches tithi.
 *  D1–D14 = Shukla Paksha tithi 1–14, P = Purnima (15),
 *  K1–K14 = Krishna Paksha tithi 16–29 (day 1–14), A = Amavasya (30). */
function tithiToCode(tithiIndex) {
  if (tithiIndex == null || tithiIndex === undefined) return ''
  const i = Number(tithiIndex)
  if (i >= 1 && i <= 14) return `D${i}`   // Shukla paksha day 1..14
  if (i === 15) return 'P'                 // Purnima
  if (i >= 16 && i <= 29) return `K${i - 15}`  // Krishna paksha day 1..14
  if (i === 30) return 'A'                 // Amavasya
  return ''
}

/** Moon phase class for CSS (matches reference: full, new, crescent, gibbous). */
function moonPhaseClass(tithiIndex) {
  if (!tithiIndex) return 'moon-default'
  const i = Number(tithiIndex)
  if (i === 15) return 'moon-purnima'
  if (i === 30) return 'moon-amavasya'
  if (i >= 1 && i <= 7) return 'moon-waxing-crescent'
  if (i >= 8 && i <= 14) return 'moon-waxing-gibbous'
  if (i >= 16 && i <= 23) return 'moon-waning-gibbous'
  if (i >= 24 && i <= 29) return 'moon-waning-crescent'
  return 'moon-default'
}

/** Build date -> { tithiIndex, karanaName } from /range for calendar cells. */
function buildDayPanchangaMap(rangeResults, year, monthIndex) {
  const prefix = `${year}-${String(monthIndex + 1).padStart(2, '0')}`
  const map = {}
  rangeResults.forEach((day) => {
    const date = day.date
    if (!date || !date.startsWith(prefix)) return
    map[date] = {
      tithiIndex: day.panchanga?.tithi?.index,
      karanaName: day.panchanga?.karana?.name,
    }
  })
  return map
}

export default function Festivals() {
  const navigate = useNavigate()
  const today = new Date()
  const [currentMonth, setCurrentMonth] = useState(new Date(today.getFullYear(), today.getMonth(), 1))
  const [filter, setFilter] = useState('festivals') // 'festivals' | 'ekadashi' | 'purnima' (match image: 3 pills only)
  const [rangeResults, setRangeResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedDate, setSelectedDate] = useState(null)
  const gridRef = useRef(null)
  const dayRefs = useRef({})

  const year = currentMonth.getFullYear()
  const monthIndex = currentMonth.getMonth()
  const monthLabel = `${MONTHS[monthIndex]} ${year}`
  const lunarLabel = getLunarMonthLabel(monthIndex, year)

  const start = `${year}-${String(monthIndex + 1).padStart(2, '0')}-01`
  const lastDay = new Date(year, monthIndex + 1, 0).getDate()
  const end = `${year}-${String(monthIndex + 1).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    getRange({
      start,
      end,
      lat: DEFAULT_LOC.lat,
      lon: DEFAULT_LOC.lon,
      tz: DEFAULT_LOC.tz,
      region: 'NORTH_INDIA',
    })
      .then((data) => {
        if (!cancelled) setRangeResults(Array.isArray(data) ? data : [])
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message)
          setRangeResults(getMockRangeResult(start, end))
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [start, end])

  const monthEvents = useMemo(
    () => mergeMonthEvents(rangeResults, year, monthIndex),
    [rangeResults, year, monthIndex]
  )

  const dayPanchangaMap = useMemo(
    () => buildDayPanchangaMap(rangeResults, year, monthIndex),
    [rangeResults, year, monthIndex]
  )

  const getEventsForDateMerged = (dateStr) => {
    const entry = monthEvents.find((e) => e.date === dateStr)
    return entry ? entry.events : []
  }

  const countByType = useMemo(() => {
    let festivals = 0
    let ekadashi = 0
    let purnima = 0
    let eclipse = 0
    monthEvents.forEach(({ events }) => {
      events.forEach((e) => {
        if (e.type === 'festival' || e.type === 'observance') festivals++
        else if (e.type === 'ekadashi') ekadashi++
        else if (e.type === 'purnima' || e.type === 'amavasya') purnima++
        else if (e.type === 'eclipse') eclipse++
      })
    })
    return { festivals, ekadashi, purnima, eclipse }
  }, [monthEvents])

  const showEvent = (event) => {
    if (filter === 'festivals') return event.type === 'festival' || event.type === 'observance'
    if (filter === 'ekadashi') return event.type === 'ekadashi'
    if (filter === 'purnima') return event.type === 'purnima' || event.type === 'amavasya'
    return true
  }

  const hasVisibleEvent = (dateStr) => {
    const events = getEventsForDateMerged(dateStr)
    return events.some(showEvent)
  }

  const handlePrevMonth = () => {
    setCurrentMonth((m) => new Date(m.getFullYear(), m.getMonth() - 1, 1))
  }

  const handleNextMonth = () => {
    setCurrentMonth((m) => new Date(m.getFullYear(), m.getMonth() + 1, 1))
  }

  const scrollToDate = (dateStr) => {
    setSelectedDate(dateStr)
    const el = dayRefs.current[dateStr]
    if (el && gridRef.current) {
      el.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' })
      el.classList.add('festivals-day-highlight')
      setTimeout(() => el.classList.remove('festivals-day-highlight'), 1500)
    }
  }

  const { blanks, days } = useMemo(() => {
    const d = new Date(year, monthIndex + 1, 0)
    const count = d.getDate()
    const first = new Date(year, monthIndex, 1).getDay()
    const firstMon = first === 0 ? 6 : first - 1
    return {
      blanks: Array(firstMon).fill(null),
      days: Array.from({ length: count }, (_, i) => i + 1),
    }
  }, [year, monthIndex])

  return (
    <div className="festivals-page">
      <header className="festivals-header">
        <div className="festivals-title-wrap">
          <span className="festivals-logo" aria-hidden>✦</span>
          <h1>Lyra · Festivals & Observances</h1>
        </div>
        <button
          type="button"
          className="festivals-settings-btn"
          onClick={() => navigate('/app/settings')}
          aria-label="Settings"
        >
          ⚙
        </button>
      </header>

      <div className="festivals-month-nav">
        <button type="button" className="month-arrow" onClick={handlePrevMonth} aria-label="Previous month">
          ‹
        </button>
        <div className="festivals-month-label">
          <span className="lunar-month">{lunarLabel}</span>
          <span className="gregorian-month">{monthLabel}</span>
        </div>
        <button type="button" className="month-arrow" onClick={handleNextMonth} aria-label="Next month">
          ›
        </button>
      </div>

      <div className="festivals-show">
        <span className="show-label">Show</span>
        <div className="show-filters">
          <button
            type="button"
            className={`filter-btn ${filter === 'festivals' ? 'active' : ''}`}
            onClick={() => setFilter('festivals')}
          >
            <span className="filter-icon filter-icon-flame">🔥</span>
            Festivals ({countByType.festivals})
          </button>
          <button
            type="button"
            className={`filter-btn ${filter === 'ekadashi' ? 'active' : ''}`}
            onClick={() => setFilter('ekadashi')}
          >
            <span className="filter-icon">🌙</span>
            Ekadashi ({countByType.ekadashi})
          </button>
          <button
            type="button"
            className={`filter-btn ${filter === 'purnima' ? 'active' : ''}`}
            onClick={() => setFilter('purnima')}
          >
            <span className="filter-icon">🌑</span>
            Purnima/Amavasya ({countByType.purnima})
          </button>
        </div>
      </div>

      {loading && (
        <div className="festivals-loading">
          <div className="spinner" />
          <p>Loading month data…</p>
        </div>
      )}
      {error && (
        <div className="festivals-error">
          <p>{error}</p>
        </div>
      )}

      {!loading && !error && (
      <div className="festivals-grid-wrap" ref={gridRef}>
        <div className="festivals-grid festivals-grid-vedic">
          {WEEKDAYS.map((d) => (
            <div key={d} className="festivals-weekday">
              {d}
            </div>
          ))}
          {blanks.map((_, i) => (
            <div key={`b-${i}`} className="festivals-day empty" />
          ))}
          {days.map((d) => {
            const dateStr = `${year}-${String(monthIndex + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
            const panchanga = dayPanchangaMap[dateStr]
            const tithiIndex = panchanga?.tithiIndex
            const code = tithiToCode(tithiIndex)
            const moonClass = moonPhaseClass(tithiIndex)
            const events = getEventsForDateMerged(dateStr)
            const visible = events.filter(showEvent)
            const hasMarker = visible.length > 0
            const isFestival = events.some((e) => e.type === 'festival' || e.type === 'observance')
            const isSelected = dateStr === selectedDate
            return (
              <button
                key={dateStr}
                type="button"
                ref={(el) => { dayRefs.current[dateStr] = el }}
                className={`festivals-day ${hasMarker ? 'has-event' : ''} ${isFestival ? 'festival-day' : ''} ${isSelected ? 'festivals-day-selected' : ''}`}
                onClick={() => setSelectedDate(dateStr)}
                title={events.map((e) => e.name).join(', ') || undefined}
              >
                <span className="festivals-day-num">{d}</span>
                {tithiIndex != null && (
                  <span className={`festivals-moon ${moonClass}`} aria-hidden />
                )}
                {code && <span className="festivals-code">{code}</span>}
                {hasMarker && (
                  <span className="festivals-dots">
                    {visible.map((ev, i) => (
                      <span
                        key={i}
                        className={`festival-dot dot-${ev.type}`}
                        title={ev.name}
                      />
                    ))}
                  </span>
                )}
              </button>
            )
          })}
        </div>
        <div className="festivals-legend">
          <span className="festivals-legend-item">
            <span className="festivals-legend-icon moon-purnima" />
            Purnima
          </span>
          <span className="festivals-legend-item">
            <span className="festivals-legend-icon moon-amavasya" />
            Amavasya
          </span>
          <span className="festivals-legend-item">
            <span className="festivals-festival-icon" aria-hidden>
              <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
                <path d="M12 2L9 8h6L12 2zm0 6l-2 4h4L12 8zm0 4l-1 2h2l-1-2zm-3 4a1 1 0 1 0 0 2 1 1 0 0 0 0-2zm6 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2z" />
              </svg>
            </span>
            Festival
          </span>
        </div>
      </div>
      )}

      <section className="festivals-this-month">
        <div className="this-month-header">
          <h2>This Month</h2>
          <button type="button" className="view-all-btn">
            View All
          </button>
        </div>
        <ul className="this-month-list">
          {monthEvents.map(({ date, events }) =>
            events.map((ev, i) => (
              <li
                key={`${date}-${i}`}
                className="this-month-item"
                role="button"
                tabIndex={0}
                onClick={() => scrollToDate(date)}
                onKeyDown={(e) => e.key === 'Enter' && scrollToDate(date)}
              >
                <span className={`event-icon icon-${ev.type}`}>
                  {ev.type === 'festival' && '🔥'}
                  {ev.type === 'ekadashi' && '🌙'}
                  {(ev.type === 'purnima' || ev.type === 'amavasya') && <span className="event-dot event-dot-red" />}
                  {ev.type === 'observance' && '◆'}
                  {ev.type === 'eclipse' && '◇'}
                </span>
                <span className="event-date">{date.slice(8, 10)} {MONTHS[monthIndex].slice(0, 3)}</span>
                <span className="event-name">{ev.name}</span>
                <span className="event-chevron">›</span>
              </li>
            ))
          )}
        </ul>
        {!loading && monthEvents.length === 0 && (
          <p className="no-events">No festivals or observances this month.</p>
        )}
      </section>
    </div>
  )
}
