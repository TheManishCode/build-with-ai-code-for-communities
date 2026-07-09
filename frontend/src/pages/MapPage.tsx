import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Popup } from 'react-leaflet'
import { Eye, EyeOff } from 'lucide-react'
import { api } from '../api/client'
import { PageWrapper, PageHeader } from '../components/ui/PageWrapper'
import { LoadingState, ErrorState } from '../components/ui/StateDisplays'
import 'leaflet/dist/leaflet.css'

const COLOR_HIGH = '#e15c5c'
const COLOR_MEDIUM = '#c98500'
const COLOR_LOW = '#2fb344'
const COLOR_SILENT = '#d5548a'

function scoreColor(score: number | null): string {
  if (score == null) return '#5c5c63'
  if (score >= 0.7) return COLOR_HIGH
  if (score >= 0.4) return COLOR_MEDIUM
  return COLOR_LOW
}

export function MapPage() {
  const [showDivergence, setShowDivergence] = useState(false)
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['boundary'],
    queryFn: api.boundary,
  })

  if (isLoading) return <PageWrapper><LoadingState message="Loading constituency map…" /></PageWrapper>
  if (error) return <PageWrapper><ErrorState message={(error as Error).message} onRetry={() => refetch()} /></PageWrapper>
  if (!data) return null

  return (
    <PageWrapper>
      <PageHeader
        title="Constituency Map"
        subtitle="Geographic view of development priorities across Bagalkot"
        actions={
          <button
            className={`btn btn-sm ${showDivergence ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setShowDivergence(!showDivergence)}
          >
            {showDivergence ? <EyeOff size={14} /> : <Eye size={14} />}
            {showDivergence ? 'Hide' : 'Show'} silent need
          </button>
        }
      />

      <div className="card card-flush">
        <MapContainer
          center={[15.85, 75.7]}
          zoom={9}
          style={{ height: 560, width: '100%' }}
          scrollWheelZoom={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />

          {/* Constituency boundary */}
          {data.constituency && (
            <GeoJSON
              data={data.constituency as GeoJSON.GeoJsonObject}
              style={() => ({
                color: 'rgba(226, 165, 61, 0.45)',
                weight: 2,
                fillColor: 'rgba(226, 165, 61, 0.04)',
                fillOpacity: 1,
              })}
            />
          )}

          {/* Village markers */}
          {data.villages.features.map((feature, i) => {
            const coords = (feature.geometry as GeoJSON.Point).coordinates
            if (!coords || coords.length < 2) return null
            const props = feature.properties || {}
            const score = props.composite_score as number | null
            const isSilent = props.silent_need === true
            const color = showDivergence && isSilent ? COLOR_SILENT : scoreColor(score)
            const radius = showDivergence && isSilent ? 7 : 5

            return (
              <CircleMarker
                key={i}
                center={[coords[1], coords[0]]}
                radius={radius}
                pathOptions={{
                  fillColor: color,
                  color: 'rgba(10,10,11,0.5)',
                  weight: 1,
                  fillOpacity: 0.9,
                }}
              >
                <Popup>
                  <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, lineHeight: 1.5 }}>
                    <strong>{props.village_name || 'Village'}</strong>
                    {score != null && <div>Score: {Math.round(score * 100)}%</div>}
                    {props.population != null && <div>Pop: {Number(props.population).toLocaleString('en-IN')}</div>}
                    {isSilent && <div style={{ color: COLOR_SILENT, fontWeight: 600 }}>Silent need</div>}
                  </div>
                </Popup>
              </CircleMarker>
            )
          })}
        </MapContainer>
      </div>

      {/* Legend */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-5)',
        marginTop: 'var(--space-4)',
        fontSize: 'var(--text-xs)',
        color: 'var(--color-text-tertiary)',
        flexWrap: 'wrap',
      }}>
        <span style={{ fontWeight: 600, color: 'var(--color-text-secondary)' }}>Legend:</span>
        {[
          { color: COLOR_HIGH, label: 'High priority (≥70%)' },
          { color: COLOR_MEDIUM, label: 'Medium (40–70%)' },
          { color: COLOR_LOW, label: 'Lower (<40%)' },
          ...(showDivergence ? [{ color: COLOR_SILENT, label: 'Silent need' }] : []),
        ].map((item) => (
          <span key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: item.color, display: 'inline-block' }} />
            {item.label}
          </span>
        ))}
      </div>

      <p style={{ marginTop: 'var(--space-3)', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
        {data.village_coverage_note}
      </p>
    </PageWrapper>
  )
}
