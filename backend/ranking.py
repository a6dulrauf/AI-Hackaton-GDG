"""
Drop-in matching brain for the blood-donor app.
Self-contained: Haversine implemented inline (no geopy needed, but geopy is fine too).

Public functions:
    resolve_hospital(name) -> (lat, lng) | None
    rank_donors(donors, blood_group, hospital_latlng, count_needed, allow_compatible=False)
        -> list of ranked donor dicts (eligible only), each with score/distance/reason/why
"""
from math import radians, sin, cos, asin, sqrt
from datetime import date

# ---------------------------------------------------------------------------
# Karachi hospitals (approximate coordinates — fine for ranking/demo).
# Keys are matched case-insensitively by substring, so "indus" or
# "liaquat national" both resolve.
# ---------------------------------------------------------------------------
HOSPITALS = {
    "Indus Hospital": (24.8460, 67.1350),
    "Liaquat National Hospital": (24.8910, 67.0750),
    "Aga Khan University Hospital": (24.8918, 67.0730),
    "Jinnah Postgraduate Medical Centre": (24.8570, 67.0420),
    "Civil Hospital Karachi": (24.8540, 67.0150),
    "National Institute of Cardiovascular Diseases": (24.8560, 67.0410),
    "South City Hospital": (24.8170, 67.0290),
    "Ziauddin Hospital Clifton": (24.8090, 67.0310),
    "Ziauddin Hospital North Nazimabad": (24.9560, 67.0360),
    "Abbasi Shaheed Hospital": (24.9170, 67.0330),
    "Patel Hospital": (24.9240, 67.0840),
    "Memon Medical Institute": (24.9380, 67.1560),
    "OMI Hospital": (24.8650, 67.0330),
    "Tabba Heart Institute": (24.9320, 67.0930),
    "Kharadar General Hospital": (24.8480, 66.9970),
    "Sindh Govt Hospital Liaquatabad": (24.9090, 67.0440),
    "Hill Park General Hospital": (24.8720, 67.0680),
    "The Kidney Centre": (24.8740, 67.0560),
    "National Medical Centre DHA": (24.8030, 67.0560),
    "Lady Dufferin Hospital": (24.8650, 67.0260),
    "Holy Family Hospital": (24.8730, 67.0330),
    "Saifee Hospital": (24.9100, 67.0820),
}
# Short aliases -> canonical key (extend freely)
ALIASES = {
    "indus": "Indus Hospital", "liaquat national": "Liaquat National Hospital",
    "lnh": "Liaquat National Hospital", "aku": "Aga Khan University Hospital",
    "aga khan": "Aga Khan University Hospital", "jpmc": "Jinnah Postgraduate Medical Centre",
    "jinnah": "Jinnah Postgraduate Medical Centre", "civil": "Civil Hospital Karachi",
    "nicvd": "National Institute of Cardiovascular Diseases", "south city": "South City Hospital",
    "ziauddin": "Ziauddin Hospital Clifton", "abbasi": "Abbasi Shaheed Hospital",
    "patel": "Patel Hospital", "tabba": "Tabba Heart Institute", "kidney": "The Kidney Centre",
}

# Recipient compatibility: a patient of group X can RECEIVE from these donor groups.
RECIPIENT_CAN_RECEIVE = {
    "O-":  ["O-"],
    "O+":  ["O+", "O-"],
    "A-":  ["A-", "O-"],
    "A+":  ["A+", "A-", "O+", "O-"],
    "B-":  ["B-", "O-"],
    "B+":  ["B+", "B-", "O+", "O-"],
    "AB-": ["AB-", "A-", "B-", "O-"],
    "AB+": ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"],
}

def resolve_hospital(name):
    """Return (lat,lng) for a hospital name, trying exact, alias, then substring."""
    if not name:
        return None
    q = name.strip().lower()
    for canonical, coords in HOSPITALS.items():
        if canonical.lower() == q:
            return coords
    for alias, canonical in ALIASES.items():
        if alias in q:
            return HOSPITALS[canonical]
    for canonical, coords in HOSPITALS.items():
        if q in canonical.lower() or canonical.lower() in q:
            return coords
    return None

def haversine_km(a, b):
    (lat1, lon1), (lat2, lon2) = a, b
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    return 2 * 6371 * asin(sqrt(h))

def _eligible(d):
    """Medical recovery window: 90 days (men) / 120 days (women), age 18-60."""
    if not (18 <= int(d["age"]) <= 60):
        return False
    window = 90 if d["gender"] == "Male" else 120
    return int(d["days_since_last_donation"]) > window

def rank_donors(donors, blood_group, hospital_latlng, count_needed=5, allow_compatible=False):
    """
    Score = 0.40*proximity + 0.25*recency + 0.20*response_rate - 0.15*fatigue
    Returns eligible, group-matching donors sorted best-first.
    """
    if allow_compatible:
        acceptable = set(RECIPIENT_CAN_RECEIVE.get(blood_group, [blood_group]))
    else:
        acceptable = {blood_group}

    ranked = []
    for d in donors:
        if d["blood_group"] not in acceptable:
            continue
        if not _eligible(d):
            continue
        dist = haversine_km(hospital_latlng, (float(d["lat"]), float(d["lng"])))
        days = int(d["days_since_last_donation"])
        rr = float(d["response_rate"])
        fatigue = min(int(d["times_contacted_last_30d"]) / 5, 1.0)
        proximity = 1 / (1 + dist)
        recency = min(days / 365, 1.0)
        score = 0.40*proximity + 0.25*recency + 0.20*rr - 0.15*fatigue
        reason = (f"{dist:.1f} km · eligible ({days}d since last) · "
                  f"responds {int(rr*100)}% · contacted {d['times_contacted_last_30d']}x/30d")
        why = (f"Recommending {d['name']} — "
               f"{'closest ' if dist < 3 else ''}eligible {d['blood_group']} donor, "
               f"last gave blood {days} days ago, responds {int(rr*100)}% of the time"
               f"{', not contacted recently' if d['times_contacted_last_30d']==0 else ''}.")
        ranked.append({**d, "distance_km": round(dist, 2), "score": round(score, 4),
                       "reason": reason, "why": why,
                       "compatible_not_exact": d["blood_group"] != blood_group})
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked

if __name__ == "__main__":
    import db
    donors = db.load_donors()
    coords = resolve_hospital("Indus")
    top = rank_donors(donors, "O+", coords, count_needed=5)[:5]
    print(f"Hospital coords: {coords}  |  matching eligible O+ donors: {len(rank_donors(donors,'O+',coords))}")
    for d in top:
        print(" ", d["why"])
