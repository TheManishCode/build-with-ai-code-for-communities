import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { GeoJSON, MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import { api } from '../api/client'
import { Loading, ErrorState, PageHeader } from './ui/PageState'
import { STATUS, scoreStatus } from '../theme'

const BAGALKOT_CENTER: [number, number] = [15.85, 75.7]
const SILENT_NEED_COLOR = '#4a3aa7' // violet -- distinct from the good/warning/critical status ramp

function scoreColor(score: number): string {
  return STATUS[scoreStatus(score)]
}

export function MapView() {
  const [showDivergence, setShowDivergence] = useState(false)
  const { data, isLoading, error } = useQuery({ queryKey: ['boundary'], queryFn: api.boundary })

  if (isLoading) return <Loading label="Loading map..." />
  if (error) return <ErrorState label={`Failed to load map data: ${(error as Error).message}`} />

  return (
    <div className="mx-auto max-w-4xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <PageHeader title="Constituency Map — Bagalkot" />
        <label className="flex items-center gap-2 text-sm text-neutral-700 dark:text-neutral-300">
          <input
            type="checkbox"
            checked={showDivergence}
            onChange={(e) => setShowDivergence(e.target.checked)}
            className="accent-brand-500"
          />
          Show need-vs-voice divergence overlay
        </label>
      </div>

      <div className="h-[560px] overflow-hidden rounded-xl border border-neutral-200 dark:border-neutral-800">
        <MapContainer center={BAGALKOT_CENTER} zoom={9} style={{ height: '100%', width: '100%' }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {data?.constituency && (
            <GeoJSON
              data={data.constituency as GeoJSON.Feature}
              style={{ color: '#374151', weight: 2, fillOpacity: 0.03 }}
            />
          )}
          {data?.villages.features.map((f) => {
            const geom = f.geometry as GeoJSON.Point
            const [lng, lat] = geom.coordinates
            const props = f.properties as {
              village_name: string
              composite_score: number
              silent_need: boolean
              gap_percentile: number | null
              voice_percentile: number | null
            }
            const isSilent = showDivergence && props.silent_need
            const color = isSilent ? SILENT_NEED_COLOR : scoreColor(props.composite_score)
            return (
              <CircleMarker
                key={`${lng}-${lat}`}
                center={[lat, lng]}
                radius={isSilent ? 8 : 5}
                pathOptions={{ color, fillColor: color, fillOpacity: 0.8, weight: isSilent ? 2 : 1 }}
              >
                <Popup>
                  <div className="text-sm">
                    <div className="font-semibold">{props.village_name}</div>
                    <div>Priority score: {Math.round(props.composite_score * 100)}</div>
                    {props.gap_percentile != null && <div>Gap percentile: {Math.round(props.gap_percentile * 100)}%</div>}
                    {props.voice_percentile != null && <div>Voice percentile: {Math.round(props.voice_percentile * 100)}%</div>}
                    {props.silent_need && <div className="font-medium text-violet-700">Silent need village</div>}
                  </div>
                </Popup>
              </CircleMarker>
            )
          })}
        </MapContainer>
      </div>

      <p className="mt-2 text-xs text-neutral-400 dark:text-neutral-500">{data?.village_coverage_note}</p>
      <div className="mt-2 flex flex-wrap gap-4 text-xs text-neutral-600 dark:text-neutral-400">
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: STATUS.critical }} /> high priority
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: STATUS.warning }} /> medium
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: STATUS.good }} /> low
        </span>
        {showDivergence && (
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: SILENT_NEED_COLOR }} /> silent need
          </span>
        )}
      </div>
    </div>
  )
}
