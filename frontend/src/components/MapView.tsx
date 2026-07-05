import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { GeoJSON, MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import { api } from '../api/client'

const BAGALKOT_CENTER: [number, number] = [15.85, 75.7]

function scoreColor(score: number): string {
  // 0 (low priority) -> green, 1 (high priority) -> red
  if (score >= 0.7) return '#dc2626'
  if (score >= 0.4) return '#f59e0b'
  return '#16a34a'
}

export function MapView() {
  const [showDivergence, setShowDivergence] = useState(false)
  const { data, isLoading, error } = useQuery({ queryKey: ['boundary'], queryFn: api.boundary })

  if (isLoading) return <div className="p-6 text-gray-500">Loading map...</div>
  if (error) return <div className="p-6 text-red-600">Failed to load map data: {(error as Error).message}</div>

  return (
    <div className="mx-auto max-w-4xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Constituency Map — Bagalkot</h2>
        <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
          <input type="checkbox" checked={showDivergence} onChange={(e) => setShowDivergence(e.target.checked)} />
          Show need-vs-voice divergence overlay
        </label>
      </div>

      <div className="h-[560px] overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
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
            const color = isSilent ? '#7c3aed' : scoreColor(props.composite_score)
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
                    {props.silent_need && <div className="font-medium text-purple-700">Silent need village</div>}
                  </div>
                </Popup>
              </CircleMarker>
            )
          })}
        </MapContainer>
      </div>

      <p className="mt-2 text-xs text-gray-400">{data?.village_coverage_note}</p>
      <div className="mt-2 flex gap-4 text-xs text-gray-600 dark:text-gray-400">
        <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full bg-red-600" /> high priority</span>
        <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full bg-amber-500" /> medium</span>
        <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full bg-green-600" /> low</span>
        {showDivergence && <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full bg-purple-600" /> silent need</span>}
      </div>
    </div>
  )
}
