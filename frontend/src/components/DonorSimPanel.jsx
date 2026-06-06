// DonorSimPanel (SCAFFOLD) — demo control strip.
// TODO: buttons to simulate donor replies (confirm / decline / "gave blood last
// month") via POST /donor/respond, plus an "Advance wave" button (more reliable
// on stage than timers).
export default function DonorSimPanel() {
  return (
    <div className="sim">
      <span className="sim__label">Demo controls</span>
      <button disabled>✅ Simulate confirm</button>
      <button disabled>❌ Simulate decline</button>
      <button disabled>🩸 "Gave blood last month"</button>
      <button disabled>⏭ Advance wave</button>
    </div>
  )
}
