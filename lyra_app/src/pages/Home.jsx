import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, BASE } from '../api/client'
import './Home.css'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const today = new Date()
const defaultDate = {
  year: today.getFullYear(),
  month: today.getMonth() + 1,
  day: today.getDate(),
  hour: 12,
  minute: 0,
  lat: 28.6139,
  lon: 77.209,
  tz: 5.5,
}

function simpleAlignmentScore(panchang) {
  if (!panchang || panchang.status !== 'ok') return null
  let score = 50
  if (panchang.tithi?.name) score += 6
  if (panchang.nakshatra?.name) score += 4
  if (panchang.rahu_kaal?.start) score -= 2
  return Math.max(0, Math.min(100, Math.round(score)))
}

function scoreLabel(score) {
  if (score >= 70) return { text: 'Favorable', color: 'var(--favorable)', borderClass: 'favorable' }
  if (score >= 50) return { text: 'Neutral', color: 'var(--neutral)', borderClass: 'neutral' }
  return { text: 'Caution', color: 'var(--caution)', borderClass: 'caution' }
}

function hinduDateLine(panchang) {
  if (!panchang?.tithi || !panchang?.nakshatra) return '—'
  const num = panchang.tithi.number
  const paksha = num <= 15 ? 'Shukla' : 'Krishna'
  const day = num <= 15 ? num : num - 15
  return `${paksha} Paksha ${day} • ${panchang.nakshatra.name}`
}

// Mock 30-day trend (in production would come from API)
function mockTrend() {
  return {
    percent: 13,
    average: 73,
    bestDay: 95,
    bestDayNum: 27,
    pattern: 'Your alignment scores tend to be highest on Wednesdays and Fridays.',
    points: [65, 70, 68, 72, 74, 71, 69, 73, 76, 74, 78, 75, 73, 77, 80, 78, 76, 79, 82, 81, 79, 83, 85, 82, 84, 87, 95, 88, 86, 84],
  }
}

