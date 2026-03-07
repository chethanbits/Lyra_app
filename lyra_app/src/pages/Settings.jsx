import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import './Settings.css'

export default function Settings() {
  const [theme, setTheme] = useState('light')
  const navigate = useNavigate()

  const experienceMode = typeof localStorage !== 'undefined' ? localStorage.getItem('lyra_experience_mode') : null
  const hasProfile = typeof localStorage !== 'undefined' && !!localStorage.getItem('lyra_birth_date')

  const setExperienceMode = (mode) => {
    try {
      localStorage.setItem('lyra_experience_mode', mode)
      if (mode === 'general') {
        localStorage.removeItem('lyra_birth_date')
        localStorage.removeItem('lyra_birth_time')
        localStorage.removeItem('lyra_birth_place')
        localStorage.removeItem('lyra_pob_lat')
        localStorage.removeItem('lyra_pob_lon')
        localStorage.removeItem('lyra_pob_tz')
      }
      if (mode === 'personal' && !hasProfile) {
        navigate('/birth-details')
      } else {
        navigate('/app/home')
      }
    } catch (_) {}
  }

  const toggleTheme = () => {
    const next = theme === 'light' ? 'dark' : 'light'
    setTheme(next)
    if (next === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark')
    } else {
      document.documentElement.removeAttribute('data-theme')
    }
  }

  return (
    <div className="settings">
      <header className="settings-header">
        <h1>Settings</h1>
      </header>

      <section className="settings-section">
        <h2>Profile / Experience</h2>
        <p className="settings-desc">Switch between Guest (location-only) and Profile (birth-details) mode.</p>
        <div className="setting-row setting-row-toggle">
          <span>Mode</span>
          <div className="mode-toggle-group">
            <button
              type="button"
              className={`mode-toggle-btn ${experienceMode === 'general' ? 'active' : ''}`}
              onClick={() => setExperienceMode('general')}
            >
              Guest
            </button>
            <button
              type="button"
              className={`mode-toggle-btn ${experienceMode === 'personal' ? 'active' : ''}`}
              onClick={() => setExperienceMode('personal')}
            >
              Profile
            </button>
          </div>
        </div>
        {hasProfile && (
          <div className="setting-row">
            <button
              type="button"
              className="link-btn"
              onClick={() => navigate('/birth-details')}
            >
              Edit birth details (DOB, TOB, place of birth) →
            </button>
          </div>
        )}
      </section>

      <section className="settings-section">
        <h2>Appearance</h2>
        <div className="setting-row">
          <span>Theme</span>
          <button
            type="button"
            className="theme-toggle"
            onClick={toggleTheme}
            aria-pressed={theme === 'dark'}
          >
            {theme === 'light' ? 'Light' : 'Dark'}
          </button>
        </div>
      </section>

      <section className="settings-section">
        <h2>Location</h2>
        <div className="setting-row">
          <span>Default location</span>
          <span className="muted">Delhi, India</span>
        </div>
      </section>

      <section className="settings-section">
        <h2>Calculation</h2>
        <div className="setting-row">
          <span>Ayanamsa</span>
          <span className="muted">Lahiri</span>
        </div>
        <div className="setting-row">
          <span>Month type</span>
          <span className="muted">Amanta</span>
        </div>
      </section>

      <section className="settings-section">
        <h2>Notifications</h2>
        <div className="setting-row">
          <span>Favorable window alerts</span>
          <span className="muted">Off</span>
        </div>
      </section>

      <p className="settings-footer">
        Lyra uses the PyJHora wrapper for all calculations. Data is processed locally when the API runs on your device or server.
      </p>
    </div>
  )
}
