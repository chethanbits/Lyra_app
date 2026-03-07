import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getDay, getProfileDay, BASE } from '../api/client'
import { fromDDMMMYYYYToISO } from '../utils/date'
import './Home.css'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const today = new Date()
const defaultDate = {
  year: today.getFullYear(),
  month: today.getMonth() + 1,
  day: today.getDate(),
  lat: 28.6139,
  lon: 77.209,
  tz: 5.5,
}
const DEFAULT_LOCATION_LABEL = 'Delhi, India'

function scoreLabelFromBand(band) {
  const b = (band || '').toUpperCase()
  if (b === 'FAVORABLE') return { text: 'Favorable', color: 'var(--favorable)', borderClass: 'favorable' }
  if (b === 'POSITIVE') return { text: 'Positive', color: 'var(--favorable)', borderClass: 'favorable' }
  if (b === 'NEUTRAL') return { text: 'Neutral', color: 'var(--neutral)', borderClass: 'neutral' }
  if (b === 'CAUTION') return { text: 'Caution', color: 'var(--caution)', borderClass: 'caution' }
  if (b === 'CHALLENGING') return { text: 'Challenging', color: 'var(--caution)', borderClass: 'caution' }
  return { text: 'Neutral', color: 'var(--neutral)', borderClass: 'neutral' }
}

function hinduDateLine(panchanga) {
  if (!panchanga?.tithi || !panchanga?.nakshatra) return '—'
  const idx = panchanga.tithi.index
  const paksha = idx <= 15 ? 'Shukla' : 'Krishna'
  const day = idx <= 15 ? idx : idx - 15
  return `${paksha} Paksha ${day} • ${panchanga.nakshatra.name}`
}

/** Parse "HH:MM" to minutes from midnight */
function timeToMinutes(str) {
  if (!str || typeof str !== 'string') return 0
  const [h, m] = str.trim().split(':').map(Number)
  if (Number.isNaN(h)) return 0
  return (h || 0) * 60 + (Number.isNaN(m) ? 0 : m)
}

/** Rahu Kaal: which 1/8 of daylight (0-indexed). Sun=1, Mon=2, ..., Sat=7 */
const RAHU_PERIOD_BY_WEEKDAY = [1, 2, 3, 4, 5, 6, 7]

/** Get Rahu Kaal as percentage of scale: { left, width } from 0-100 */
function getRahuKaalPercent(sunriseStr, sunsetStr, year, month, day) {
  const sunriseMin = timeToMinutes(sunriseStr)
  const sunsetMin = timeToMinutes(sunsetStr)
  let duration = sunsetMin - sunriseMin
  if (duration <= 0) return null
  const d = new Date(year, month - 1, day)
  const weekday = d.getDay()
  const periodIndex = RAHU_PERIOD_BY_WEEKDAY[weekday] - 1
  const periodDuration = duration / 8
  const startMin = sunriseMin + periodIndex * periodDuration
  const left = ((startMin - sunriseMin) / duration) * 100
  const width = (periodDuration / duration) * 100
  return { left, width }
}

function SunriseIcon() {
  return (
    <span className="panchang-sun-icon sunrise" aria-hidden>
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
        <circle cx="12" cy="10" r="4" fill="url(#sunriseGrad)" stroke="none" />
        <path d="M8 14h8" stroke="#374151" strokeWidth="1" />
        <path d="M12 14v2" stroke="#111" strokeWidth="1" />
        <defs>
          <linearGradient id="sunriseGrad" x1="0" y1="1" x2="0" y2="0">
            <stop offset="0%" stopColor="#f97316" />
            <stop offset="100%" stopColor="#fbbf24" />
          </linearGradient>
        </defs>
      </svg>
    </span>
  )
}

