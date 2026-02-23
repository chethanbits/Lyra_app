import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import './Registration.css'

export default function Registration() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    // Placeholder: in production would call auth API
    navigate('/personalization')
  }

  return (
    <div className="registration">
      <header className="reg-header">
        <button
          type="button"
          className="back-btn"
          onClick={() => navigate(-1)}
          aria-label="Go back"
        >
          ←
        </button>
        <div className="reg-logo" aria-hidden>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
          </svg>
        </div>
        <h1>Create Your Lyra</h1>
      </header>

      <form onSubmit={handleSubmit} className="reg-form">
        <div className="form-group">
          <label htmlFor="reg-email">Email</label>
          <input
            id="reg-email"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />
        </div>
        <div className="form-group">
          <label htmlFor="reg-password">Password</label>
          <input
            id="reg-password"
            type="password"
            placeholder="Create a secure password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
          />
        </div>
        <button type="submit" className="btn btn-primary btn-full">
          Continue
        </button>
        <p className="reg-login">
          Already have an account?{' '}
          <button type="button" className="link" onClick={() => navigate('/welcome')}>
            Log in
          </button>
        </p>
      </form>

      <div className="reg-privacy">
        Your data is used only for personalization and stored securely.
      </div>
    </div>
  )
}
