import { useEffect } from 'react'
import { MapContainer, TileLayer, CircleMarker, Tooltip, useMap } from 'react-leaflet'

// MapPanel — Leaflet + OpenStreetMap (no API key). Hospital marker + donor pins
// colored by status. CircleMarkers avoid Leaflet's default icon-asset issue.
const KARACHI_CENTER = [24.8607, 67.0011]

const STATUS_COLOR = {
  pending: '#22c55e',    // eligible, not yet contacted
  contacted: '#e0a800',  // messaged this wave
  confirmed: '#3b82f6',  // committed
  declined: '#6b7280',   // said no
}

// Pan/zoom the map when the active request (hospital) changes.
function Recenter({ center, zoom }) {
  const map = useMap()
  useEffect(() => {
    if (center) map.setView(center, zoom)
  }, [center, zoom, map])
  return null
}

export default function MapPanel({ request }) {
  const hospital = request?.hospital_latlng
  const donors = request?.donors || []

  return (
    <div className="map">
      <h2 className="panel__title">Map</h2>
      <MapContainer center={KARACHI_CENTER} zoom={11} className="map__canvas">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {hospital && <Recenter center={hospital} zoom={13} />}

        {hospital && (
          <CircleMarker
            center={hospital}
            radius={11}
            pathOptions={{ color: '#fff', weight: 2, fillColor: '#e5484d', fillOpacity: 1 }}
          >
            <Tooltip permanent direction="top" offset={[0, -8]}>🏥 {request.hospital}</Tooltip>
          </CircleMarker>
        )}

        {donors.map((d) => (
          <CircleMarker
            key={d.donor_id}
            center={[Number(d.lat), Number(d.lng)]}
            radius={6}
            pathOptions={{
              color: '#0f1115',
              weight: 1,
              fillColor: STATUS_COLOR[d.status] || '#888',
              fillOpacity: 0.9,
            }}
          >
            <Tooltip direction="top">
              {d.name} · {d.blood_group}{d.compatible_not_exact ? ' (compatible)' : ''} · {d.status} · {d.distance_km} km
            </Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>

      <div className="map__legend">
        <span><i style={{ background: '#e5484d' }} />Hospital</span>
        <span><i style={{ background: STATUS_COLOR.pending }} />Eligible</span>
        <span><i style={{ background: STATUS_COLOR.contacted }} />Contacted</span>
        <span><i style={{ background: STATUS_COLOR.confirmed }} />Confirmed</span>
      </div>
    </div>
  )
}
