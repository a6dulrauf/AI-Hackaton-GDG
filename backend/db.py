"""
LifeLine — SQLite data layer.

A single portable database file (data/lifeline.db) ships with the repo so any
developer gets the full donor dataset on clone — no setup, no driver, no
connection string. This module is the *read* side: it opens that file and hands
the donor table to the app as a list of plain dicts with native types
(int age / float lat,lng,response_rate) so ranking.py and the frontend get
real numbers instead of CSV strings.

Seeding is done by `data/generate_donors.py` (run once, reproducible). To
inspect the data by hand: `sqlite3 data/lifeline.db "select * from donors limit 5"`.
"""
import os
import sqlite3

# --- Paths --------------------------------------------------------------------
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(BACKEND_DIR)
DB_PATH = os.path.join(REPO_ROOT, "data", "lifeline.db")

# Column -> SQLite type. Declared types give us native int/real back on read
# (instead of the all-strings we used to get from csv.DictReader).
DONOR_COLUMNS = {
    "donor_id": "TEXT PRIMARY KEY",
    "name": "TEXT",
    "gender": "TEXT",
    "dob": "TEXT",
    "age": "INTEGER",
    "blood_group": "TEXT",
    "phone": "TEXT",
    "neighbourhood": "TEXT",
    "lat": "REAL",
    "lng": "REAL",
    "last_donation_date": "TEXT",
    "days_since_last_donation": "INTEGER",
    "total_donations": "INTEGER",
    "times_contacted_last_30d": "INTEGER",
    "response_rate": "REAL",
}

CREATE_DONORS_SQL = (
    "CREATE TABLE IF NOT EXISTS donors (\n  "
    + ",\n  ".join(f"{name} {decl}" for name, decl in DONOR_COLUMNS.items())
    + "\n)"
)


def connect(path: str = DB_PATH) -> sqlite3.Connection:
    """Open a connection with a dict-friendly row factory."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def load_donors(path: str = DB_PATH) -> list[dict]:
    """Load all donors from the SQLite file as a list of dicts.

    Returns [] (with a warning) if the database is missing, so the app still
    boots — mirrors the old CSV behaviour."""
    if not os.path.exists(path):
        print(f"[startup] WARNING: {path} not found. "
              f"Run `cd data && python generate_donors.py` to create it.")
        return []
    with connect(path) as conn:
        rows = conn.execute("SELECT * FROM donors ORDER BY donor_id").fetchall()
    donors = [dict(r) for r in rows]
    print(f"[startup] Loaded {len(donors)} donors from {path}")
    return donors
