import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import './Splash.css'

/**
 * Lyra splash screen. Shows for 2 seconds then navigates to onboarding.
 */
export default function Splash() {
  const navigate = useNavigate()

  useEffect(() => {
    const t = setTimeout(() => navigate('/onboarding'), 2000)
    return () => clearTimeout(t)
  }, [navigate])

  return (
    <div className="splash" aria-hidden="true">
      <img
        src="/images/Lyra_Splash_Screen.png"
        alt="Lyra"
        className="splash-img"
      />
    </div>
  )
}
