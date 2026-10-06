"""SQLite schema, connections, and one-time local demo seed."""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .config import DATABASE_PATH

DEPARTMENTS = (
    ("Roads", "Road maintenance, potholes & street repairs", "⌁", 48),
    ("Sanitation", "Waste collection & neighborhood cleanliness", "♻", 24),
    ("Electrical", "Street lighting & traffic signals", "☼", 36),
    ("Water Supply", "Water lines, leakage & drainage", "≈", 24),
    ("Public Works", "Parks, sidewalks & public infrastructure", "⌂", 72),
)
STAFF = (
    ("worker-1", "Taylor Brooks", "Roads", ["Pothole", "Road damage"]),
    ("worker-2", "Morgan Chen", "Roads", ["Road damage", "Pothole"]),
    ("worker-3", "Jamie Patel", "Sanitation", ["Garbage"]),
    ("worker-4", "Casey Nguyen", "Electrical", ["Streetlight", "Traffic signal"]),
    ("worker-5", "Riley James", "Water Supply", ["Water leakage", "Drainage"]),
    ("worker-6", "Avery Kim", "Public Works", ["Public infrastructure", "Other"]),
)
DEMO_USERS = (
    ("demo-citizen", "Alex Morgan", "alex@civicflow.local", "citizen", None),
    ("demo-admin", "Jordan Lee", "admin@civicflow.local", "admin", None),
    ("demo-supervisor", "Sam Rivera", "supervisor@civicflow.local", "supervisor", "Roads"),
    ("demo-worker", "Taylor Brooks", "worker@civicflow.local", "worker", "Roads"),
    ("demo-staff", "Robin Singh", "staff@civicflow.local", "staff", "Roads"),
    ("demo-department_admin", "Priya Nair", "department-admin@civicflow.local", "department_admin", "Roads"),
    ("demo-city_admin", "Asha Rao", "city-admin@civicflow.local", "city_admin", None),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS departments (
    name TEXT PRIMARY KEY COLLATE NOCASE,
    description TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT '◇',
    sla_hours INTEGER NOT NULL DEFAULT 48 CHECK (sla_hours BETWEEN 1 AND 8760),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    role TEXT NOT NULL CHECK (role IN ('citizen', 'admin', 'supervisor', 'worker', 'staff', 'department_admin', 'city_admin')),
    department TEXT REFERENCES departments(name),
    password_hash TEXT,
    created_at INTEGER NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);
CREATE TABLE IF NOT EXISTS staff (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    department TEXT NOT NULL REFERENCES departments(name),
    skills_json TEXT NOT NULL DEFAULT '[]',
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    location TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    reported_at INTEGER NOT NULL,
    citizen_name TEXT NOT NULL,
    citizen_id TEXT REFERENCES users(id),
    status TEXT NOT NULL,
    severity TEXT NOT NULL,
    priority INTEGER NOT NULL CHECK (priority BETWEEN 0 AND 100),
    department TEXT REFERENCES departments(name),
    worker TEXT,
    latitude REAL,
    longitude REAL,
    duplicate_of TEXT REFERENCES reports(id),
    image TEXT NOT NULL DEFAULT '',
    resolution TEXT,
    resolution_image TEXT NOT NULL DEFAULT '',
    resolved_at INTEGER,
    feedback_rating INTEGER CHECK (feedback_rating BETWEEN 1 AND 5),
    feedback_comment TEXT,
    feedback_at INTEGER
);
CREATE INDEX IF NOT EXISTS idx_reports_status_priority ON reports(status, priority DESC);
CREATE INDEX IF NOT EXISTS idx_reports_category_location ON reports(category, location);
CREATE INDEX IF NOT EXISTS idx_reports_created ON reports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_department_status ON reports(department, status);
CREATE TABLE IF NOT EXISTS report_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    actor TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_report_date ON report_events(report_id, created_at);
CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    message TEXT NOT NULL,
    report_id TEXT REFERENCES reports(id) ON DELETE SET NULL,
    recipient_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    created_at INTEGER NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0 CHECK (is_read IN (0, 1))
);
CREATE INDEX IF NOT EXISTS idx_notifications_recipient_date ON notifications(recipient_id, created_at DESC);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    actor_name TEXT NOT NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_date ON audit_log(created_at DESC);
CREATE TABLE IF NOT EXISTS escalation_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    level INTEGER NOT NULL CHECK (level > 0),
    reason TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    UNIQUE(report_id, level)
);
CREATE INDEX IF NOT EXISTS idx_escalation_report ON escalation_records(report_id, created_at DESC);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions(expires_at);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at INTEGER NOT NULL
);
"""


def connect(path: Path = DATABASE_PATH) -> sqlite3.Connection:
    """Open a configured SQLite connection; SQLite is embedded and needs no service."""
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


@contextmanager
def transaction(path: Path = DATABASE_PATH) -> Iterator[sqlite3.Connection]:
    connection = connect(path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


@contextmanager
def read_connection(path: Path = DATABASE_PATH) -> Iterator[sqlite3.Connection]:
    connection = connect(path)
    try:
        yield connection
    finally:
        connection.close()


def initialize(path: Path = DATABASE_PATH) -> None:
    """Create schema and deterministic sample records if this is a new database."""
    connection = connect(path)
    try:
        connection.executescript(SCHEMA)
    finally:
        connection.close()
    with transaction(path) as connection:
        connection.execute(
            "INSERT OR IGNORE INTO schema_version(version, applied_at) VALUES(1, ?)",
            (int(time.time() * 1000),),
        )
        report_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(reports)")
        }
        if "resolved_at" not in report_columns:
            connection.execute("ALTER TABLE reports ADD COLUMN resolved_at INTEGER")
        stamp = int(time.time() * 1000)
        for name, description, icon, sla_hours in DEPARTMENTS:
            connection.execute(
                """INSERT OR IGNORE INTO departments(name, description, icon, sla_hours, created_at)
                   VALUES(?, ?, ?, ?, ?)""",
                (name, description, icon, sla_hours, stamp),
            )
        for user_id, name, email, role, department in DEMO_USERS:
            connection.execute(
                """INSERT OR IGNORE INTO users(id, name, email, role, department, created_at)
                   VALUES(?, ?, ?, ?, ?, ?)""",
                (user_id, name, email, role, department, stamp),
            )
        for staff_id, name, department, skills in STAFF:
            connection.execute(
                """INSERT OR IGNORE INTO staff(id, name, department, skills_json, created_at)
                   VALUES(?, ?, ?, ?, ?)""",
                (staff_id, name, department, json.dumps(skills), stamp),
            )
        if connection.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 0:
            _seed_reports(connection, stamp)
        connection.execute(
            "INSERT OR IGNORE INTO settings(key, value_json, updated_at) VALUES('city_name', ?, ?)",
            (json.dumps("CivicFlow City"), stamp),
        )
        connection.execute(
            """UPDATE reports SET resolved_at=(
                 SELECT MAX(created_at) FROM report_events e
                 WHERE e.report_id=reports.id AND e.status='Resolved'
               )
               WHERE status='Resolved' AND resolved_at IS NULL"""
        )


def _seed_reports(connection: sqlite3.Connection, now: int) -> None:
    samples = (
        ("CF-1042", "Deep pothole on Oak Avenue", "Pothole",
         "A deep pothole has formed by the crosswalk and drivers are swerving into the next lane.",
         "Oak Avenue & 3rd Street", "demo-citizen", "Alex Morgan", "In progress", "High", 82,
         "Roads", "Taylor Brooks", 37, "Jordan Lee", 16.5121, 80.6298),
        ("CF-1041", "Streetlight out near Maple Park", "Streetlight",
         "The lamp on the northeast corner has been out for several nights.",
         "Maple Park, north entrance", None, "Priya Shah", "Awaiting review", "Medium", 51,
         "Electrical", None, 240, None, 16.5204, 80.6405),
        ("CF-1040", "Overflowing bins on Pine Street", "Garbage",
         "Public bins are overflowing and litter is spreading onto the sidewalk.",
         "Pine Street, block 200", None, "Noah Williams", "Assigned", "Medium", 59,
         "Sanitation", "Jamie Patel", 1140, "Jordan Lee", 16.5068, 80.6317),
        ("CF-1039", "Water leak by community center", "Water leakage",
         "Water is pooling near the sidewalk and appears to be coming from below the road.",
         "Riverside Community Center", None, "Elena Garcia", "Resolved", "Critical", 96,
         "Water Supply", "Riley James", 1800, "Sam Rivera", 16.5180, 80.6362),
        ("CF-1038", "Broken bench in Cedar Square", "Public infrastructure",
         "The bench beside the playground has a loose, broken plank.",
         "Cedar Square playground", "demo-citizen", "Alex Morgan", "Awaiting review", "Low", 30,
         "Public Works", None, 2880, None, 16.5144, 80.6431),
    )
    for item in samples:
        (report_id, title, category, description, location, citizen_id, citizen_name,
         status, severity, priority, department, worker, age_minutes, assigned_by, latitude, longitude) = item
        created = now - age_minutes * 60_000
        connection.execute(
            """INSERT INTO reports(
                id, title, category, description, location, created_at, reported_at,
                citizen_name, citizen_id, status, severity, priority, department, worker,
                resolution, resolved_at, latitude, longitude
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (report_id, title, category, description, location, created, created,
             citizen_name, citizen_id, status, severity, priority, department, worker,
             "Repaired the damaged connection and cleared standing water."
             if status == "Resolved" else None,
             created + 180_000 if status == "Resolved" else None, latitude, longitude),
        )
        events = [("Reported", citizen_name, "", created)]
        if status in ("Assigned", "In progress", "Resolved"):
            events.append(("Assigned", assigned_by or "Jordan Lee", department, created + 60_000))
        if status == "In progress":
            events.append(("In progress", worker or "Field worker", "", created + 90_000))
        if status == "Resolved":
            events.append(("In progress", worker or "Field worker", "", created + 2 * 60 * 60_000))
            events.append(("Resolved", assigned_by or "Sam Rivera", "", created + 3 * 60 * 60_000))
            connection.execute(
                "UPDATE reports SET feedback_rating=5, feedback_comment=?, feedback_at=? WHERE id=?",
                ("Thanks for sorting this out so quickly.", created + 3 * 60 * 60_000 + 20 * 60_000, report_id),
            )
        for event_status, actor, note, event_time in events:
            connection.execute(
                """INSERT INTO report_events(report_id, status, actor, note, created_at)
                   VALUES(?, ?, ?, ?, ?)""",
                (report_id, event_status, actor, note, event_time),
            )
