import { useMemo, useState } from 'react'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import soilPayload from './data/soil-data.json'
import './App.css'
import type { MergedByTime, SoilPayload, SoilReading } from './types/soil'

const data = soilPayload as SoilPayload

const LOCATION_KEYS = ['huntsville', 'uncc'] as const

type LocationKey = (typeof LOCATION_KEYS)[number]

const LOCATION_LABEL: Record<LocationKey, string> = {
  huntsville: data.notes.locations[0],
  uncc: data.notes.locations[1],
}

const COLORS: Record<LocationKey, string> = {
  huntsville: '#2d6a4f',
  uncc: '#1d3557',
}

function mergeSeries(payload: SoilPayload): MergedByTime[] {
  const { huntsville, uncc } = payload.series
  const n = Math.min(huntsville.length, uncc.length)
  const out: MergedByTime[] = []
  for (let i = 0; i < n; i++) {
    const h = huntsville[i]
    const u = uncc[i]
    out.push({
      t: h.t,
      huntsvilleMoisture: h.moisture,
      unccMoisture: u.moisture,
      huntsvilleEc: h.ecMicroSiemens,
      unccEc: u.ecMicroSiemens,
      huntsvillePh: h.ph,
      unccPh: u.ph,
      huntsvilleTemp: h.tempC,
      unccTemp: u.tempC,
      huntsvilleN: h.nitrogenMgKg,
      unccN: u.nitrogenMgKg,
    })
  }
  return out
}

function lastReading(series: SoilReading[]) {
  return series[series.length - 1]
}

function StatCard({
  label,
  value,
  unit,
}: {
  label: string
  value: string
  unit?: string
}) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value">
        {value}
        {unit ? <span className="stat-unit">{unit}</span> : null}
      </div>
    </div>
  )
}

