import { useState } from 'react'
import './Planner.css'

const EVENT_TYPES = [
  { id: 'marriage', label: 'Marriage', icon: '💒' },
  { id: 'travel', label: 'Travel', icon: '✈️' },
  { id: 'investment', label: 'Investment', icon: '📈' },
  { id: 'business', label: 'Business Start', icon: '🏢' },
  { id: 'property', label: 'Property', icon: '🏠' },
]

const RANGES = [
  { value: 30, label: '30 Days' },
  { value: 60, label: '60 Days' },
  { value: 90, label: '90 Days' },
]

export default function Planner() {
  const [category, setCategory] = useState(null)
  const [range, setRange] = useState(30)

  return (
    <div className="planner planner-figma">
      <p className="planner-hero">
        Find the most auspicious dates for your important events.
      </p>

      <section className="planner-section">
        <h2 className="planner-section-title">Select Event Type</h2>
        <div className="planner-event-grid">
          {EVENT_TYPES.map((item) => (
            <button
              key={item.id}
              type="button"
              className="planner-event-card"
              onClick={() => setCategory(category === item.id ? null : item.id)}
            >
              <span className="planner-event-icon">{item.icon}</span>
              <span className="planner-event-label">{item.label}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="planner-section">
        <h2 className="planner-section-title">Look Ahead</h2>
        <div className="planner-lookahead">
          {RANGES.map((r) => (
            <button
              key={r.value}
              type="button"
              className={`planner-lookahead-btn ${range === r.value ? 'active' : ''}`}
              onClick={() => setRange(r.value)}
            >
              {r.label}
            </button>
          ))}
        </div>
      </section>
    </div>
  )
}
