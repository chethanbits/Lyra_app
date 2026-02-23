import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'motion/react'
import './Onboarding.css'

/* Exact transition from Lyra Mobile App Design reference: Onboarding.tsx
   – AnimatePresence mode="wait", slide: initial x 100, exit x -100, duration 0.3 easeInOut
   – Icon: scale 0.5 opacity 0 → 1, delay 0.2, duration 0.5
   – Title: opacity 0 y 20 → 1 0, delay 0.3, duration 0.5
   – Description: delay 0.4, duration 0.5 */

const SLIDES = [
  {
    icon: 'chart',
    iconBg: 'emerald',
    title: 'Your Alignment Score',
    text: "See at a glance how favorable each day is. 70+ is great, 40-70 is neutral, below 40 needs caution.",
  },
  {
    icon: 'star',
    iconBg: 'midnight',
    title: 'Align Your Day',
    text: "Understand your day through cosmic rhythm. No clutter, no superstition—just clear insights.",
  },
  {
    icon: 'calendar',
    iconBg: 'amber',
    title: 'Plan Ahead',
    text: "Find the best dates for important events—marriages, travel, business starts, and more.",
  },
  {
    icon: 'star',
    iconBg: 'purple',
    title: 'Personal or General',
    text: "Choose location-based insights or unlock deeply personalized guidance with your birth details.",
  },
]

export default function Onboarding() {
  const [current, setCurrent] = useState(0)
  const navigate = useNavigate()
  const isLast = current === SLIDES.length - 1

  const handleNext = () => {
    if (isLast) {
      navigate('/welcome')
    } else {
      setCurrent((i) => i + 1)
    }
  }

  const handleSkip = () => {
    navigate('/welcome')
  }

  return (
    <div className="onboarding">
      <button
        type="button"
        className="onboarding-skip"
        onClick={handleSkip}
      >
        Skip
      </button>

      <div className="onboarding-slide-wrap">
        <AnimatePresence mode="wait">
          <motion.div
            key={current}
            initial={{ opacity: 0, x: 100 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -100 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="onboarding-slide"
          >
            <motion.div
              initial={{ scale: 0.5, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.2, duration: 0.5 }}
              className={`onboarding-icon ${SLIDES[current].iconBg}`}
            >
              {SLIDES[current].icon === 'chart' && (
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 3v18h18" />
                  <path d="M7 16l4-6 4 2 4-6" />
                </svg>
              )}
              {SLIDES[current].icon === 'star' && (
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                </svg>
              )}
              {SLIDES[current].icon === 'calendar' && (
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                  <line x1="16" y1="2" x2="16" y2="6" />
                  <line x1="8" y1="2" x2="8" y2="6" />
                  <line x1="3" y1="10" x2="21" y2="10" />
                </svg>
              )}
            </motion.div>
            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.5 }}
              className="onboarding-title"
            >
              {SLIDES[current].title}
            </motion.h2>
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.5 }}
              className="onboarding-text"
            >
              {SLIDES[current].text}
            </motion.p>
          </motion.div>
        </AnimatePresence>
      </div>

      <div className="onboarding-dots">
        {SLIDES.map((_, i) => (
          <span
            key={i}
            className={`dot ${i === current ? 'active' : ''}`}
            aria-hidden
          />
        ))}
      </div>

      <button
        type="button"
        className="onboarding-btn"
        onClick={handleNext}
      >
        {isLast ? 'Get Started' : 'Next'}
      </button>
    </div>
  )
}
