import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { toDDMMMYYYY, storedToInputValue } from '../utils/date'
import './BirthDetails.css'

const DEFAULT_POB = { lat: 28.6139, lon: 77.209, tz: 5.5, name: 'Delhi, India' }

function getStoredProfile() {
  if (typeof localStorage === 'undefined') return null
  const date = localStorage.getItem('lyra_birth_date')
  const time = localStorage.getItem('lyra_birth_time')
  const place = localStorage.getItem('lyra_birth_place')
  const lat = localStorage.getItem('lyra_pob_lat')
  const lon = localStorage.getItem('lyra_pob_lon')
  const tz = localStorage.getItem('lyra_pob_tz')
  if (!date) return null
  return { date, time: time || '10:30', place: place || '', lat, lon, tz }
}

export default function BirthDetails() {
  const navigate = useNavigate()
  const stored = getStoredProfile()
  const [date, setDate] = useState(stored ? storedToInputValue(stored.date) || '1990-01-15' : '1990-01-15')
  const [time, setTime] = useState(stored?.time ?? '10:30')
  const [place, setPlace] = useState('')
  const [pobLat, setPobLat] = useState(stored?.lat ?? String(DEFAULT_POB.lat))
  const [pobLon, setPobLon] = useState(stored?.lon ?? String(DEFAULT_POB.lon))
  const [pobTz, setPobTz] = useState(stored?.tz ?? String(DEFAULT_POB.tz))
  const [geocodeLoading, setGeocodeLoading] = useState(false)
  const [geocodeError, setGeocodeError] = useState(null)
  const [hasLookedUp, setHasLookedUp] = useState(false)

  const handleLookupCity = async () => {
    const city = (place || '').trim()
    if (!city) {
      setGeocodeError('Enter a city name first.')
      return
    }
    setGeocodeError(null)
    setGeocodeLoading(true)
    try {
      const res = await api.geocode(city)
      if (res && typeof res.lat === 'number' && typeof res.lon === 'number') {
        setPobLat(String(res.lat))
        setPobLon(String(res.lon))
        if (typeof res.tz === 'number') setPobTz(String(res.tz))
        if (res.name) setPlace(res.name)
        setHasLookedUp(true)
      } else {
        setGeocodeError('Could not resolve coordinates.')
      }
    } catch (e) {
      setGeocodeError(e.message || 'Lookup failed.')
    } finally {
      setGeocodeLoading(false)
    }
  }

  const handleSave = (e) => {
    e.preventDefault()
    try {
      const lat = parseFloat(pobLat)
      const lon = parseFloat(pobLon)
      const tz = parseFloat(pobTz)
      const dateDisplay = toDDMMMYYYY(date)
      localStorage.setItem('lyra_experience_mode', 'personal')
      localStorage.setItem('lyra_birth_date', dateDisplay || toDDMMMYYYY('1990-01-15'))
      localStorage.setItem('lyra_birth_time', time)
      localStorage.setItem('lyra_birth_place', place || DEFAULT_POB.name)
      localStorage.setItem('lyra_pob_lat', isNaN(lat) ? String(DEFAULT_POB.lat) : String(lat))
      localStorage.setItem('lyra_pob_lon', isNaN(lon) ? String(DEFAULT_POB.lon) : String(lon))
      localStorage.setItem('lyra_pob_tz', isNaN(tz) ? String(DEFAULT_POB.tz) : String(tz))
    } catch (_) {}
    navigate('/app/home')
  }

  const hasCoords = pobLat && pobLon

  return (
    <div className="birth-details">
      <header className="birth-header">
        <button
          type="button"
          className="back-btn"
          onClick={() => navigate(-1)}
          aria-label="Go back"
        >
          ←
        </button>
        <h1>Birth Details</h1>
      </header>

      <p className="birth-subtitle">
        Enter your birth information for personalized cosmic insights. Date is stored as DD-MMM-YYYY.
      </p>

      <form onSubmit={handleSave} className="birth-form">
        <div className="form-group">
          <label htmlFor="birth-date">Birth Date</label>
          <input
            id="birth-date"
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
          <span className="form-hint">Stored as: {toDDMMMYYYY(date) || '—'}</span>
        </div>
        <div className="form-group">
          <label htmlFor="birth-time">Birth Time (optional)</label>
          <input
            id="birth-time"
            type="time"
            value={time}
            onChange={(e) => setTime(e.target.value)}
          />
        </div>
        <div className="form-group form-group-city">
          <label htmlFor="birth-place">Birth place (city)</label>
          <div className="city-input-wrap">
            <input
              id="birth-place"
              type="text"
              className="city-input"
              placeholder="e.g. Mumbai, Bangalore, Delhi"
              value={place ?? ''}
              onChange={(e) => {
                setPlace(e.target.value)
                if (geocodeError) setGeocodeError(null)
              }}
              aria-label="City name"
              autoComplete="address-level2"
            />
            <button
              type="button"
              className="city-check-btn"
              onClick={handleLookupCity}
              disabled={geocodeLoading}
              aria-label="Look up coordinates"
              title="Look up coordinates"
            >
              {geocodeLoading ? (
                <span className="city-check-spinner">…</span>
              ) : (
                <span className="city-check-icon" aria-hidden>✓</span>
              )}
            </button>
          </div>
          {geocodeError && <p className="form-error">{geocodeError}</p>}
          <label className="coordinates-label" htmlFor="coordinates-display">
            Coordinates
          </label>
          <div
            id="coordinates-display"
            className={`coordinates-box ${hasLookedUp ? 'coordinates-box--filled' : 'coordinates-box--blocked'}`}
            aria-live="polite"
            role="status"
          >
            {hasLookedUp ? (
              <>Coordinates: {Number(pobLat).toFixed(2)}, {Number(pobLon).toFixed(2)} (TZ {pobTz})</>
            ) : (
              <span className="coordinates-placeholder">Enter city and click ✓ to get coordinates</span>
            )}
          </div>
        </div>
        <button type="submit" className="btn btn-primary btn-full">
          Save & Continue
        </button>
      </form>
    </div>
  )
}
