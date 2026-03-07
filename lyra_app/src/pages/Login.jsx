import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import './Login.css'

export default function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    try {
      if (email) localStorage.setItem('lyra_user_email', email)
      localStorage.setItem('lyra_logged_in', '1')
    } catch (_) {}
    navigate('/personalization')
  }

  return (
    <div className="login-page">
      <header className="login-header">
        <button
          type="button"
          className="back-btn"
          onClick={() => navigate('/welcome')}
          aria-label="Go back"
        >
          ←
        </button>
        <div className="login-logo" aria-hidden>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
          </svg>
        </div>
        <h1>Log in</h1>
      </header>

      <form onSubmit={handleSubmit} className="login-form">
        <div className="form-group">
          <label htmlFor="login-email">Email</label>
          <input
            id="login-email"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />
        </div>
        <div className="form-group">
          <label htmlFor="login-password">Password</label>
          <input
            id="login-password"
            type="password"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </div>
        <button type="submit" className="btn btn-primary btn-full">
          Log in
        </button>
        <p className="login-signup">
          Don&apos;t have an account?{' '}
          <button type="button" className="link" onClick={() => navigate('/register')}>
            Create one
          </button>
        </p>
      </form>

      <div className="login-privacy">
        Your data is used only for personalization and stored securely.
      </div>
    </div>
  )
}
