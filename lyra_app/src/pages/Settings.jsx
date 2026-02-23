import { useState } from 'react'
import './Settings.css'

export default function Settings() {
  const [theme, setTheme] = useState('light')

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
