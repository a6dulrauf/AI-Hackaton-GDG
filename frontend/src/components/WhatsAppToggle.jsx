// WhatsAppToggle — header switch for real outreach. Defaults to "Mocked" so a
// flaky WhatsApp connection never blocks the demo; flip to "Live" only when the
// Meta Cloud API creds are wired up. Disabled (with a hint) when unconfigured.
import { useState, useEffect } from 'react'
import { getWhatsappStatus, toggleWhatsapp } from '../api.js'

export default function WhatsAppToggle() {
  const [status, setStatus] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    getWhatsappStatus()
      .then(setStatus)
      .catch(() => setStatus({ configured: false, enabled: false }))
  }, [])

  if (!status) return null
  const { configured, enabled } = status

  const label = !configured ? 'not set up' : enabled ? 'Live' : 'Mocked'
  const title = configured
    ? enabled
      ? 'Live — contacted donors receive a real WhatsApp message'
      : 'Mocked — wave outreach is simulated, no real messages sent'
    : 'Set WHATSAPP_TOKEN + WHATSAPP_PHONE_NUMBER_ID in backend/.env to enable'

  async function flip() {
    if (!configured || busy) return
    setBusy(true)
    try {
      setStatus(await toggleWhatsapp(!enabled))
    } catch {
      /* keep last good state */
    } finally {
      setBusy(false)
    }
  }

  return (
    <button
      type="button"
      className={`wa-toggle ${enabled ? 'wa-toggle--on' : ''} ${!configured ? 'wa-toggle--off' : ''}`}
      onClick={flip}
      disabled={!configured || busy}
      title={title}
    >
      <span className="wa-toggle__dot" />
      WhatsApp: {label}
    </button>
  )
}