export default function Home() {
  const navigate = useNavigate()
  const [params, setParams] = useState(defaultDate)
  const [panchang, setPanchang] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    api.panchangDetailed(params)
      .then((data) => {
        if (!cancelled) setPanchang(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [params.year, params.month, params.day, params.lat, params.lon, params.tz])

  const score = panchang ? simpleAlignmentScore(panchang) : null
  const label = score != null ? scoreLabel(score) : null
  const trend = mockTrend()

  const dateStr = `${params.year}-${String(params.month).padStart(2, '0')}-${String(params.day).padStart(2, '0')}`
  const displayDate = `${MONTHS[params.month - 1]} ${params.day}`
  const hinduLine = panchang ? hinduDateLine(panchang) : '—'

  const goPrevDay = () => {
    const d = new Date(params.year, params.month - 1, params.day - 1)
    setParams({ ...params, year: d.getFullYear(), month: d.getMonth() + 1, day: d.getDate() })
  }
  const goNextDay = () => {
    const d = new Date(params.year, params.month - 1, params.day + 1)
    setParams({ ...params, year: d.getFullYear(), month: d.getMonth() + 1, day: d.getDate() })
  }

  const handleShare = () => {
    if (navigator.share) {
      navigator.share({
        title: 'Lyra – My alignment',
        text: `My alignment score today: ${score}/100 (${label?.text}).`,
        url: window.location.href,
      }).catch(() => {})
    }
  }

  return (
    <div className="home home-premium">
      {/* Top bar: Guest Mode | streak | location */}
      <div className="home-topbar">
        <span className="guest-badge">Guest Mode</span>
        <span className="streak-badge">
          <span className="streak-icon">🔥</span>
          12 day streak
        </span>
        <span className="home-location">Delhi, India</span>
      </div>

      {/* Date navigation */}
      <div className="home-datenav">
        <button type="button" className="nav-arrow" onClick={goPrevDay} aria-label="Previous day">‹</button>
        <span className="datenav-date">{displayDate}</span>
        <button type="button" className="nav-arrow" onClick={goNextDay} aria-label="Next day">›</button>
      </div>
      <p className="home-hindu">{hinduLine}</p>

      {loading && (
        <div className="home-loading">
          <div className="spinner" />
          <p>Loading cosmic data…</p>
        </div>
      )}

      {error && (
        <div className="home-error">
          <p>{error}</p>
          <p className="hint">API base: {BASE}</p>
          <p className="hint">Ensure the API is running, emulator is up, and you ran: adb reverse tcp:8000 tcp:8000</p>
        </div>
      )}

      {!loading && !error && panchang && (
        <>
          {/* Alignment Score card - premium */}
          <section className={`score-card score-card-premium ${label?.borderClass || ''}`}>
            <h2>Alignment Score</h2>
            <div className="score-value" style={{ color: label?.color }}>
              {score} <span className="score-max">/100</span>
            </div>
            <p className="score-label" style={{ color: label?.color }}>{label?.text}</p>
            <div className="score-chips">
              <span className="chip favorable">Tithi +6</span>
              <span className="chip favorable">Nakshatra +4</span>
              <span className="chip neutral">Yoga +3</span>
              <span className="chip caution">Rahu -2</span>
            </div>
            <p className="daily-insight">
              Today favors new beginnings and communication. Afternoon hours are most auspicious for important decisions.
            </p>
            <button type="button" className="share-btn" onClick={handleShare}>
              <span className="share-icon">⎘</span>
              Share my alignment
            </button>
          </section>

          {/* 30-Day Trend */}
          <section className="trend-card">
            <div className="trend-header">
              <h2>30-Day Trend</h2>
              <span className="trend-up">
                <span className="trend-arrow">↑</span> {trend.percent}%
              </span>
            </div>
            <div className="trend-chart">
              <svg viewBox="0 0 300 60" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="trendGrad" x1="0" y1="1" x2="0" y2="0">
                    <stop offset="0%" stopColor="var(--favorable)" stopOpacity="0.3" />
                    <stop offset="100%" stopColor="var(--favorable)" stopOpacity="0" />
                  </linearGradient>
                </defs>
                <polygon
                  fill="url(#trendGrad)"
                  points={trend.points.map((y, i) => `${(i / (trend.points.length - 1)) * 300},${60 - (y / 100) * 50}`).join(' ') + ' 300,60 0,60'}
                />
                <polyline
                  fill="none"
                  stroke="var(--favorable)"
                  strokeWidth="2"
                  points={trend.points.map((y, i) => `${(i / (trend.points.length - 1)) * 300},${60 - (y / 100) * 50}`).join(' ')}
                />
              </svg>
            </div>
            <div className="trend-stats">
              <div>
                <span className="trend-stat-label">Average Score</span>
                <span className="trend-stat-value">{trend.average}</span>
              </div>
              <div>
                <span className="trend-stat-label">Best Day</span>
                <span className="trend-stat-value">{trend.bestDay}</span>
                <span className="trend-stat-sub">Day {trend.bestDayNum}</span>
              </div>
            </div>
            <p className="trend-pattern">{trend.pattern}</p>
          </section>

          {/* Today's Panchang - two column + timeline */}
          <section className="panchang-card">
            <h2>Today's Panchang</h2>
            <div className="panchang-two-col">
              <div className="panchang-col">
                <div className="panchang-item">
                  <span className="panchang-label">Tithi</span>
                  <span className="panchang-val">{panchang.tithi?.name ?? '—'}</span>
                  <span className="panchang-meta">{panchang.tithi?.end_time ? `ends ${panchang.tithi.end_time}` : ''}</span>
                </div>
                <div className="panchang-item">
                  <span className="panchang-label">Yoga</span>
                  <span className="panchang-val">—</span>
                </div>
                <div className="panchang-item">
                  <span className="panchang-label">Sunrise</span>
                  <span className="panchang-val">{panchang.sunrise ?? '—'}</span>
                </div>
              </div>
              <div className="panchang-col">
                <div className="panchang-item">
                  <span className="panchang-label">Nakshatra</span>
                  <span className="panchang-val">{panchang.nakshatra?.name ?? '—'}</span>
                  <span className="panchang-meta">{panchang.nakshatra?.end_time ? `ends ${panchang.nakshatra.end_time}` : ''}</span>
                </div>
                <div className="panchang-item">
                  <span className="panchang-label">Rahu Kalam</span>
                  <span className="panchang-val">{panchang.rahu_kaal?.start ?? '—'} – {panchang.rahu_kaal?.end ?? '—'}</span>
                </div>
                <div className="panchang-item">
                  <span className="panchang-label">Sunset</span>
                  <span className="panchang-val">{panchang.sunset ?? '—'}</span>
                </div>
              </div>
            </div>
            <div className="panchang-timeline">
              <span className="timeline-start">{panchang.sunrise ?? '—'}</span>
              <div className="timeline-bar">
                <div className="timeline-dot" style={{ left: '35%' }} />
              </div>
              <span className="timeline-end">{panchang.sunset ?? '—'}</span>
            </div>
          </section>

          <div className="home-actions">
            <button type="button" className="btn btn-outline">
              <span className="btn-icon" aria-hidden>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18" /><path d="M7 14l4-5 4 2 5-6" /></svg>
              </span>
              Plan Event
            </button>
            <button type="button" className="btn btn-outline">
              <span className="btn-icon" aria-hidden>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" /></svg>
              </span>
              30-Day Outlook
            </button>
          </div>
          <button type="button" className="link-details" onClick={() => navigate('/app/home')}>
            View Full Day Details →
          </button>
        </>
      )}
    </div>
  )
}
