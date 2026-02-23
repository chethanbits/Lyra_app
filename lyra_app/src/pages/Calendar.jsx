import './Calendar.css'

export default function Calendar() {
  const year = 2026
  const month = 2
  const daysInMonth = new Date(year, month, 0).getDate()
  const firstDay = new Date(year, month - 1, 1).getDay()
  const blanks = Array(firstDay).fill(null)
  const days = Array.from({ length: daysInMonth }, (_, i) => i + 1)

  return (
    <div className="calendar">
      <header className="calendar-header">
        <h1>Calendar</h1>
        <p>February 2026</p>
      </header>

      <div className="calendar-legend">
        <span className="dot favorable" /> Favorable
        <span className="dot neutral" /> Neutral
        <span className="dot caution" /> Caution
      </div>

      <div className="calendar-grid">
        {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d) => (
          <div key={d} className="weekday">{d}</div>
        ))}
        {blanks.map((_, i) => (
          <div key={`b-${i}`} className="day empty" />
        ))}
        {days.map((d) => (
          <div key={d} className="day">
            {d}
          </div>
        ))}
      </div>

      <p className="calendar-hint">Color-coded days and heatmap use Panchang data from the API.</p>
    </div>
  )
}
