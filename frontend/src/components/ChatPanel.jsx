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

export default function ChatPanel({ messages, fields, busy, onSend }) {
  const [text, setText] = useState('')
  const [recording, setRecording] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const logRef = useRef(null)
  const recorderRef = useRef(null)
  const chunksRef = useRef([])

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
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
        {recording && <div className="bubble bubble--user bubble--rec">🎙 recording… (tap mic to stop)</div>}
        {(busy || transcribing) && (
          <div className="bubble bubble--bot bubble--typing">{transcribing ? 'transcribing…' : '…'}</div>
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
