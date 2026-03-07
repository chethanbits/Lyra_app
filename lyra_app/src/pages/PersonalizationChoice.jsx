import { useNavigate } from 'react-router-dom'
import './PersonalizationChoice.css'

export default function PersonalizationChoice() {
  const navigate = useNavigate()
  const isLoggedIn = typeof localStorage !== 'undefined' && localStorage.getItem('lyra_logged_in') === '1'

  const handleMode = (mode) => {
    try {
      localStorage.setItem('lyra_experience_mode', mode)
      if (mode === 'general') {
        localStorage.removeItem('lyra_birth_date')
        localStorage.removeItem('lyra_birth_time')
        localStorage.removeItem('lyra_birth_place')
      }
    } catch (_) {}
    if (mode === 'personal') {
      navigate('/birth-details')
    } else {
      navigate('/app/home')
    }
  }

  return (
    <div className="personalization">
      <header className="personalization-header">
        <button
          type="button"
          className="back-btn"
          onClick={() => navigate(-1)}
          aria-label="Go back"
        >
          ←
        </button>
        <h1>Choose Your Experience</h1>
        {isLoggedIn ? (
          <span className="account-badge" title="Account" aria-label="Logged in">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </span>
        ) : (
          <span className="header-spacer" />
        )}
      </header>

      <p className="personalization-subtitle">
        Select how you'd like Lyra to personalize your cosmic insights.
      </p>

      <div className="mode-cards">
        <button
          type="button"
          className="mode-card"
          onClick={() => handleMode('general')}
        >
          <div className="mode-icon amber">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" />
              <circle cx="12" cy="10" r="3" />
            </svg>
          </div>
          <div className="mode-content">
            <h3>General Mode</h3>
            <p>
              Cosmic insights based on your location. Perfect for exploring
              auspicious times without personal details.
            </p>
          </div>
        </button>

        <button
          type="button"
          className="mode-card"
          onClick={() => handleMode('personal')}
        >
          <div className="mode-icon emerald">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
            </svg>
          </div>
          <div className="mode-content">
            <h3>Personal Mode</h3>
            <p>
              Align insights to your birth star for deeply personalized
              cosmic guidance tailored to your unique chart.
            </p>
          </div>
        </button>
      </div>

      <p className="personalization-footer">
        You can change this anytime in Settings.
      </p>
    </div>
  )
}
