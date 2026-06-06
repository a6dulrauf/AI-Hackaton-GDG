import { MapContainer, TileLayer } from 'react-leaflet'

// MapPanel (SCAFFOLD) — Leaflet + OpenStreetMap tiles (no API key).
// Centered on Karachi. TODO: hospital marker + donor pins colored by status
// (eligible=green, ineligible=grey, contacted=amber, confirmed=blue).
const KARACHI_CENTER = [24.8607, 67.0011]

export default function MapPanel() {
  return (
    <div className="map">
      <h2 className="panel__title">Map</h2>
      <MapContainer center={KARACHI_CENTER} zoom={11} className="map__canvas">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
      </MapContainer>
    </div>
  )
}
