// ChatPanel (SCAFFOLD) — WhatsApp-style intake.
// TODO: on send -> POST /request/parse, render extracted fields as chips,
// ask for missing_fields, then POST /request/create.
export default function ChatPanel() {
  return (
    <div className="chat">
      <h2 className="panel__title">Chat</h2>
      <div className="chat__log">
        <div className="bubble bubble--bot">
          Assalam-o-Alaikum. Apni blood request likhein (Urdu / Roman Urdu / English).
        </div>
        <p className="placeholder">Chat intake wired up in a later phase.</p>
      </div>
      <div className="chat__input">
        <input type="text" placeholder="e.g. AB negative chahiye jaldi, Liaquat National mein" disabled />
        <button disabled>Send</button>
      </div>
    </div>
  )
}
