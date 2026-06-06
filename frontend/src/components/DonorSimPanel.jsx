// DonorSimPanel — demo control strip. Sends canned donor replies through the real
// /donor/respond classifier (so judges see live intent classification, not fakes),
// plus a manual "Advance wave" — more reliable on stage than timers.
const CANNED = {
  confirm: 'Haan ji, main aa raha hoon',
  decline: 'Sorry, abhi nahi aa sakta',
  eligibility: 'Maine pichle mahine blood diya tha',
}

export default function DonorSimPanel({ request, onRespond, onEscalate }) {
  const donors = request?.donors || []
  // Act on the next donor we've messaged who hasn't replied yet.
  const target = donors.find((d) => d.status === 'contacted')
  const hasPending = donors.some((d) => d.status === 'pending')
  const disabled = !request || !target
  const who = target ? `${target.name} (${target.blood_group})` : 'no one awaiting reply'

  return (
    <div className="sim">
      <span className="sim__label">Demo · next reply from <strong>{who}</strong>:</span>
      <button disabled={disabled} onClick={() => onRespond(target.donor_id, CANNED.confirm)}>✅ Confirm</button>
      <button disabled={disabled} onClick={() => onRespond(target.donor_id, CANNED.decline)}>❌ Decline</button>
      <button disabled={disabled} onClick={() => onRespond(target.donor_id, CANNED.eligibility)}>🩸 "Gave blood last month"</button>
      <button className="sim__wave" disabled={!request || !hasPending} onClick={onEscalate}>⏭ Advance wave</button>
    </div>
  )
}
