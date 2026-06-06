import { useState, useEffect, useRef } from 'react'
import ChatPanel from './components/ChatPanel.jsx'
import MapPanel from './components/MapPanel.jsx'
import DashboardPanel from './components/DashboardPanel.jsx'
import DonorSimPanel from './components/DonorSimPanel.jsx'
import WhatsAppToggle from './components/WhatsAppToggle.jsx'
import { parseRequest, createRequest, getStatus, escalateRequest, respondDonor } from './api.js'

const REQUIRED = ['blood_group', 'count', 'hospital']
const EMPTY_FIELDS = { blood_group: null, count: null, hospital: null, location: null, urgency: 'normal' }

const FIELD_PROMPTS = {
  blood_group: 'Which blood group is needed? (e.g. O+, AB-)',
  count: 'How many units / donors are needed?',
  hospital: 'Which hospital? (e.g. Indus, Liaquat National, AKU)',
}

// Prefer a freshly-parsed non-null value, otherwise keep what we already knew.
function mergeFields(prev, next) {
  const out = { ...prev }
  for (const k of ['blood_group', 'count', 'hospital', 'location']) {
    if (next[k] !== null && next[k] !== undefined && next[k] !== '') out[k] = next[k]
  }
  if (next.urgency === 'high') out.urgency = 'high'
  return out
}

const missingOf = (f) => REQUIRED.filter((k) => f[k] === null || f[k] === undefined || f[k] === '')

export default function App() {
  const [messages, setMessages] = useState([
    { role: 'bot', text: 'Assalam-o-Alaikum. Apni blood request likhein (Urdu / Roman Urdu / English).' },
  ])
  const [fields, setFields] = useState(EMPTY_FIELDS)
  const [convo, setConvo] = useState('')      // running text fed to the parser
  const [request, setRequest] = useState(null)
  const [busy, setBusy] = useState(false)

  const say = (role, text) => setMessages((m) => [...m, { role, text }])

  // Poll live status every 2s while a request is open and not yet fulfilled.
  const reqId = request?.id
  const done = request?.done
  useEffect(() => {
    if (!reqId || done) return
    const t = setInterval(async () => {
      try { setRequest(await getStatus(reqId)) } catch { /* keep last good state */ }
    }, 2000)
    return () => clearInterval(t)
  }, [reqId, done])

  async function handleSend(text) {
    if (!text.trim() || busy) return
    say('user', text)
    setBusy(true)

    const fullText = `${convo} ${text}`.trim()
    setConvo(fullText)

    try {
      const parsed = await parseRequest(fullText)
      const merged = mergeFields(fields, parsed)
      setFields(merged)

      const missing = missingOf(merged)
      if (missing.length > 0) {
        // Prefer the LLM's natural, same-language reply; fall back to a fixed
        // prompt only if Groq was unavailable (parsed.reply === null).
        say('bot', parsed.reply || FIELD_PROMPTS[missing[0]])
      } else {
        say('bot', parsed.reply || 'Got it — ranking eligible donors nearby…')
        const res = await createRequest({
          blood_group: merged.blood_group,
          count: Number(merged.count),
          hospital: merged.hospital,
          urgency: merged.urgency,
          location: merged.location,
          raw_text: fullText,
        })
        setRequest(res)
        const compatNote = res.used_compatible
          ? `No exact ${res.blood_group} donors available, so I broadened to ${res.total_matching} medically-compatible donors (safe to give ${res.blood_group}). `
          : `Found ${res.total_matching} eligible ${res.blood_group} donor(s) near ${res.hospital}. `
        say('bot',
          compatNote +
          `Contacted the top ${res.contacted} (wave 1). A mass blast would have messaged all ${res.total_matching}.`)
      }
    } catch (err) {
      say('bot', `⚠️ ${err.message}`)
    } finally {
      setBusy(false)
    }
  }

  async function handleRespond(donorId, text) {
    if (!request) return
    try {
      setRequest(await respondDonor({ donor_id: donorId, text, request_id: request.id }))
    } catch (err) {
      say('bot', `⚠️ ${err.message}`)
    }
  }

  async function handleEscalate() {
    if (!request) return
    try {
      setRequest(await escalateRequest(request.id))
    } catch (err) {
      say('bot', `⚠️ ${err.message}`)
    }
  }

  function handleReset() {
    setMessages([{ role: 'bot', text: 'New request — go ahead.' }])
    setFields(EMPTY_FIELDS)
    setConvo('')
    setRequest(null)
  }

  const urgent = request?.urgency === 'high' && !request?.done

  return (
    <div className={`app ${urgent ? 'app--urgent' : ''}`}>
      <header className="app__header">
        <span className="app__logo">🩸 LifeLine</span>
        <span className="app__tag">Real-time blood-donor matching · Al-Khidmat Karachi</span>
        {urgent && <span className="app__urgent">● HIGH URGENCY</span>}
        <div className="app__actions">
          <WhatsAppToggle />
          <button className="app__reset" onClick={handleReset}>New request</button>
        </div>
      </header>

      <main className="app__grid">
        <section className="panel panel--chat">
          <ChatPanel messages={messages} fields={fields} busy={busy} onSend={handleSend} />
        </section>
        <section className="panel panel--map">
          <MapPanel request={request} />
        </section>
        <section className="panel panel--dash">
          <DashboardPanel request={request} />
        </section>
      </main>

      <footer className="app__footer">
        <DonorSimPanel request={request} onRespond={handleRespond} onEscalate={handleEscalate} />
      </footer>
    </div>
  )
}
