import { useNavigate } from 'react-router-dom'
import { motion } from 'motion/react'
import './Welcome.css'

/* Exact transition from Lyra Mobile App Design reference: Welcome.tsx
   – Logo: spring scale + rotate
   – Title, description, buttons: staggered fade-up (opacity + y) */
export default function Welcome() {
  const navigate = useNavigate()

  return (
    <div className="welcome">
      <div className="welcome-bg" aria-hidden />
      <div className="welcome-content">
        {/* Logo/Icon – same as reference: spring scale 0 → 1, rotate -180 → 0 */}
        <motion.div
          initial={{ scale: 0, rotate: -180 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ type: 'spring', stiffness: 200, damping: 20 }}
          className="welcome-logo-wrap"
        >
          <div className="welcome-logo" aria-hidden>
            {/* Figma: white outline four-pointed star + smaller plus in top-right quadrant */}
            <svg className="welcome-logo-sparkle" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="2" x2="12" y2="22" />
              <line x1="2" y1="12" x2="22" y2="12" />
              <line x1="6" y1="6" x2="18" y2="18" />
              <line x1="18" y1="6" x2="6" y2="18" />
              <g transform="translate(15, 5)">
                <line x1="1.5" y1="0" x2="1.5" y2="3" />
                <line x1="0" y1="1.5" x2="3" y2="1.5" />
              </g>
            </svg>
          </div>
        </motion.div>

        {/* App name – reference: opacity 0, y 20 → 1, 0, delay 0.3 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="welcome-title-wrap"
        >
          <h1 className="welcome-title">Lyra</h1>
          <p className="welcome-tagline">Align Your Day</p>
        </motion.div>

        {/* Description – reference: delay 0.5 */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="welcome-desc"
        >
          Understand your day through cosmic rhythm.
        </motion.p>

        {/* Buttons – reference: delay 0.7, whileHover/whileTap on buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="welcome-actions"
        >
          <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => {
                try { localStorage.removeItem('lyra_logged_in') } catch (_) {}
                navigate('/personalization')
              }}
            >
              Explore Lyra (Guest Mode)
            </button>
          </motion.div>
          <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => navigate('/register')}
            >
              Create Your Lyra
            </button>
          </motion.div>
        </motion.div>
      </div>
    </div>
  )
}
