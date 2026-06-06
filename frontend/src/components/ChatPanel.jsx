import { useState, useRef, useEffect } from 'react'

// ChatPanel — WhatsApp-style intake. Controlled input; parsing/creation live in App.
// Shows the fields extracted so far as chips, so a judge sees the LLM "understanding".
const CHIP_DEFS = [
  { key: 'blood_group', label: 'Group' },
  { key: 'count', label: 'Count' },
  { key: 'hospital', label: 'Hospital' },
  { key: 'location', label: 'Area' },
  { key: 'urgency', label: 'Urgency' },
]

export default function ChatPanel({ messages, fields, busy, onSend }) {
  const [text, setText] = useState('')
  const logRef = useRef(null)

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [messages])

  function submit(e) {
    e.preventDefault()
    if (!text.trim() || busy) return
    onSend(text)
    setText('')
  }

  const hasAnyField = CHIP_DEFS.some(({ key }) => fields[key] && !(key === 'urgency' && fields[key] === 'normal'))

  return (
    <div className="chat">
      <h2 className="panel__title">Chat</h2>

      {hasAnyField && (
        <div className="chips">
          {CHIP_DEFS.map(({ key, label }) => {
            const val = fields[key]
            if (!val || (key === 'urgency' && val === 'normal')) return null
            return (
              <span key={key} className={`chip ${key === 'urgency' && val === 'high' ? 'chip--urgent' : ''}`}>
                <span className="chip__label">{label}</span> {val}
              </span>
            )
          })}
        </div>
      )}

      <div className="chat__log" ref={logRef}>
        {messages.map((m, i) => (
          <div key={i} className={`bubble bubble--${m.role}`}>{m.text}</div>
        ))}
        {busy && <div className="bubble bubble--bot bubble--typing">…</div>}
      </div>

      <form className="chat__input" onSubmit={submit}>
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="e.g. AB negative chahiye jaldi, Liaquat National mein"
          disabled={busy}
        />
        <button type="submit" disabled={busy || !text.trim()}>Send</button>
      </form>
    </div>
  )
}
