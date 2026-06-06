// DashboardPanel (SCAFFOLD) — ranked donor list + live status + win-condition stats.
// TODO: "X of Y confirmed" ring, per-donor `why` sentence, network-health
// indicator, and the Spam Shield stat ("a blast would message N, we contacted M").
export default function DashboardPanel() {
  return (
    <div className="dash">
      <h2 className="panel__title">Coordinator Dashboard</h2>
      <div className="dash__stats">
        <div className="stat"><span className="stat__num">—</span><span className="stat__label">Confirmed</span></div>
        <div className="stat"><span className="stat__num">—</span><span className="stat__label">Contacted</span></div>
        <div className="stat"><span className="stat__num">—</span><span className="stat__label">Spam Shield</span></div>
      </div>
      <p className="placeholder">Ranked donor list &amp; live status wired up in a later phase.</p>
    </div>
  )
}
