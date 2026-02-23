import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import './BirthDetails.css'

export default function BirthDetails() {
  const navigate = useNavigate()
  const [date, setDate] = useState('1990-01-15')
  const [time, setTime] = useState('10:30')
  const [place, setPlace] = useState('')

  const handleSave = (e) => {
    e.preventDefault()
    navigate('/app/home')
  }

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
      Enter your birth information for personalized cosmic insights.
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
        <div className="form-group">
          <label htmlFor="birth-place">Birth Place</label>
          <input
            id="birth-place"
            type="text"
            placeholder="City, Country"
            value={place}
            onChange={(e) => setPlace(e.target.value)}
          />
        </div>
        <button type="submit" className="btn btn-primary btn-full">
          Save & Continue
        </button>
      </form>
    </div>
  )
}
