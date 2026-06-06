"""
Generate a reproducible synthetic Karachi blood-donor dataset into a portable
SQLite database (data/lifeline.db) that ships with the repo.
Pure standard library — no pip installs (sqlite3 is stdlib). Run: python generate_donors.py
Seed is fixed so everyone on the team gets the byte-identical dataset.
"""
import os, sqlite3, random, datetime
from collections import Counter

random.seed(42)

# Karachi neighbourhood centroids (approx) -> donors get a small jitter around these.
AREAS = {
    "Gulshan-e-Iqbal": (24.9215, 67.0915), "Gulistan-e-Johar": (24.9180, 67.1300),
    "North Nazimabad": (24.9420, 67.0380), "Nazimabad": (24.9120, 67.0300),
    "F.B. Area": (24.9430, 67.0640), "Clifton": (24.8138, 67.0300), "DHA": (24.8000, 67.0500),
    "Korangi": (24.8430, 67.1340), "Malir": (24.8930, 67.2050), "Saddar": (24.8600, 67.0220),
    "Liaquatabad": (24.9070, 67.0420), "Lyari": (24.8770, 66.9920), "PECHS": (24.8720, 67.0640),
    "Shah Faisal Colony": (24.8790, 67.1600), "Landhi": (24.8500, 67.1900),
    "Orangi Town": (24.9540, 66.9880), "Gulberg": (24.9300, 67.0500), "Bahadurabad": (24.8810, 67.0640),
}
# Blood-group distribution roughly reflecting Pakistan (B+ and O+ dominant).
BG_WEIGHTS = {"B+": 34, "O+": 28, "A+": 21, "AB+": 9, "O-": 3, "B-": 2.5, "A-": 1.7, "AB-": 0.8}
GROUPS, WEIGHTS = list(BG_WEIGHTS), list(BG_WEIGHTS.values())

MALE = ["Ahmed","Bilal","Usman","Hamza","Faizan","Saad","Zain","Imran","Asad","Rehan","Kashif",
        "Owais","Talha","Danish","Adnan","Fahad","Junaid","Salman","Waqas","Hassan","Ali","Umar",
        "Shahzaib","Noman","Yasir","Arsalan","Taimoor","Haris","Faraz","Bilawal"]
FEMALE = ["Ayesha","Fatima","Hira","Sana","Maryam","Zara","Nida","Areeba","Mahnoor","Rabia","Komal",
          "Iqra","Sadia","Anum","Mehwish","Bushra","Sidra","Amna","Saba","Laiba","Eman","Tooba",
          "Warda","Aiman","Kiran"]
LAST = ["Khan","Ahmed","Siddiqui","Sheikh","Malik","Qureshi","Hussain","Raza","Abbasi","Memon","Baig",
        "Ansari","Farooqi","Rizvi","Chaudhry","Butt","Awan","Shah","Nawaz","Jamali","Soomro","Bhatti",
        "Mughal","Lodhi","Khokhar"]

TODAY = datetime.date(2026, 6, 6)
N = 220

# Portable DB file lives next to this script (data/lifeline.db), resolved
# absolutely so it doesn't matter which directory you run from.
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lifeline.db")

# Column order here must match backend/db.py DONOR_COLUMNS (kept in sync by hand).
SCHEMA = """
CREATE TABLE donors (
  donor_id TEXT PRIMARY KEY,
  name TEXT,
  gender TEXT,
  dob TEXT,
  age INTEGER,
  blood_group TEXT,
  phone TEXT,
  neighbourhood TEXT,
  lat REAL,
  lng REAL,
  last_donation_date TEXT,
  days_since_last_donation INTEGER,
  total_donations INTEGER,
  times_contacted_last_30d INTEGER,
  response_rate REAL
)
"""

def jitter(lat, lng):
    return round(lat + random.uniform(-0.012, 0.012), 5), round(lng + random.uniform(-0.012, 0.012), 5)

def build():
    rows = []
    for i in range(1, N + 1):
        gender = random.choices(["Male", "Female"], weights=[68, 32])[0]
        first = random.choice(MALE if gender == "Male" else FEMALE)
        name = f"{first} {random.choice(LAST)}"
        age = random.randint(18, 60)
        dob = datetime.date(TODAY.year - age, random.randint(1, 12), random.randint(1, 28))
        bg = random.choices(GROUPS, weights=WEIGHTS)[0]
        area = random.choice(list(AREAS))
        lat, lng = jitter(*AREAS[area])
        phone = "+923" + str(random.randint(0, 4)) + str(random.randint(10**7, 10**8 - 1))
        days = random.choices(
            [random.randint(0, 89), random.randint(90, 365), random.randint(366, 900)],
            weights=[30, 45, 25])[0]
        last_don = TODAY - datetime.timedelta(days=days)
        total = random.choices([0,1,2,3,4,5,6,8,10,15], weights=[8,15,20,18,12,10,7,5,3,2])[0]
        c30 = random.choices([0,1,2,3,5,8], weights=[40,25,15,10,7,3])[0]
        rr = round(random.choices(
            [random.uniform(0.7,1.0), random.uniform(0.4,0.7), random.uniform(0.0,0.4)],
            weights=[45,35,20])[0], 2)
        rows.append(dict(
            donor_id=f"D{i:04d}", name=name, gender=gender, dob=dob.isoformat(), age=age,
            blood_group=bg, phone=phone, neighbourhood=area, lat=lat, lng=lng,
            last_donation_date=last_don.isoformat(), days_since_last_donation=days,
            total_donations=total, times_contacted_last_30d=c30, response_rate=rr))
    return rows

def main():
    rows = build()
    cols = list(rows[0])
    placeholders = ", ".join("?" for _ in cols)
    # Fresh build every run — drop and recreate so re-seeding is idempotent.
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(SCHEMA)
        conn.executemany(
            f"INSERT INTO donors ({', '.join(cols)}) VALUES ({placeholders})",
            [tuple(r[c] for c in cols) for r in rows],
        )
        conn.commit()
    bgc = Counter(r["blood_group"] for r in rows)
    elig = sum(1 for r in rows if (r["gender"]=="Male" and r["days_since_last_donation"]>90)
                                 or (r["gender"]=="Female" and r["days_since_last_donation"]>120))
    print(f"Wrote {DB_PATH}  ({len(rows)} rows)")
    print(f"Eligible by recovery window: {elig} ({round(100*elig/len(rows))}%)")
    print("Blood-group mix:", dict(sorted(bgc.items(), key=lambda x: -x[1])))

if __name__ == "__main__":
    main()
