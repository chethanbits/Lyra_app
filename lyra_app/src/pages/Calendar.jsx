import { useEffect, useMemo, useState } from 'react'
import { getHeatmap } from '../api/client'
import { getEventsForDate } from '../data/festivals'
import './Calendar.css'

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

function classifyScoreBand(score, band) {
  const b = (band || '').toUpperCase()
  if (b === 'FAVORABLE' || b === 'POSITIVE') return 'favorable'
  if (b === 'CAUTION' || b === 'CHALLENGING') return 'caution'
  if (b === 'NEUTRAL') return 'neutral'
  if (typeof score === 'number') {
    if (score >= 70) return 'favorable'
    if (score >= 40) return 'neutral'
    return 'caution'
  }
  return null
}

export default function Calendar() {
  const today = new Date()
  const [currentMonth, setCurrentMonth] = useState(new Date(today.getFullYear(), today.getMonth(), 1))
  const [showHeatmap, setShowHeatmap] = useState(true)
  const [selectedDate, setSelectedDate] = useState(today.toISOString().slice(0, 10))

  const [lat, setLat] = useState(28.6139)
  const [lon, setLon] = useState(77.209)
  const [tz, setTz] = useState(5.5)

  const [heatmap, setHeatmap] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Derive year/month helpers
  const year = currentMonth.getFullYear()
  const monthIndex = currentMonth.getMonth()
  const monthLabel = `${MONTHS[monthIndex]} ${year}`

  const { daysInMonth, firstWeekday, blanks, days } = useMemo(() => {
    const d = new Date(year, monthIndex + 1, 0)
    const count = d.getDate()
    const first = new Date(year, monthIndex, 1).getDay()
    return {
      daysInMonth: count,
      firstWeekday: first,
      blanks: Array(first).fill(null),
      days: Array.from({ length: count }, (_, i) => i + 1),
    }
  }, [year, monthIndex])

  // Keep location in sync with device GPS (same behaviour as Home)
  useEffect(() => {
    if (!navigator.geolocation) return
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude)
        setLon(pos.coords.longitude)
        setTz(-new Date().getTimezoneOffset() / 60)
      },
      () => {
        // Fallback stays Delhi defaults
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 },
    )
  }, [])

  // Fetch heatmap for the whole month whenever month/location changes and toggle is on
  useEffect(() => {
    if (!showHeatmap) return
    const start = `${year}-${String(monthIndex + 1).padStart(2, '0')}-01`
    const end = `${year}-${String(monthIndex + 1).padStart(2, '0')}-${String(daysInMonth).padStart(2, '0')}`
    const region = lat < 20 ? 'SOUTH_INDIA' : 'NORTH_INDIA'

    let cancelled = false
    setLoading(true)
    setError(null)
    getHeatmap({ start, end, lat, lon, tz, region })
      .then((rows) => {
        if (cancelled) return
        const map = {}
        rows.forEach((r) => {
          map[r.date] = r
        })
        setHeatmap(map)
      })
      .catch((e) => {
        if (!cancelled) setError(e.message || 'Failed to load heatmap')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [showHeatmap, year, monthIndex, daysInMonth, lat, lon, tz])

  const handlePrevMonth = () => {
    setCurrentMonth((m) => new Date(m.getFullYear(), m.getMonth() - 1, 1))
  }

  const handleNextMonth = () => {
    setCurrentMonth((m) => new Date(m.getFullYear(), m.getMonth() + 1, 1))
  }

  const eventsForDate = (dateStr) => getEventsForDate(dateStr)

  return (
    <div className="calendar">
      <header className="calendar-header">
        <h1>Calendar</h1>
        <div className="calendar-month-nav">
          <button type="button" className="month-arrow" onClick={handlePrevMonth} aria-label="Previous month">
            ‹
          </button>
          <div className="month-label">{monthLabel}</div>
          <button type="button" className="month-arrow" onClick={handleNextMonth} aria-label="Next month">
            ›
          </button>
        </div>
      </header>

      <div className="calendar-toggle-row">
        <label className="toggle-label">
          <input
            type="checkbox"
            checked={showHeatmap}
            onChange={(e) => setShowHeatmap(e.target.checked)}
          />
          <span className="toggle-ui">
            <span className="toggle-thumb" />
          </span>
          <span className="toggle-text">Show alignment heatmap</span>
        </label>
      </div>

      <div className="calendar-grid">
        {WEEKDAYS.map((d) => (
          <div key={d} className="weekday">
            {d}
          </div>
        ))}
        {blanks.map((_, i) => (
          <div key={`b-${i}`} className="day empty" />
        ))}
        {days.map((d) => {
          const dateStr = `${year}-${String(monthIndex + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
          const data = heatmap[dateStr]
          const bandClass = showHeatmap && data ? classifyScoreBand(data.score, data.band) : null
          const classes = ['day']
          if (bandClass) classes.push(`day-${bandClass}`)
          if (dateStr === selectedDate) classes.push('day-selected')
          const events = eventsForDate(dateStr)
          const hasFestival = events.length > 0
          const festivalTitle = hasFestival ? events.map((e) => e.name).join(', ') : ''
          return (
            <button
              key={dateStr}
              type="button"
              className={classes.join(' ')}
              onClick={() => setSelectedDate(dateStr)}
              title={festivalTitle}
            >
              <span className="day-number">{d}</span>
              {hasFestival && <span className="festival-dot" title={festivalTitle} />}
            </button>
          )
        })}
      </div>

      <div className="calendar-legend">
        <div className="legend-item">
          <span className="legend-swatch favorable" />
          <span>Favorable (70–100)</span>
        </div>
        <div className="legend-item">
          <span className="legend-swatch neutral" />
          <span>Neutral (40–69)</span>
        </div>
        <div className="legend-item">
          <span className="legend-swatch caution" />
          <span>Caution (Below 40)</span>
        </div>
        <div className="legend-item">
          <span className="legend-swatch festival" />
          <span>Festival / Special Day</span>
        </div>
      </div>

      {error && (
        <p className="calendar-hint error">
          {error}
        </p>
      )}
    </div>
  )
}
