"""
database.py – SQLite data layer.

Handles:
  • Schema creation / migration
  • User management (create, authenticate)
  • Vehicle registry
  • StandardParameters CRUD and average calculation
  • Score persistence (local JSON; Firebase removed)

All public functions open and close their own connection so callers
don't need to manage connection state.
"""

import json
import sqlite3
from sqlite3 import Error
from pathlib import Path

from hashing import hash_password
from config import DATABASE, SCORES_FILE

# ── Default tuning parameters ─────────────────────────────────────────────────

STANDARD_PARAMETERS: dict[str, tuple[float, str]] = {
    "Adjust Torque Levels":
        (500,  "Engine torque in Nm"),
    "Change Tire Width":
        (1,    "Multiplier for tire width"),
    "Modify Drag Coefficient":
        (0.3,  "Drag coefficient for aerodynamic resistance"),
    "Adjust Gear Ratio":
        (3.5,  "Gear ratio for power transmission"),
    "Adjust Damping and Rebound Settings\n(Suspension System)":
        (1,    "Multiplier for suspension damping performance"),
    "Adjust Brake Caliper Settings":
        (1,    "Multiplier for brake caliper performance"),
    "Alter Weight Distribution\nThroughout Vehicle":
        (50,   "Percentage of weight distribution at the front"),
    "Modifying Differential Limited-Slip Settings\nfor Various Driving Conditions":
        (1,    "Multiplier for differential slip performance"),
    "Adjust Fuel-Air Mixture\nand Injection Timing":
        (14.7, "Standard stoichiometric fuel-air mixture"),
    "Modify Exhaust Diameter and Configuration":
        (2.5,  "Exhaust diameter in inches"),
    "Adjust ECU Parameters":
        (1,    "Multiplier for Engine Control Unit performance"),
    "Adjust Vehicle Cold Air Intake (CAI)":
        (1,    "Multiplier for cold air intake flow"),
}

# ── Internal helpers ──────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection | None:
    """Open a database connection; returns None on failure."""
    try:
        return sqlite3.connect(DATABASE)
    except Error as exc:
        print(f"[DB] Connection error: {exc}")
        return None


# ── Schema ────────────────────────────────────────────────────────────────────