export default function App() {
  const merged = useMemo(() => mergeSeries(data), [])
  const [focus, setFocus] = useState<LocationKey | 'all'>('all')

  const hLast = lastReading(data.series.huntsville)
  const uLast = lastReading(data.series.uncc)

  const singleLocationChart = useMemo(() => {
    if (focus === 'all') return []
    return merged.map((row) => {
      switch (focus) {
        case 'huntsville':
          return {
            t: row.t,
            moisture: row.huntsvilleMoisture,
            ec: row.huntsvilleEc,
            ph: row.huntsvillePh,
            tempC: row.huntsvilleTemp,
            n: row.huntsvilleN,
          }
        case 'uncc':
          return {
            t: row.t,
            moisture: row.unccMoisture,
            ec: row.unccEc,
            ph: row.unccPh,
            tempC: row.unccTemp,
            n: row.unccN,
          }
      }
    })
  }, [focus, merged])

  const chartData: Array<Record<string, number>> =
    focus === 'all' ? merged : singleLocationChart

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>Soil sensor readings</h1>
          <p className="subtitle">
            Moisture, pH, EC (µS/cm), temperature (°C), nitrogen (mg/kg) — from{' '}
            <a href={data.source} target="_blank" rel="noreferrer">
              Soil Testing spreadsheet
            </a>
            .
          </p>
        </div>
      </header>

      <section className="toolbar">
        <span className="toolbar-label">Chart focus</span>
        <div className="segmented">
          <button
            type="button"
            className={focus === 'all' ? 'active' : ''}
            onClick={() => setFocus('all')}
          >
            Both locations
          </button>
          {LOCATION_KEYS.map((key) => (
            <button
              key={key}
              type="button"
              className={focus === key ? 'active' : ''}
              onClick={() => setFocus(key)}
            >
              {LOCATION_LABEL[key]}
            </button>
          ))}
        </div>
      </section>

      <section className="stats-grid" aria-label="Latest readings by location">
        <h2 className="section-title">Latest sample (end of run)</h2>
        <div className="location-blocks">
          <div className="location-block">
            <h3>{LOCATION_LABEL.huntsville}</h3>
            <div className="stat-row">
              <StatCard label="Moisture" value={hLast.moisture.toFixed(3)} />
              <StatCard label="pH" value={hLast.ph.toFixed(1)} />
              <StatCard
                label="EC"
                value={String(Math.round(hLast.ecMicroSiemens))}
                unit=" µS/cm"
              />
              <StatCard
                label="Temp"
                value={hLast.tempC.toFixed(1)}
                unit=" °C"
              />
              <StatCard
                label="N"
                value={String(Math.round(hLast.nitrogenMgKg))}
                unit=" mg/kg"
              />
            </div>
          </div>
          <div className="location-block">
            <h3>{LOCATION_LABEL.uncc}</h3>
            <div className="stat-row">
              <StatCard label="Moisture" value={uLast.moisture.toFixed(3)} />
              <StatCard label="pH" value={uLast.ph.toFixed(1)} />
              <StatCard
                label="EC"
                value={String(Math.round(uLast.ecMicroSiemens))}
                unit=" µS/cm"
              />
              <StatCard
                label="Temp"
                value={uLast.tempC.toFixed(1)}
                unit=" °C"
              />
              <StatCard
                label="N"
                value={String(Math.round(uLast.nitrogenMgKg))}
                unit=" mg/kg"
              />
            </div>
          </div>
        </div>
      </section>

      <section className="charts">
        <h2 className="section-title">Time series (t = sample index)</h2>

        <figure className="chart-wrap">
          <figcaption>Moisture</figcaption>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={focus === 'all' ? merged : chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
              <XAxis dataKey="t" tick={{ fontSize: 12 }} />
              <YAxis domain={['auto', 'auto']} tick={{ fontSize: 12 }} />
              <Tooltip />
              {focus === 'all' ? (
                <Legend />
              ) : null}
              {focus === 'all' ? (
                <>
                  <Line
                    type="monotone"
                    dataKey="huntsvilleMoisture"
                    name={LOCATION_LABEL.huntsville}
                    stroke={COLORS.huntsville}
                    dot={false}
                    strokeWidth={2}
                  />
                  <Line
                    type="monotone"
                    dataKey="unccMoisture"
                    name={LOCATION_LABEL.uncc}
                    stroke={COLORS.uncc}
                    dot={false}
                    strokeWidth={2}
                  />
                </>
              ) : (
                <Line
                  type="monotone"
                  dataKey="moisture"
                  name="Moisture"
                  stroke={COLORS[focus]}
                  dot={false}
                  strokeWidth={2}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        </figure>

        <figure className="chart-wrap">
          <figcaption>Electrical conductivity (EC)</figcaption>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={focus === 'all' ? merged : chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
              <XAxis dataKey="t" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              {focus === 'all' ? <Legend /> : null}
              {focus === 'all' ? (
                <>
                  <Line
                    type="monotone"
                    dataKey="huntsvilleEc"
                    name={LOCATION_LABEL.huntsville}
                    stroke={COLORS.huntsville}
                    dot={false}
                    strokeWidth={2}
                  />
                  <Line
                    type="monotone"
                    dataKey="unccEc"
                    name={LOCATION_LABEL.uncc}
                    stroke={COLORS.uncc}
                    dot={false}
                    strokeWidth={2}
                  />
                </>
              ) : (
                <Line
                  type="monotone"
                  dataKey="ec"
                  name="EC µS/cm"
                  stroke={COLORS[focus]}
                  dot={false}
                  strokeWidth={2}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        </figure>

        <figure className="chart-wrap">
          <figcaption>pH</figcaption>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={focus === 'all' ? merged : chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
              <XAxis dataKey="t" tick={{ fontSize: 12 }} />
              <YAxis domain={[4, 8]} tick={{ fontSize: 12 }} />
              <Tooltip />
              {focus === 'all' ? <Legend /> : null}
              {focus === 'all' ? (
                <>
                  <Line
                    type="monotone"
                    dataKey="huntsvillePh"
                    name={LOCATION_LABEL.huntsville}
                    stroke={COLORS.huntsville}
                    dot={false}
                    strokeWidth={2}
                  />
                  <Line
                    type="monotone"
                    dataKey="unccPh"
                    name={LOCATION_LABEL.uncc}
                    stroke={COLORS.uncc}
                    dot={false}
                    strokeWidth={2}
                  />
                </>
              ) : (
                <Line
                  type="monotone"
                  dataKey="ph"
                  name="pH"
                  stroke={COLORS[focus]}
                  dot={false}
                  strokeWidth={2}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        </figure>

        <figure className="chart-wrap">
          <figcaption>Temperature (°C)</figcaption>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={focus === 'all' ? merged : chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
              <XAxis dataKey="t" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              {focus === 'all' ? <Legend /> : null}
              {focus === 'all' ? (
                <>
                  <Line
                    type="monotone"
                    dataKey="huntsvilleTemp"
                    name={LOCATION_LABEL.huntsville}
                    stroke={COLORS.huntsville}
                    dot={false}
                    strokeWidth={2}
                  />
                  <Line
                    type="monotone"
                    dataKey="unccTemp"
                    name={LOCATION_LABEL.uncc}
                    stroke={COLORS.uncc}
                    dot={false}
                    strokeWidth={2}
                  />
                </>
              ) : (
                <Line
                  type="monotone"
                  dataKey="tempC"
                  name="°C"
                  stroke={COLORS[focus]}
                  dot={false}
                  strokeWidth={2}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        </figure>

        <figure className="chart-wrap">
          <figcaption>Nitrogen (mg/kg)</figcaption>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={focus === 'all' ? merged : chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
              <XAxis dataKey="t" tick={{ fontSize: 12 }} />
              <YAxis domain={['auto', 'auto']} tick={{ fontSize: 12 }} />
              <Tooltip />
              {focus === 'all' ? <Legend /> : null}
              {focus === 'all' ? (
                <>
                  <Line
                    type="monotone"
                    dataKey="huntsvilleN"
                    name={LOCATION_LABEL.huntsville}
                    stroke={COLORS.huntsville}
                    dot={false}
                    strokeWidth={2}
                  />
                  <Line
                    type="monotone"
                    dataKey="unccN"
                    name={LOCATION_LABEL.uncc}
                    stroke={COLORS.uncc}
                    dot={false}
                    strokeWidth={2}
                  />
                </>
              ) : (
                <Line
                  type="monotone"
                  dataKey="n"
                  name="N (mg/kg)"
                  stroke={COLORS[focus]}
                  dot={false}
                  strokeWidth={2}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        </figure>
      </section>

      <footer className="footer">
        <p>
          {merged.length} aligned samples per location — regenerate{' '}
          <code>src/data/soil-data.json</code> with{' '}
          <code>python scripts/csv-to-json.py</code> after exporting CSV to{' '}
          <code>scripts/sheet.csv</code>.
        </p>
      </footer>
    </div>
  )
}
