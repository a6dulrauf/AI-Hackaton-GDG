import ChatPanel from './components/ChatPanel.jsx'
import MapPanel from './components/MapPanel.jsx'
import DashboardPanel from './components/DashboardPanel.jsx'
import DonorSimPanel from './components/DonorSimPanel.jsx'

// SCAFFOLD layout only. Three working columns + a demo-control strip.
// Feature wiring (state, fetch, polling) gets added on top in later phases.
export default function App() {
  return (
    <div className="app">
      <header className="app__header">
        <span className="app__logo">🩸 LifeLine</span>
        <span className="app__tag">Real-time blood-donor matching · Al-Khidmat Karachi</span>
      </header>

      <main className="app__grid">
        <section className="panel panel--chat">
          <ChatPanel />
        </section>
        <section className="panel panel--map">
          <MapPanel />
        </section>
        <section className="panel panel--dash">
          <DashboardPanel />
        </section>
      </main>

      <footer className="app__footer">
        <DonorSimPanel />
      </footer>
    </div>
  )
}