function SunsetIcon() {
  return (
    <span className="panchang-sun-icon sunset" aria-hidden>
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
        <circle cx="12" cy="14" r="4" fill="url(#sunsetGrad)" stroke="none" />
        <path d="M8 10h8" stroke="#374151" strokeWidth="1" />
        <path d="M12 10v2" stroke="#f97316" strokeWidth="1" />
        <defs>
          <linearGradient id="sunsetGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#fbbf24" />
            <stop offset="100%" stopColor="#f97316" />
          </linearGradient>
        </defs>
      </svg>
    </span>
  )
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
  const [locationLabel, setLocationLabel] = useState(DEFAULT_LOCATION_LABEL)
  const [locationLoading, setLocationLoading] = useState(true)
  const [dayResult, setDayResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Profile mode: personal experience + birth details + POB coords for /p/day
  const profile = (() => {
    if (typeof localStorage === 'undefined') return null
    const mode = localStorage.getItem('lyra_experience_mode')
    const birthDate = localStorage.getItem('lyra_birth_date')
    const birthTime = localStorage.getItem('lyra_birth_time')
    const pobLat = localStorage.getItem('lyra_pob_lat')
    const pobLon = localStorage.getItem('lyra_pob_lon')
    const pobTz = localStorage.getItem('lyra_pob_tz')
    if (mode !== 'personal' || !birthDate) return null
    const lat = parseFloat(pobLat)
    const lon = parseFloat(pobLon)
    const tz = parseFloat(pobTz)
    if (Number.isNaN(lat) || Number.isNaN(lon) || Number.isNaN(tz)) return null
    return {
      birth_date: birthDate,
      birth_time: birthTime || '10:30',
      pob_lat: lat,
      pob_lon: lon,
      pob_tz: tz,
      pob_name: localStorage.getItem('lyra_birth_place') || undefined,
    }
  })()

  const isProfileMode = Boolean(profile)
  const experienceMode = (() => {
    if (typeof localStorage === 'undefined') return null
    const mode = localStorage.getItem('lyra_experience_mode')
    const hasBirth = localStorage.getItem('lyra_birth_date')
    if (mode === 'personal' && hasBirth) return 'personal'
    if (mode === 'general') return 'general'
    return null
  })()
  const modeLabel = isProfileMode ? 'Profile Mode' : experienceMode === 'general' ? 'General Mode' : 'Guest Mode'
  const isLoggedIn = typeof localStorage !== 'undefined' && localStorage.getItem('lyra_logged_in') === '1'

  // Try to get local GPS on mount so panchang is for user's actual location
  useEffect(() => {
    if (!navigator.geolocation) {
      setLocationLabel('Using Delhi (no GPS)')
      setLocationLoading(false)
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude
        const lon = pos.coords.longitude
        const tz = -new Date().getTimezoneOffset() / 60
        setParams((p) => ({ ...p, lat, lon, tz }))
        setLocationLabel('Your location')
        setLocationLoading(false)
      },
      () => {
        setLocationLabel('Using Delhi (location denied)')
        setLocationLoading(false)
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 }
    )
  }, [])

  const useMyLocation = () => {
    if (!navigator.geolocation) return
    setLocationLoading(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude
        const lon = pos.coords.longitude
        const tz = -new Date().getTimezoneOffset() / 60
        setParams((p) => ({ ...p, lat, lon, tz }))
        setLocationLabel('Your location')
        setLocationLoading(false)
      },
      () => {
        setLocationLabel('Using Delhi (location denied)')
        setLocationLoading(false)
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    )
  }

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    const dateStr = `${params.year}-${String(params.month).padStart(2, '0')}-${String(params.day).padStart(2, '0')}`
    const region = params.lat < 20 ? 'SOUTH_INDIA' : 'NORTH_INDIA'
    const opts = {
      date: dateStr,
      lat: params.lat,
      lon: params.lon,
      tz: params.tz,
      region,
    }
    const promise = isProfileMode && profile
      ? getProfileDay({
          ...opts,
          birth_date: fromDDMMMYYYYToISO(profile.birth_date) || profile.birth_date,
          birth_time: profile.birth_time,
          pob_lat: profile.pob_lat,
          pob_lon: profile.pob_lon,
          pob_tz: profile.pob_tz,
          pob_name: profile.pob_name,
        })
      : getDay(opts)
    promise
      .then((data) => {
        if (!cancelled) {
          setDayResult(data)
          if (data.place_used) setLocationLabel(`Your location (${data.place_used})`)
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [params.year, params.month, params.day, params.lat, params.lon, params.tz, isProfileMode, profile?.birth_date, profile?.birth_time, profile?.pob_lat, profile?.pob_lon, profile?.pob_tz])

  const panchanga = dayResult?.panchanga
  const scoreResult = dayResult?.score
  // In Profile Mode use personal alignment from profile overlay
  const profileOverlay = dayResult?.profile
  const score = isProfileMode && profileOverlay
    ? profileOverlay.personal_alignment_score
    : (scoreResult?.alignment_score ?? null)
  const band = isProfileMode && profileOverlay
    ? profileOverlay.personal_band
    : scoreResult?.band
  const label = score != null ? scoreLabelFromBand(band) : null
  const summaryLines = scoreResult?.summary || []
  const dailyInsight = summaryLines[0] || 'Loading…'
  const cautionLine = summaryLines[1]
  const taraBala = profileOverlay?.tara_bala
  const personality = profileOverlay?.personality

  const dateStr = `${params.year}-${String(params.month).padStart(2, '0')}-${String(params.day).padStart(2, '0')}`
  const displayDate = `${MONTHS[params.month - 1]} ${params.day}`
  const hinduLine = panchanga ? hinduDateLine(panchanga) : '—'
  const trend = mockTrend()

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
      {/* Top bar: back | Mode | location */}
      <div className="home-topbar">
        <button
          type="button"
          className="home-back-btn"
          onClick={() => navigate('/welcome')}
          aria-label="Go back"
        >
          ←
        </button>
        <span className={`guest-badge ${experienceMode === 'personal' ? 'personal-badge' : ''}`}>{modeLabel}</span>
        <button
          type="button"
          className="home-location home-location-btn"
          onClick={useMyLocation}
          disabled={locationLoading}
          title="Use device location for panchang"
        >
          {locationLoading ? 'Getting location…' : locationLabel}
        </button>
        {isLoggedIn && (
          <span className="home-account-badge" title="Account" aria-label="Logged in">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </span>
        )}
      </div>
      <p className="home-location-hint">Panchang uses this location for sunrise and scoring.</p>

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

      {!loading && !error && dayResult && panchanga && (
        <>
          {/* Alignment Score card - guest score or Profile personal alignment */}
          <section className={`score-card score-card-premium ${label?.borderClass || ''}`}>
            <h2>{isProfileMode ? 'Personal Alignment Score' : 'Alignment Score'}</h2>
            <div className="score-value" style={{ color: label?.color }}>
              {score} <span className="score-max">/100</span>
            </div>
            <p className="score-label" style={{ color: label?.color }}>{label?.text}</p>
            <p className="daily-insight">
              {dailyInsight}
            </p>
            {cautionLine && (
              <p className="daily-caution">{cautionLine}</p>
            )}
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

          {/* Today's Panchang - from backend */}
          <section className="panchang-card">
            <h2>Today's Panchang</h2>
            <div className="panchang-two-col">
              <div className="panchang-col">
                <div className="panchang-item">
                  <span className="panchang-label">Tithi</span>
                  <span className="panchang-val">{panchanga.tithi?.name ?? '—'}</span>
                  <span className="panchang-meta">{panchanga.tithi?.ends_at ? `ends ${panchanga.tithi.ends_at}` : ''}</span>
                </div>
                <div className="panchang-item">
                  <span className="panchang-label">Yoga</span>
                  <span className="panchang-val">{panchanga.yoga?.name ?? '—'}</span>
                  <span className="panchang-meta">{panchanga.yoga?.ends_at ? `ends ${panchanga.yoga.ends_at}` : ''}</span>
                </div>
              </div>
              <div className="panchang-col">
                <div className="panchang-item">
                  <span className="panchang-label">Nakshatra</span>
                  <span className="panchang-val">{panchanga.nakshatra?.name ?? '—'}</span>
                  <span className="panchang-meta">{panchanga.nakshatra?.ends_at ? `ends ${panchanga.nakshatra.ends_at}` : ''}</span>
                </div>
                <div className="panchang-item">
                  <span className="panchang-label">Karana</span>
                  <span className="panchang-val">{panchanga.karana?.name ?? '—'}</span>
                  <span className="panchang-meta">{panchanga.karana?.ends_at ? `ends ${panchanga.karana.ends_at}` : ''}</span>
                </div>
              </div>
            </div>
            <div className="panchang-timeline">
              <span className="timeline-endpoint">
                <SunriseIcon />
                <span className="timeline-time">{panchanga.sunrise ?? '—'}</span>
              </span>
              <div className="timeline-bar-wrap">
                <div className="timeline-bar">
                  {(() => {
                    const rahu = getRahuKaalPercent(panchanga.sunrise, panchanga.sunset, params.year, params.month, params.day)
                    return (
                      <>
                        {rahu && (
                          <div
                            className="timeline-rahu"
                            style={{ left: `${rahu.left}%`, width: `${rahu.width}%` }}
                            title="Rahu Kaal"
                          />
                        )}
                        <div className="timeline-dot" style={{ left: '35%' }} />
                      </>
                    )
                  })()}
                </div>
                {getRahuKaalPercent(panchanga.sunrise, panchanga.sunset, params.year, params.month, params.day) && (
                  <p className="timeline-rahu-label">
                    <span className="timeline-rahu-swatch" /> Rahu Kaal (inauspicious)
                  </p>
                )}
              </div>
              <span className="timeline-endpoint">
                <SunsetIcon />
                <span className="timeline-time">{panchanga.sunset ?? '—'}</span>
              </span>
            </div>

            {isProfileMode && taraBala && (
              <div className="panchang-profile-section">
                <h3>Tara Bala</h3>
                <p className="tara-summary">
                  Birth nakshatra: <strong>{taraBala.birth_nakshatra}</strong> · Today: <strong>{taraBala.todays_nakshatra}</strong>
                </p>
                <p className="tara-result">
                  <span className={`tara-category tara-${(taraBala.tara_category || '').toLowerCase()}`}>{taraBala.tara_name}</span> Tara ({taraBala.tara_number}/9) — {taraBala.tara_category}
                </p>
              </div>
            )}
            {isProfileMode && personality && (
              <div className="panchang-profile-section">
                <h3>Nakshatra Personality</h3>
                <p className="personality-nakshatra"><strong>{personality.nakshatra}</strong></p>
                {personality.ruling_planet && <p className="personality-detail">Ruling planet: {personality.ruling_planet}</p>}
                {personality.symbol && <p className="personality-detail">Symbol: {personality.symbol}</p>}
                {personality.deity && <p className="personality-detail">Deity: {personality.deity}</p>}
                {personality.keywords?.length > 0 && (
                  <p className="personality-keywords">{personality.keywords.join(' · ')}</p>
                )}
              </div>
            )}
            {!isProfileMode && (
              <p className="panchang-profile-hint">
                Switch to <strong>Profile</strong> in Settings and add birth details to see Tara Bala and Nakshatra Personality here.
              </p>
            )}
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
