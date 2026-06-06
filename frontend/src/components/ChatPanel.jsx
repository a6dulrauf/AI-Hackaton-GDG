import { useState, useRef, useEffect } from 'react'
import { transcribeVoice } from '../api.js'

// ChatPanel — WhatsApp-style intake. Controlled input; parsing/creation live in App.
// Shows the fields extracted so far as chips, so a judge sees the LLM "understanding".
// Mic button (S1) records audio -> Groq Whisper -> feeds the transcript into onSend.
const CHIP_DEFS = [
  { key: 'blood_group', label: 'Group' },
  { key: 'count', label: 'Count' },
  { key: 'hospital', label: 'Hospital' },
  { key: 'location', label: 'Area' },
  { key: 'urgency', label: 'Urgency' },
]

// One-tap example requests so a first-time judge isn't staring at an empty box.
// Deliberately messy + mixed-language to show off the parser.
const STARTERS = [
  'AB+ ke 2 donor chahiye jaldi, Indus',
  'Need 3 units O+ at Liaquat National',
  'B negative chahiye Civil Hospital',
]

const timeLabel = () =>
  new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

// Animated "bot is thinking" indicator (three bouncing dots).
function TypingDots() {
  return (
    <span className="typing-dots" aria-label="typing">
      <i /><i /><i />
    </span>
  )
}

// A single chat row: avatar + bubble + timestamp. Bot messages type themselves
// out once on first appearance (captured at mount so they never re-animate).
function Bubble({ msg, fresh, onType }) {
  const [time] = useState(timeLabel)
  const [animate] = useState(() => fresh && msg.role === 'bot')
  const [shown, setShown] = useState(() => (fresh && msg.role === 'bot' ? '' : msg.text))

  useEffect(() => {
    if (!animate) return
    let i = 0
    const id = setInterval(() => {
      i += 2
      setShown(msg.text.slice(0, i))
      onType?.()
      if (i >= msg.text.length) {
        setShown(msg.text)
        clearInterval(id)
      }
    }, 16)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const typing = animate && shown.length < msg.text.length
  return (
    <div className={`msg msg--${msg.role}`}>
      <div className="avatar">{msg.role === 'bot' ? '🩸' : '🧑'}</div>
      <div className={`bubble bubble--${msg.role}`}>
        <span className="bubble__text">
          {shown}
          {typing && <span className="caret" />}
        </span>
        <span className="bubble__time">{time}</span>
      </div>
    </div>
  )
}

export default function ChatPanel({ messages, fields, busy, onSend }) {
  const [text, setText] = useState('')
  const [recording, setRecording] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const logRef = useRef(null)
  const recorderRef = useRef(null)
  const chunksRef = useRef([])
  // Track how many messages we've already rendered so only the newest animates.
  const seenRef = useRef(0)

  const scrollToBottom = () => {
    const el = logRef.current
    if (el) el.scrollTop = el.scrollHeight
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, busy, transcribing])

  // Only messages appended since the last commit are "fresh" (and animate).
  // Updated in an effect (not during render) so it's StrictMode-safe.
  const prevCount = seenRef.current
  useEffect(() => {
    seenRef.current = messages.length
  }, [messages])

  function submit(e) {
    e.preventDefault()
    if (!text.trim() || busy) return
    onSend(text)
    setText('')
  }

  async function toggleMic() {
    if (recording) {
      recorderRef.current?.stop()
      return
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      alert('Microphone not supported in this browser.')
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mr = new MediaRecorder(stream)
      chunksRef.current = []
      mr.ondataavailable = (e) => { if (e.data.size) chunksRef.current.push(e.data) }
      mr.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        setRecording(false)
        const blob = new Blob(chunksRef.current, { type: mr.mimeType || 'audio/webm' })
        if (!blob.size) return
        setTranscribing(true)
        try {
          const { text: heard } = await transcribeVoice(blob)
          if (heard?.trim()) onSend(heard.trim())
        } catch (err) {
          alert(`Transcription failed: ${err.message}`)
        } finally {
          setTranscribing(false)
        }
      }
      recorderRef.current = mr
      mr.start()
      setRecording(true)
    } catch {
      alert('Microphone access was denied.')
    }
  }

  const hasAnyField = CHIP_DEFS.some(({ key }) => fields[key] && !(key === 'urgency' && fields[key] === 'normal'))
  const inputDisabled = busy || transcribing
  const showStarters = messages.length <= 1 && !busy && !transcribing

  return (
    <div className="chat">
      <h2 className="panel__title">
        Chat <span className="chat__status"><i className="chat__dot" />online</span>
      </h2>

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
          <Bubble key={i} msg={m} fresh={i >= prevCount} onType={scrollToBottom} />
        ))}

        {showStarters && (
          <div className="starters">
            <span className="starters__label">Try one of these:</span>
            {STARTERS.map((s) => (
              <button key={s} className="starter" disabled={inputDisabled} onClick={() => onSend(s)}>
                {s}
              </button>
            ))}
          </div>
        )}

        {recording && (
          <div className="msg msg--user">
            <div className="avatar">🧑</div>
            <div className="bubble bubble--user bubble--rec">🎙 recording… (tap mic to stop)</div>
          </div>
        )}
        {(busy || transcribing) && (
          <div className="msg msg--bot">
            <div className="avatar">🩸</div>
            <div className="bubble bubble--bot bubble--typing">
              {transcribing ? 'transcribing…' : <TypingDots />}
            </div>
          </div>
        )}
      </div>

      <form className="chat__input" onSubmit={submit}>
        <button
          type="button"
          className={`mic ${recording ? 'mic--on' : ''}`}
          onClick={toggleMic}
          disabled={busy || transcribing}
          title={recording ? 'Stop recording' : 'Record voice request'}
        >
          {recording ? '⏹' : '🎙'}
        </button>
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="e.g. AB negative chahiye jaldi, Liaquat National mein"
          disabled={inputDisabled}
        />
        <button type="submit" disabled={inputDisabled || !text.trim()}>Send</button>
      </form>
    </div>
  )
}
