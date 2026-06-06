// DashboardPanel — ranked donor list + Spam Shield. (Live status ring lands in Phase 5.)
const STATUS_LABEL = {
  contacted: 'Contacted',
  pending: 'Pending',
  confirmed: 'Confirmed',
  declined: 'Declined',
}

export default function DashboardPanel({ request }) {
  if (!request) {
    return (
      <div className="dash">
        <h2 className="panel__title">Coordinator Dashboard</h2>
        <p className="placeholder">Send a request to see ranked donors and the Spam Shield here.</p>
      </div>
    )
  }

  const { donors = [], total_matching = 0, contacted = 0, confirmed = 0, count_needed = 0,
          used_compatible = false, blood_group, hospital, done = false, network_protected = 0 } = request
  const deg = Math.min(1, count_needed ? confirmed / count_needed : 0) * 360
  const confirmedDonors = donors.filter((d) => d.status === 'confirmed')

  return (
    <div className="dash">
      <h2 className="panel__title">Coordinator Dashboard</h2>

      <div className="dash__top">
        <div className="ring" style={{ '--deg': `${deg}deg` }}>
          <div className="ring__inner">
            <span className="ring__num">{confirmed}/{count_needed}</span>
            <span className="ring__label">confirmed</span>
          </div>
        </div>
        <div className="dash__side">
          <div className="stat">
            <span className="stat__num">{contacted}</span>
            <span className="stat__label">Contacted</span>
          </div>
          <div className="stat stat--shield">
            <span className="stat__num">{contacted}<span className="stat__den">/{total_matching}</span></span>
            <span className="stat__label">Spam Shield</span>
          </div>
        </div>
      </div>

      {done && (
        <div className="done-banner">✅ Target reached — {confirmed} of {count_needed} donors confirmed.</div>
      )}

      {done && confirmedDonors.length > 0 && (
        <div className="summary-card">
          <div className="summary-card__title">📋 Dispatch summary · {hospital}</div>
          {confirmedDonors.map((d) => (
            <div key={d.donor_id} className="summary-row">
              <span className="summary-row__name">{d.name} <em>{d.blood_group}</em></span>
              <a className="summary-row__phone" href={`tel:${d.phone}`}>{d.phone}</a>
            </div>
          ))}
          <div className="summary-card__foot">Coordinator: please confirm ETAs with the above donors.</div>
        </div>
      )}

      {network_protected > 0 && (
        <p className="net-note">
          🌐 <strong>Network health:</strong> {network_protected} over-contacted volunteer(s) held back to later waves to prevent fatigue.
        </p>
      )}

      <p className="shield-note">
        🛡️ A mass blast would have messaged <strong>{total_matching}</strong> people.
        We contacted <strong>{contacted}</strong>.
      </p>

      {used_compatible && (
        <p className="compat-note">
          🧬 No exact <strong>{blood_group}</strong> donors — showing medically-compatible donors who can safely give to {blood_group}.
        </p>
      )}

      <div className="donors">
        {donors.map((d) => (
          <div key={d.donor_id} className={`donor donor--${d.status}`}>
            <div className="donor__head">
              <span className="donor__name">{d.name}</span>
              <span className="donor__bg">{d.blood_group}</span>
              {d.compatible_not_exact && <span className="tag-compat" title="Compatible, not exact group">compatible</span>}
              <span className={`badge badge--${d.status}`}>{STATUS_LABEL[d.status] || d.status} · W{d.wave}</span>
            </div>
            <div className="donor__meta">
              {d.distance_km} km · {d.days_since_last_donation}d since last ·
              responds {Math.round(Number(d.response_rate) * 100)}% ·{' '}
              <span className={Number(d.times_contacted_last_30d) >= 3 ? 'fatigue fatigue--high' : 'fatigue'}>
                {d.times_contacted_last_30d}×/30d
              </span>
            </div>
            <div className="donor__why">{d.why}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