def initialise_database() -> None:
    """Create all tables if they do not already exist."""
    conn = _connect()
    if conn is None:
        return
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS Users (
                user_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT    NOT NULL UNIQUE,
                password    TEXT    NOT NULL,
                date_joined DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS Vehicles (
                vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                make       TEXT NOT NULL,
                model      TEXT NOT NULL,
                year       INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS UserVehicles (
                user_id              INTEGER,
                vehicle_id           INTEGER,
                customization_details TEXT,
                PRIMARY KEY (user_id, vehicle_id),
                FOREIGN KEY (user_id)    REFERENCES Users(user_id),
                FOREIGN KEY (vehicle_id) REFERENCES Vehicles(vehicle_id)
            );

            CREATE TABLE IF NOT EXISTS StandardParameters (
                parameter_name TEXT PRIMARY KEY,
                value          REAL,
                description    TEXT
            );

            CREATE TABLE IF NOT EXISTS vehicle_performance (
                vehicle_id                     INTEGER PRIMARY KEY AUTOINCREMENT,
                torque_level                   REAL,
                tire_width_multiplier          REAL,
                drag_coefficient               REAL,
                gear_ratio                     REAL,
                suspension_damping_multiplier  REAL,
                brake_caliper_multiplier       REAL,
                weight_distribution_percentage REAL,
                differential_slip_multiplier   REAL,
                fuel_air_mixture_ratio         REAL,
                exhaust_diameter_inches        REAL,
                ecu_performance_multiplier     REAL,
                cold_air_intake_flow_multiplier REAL,
                FOREIGN KEY (vehicle_id) REFERENCES Vehicles(vehicle_id)
            );
        """)
        conn.commit()
        print("[DB] Schema ready.")
    except Error as exc:
        print(f"[DB] Schema error: {exc}")
    finally:
        conn.close()


def populate_standard_parameters() -> None:
    """Insert default parameter values (INSERT OR REPLACE – idempotent)."""
    conn = _connect()
    if conn is None:
        return
    try:
        cur = conn.cursor()
        for name, (value, desc) in STANDARD_PARAMETERS.items():
            cur.execute(
                "INSERT OR REPLACE INTO StandardParameters (parameter_name, value, description) "
                "VALUES (?, ?, ?);",
                (name, value, desc),
            )
        conn.commit()
        print("[DB] Standard parameters populated.")
    except Error as exc:
        print(f"[DB] Populate error: {exc}")
    finally:
        conn.close()


# ── StandardParameters ────────────────────────────────────────────────────────

def update_standard_parameters(modified: dict[str, float]) -> None:
    """Persist slider-modified parameter values to the database."""
    conn = _connect()
    if conn is None:
        return
    try:
        cur = conn.cursor()
        for name, value in modified.items():
            cur.execute(
                "UPDATE StandardParameters SET value = ? WHERE parameter_name = ?;",
                (value, name),
            )
        conn.commit()
        print("[DB] Parameters updated.")
    except Error as exc:
        print(f"[DB] Update error: {exc}")
    finally:
        conn.close()


def calculate_average_value() -> float | None:
    """Return the mean of all StandardParameter values, or None on failure."""
    conn = _connect()
    if conn is None:
        return None
    try:
        result = conn.execute("SELECT AVG(value) FROM StandardParameters;").fetchone()
        avg = result[0] if result else None
        print(f"[DB] Average parameter value: {avg}")
        return avg
    except Error as exc:
        print(f"[DB] Average error: {exc}")
        return None
    finally:
        conn.close()


# ── User management ───────────────────────────────────────────────────────────

def create_user(username: str, password: str) -> bool:
    """
    Register a new user. *password* should be the plain-text string;
    this function hashes it before storage.

    Returns True on success, False if the username is already taken.
    """
    conn = _connect()
    if conn is None:
        return False
    hashed = hash_password(password)
    try:
        conn.execute(
            "INSERT INTO Users (username, password) VALUES (?, ?);",
            (username, hashed),
        )
        conn.commit()
        print(f"[DB] User '{username}' created.")
        return True
    except sqlite3.IntegrityError:
        print(f"[DB] Username '{username}' already exists.")
        return False
    except Error as exc:
        print(f"[DB] Create user error: {exc}")
        return False
    finally:
        conn.close()


def authenticate_user(username: str, password: str) -> bool:
    """
    Return True if *username* / *password* match the stored record.
    *password* is the plain-text input; it is hashed for comparison.
    """
    conn = _connect()
    if conn is None:
        return False
    try:
        row = conn.execute(
            "SELECT password FROM Users WHERE username = ?;", (username,)
        ).fetchone()
        if not row:
            print("[DB] Username not found.")
            return False

        stored = int(row[0])
        candidate = int(hash_password(password))
        success = stored == candidate
        print(f"[DB] Auth for '{username}': {'OK' if success else 'FAIL'}")
        return success
    except (Error, ValueError) as exc:
        print(f"[DB] Auth error: {exc}")
        return False
    finally:
        conn.close()


# ── Vehicle registry ──────────────────────────────────────────────────────────

def get_vehicle_id(make: str, model: str, year: int) -> int | None:
    """Look up vehicle_id by make/model/year; returns None if not found."""
    conn = _connect()
    if conn is None:
        return None
    try:
        row = conn.execute(
            "SELECT vehicle_id FROM Vehicles WHERE make=? AND model=? AND year=?;",
            (make, model, year),
        ).fetchone()
        return row[0] if row else None
    except Error as exc:
        print(f"[DB] Vehicle lookup error: {exc}")
        return None
    finally:
        conn.close()


def load_parameters_from_database(vehicle_id: int) -> dict:
    """
    Load performance parameters for *vehicle_id*.
    Falls back to a copy of STANDARD_PARAMETERS if no record exists.
    """
    conn = _connect()
    if conn is None:
        return dict(STANDARD_PARAMETERS)
    try:
        row = conn.execute(
            "SELECT torque_level, drag_coefficient FROM vehicle_performance WHERE vehicle_id=?;",
            (vehicle_id,),
        ).fetchone()
        if row:
            return {"torque_level": row[0], "drag_coefficient": row[1]}
        return {k: v for k, (v, _) in STANDARD_PARAMETERS.items()}
    except Error as exc:
        print(f"[DB] Load params error: {exc}")
        return {k: v for k, (v, _) in STANDARD_PARAMETERS.items()}
    finally:
        conn.close()


# ── Score persistence (local only – Firebase removed) ─────────────────────────

def load_scores() -> list[dict]:
    """Load scores from the local JSON file; returns [] if missing/corrupt."""
    path = Path(SCORES_FILE)
    if not path.exists():
        return []
    try:
        with path.open() as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_score(username: str, score: float) -> None:
    """Append *score* for *username* to the local JSON scores file."""
    scores = load_scores()
    scores.append({"username": username, "score": score})
    try:
        with open(SCORES_FILE, "w") as f:
            json.dump(scores, f, indent=2)
        print(f"[Scores] Saved score {score:.0f} for '{username}'.")
    except OSError as exc:
        print(f"[Scores] Save error: {exc}")


# ── Entry point (run directly to initialise / seed the DB) ───────────────────
if __name__ == "__main__":
    initialise_database()
    populate_standard_parameters()