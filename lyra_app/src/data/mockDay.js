/**
 * Mock day/panchang data for UI demo when API is unavailable.
 * Same shape as prodbackend /day response.
 */
export function getMockDayResult(dateStr = null) {
  const d = dateStr ? new Date(dateStr) : new Date()
  const month = d.getMonth() + 1
  const day = d.getDate()
  const year = d.getFullYear()
  const pad = (n) => String(n).padStart(2, '0')
  const date = dateStr || `${year}-${pad(month)}-${pad(day)}`

  return {
    date,
    place: { lat: 28.6139, lon: 77.209, tz: 5.5, name: 'Delhi, India' },
    anchor: 'SUNRISE',
    panchanga: {
      sunrise: '07:12',
      sunset: '18:05',
      tithi: { name: 'Shukla Paksha 7', index: 7, ends_at: '14:30' },
      nakshatra: { name: 'Pushya', index: 8, ends_at: '18:45' },
      yoga: { name: 'Siddha', index: 12, ends_at: '09:15' },
      karana: { name: 'Bava', index: 1, ends_at: '08:22' },
      vaara: 'Saturday',
    },
    score: {
      alignment_score: 78,
      band: 'POSITIVE',
      breakdown: [],
      summary: [
        'Good day for starting new tasks and spiritual practices.',
        'Rahu Kaal 10:30–12:00 — avoid important decisions then.',
      ],
    },
  }
}

/** Mock for getRange (minimal shape for calendar/range). */
export function getMockRangeResult(start, end) {
  const out = []
  const startD = new Date(start)
  const endD = new Date(end)
  for (let d = new Date(startD); d <= endD; d.setDate(d.getDate() + 1)) {
    const date = d.toISOString().slice(0, 10)
    const mock = getMockDayResult(date)
    out.push({ ...mock, date })
  }
  return out
}

/** Mock heatmap (date, score, band, tithi_index, nakshatra_index). */
export function getMockHeatmapResult(start, end) {
  const out = []
  const startD = new Date(start)
  const endD = new Date(end)
  for (let d = new Date(startD); d <= endD; d.setDate(d.getDate() + 1)) {
    out.push({
      date: d.toISOString().slice(0, 10),
      score: 65 + Math.floor(Math.random() * 30),
      band: 'POSITIVE',
      tithi_index: 7,
      nakshatra_index: 8,
    })
  }
  return out
}
