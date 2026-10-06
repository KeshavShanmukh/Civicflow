"""Extended CivicFlow platform services.

This module adds the enterprise-style capabilities required by the CivicFlow
specification while keeping the application local-first and free of external
API-key dependencies.  It intentionally uses only the Python standard
library and the existing SQLite data layer.
"""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import math
import re
import secrets
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

from .database import read_connection, transaction
from .service import CivicFlowService, DomainError, hash_password


EXTENDED_SCHEMA = """
CREATE TABLE IF NOT EXISTS roles (
    name TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS permissions (
    name TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS role_permissions (
    role_name TEXT NOT NULL REFERENCES roles(name) ON DELETE CASCADE,
    permission_name TEXT NOT NULL REFERENCES permissions(name) ON DELETE CASCADE,
    granted_at INTEGER NOT NULL,
    PRIMARY KEY(role_name, permission_name)
);
CREATE TABLE IF NOT EXISTS citizen_profiles (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    phone TEXT NOT NULL DEFAULT '',
    address_line1 TEXT NOT NULL DEFAULT '',
    address_line2 TEXT NOT NULL DEFAULT '',
    city TEXT NOT NULL DEFAULT '',
    postal_code TEXT NOT NULL DEFAULT '',
    latitude REAL,
    longitude REAL,
    preferred_language TEXT NOT NULL DEFAULT 'en-IN',
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS notification_preferences (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    report_updates INTEGER NOT NULL DEFAULT 1 CHECK(report_updates IN (0,1)),
    assignments INTEGER NOT NULL DEFAULT 1 CHECK(assignments IN (0,1)),
    escalations INTEGER NOT NULL DEFAULT 1 CHECK(escalations IN (0,1)),
    feedback INTEGER NOT NULL DEFAULT 1 CHECK(feedback IN (0,1)),
    system INTEGER NOT NULL DEFAULT 1 CHECK(system IN (0,1)),
    updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS account_verification_tokens (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at INTEGER NOT NULL,
    used_at INTEGER
);
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at INTEGER NOT NULL,
    used_at INTEGER
);
CREATE TABLE IF NOT EXISTS account_security (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until INTEGER,
    last_login_at INTEGER,
    last_failed_at INTEGER,
    verified_at INTEGER,
    updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS user_devices (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_label TEXT NOT NULL,
    fingerprint_hash TEXT NOT NULL,
    first_seen_at INTEGER NOT NULL,
    last_seen_at INTEGER NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1))
);
CREATE INDEX IF NOT EXISTS idx_user_devices_user ON user_devices(user_id, last_seen_at DESC);
CREATE TABLE IF NOT EXISTS address_book (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    address_text TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    is_primary INTEGER NOT NULL DEFAULT 0 CHECK(is_primary IN (0,1)),
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_address_book_user ON address_book(user_id, is_primary DESC, label);
CREATE TABLE IF NOT EXISTS report_comments (
    id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    author_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    author_name TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    edited_at INTEGER
);
CREATE INDEX IF NOT EXISTS idx_report_comments_report ON report_comments(report_id, created_at);
CREATE TABLE IF NOT EXISTS report_attachments (
    id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    data TEXT NOT NULL,
    checksum TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_report_attachments_report ON report_attachments(report_id, created_at);
CREATE TABLE IF NOT EXISTS duplicate_groups (
    id TEXT PRIMARY KEY,
    primary_report_id TEXT REFERENCES reports(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'candidate',
    score REAL NOT NULL DEFAULT 0,
    verified_by TEXT,
    verified_at INTEGER,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS duplicate_group_members (
    group_id TEXT NOT NULL REFERENCES duplicate_groups(id) ON DELETE CASCADE,
    report_id TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    relationship TEXT NOT NULL,
    score REAL NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    PRIMARY KEY(group_id, report_id)
);
CREATE INDEX IF NOT EXISTS idx_duplicate_members_report ON duplicate_group_members(report_id);
CREATE TABLE IF NOT EXISTS department_categories (
    department TEXT NOT NULL REFERENCES departments(name) ON DELETE CASCADE,
    category TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
    created_at INTEGER NOT NULL,
    PRIMARY KEY(department, category)
);
CREATE TABLE IF NOT EXISTS department_regions (
    id TEXT PRIMARY KEY,
    department TEXT NOT NULL REFERENCES departments(name) ON DELETE CASCADE,
    region_name TEXT NOT NULL,
    min_lat REAL NOT NULL,
    max_lat REAL NOT NULL,
    min_lon REAL NOT NULL,
    max_lon REAL NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_department_regions_bounds ON department_regions(department, min_lat, max_lat, min_lon, max_lon);
CREATE TABLE IF NOT EXISTS department_policies (
    department TEXT PRIMARY KEY REFERENCES departments(name) ON DELETE CASCADE,
    policy_json TEXT NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS worker_availability (
    worker_id TEXT PRIMARY KEY REFERENCES staff(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'available',
    available_from INTEGER,
    available_until INTEGER,
    updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS worker_leaves (
    id TEXT PRIMARY KEY,
    worker_id TEXT NOT NULL REFERENCES staff(id) ON DELETE CASCADE,
    starts_at INTEGER NOT NULL,
    ends_at INTEGER NOT NULL,
    reason TEXT NOT NULL,
    approved INTEGER NOT NULL DEFAULT 0 CHECK(approved IN (0,1)),
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_worker_leaves_worker ON worker_leaves(worker_id, starts_at, ends_at);
CREATE TABLE IF NOT EXISTS work_orders (
    id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL UNIQUE REFERENCES reports(id) ON DELETE CASCADE,
    department TEXT NOT NULL REFERENCES departments(name),
    supervisor_id TEXT,
    worker_id TEXT,
    title TEXT NOT NULL,
    instructions TEXT NOT NULL DEFAULT '',
    materials_json TEXT NOT NULL DEFAULT '[]',
    estimated_minutes INTEGER NOT NULL DEFAULT 60,
    actual_minutes INTEGER,
    status TEXT NOT NULL,
    scheduled_start INTEGER,
    scheduled_end INTEGER,
    started_at INTEGER,
    completed_at INTEGER,
    verified_at INTEGER,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_work_orders_department_status ON work_orders(department, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_work_orders_worker_status ON work_orders(worker_id, status, updated_at DESC);
CREATE TABLE IF NOT EXISTS work_order_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_order_id TEXT NOT NULL REFERENCES work_orders(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    actor_id TEXT,
    actor_name TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_work_order_events_order ON work_order_events(work_order_id, created_at);
CREATE TABLE IF NOT EXISTS sla_policies (
    id TEXT PRIMARY KEY,
    department TEXT NOT NULL REFERENCES departments(name) ON DELETE CASCADE,
    severity TEXT NOT NULL,
    target_hours INTEGER NOT NULL CHECK(target_hours > 0),
    warning_ratio REAL NOT NULL DEFAULT 0.75,
    escalation_level INTEGER NOT NULL DEFAULT 1,
    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    UNIQUE(department, severity)
);
CREATE TABLE IF NOT EXISTS search_terms (
    term TEXT PRIMARY KEY,
    document_type TEXT NOT NULL,
    document_id TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 1,
    updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_search_terms_lookup ON search_terms(document_type, term, weight DESC);
CREATE TABLE IF NOT EXISTS analytics_snapshots (
    id TEXT PRIMARY KEY,
    scope_type TEXT NOT NULL,
    scope_id TEXT NOT NULL,
    period_start INTEGER NOT NULL,
    period_end INTEGER NOT NULL,
    metrics_json TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    UNIQUE(scope_type, scope_id, period_start, period_end)
);
CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id TEXT PRIMARY KEY,
    job_name TEXT NOT NULL,
    schedule_key TEXT NOT NULL UNIQUE,
    last_run_at INTEGER,
    next_run_at INTEGER,
    enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1)),
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
"""


ROLE_SEED = (
    ("citizen", "Resident who submits and follows civic reports."),
    ("worker", "Field worker who executes assigned repairs."),
    ("supervisor", "Supervisor who reviews, assigns and verifies work."),
    ("staff", "Department staff member who manages operational queues."),
    ("department_admin", "Department administrator for local settings."),
    ("city_admin", "City administrator overseeing departments and analytics."),
    ("admin", "System administrator with platform-wide authority."),
)

PERMISSION_SEED = (
    ("report.create", "Create civic reports."),
    ("report.read.own", "Read owned citizen reports."),
    ("report.read.department", "Read reports routed to a department."),
    ("report.read.city", "Read city-wide reports."),
    ("report.update", "Update eligible report fields."),
    ("report.cancel", "Cancel eligible reports."),
    ("report.comment", "Comment on reports."),
    ("report.assign", "Assign reports to departments and workers."),
    ("report.verify", "Verify repair completion."),
    ("report.reopen", "Request a reopened resolution."),
    ("department.read", "Read department information."),
    ("department.manage", "Create and configure departments."),
    ("worker.read", "Read worker profiles and workload."),
    ("worker.manage", "Manage worker records."),
    ("workorder.read", "Read work orders."),
    ("workorder.manage", "Manage work orders."),
    ("sla.manage", "Manage service-level policies."),
    ("analytics.read", "Read analytics and dashboards."),
    ("analytics.export", "Export analytical reports."),
    ("audit.read", "Read audit records."),
    ("user.manage", "Manage user accounts and roles."),
    ("system.manage", "Manage platform configuration."),
)

ROLE_PERMISSIONS = {
    "citizen": {"report.create", "report.read.own", "report.comment", "report.reopen"},
    "worker": {"report.read.department", "report.comment", "workorder.read", "workorder.manage"},
    "supervisor": {"report.read.department", "report.update", "report.comment", "report.assign", "report.verify", "workorder.read", "workorder.manage", "worker.read", "analytics.read"},
    "staff": {"report.read.department", "report.update", "report.comment", "workorder.read", "workorder.manage", "worker.read", "analytics.read"},
    "department_admin": {"report.read.department", "report.update", "report.comment", "report.assign", "report.verify", "department.read", "department.manage", "worker.read", "worker.manage", "workorder.read", "workorder.manage", "sla.manage", "analytics.read", "analytics.export"},
    "city_admin": {"report.read.city", "report.update", "report.comment", "report.assign", "report.verify", "department.read", "department.manage", "worker.read", "worker.manage", "workorder.read", "workorder.manage", "sla.manage", "analytics.read", "analytics.export", "audit.read"},
    "admin": {permission for permission, _ in PERMISSION_SEED},
}


@dataclass(frozen=True)
class SearchResult:
    document_type: str
    document_id: str
    title: str
    score: float
    snippet: str


def platform_now() -> int:
    return int(time.time() * 1000)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s-]", " ", value.casefold())).strip()


def tokenize(value: str) -> tuple[str, ...]:
    return tuple(token for token in normalize_text(value).split() if len(token) >= 2)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class CivicFlowPlatform:
    """Facade for extended CivicFlow workflows and administration."""

    def __init__(self, database_path: Path, core: CivicFlowService | None = None) -> None:
        self.database_path = database_path
        self.core = core or CivicFlowService(database_path)
        self.ensure_schema()

    def ensure_schema(self) -> None:
        stamp = platform_now()
        with transaction(self.database_path) as connection:
            connection.executescript(EXTENDED_SCHEMA)
            for name, description in ROLE_SEED:
                connection.execute(
                    "INSERT OR IGNORE INTO roles(name, description, created_at) VALUES(?, ?, ?)",
                    (name, description, stamp),
                )
            for name, description in PERMISSION_SEED:
                connection.execute(
                    "INSERT OR IGNORE INTO permissions(name, description, created_at) VALUES(?, ?, ?)",
                    (name, description, stamp),
                )
            for role, permissions in ROLE_PERMISSIONS.items():
                for permission in permissions:
                    connection.execute(
                        "INSERT OR IGNORE INTO role_permissions(role_name, permission_name, granted_at) VALUES(?, ?, ?)",
                        (role, permission, stamp),
                    )
            for user in connection.execute("SELECT id FROM users"):
                connection.execute(
                    "INSERT OR IGNORE INTO account_security(user_id, updated_at) VALUES(?, ?)",
                    (user["id"], stamp),
                )
                connection.execute(
                    "INSERT OR IGNORE INTO notification_preferences(user_id, updated_at) VALUES(?, ?)",
                    (user["id"], stamp),
                )
                connection.execute(
                    "INSERT OR IGNORE INTO citizen_profiles(user_id, created_at, updated_at) VALUES(?, ?, ?)",
                    (user["id"], stamp, stamp),
                )
            self._backfill_work_orders(connection, stamp)
            self._backfill_sla(connection, stamp)

    def _backfill_work_orders(self, connection, stamp: int) -> None:
        rows = connection.execute(
            "SELECT id, department, worker, title, description, status, created_at FROM reports WHERE department IS NOT NULL"
        ).fetchall()
        for row in rows:
            order_id = f"WO-{row['id']}"
            connection.execute(
                """INSERT OR IGNORE INTO work_orders(
                    id, report_id, department, worker_id, title, instructions, status, created_at, updated_at
                ) VALUES(?, ?, ?, (SELECT id FROM staff WHERE name=? COLLATE NOCASE LIMIT 1), ?, ?, ?, ?, ?)""",
                (order_id, row["id"], row["department"], row["worker"], row["title"], row["description"], self._work_status(row["status"]), row["created_at"], stamp),
            )

    def _backfill_sla(self, connection, stamp: int) -> None:
        departments = connection.execute("SELECT name, sla_hours FROM departments WHERE active=1").fetchall()
        severities = ("Critical", "High", "Medium", "Low")
        for department in departments:
            defaults = {"Critical": max(1, department["sla_hours"] // 2), "High": department["sla_hours"], "Medium": department["sla_hours"] * 2, "Low": department["sla_hours"] * 4}
            for severity in severities:
                policy_id = f"SLA-{hash_token(department['name'] + ':' + severity)[:12]}"
                connection.execute(
                    """INSERT OR IGNORE INTO sla_policies(
                        id, department, severity, target_hours, warning_ratio, escalation_level, created_at, updated_at
                    ) VALUES(?, ?, ?, ?, 0.75, ?, ?, ?)""",
                    (policy_id, department["name"], severity, defaults[severity], 1, stamp, stamp),
                )

    @staticmethod
    def _work_status(report_status: str) -> str:
        return {
            "Assigned": "Assigned",
            "In progress": "In Progress",
            "Awaiting verification": "Completed",
            "Resolved": "Verified",
            "Cancelled": "Cancelled",
        }.get(report_status, "Created")

    # ------------------------------------------------------------------
    # Identity, security, roles and sessions.
    # ------------------------------------------------------------------
    def account_security(self, user_id: str) -> dict:
        with read_connection(self.database_path) as connection:
            row = connection.execute("SELECT * FROM account_security WHERE user_id=?", (user_id,)).fetchone()
            return dict(row) if row else {}

    def issue_verification_token(self, user_id: str, hours: int = 24) -> str:
        self._ensure_hours(hours)
        token = secrets.token_urlsafe(32)
        with transaction(self.database_path) as connection:
            self._require_user_row(connection, user_id)
            connection.execute("DELETE FROM account_verification_tokens WHERE user_id=?", (user_id,))
            connection.execute(
                "INSERT INTO account_verification_tokens(token_hash, user_id, expires_at) VALUES(?, ?, ?)",
                (hash_token(token), user_id, platform_now() + hours * 3_600_000),
            )
        return token

    def verify_account(self, token: str) -> None:
        if not token:
            raise DomainError("Verification token is required.")
        stamp = platform_now()
        with transaction(self.database_path) as connection:
            row = connection.execute(
                "SELECT user_id, expires_at, used_at FROM account_verification_tokens WHERE token_hash=?",
                (hash_token(token),),
            ).fetchone()
            if row is None or row["used_at"] is not None or row["expires_at"] <= stamp:
                raise DomainError("Verification token is invalid or expired.", 400)
            connection.execute("UPDATE account_security SET verified_at=?, updated_at=? WHERE user_id=?", (stamp, stamp, row["user_id"]))
            connection.execute("UPDATE account_verification_tokens SET used_at=? WHERE token_hash=?", (stamp, hash_token(token)))

    def issue_password_reset(self, email: str, hours: int = 1) -> str | None:
        self._ensure_hours(hours)
        with transaction(self.database_path) as connection:
            row = connection.execute("SELECT id FROM users WHERE email=? COLLATE NOCASE AND active=1", (email.strip(),)).fetchone()
            if row is None:
                return None
            token = secrets.token_urlsafe(32)
            connection.execute("DELETE FROM password_reset_tokens WHERE user_id=?", (row["id"],))
            connection.execute(
                "INSERT INTO password_reset_tokens(token_hash, user_id, expires_at) VALUES(?, ?, ?)",
                (hash_token(token), row["id"], platform_now() + hours * 3_600_000),
            )
            return token

    def reset_password(self, token: str, new_password: str) -> None:
        self._validate_password(new_password)
        stamp = platform_now()
        with transaction(self.database_path) as connection:
            row = connection.execute(
                "SELECT user_id, expires_at, used_at FROM password_reset_tokens WHERE token_hash=?",
                (hash_token(token),),
            ).fetchone()
            if row is None or row["used_at"] is not None or row["expires_at"] <= stamp:
                raise DomainError("Password reset token is invalid or expired.")
            encoded = hash_password(new_password)
            connection.execute("UPDATE users SET password_hash=? WHERE id=?", (encoded, row["user_id"]))
            connection.execute("DELETE FROM sessions WHERE user_id=?", (row["user_id"],))
            connection.execute("UPDATE password_reset_tokens SET used_at=? WHERE token_hash=?", (stamp, hash_token(token)))

    def set_account_lock(self, actor: dict, user_id: str, locked: bool, minutes: int = 60) -> None:
        self._require_admin(actor)
        if locked:
            self._ensure_positive(minutes)
            locked_until = platform_now() + minutes * 60_000
        else:
            locked_until = None
        with transaction(self.database_path) as connection:
            self._require_user_row(connection, user_id)
            connection.execute(
                "UPDATE account_security SET locked_until=?, failed_attempts=0, updated_at=? WHERE user_id=?",
                (locked_until, platform_now(), user_id),
            )
            connection.execute(
                "INSERT INTO audit_log(actor_id, actor_name, action, entity_type, entity_id, details_json, created_at) VALUES(?, ?, ?, 'user', ?, ?, ?)",
                (actor["id"], actor["name"], "account_lock_changed", user_id, json.dumps({"locked": locked}), platform_now()),
            )

    def register_device(self, actor: dict, label: str, fingerprint: str) -> dict:
        label = label.strip()
        fingerprint = fingerprint.strip()
        if not 2 <= len(label) <= 80:
            raise DomainError("Device label must be between 2 and 80 characters.")
        if not 8 <= len(fingerprint) <= 256:
            raise DomainError("Device fingerprint is invalid.")
        now = platform_now()
        fingerprint_hash = hash_token(fingerprint)
        device_id = f"DEV-{secrets.token_hex(8)}"
        with transaction(self.database_path) as connection:
            existing = connection.execute(
                "SELECT id FROM user_devices WHERE user_id=? AND fingerprint_hash=? AND active=1",
                (actor["id"], fingerprint_hash),
            ).fetchone()
            if existing:
                connection.execute("UPDATE user_devices SET last_seen_at=?, device_label=? WHERE id=?", (now, label, existing["id"]))
                device_id = existing["id"]
            else:
                connection.execute(
                    "INSERT INTO user_devices(id, user_id, device_label, fingerprint_hash, first_seen_at, last_seen_at) VALUES(?, ?, ?, ?, ?, ?)",
                    (device_id, actor["id"], label, fingerprint_hash, now, now),
                )
        return {"id": device_id, "label": label, "lastSeenAt": now}

    def devices(self, actor: dict) -> list[dict]:
        with read_connection(self.database_path) as connection:
            return [dict(row) for row in connection.execute(
                "SELECT id, device_label AS label, first_seen_at AS firstSeenAt, last_seen_at AS lastSeenAt, active FROM user_devices WHERE user_id=? ORDER BY last_seen_at DESC",
                (actor["id"],),
            )]

    def revoke_device(self, actor: dict, device_id: str) -> None:
        with transaction(self.database_path) as connection:
            cursor = connection.execute("UPDATE user_devices SET active=0 WHERE id=? AND user_id=?", (device_id, actor["id"]))
            if cursor.rowcount != 1:
                raise DomainError("Device not found.", 404)

    def list_roles(self, actor: dict) -> list[dict]:
        self._require_permission(actor, "user.manage")
        with read_connection(self.database_path) as connection:
            return [dict(row) for row in connection.execute("SELECT name, description, active FROM roles ORDER BY name")]

    def set_role(self, actor: dict, user_id: str, role_name: str) -> None:
        self._require_permission(actor, "user.manage")
        role_name = role_name.strip().casefold()
        with transaction(self.database_path) as connection:
            self._require_user_row(connection, user_id)
            if connection.execute("SELECT 1 FROM roles WHERE name=? AND active=1", (role_name,)).fetchone() is None:
                raise DomainError("Unknown or inactive role.")
            connection.execute("UPDATE users SET role=? WHERE id=?", (role_name, user_id))
            self._platform_audit(connection, actor, "role_changed", "user", user_id, {"role": role_name})

    # ------------------------------------------------------------------
    # Profiles, addresses and preferences.
    # ------------------------------------------------------------------
    def get_profile(self, actor: dict) -> dict:
        with read_connection(self.database_path) as connection:
            user = self._require_user_row(connection, actor["id"])
            profile = connection.execute("SELECT * FROM citizen_profiles WHERE user_id=?", (actor["id"],)).fetchone()
            preference = connection.execute("SELECT * FROM notification_preferences WHERE user_id=?", (actor["id"],)).fetchone()
            addresses = connection.execute("SELECT id, label, address_text, latitude, longitude, is_primary FROM address_book WHERE user_id=? ORDER BY is_primary DESC, label", (actor["id"],)).fetchall()
            return {
                "user": dict(user),
                "profile": dict(profile) if profile else {},
                "preferences": dict(preference) if preference else {},
                "addresses": [dict(row) for row in addresses],
            }

    def update_profile(self, actor: dict, payload: dict) -> dict:
        phone = str(payload.get("phone", "")).strip()
        city = str(payload.get("city", "")).strip()
        postal = str(payload.get("postalCode", "")).strip()
        language = str(payload.get("preferredLanguage", "en-IN")).strip()
        if phone and not re.fullmatch(r"[+0-9 ()-]{7,20}", phone):
            raise DomainError("Phone number format is invalid.")
        if len(city) > 80 or len(postal) > 20 or len(language) > 20:
            raise DomainError("Profile field is too long.")
        lat, lon = self._coords(payload.get("latitude"), payload.get("longitude"))
        now = platform_now()
        with transaction(self.database_path) as connection:
            connection.execute(
                """INSERT INTO citizen_profiles(user_id, phone, address_line1, address_line2, city, postal_code, latitude, longitude, preferred_language, created_at, updated_at)
                   VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET phone=excluded.phone, address_line1=excluded.address_line1, address_line2=excluded.address_line2, city=excluded.city, postal_code=excluded.postal_code, latitude=excluded.latitude, longitude=excluded.longitude, preferred_language=excluded.preferred_language, updated_at=excluded.updated_at""",
                (actor["id"], phone, str(payload.get("addressLine1", "")).strip(), str(payload.get("addressLine2", "")).strip(), city, postal, lat, lon, language, now, now),
            )
            self._platform_audit(connection, actor, "profile_updated", "user", actor["id"], {})
        return self.get_profile(actor)

    def add_address(self, actor: dict, payload: dict) -> dict:
        label = str(payload.get("label", "")).strip()
        address = str(payload.get("address", "")).strip()
        if not 2 <= len(label) <= 50 or not 3 <= len(address) <= 240:
            raise DomainError("Address label or address is invalid.")
        lat, lon = self._coords(payload.get("latitude"), payload.get("longitude"))
        now = platform_now()
        address_id = f"ADDR-{secrets.token_hex(8)}"
        make_primary = bool(payload.get("primary", False))
        with transaction(self.database_path) as connection:
            if make_primary:
                connection.execute("UPDATE address_book SET is_primary=0 WHERE user_id=?", (actor["id"],))
            connection.execute(
                "INSERT INTO address_book(id, user_id, label, address_text, latitude, longitude, is_primary, created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (address_id, actor["id"], label, address, lat, lon, int(make_primary), now, now),
            )
        return {"id": address_id, "label": label, "address": address, "latitude": lat, "longitude": lon, "primary": make_primary}

    def remove_address(self, actor: dict, address_id: str) -> None:
        with transaction(self.database_path) as connection:
            row = connection.execute("SELECT id, is_primary FROM address_book WHERE id=? AND user_id=?", (address_id, actor["id"])).fetchone()
            if row is None:
                raise DomainError("Address not found.", 404)
            connection.execute("DELETE FROM address_book WHERE id=?", (address_id,))
            if row["is_primary"]:
                connection.execute("UPDATE address_book SET is_primary=1 WHERE id=(SELECT id FROM address_book WHERE user_id=? ORDER BY created_at LIMIT 1)", (actor["id"],))

    def update_notification_preferences(self, actor: dict, payload: dict) -> dict:
        fields = {key: int(bool(payload.get(key, True))) for key in ("reportUpdates", "assignments", "escalations", "feedback", "system")}
        now = platform_now()
        with transaction(self.database_path) as connection:
            connection.execute(
                """INSERT INTO notification_preferences(user_id, report_updates, assignments, escalations, feedback, system, updated_at)
                   VALUES(?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET report_updates=excluded.report_updates, assignments=excluded.assignments, escalations=excluded.escalations, feedback=excluded.feedback, system=excluded.system, updated_at=excluded.updated_at""",
                (actor["id"], fields["reportUpdates"], fields["assignments"], fields["escalations"], fields["feedback"], fields["system"], now),
            )
        return self.get_profile(actor)["preferences"]

    # ------------------------------------------------------------------
    # Report lifecycle, comments, attachments and duplicate groups.
    # ------------------------------------------------------------------
    def update_report(self, actor: dict, report_id: str, payload: dict) -> dict:
        with transaction(self.database_path) as connection:
            report = self._report(connection, report_id)
            self._can_edit_report(actor, report)
            editable = {
                "title": str(payload.get("title", report["title"])).strip(),
                "description": str(payload.get("description", report["description"])).strip(),
                "location": str(payload.get("location", report["location"])).strip(),
            }
            if not editable["title"] or not 12 <= len(editable["description"]) <= 1000 or not editable["location"]:
                raise DomainError("Title, description and location must be valid.")
            connection.execute("UPDATE reports SET title=?, description=?, location=? WHERE id=?", (editable["title"], editable["description"], editable["location"], report_id))
            self._platform_audit(connection, actor, "report_updated", "report", report_id, editable)
            return self._report_payload(connection, report_id)

    def cancel_report(self, actor: dict, report_id: str, reason: str = "") -> None:
        reason = reason.strip()
        if len(reason) > 500:
            raise DomainError("Cancellation reason is too long.")
        with transaction(self.database_path) as connection:
            report = self._report(connection, report_id)
            if actor["role"] == "citizen" and report["citizen_id"] != actor["id"]:
                raise DomainError("You can only cancel your own reports.", 403)
            if report["status"] in ("Resolved", "Cancelled"):
                raise DomainError("This report cannot be cancelled.", 409)
            connection.execute("UPDATE reports SET status='Cancelled' WHERE id=?", (report_id,))
            self._platform_audit(connection, actor, "report_cancelled", "report", report_id, {"reason": reason})

    def add_comment(self, actor: dict, report_id: str, body: str) -> dict:
        body = body.strip()
        if not 2 <= len(body) <= 1000:
            raise DomainError("Comment must be between 2 and 1,000 characters.")
        with transaction(self.database_path) as connection:
            report = self._report(connection, report_id)
            self._can_view_report(actor, report)
            comment_id = f"CMT-{secrets.token_hex(8)}"
            now = platform_now()
            connection.execute(
                "INSERT INTO report_comments(id, report_id, author_id, author_name, body, created_at) VALUES(?, ?, ?, ?, ?, ?)",
                (comment_id, report_id, actor["id"], actor["name"], body, now),
            )
            self._platform_audit(connection, actor, "report_comment_added", "report", report_id, {"commentId": comment_id})
            return {"id": comment_id, "reportId": report_id, "author": actor["name"], "body": body, "createdAt": now}

    def comments(self, actor: dict, report_id: str) -> list[dict]:
        with read_connection(self.database_path) as connection:
            report = self._report(connection, report_id)
            self._can_view_report(actor, report)
            return [dict(row) for row in connection.execute(
                "SELECT id, author_name AS author, body, created_at AS createdAt, edited_at AS editedAt FROM report_comments WHERE report_id=? ORDER BY created_at",
                (report_id,),
            )]

    def add_attachment(self, actor: dict, report_id: str, filename: str, mime_type: str, encoded: str, kind: str = "report") -> dict:
        filename = Path(filename).name
        if not filename or len(filename) > 150:
            raise DomainError("Attachment filename is invalid.")
        if mime_type not in {"image/png", "image/jpeg", "image/webp", "text/plain", "application/pdf"}:
            raise DomainError("Attachment type is not supported.")
        if len(encoded) > 4_000_000:
            raise DomainError("Attachment is too large.")
        try:
            base64.b64decode(encoded, validate=True)
        except Exception as exc:
            raise DomainError("Attachment data is invalid.") from exc
        with transaction(self.database_path) as connection:
            report = self._report(connection, report_id)
            self._can_edit_report(actor, report)
            attachment_id = f"ATT-{secrets.token_hex(8)}"
            checksum = hashlib.sha256(encoded.encode()).hexdigest()
            now = platform_now()
            connection.execute(
                "INSERT INTO report_attachments(id, report_id, kind, filename, mime_type, data, checksum, created_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                (attachment_id, report_id, kind, filename, mime_type, encoded, checksum, now),
            )
            return {"id": attachment_id, "reportId": report_id, "filename": filename, "mimeType": mime_type, "checksum": checksum, "createdAt": now}

    def attachments(self, actor: dict, report_id: str) -> list[dict]:
        with read_connection(self.database_path) as connection:
            report = self._report(connection, report_id)
            self._can_view_report(actor, report)
            return [dict(row) for row in connection.execute(
                "SELECT id, kind, filename, mime_type AS mimeType, checksum, created_at AS createdAt FROM report_attachments WHERE report_id=? ORDER BY created_at",
                (report_id,),
            )]

    def scan_duplicate_candidates(self, actor: dict, report_id: str | None = None, limit: int = 100) -> list[dict]:
        self._require_permission(actor, "report.read.department" if actor["role"] != "citizen" else "report.read.own")
        self._ensure_limit(limit)
        with read_connection(self.database_path) as connection:
            if report_id:
                base = self._report(connection, report_id)
                self._can_view_report(actor, base)
                rows = self._duplicate_candidates_for(connection, base, limit)
            else:
                rows = []
                reports = connection.execute("SELECT * FROM reports WHERE status NOT IN ('Resolved','Cancelled') ORDER BY created_at DESC LIMIT ?", (min(limit, 250),)).fetchall()
                for base in reports:
                    for candidate in self._duplicate_candidates_for(connection, base, 10):
                        rows.append({"source": base["id"], **candidate})
            return rows

    def verify_duplicate(self, actor: dict, source_report_id: str, duplicate_report_id: str, confirmed: bool, score: float = 0) -> dict:
        self._require_manager(actor)
        self._ensure_id(source_report_id)
        self._ensure_id(duplicate_report_id)
        if not 0 <= score <= 1:
            raise DomainError("Duplicate score must be between 0 and 1.")
        with transaction(self.database_path) as connection:
            source = self._report(connection, source_report_id)
            duplicate = self._report(connection, duplicate_report_id)
            self._can_manage_report(actor, source)
            self._can_manage_report(actor, duplicate)
            group = connection.execute(
                "SELECT group_id FROM duplicate_group_members WHERE report_id=? LIMIT 1", (source_report_id,)
            ).fetchone()
            group_id = group["group_id"] if group else f"DUP-{secrets.token_hex(8)}"
            now = platform_now()
            if not group:
                connection.execute(
                    "INSERT INTO duplicate_groups(id, primary_report_id, status, score, verified_by, verified_at, created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                    (group_id, source_report_id, "confirmed" if confirmed else "rejected", score, actor["name"], now, now, now),
                )
            else:
                connection.execute("UPDATE duplicate_groups SET status=?, score=?, verified_by=?, verified_at=?, updated_at=? WHERE id=?", ("confirmed" if confirmed else "rejected", score, actor["name"], now, now, group_id))
            relationship = "confirmed_duplicate" if confirmed else "not_duplicate"
            connection.execute(
                "INSERT OR REPLACE INTO duplicate_group_members(group_id, report_id, relationship, score, created_at) VALUES(?, ?, ?, ?, ?)",
                (group_id, duplicate_report_id, relationship, score, now),
            )
            if confirmed and source_report_id != duplicate_report_id:
                connection.execute("UPDATE reports SET duplicate_of=? WHERE id=?", (source_report_id, duplicate_report_id))
            self._platform_audit(connection, actor, "duplicate_verification", "duplicate_group", group_id, {"source": source_report_id, "duplicate": duplicate_report_id, "confirmed": confirmed, "score": score})
            return {"groupId": group_id, "confirmed": confirmed, "score": score}

    def merge_duplicate_group(self, actor: dict, group_id: str, primary_report_id: str) -> dict:
        self._require_manager(actor)
        with transaction(self.database_path) as connection:
            group = connection.execute("SELECT * FROM duplicate_groups WHERE id=?", (group_id,)).fetchone()
            if group is None:
                raise DomainError("Duplicate group not found.", 404)
            primary = self._report(connection, primary_report_id)
            self._can_manage_report(actor, primary)
            members = connection.execute("SELECT report_id FROM duplicate_group_members WHERE group_id=?", (group_id,)).fetchall()
            for member in members:
                if member["report_id"] != primary_report_id:
                    connection.execute("UPDATE reports SET duplicate_of=? WHERE id=?", (primary_report_id, member["report_id"]))
            now = platform_now()
            connection.execute("UPDATE duplicate_groups SET primary_report_id=?, status='merged', updated_at=? WHERE id=?", (primary_report_id, now, group_id))
            self._platform_audit(connection, actor, "duplicate_group_merged", "duplicate_group", group_id, {"primary": primary_report_id, "members": len(members)})
            return {"groupId": group_id, "primaryReportId": primary_report_id, "memberCount": len(members)}

    # ------------------------------------------------------------------
    # Departments, categories, regions, policies, workers and SLA.
    # ------------------------------------------------------------------
    def update_department(self, actor: dict, department: str, payload: dict) -> dict:
        self._require_admin(actor)
        with transaction(self.database_path) as connection:
            row = connection.execute("SELECT * FROM departments WHERE name=? COLLATE NOCASE", (department,)).fetchone()
            if row is None:
                raise DomainError("Department not found.", 404)
            name = str(payload.get("name", row["name"])).strip()
            description = str(payload.get("description", row["description"])).strip()
            sla = int(payload.get("slaHours", row["sla_hours"]))
            active = int(bool(payload.get("active", bool(row["active"]))))
            if not 2 <= len(name) <= 60 or not 8 <= len(description) <= 160 or not 1 <= sla <= 8760:
                raise DomainError("Department configuration is invalid.")
            if name.casefold() != row["name"].casefold():
                if connection.execute("SELECT 1 FROM departments WHERE name=? COLLATE NOCASE", (name,)).fetchone():
                    raise DomainError("That department name already exists.", 409)
                connection.execute("UPDATE departments SET name=?, description=?, sla_hours=?, active=? WHERE name=?", (name, description, sla, active, row["name"]))
                connection.execute("UPDATE staff SET department=? WHERE department=?", (name, row["name"]))
                connection.execute("UPDATE reports SET department=? WHERE department=?", (name, row["name"]))
            else:
                connection.execute("UPDATE departments SET description=?, sla_hours=?, active=? WHERE name=?", (description, sla, active, row["name"]))
            self._platform_audit(connection, actor, "department_updated", "department", name, {"active": active, "slaHours": sla})
            return dict(connection.execute("SELECT * FROM departments WHERE name=?", (name,)).fetchone())

    def set_department_categories(self, actor: dict, department: str, categories: list[str]) -> list[str]:
        self._require_admin(actor)
        categories = sorted({str(item).strip() for item in categories if str(item).strip()})
        if not categories or len(categories) > 50:
            raise DomainError("Provide between 1 and 50 categories.")
        with transaction(self.database_path) as connection:
            if connection.execute("SELECT 1 FROM departments WHERE name=?", (department,)).fetchone() is None:
                raise DomainError("Department not found.", 404)
            connection.execute("DELETE FROM department_categories WHERE department=?", (department,))
            now = platform_now()
            for category in categories:
                connection.execute("INSERT INTO department_categories(department, category, created_at) VALUES(?, ?, ?)", (department, category, now))
            self._platform_audit(connection, actor, "department_categories_set", "department", department, {"count": len(categories)})
        return categories

    def set_department_region(self, actor: dict, department: str, payload: dict) -> dict:
        self._require_admin(actor)
        name = str(payload.get("regionName", "")).strip()
        if not 2 <= len(name) <= 100:
            raise DomainError("Region name is invalid.")
        bounds = [float(payload.get(key)) for key in ("minLat", "maxLat", "minLon", "maxLon")]
        if not (-90 <= bounds[0] <= bounds[1] <= 90 and -180 <= bounds[2] <= bounds[3] <= 180):
            raise DomainError("Region bounds are invalid.")
        region_id = str(payload.get("id") or f"REG-{secrets.token_hex(8)}")
        with transaction(self.database_path) as connection:
            self._require_department(connection, department)
            connection.execute(
                "INSERT OR REPLACE INTO department_regions(id, department, region_name, min_lat, max_lat, min_lon, max_lon, active, created_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM department_regions WHERE id=?), ?))",
                (region_id, department, name, *bounds, int(bool(payload.get("active", True))), region_id, platform_now()),
            )
        return {"id": region_id, "department": department, "regionName": name, "minLat": bounds[0], "maxLat": bounds[1], "minLon": bounds[2], "maxLon": bounds[3]}

    def set_department_policy(self, actor: dict, department: str, policy: dict) -> dict:
        self._require_admin(actor)
        if not isinstance(policy, dict) or len(policy) > 100:
            raise DomainError("Policy payload is invalid.")
        encoded = json.dumps(policy, sort_keys=True)
        if len(encoded) > 20_000:
            raise DomainError("Policy payload is too large.")
        with transaction(self.database_path) as connection:
            self._require_department(connection, department)
            now = platform_now()
            connection.execute("INSERT INTO department_policies(department, policy_json, updated_at) VALUES(?, ?, ?) ON CONFLICT(department) DO UPDATE SET policy_json=excluded.policy_json, updated_at=excluded.updated_at", (department, encoded, now))
            self._platform_audit(connection, actor, "department_policy_set", "department", department, policy)
        return policy

    def worker_profile(self, actor: dict, worker_id: str) -> dict:
        with read_connection(self.database_path) as connection:
            row = connection.execute("SELECT * FROM staff WHERE id=?", (worker_id,)).fetchone()
            if row is None:
                raise DomainError("Worker not found.", 404)
            if actor["role"] == "worker" and actor["id"] != worker_id:
                raise DomainError("Workers can only inspect their own profile.", 403)
            availability = connection.execute("SELECT * FROM worker_availability WHERE worker_id=?", (worker_id,)).fetchone()
            leaves = connection.execute("SELECT * FROM worker_leaves WHERE worker_id=? ORDER BY starts_at DESC", (worker_id,)).fetchall()
            active_orders = connection.execute("SELECT COUNT(*) FROM work_orders WHERE worker_id=? AND status NOT IN ('Verified','Cancelled')", (worker_id,)).fetchone()[0]
            return {"worker": dict(row), "skills": json.loads(row["skills_json"]), "availability": dict(availability) if availability else {}, "leaves": [dict(item) for item in leaves], "activeOrders": active_orders}

    def update_worker_availability(self, actor: dict, worker_id: str, status: str, available_from: int | None, available_until: int | None) -> dict:
        status = status.strip().casefold()
        if status not in {"available", "busy", "leave", "offline"}:
            raise DomainError("Invalid worker availability status.")
        if available_from is not None and available_until is not None and available_until < available_from:
            raise DomainError("Availability window is invalid.")
        self._can_manage_worker(actor, worker_id)
        now = platform_now()
        with transaction(self.database_path) as connection:
            self._require_worker(connection, worker_id)
            connection.execute(
                "INSERT INTO worker_availability(worker_id, status, available_from, available_until, updated_at) VALUES(?, ?, ?, ?, ?) ON CONFLICT(worker_id) DO UPDATE SET status=excluded.status, available_from=excluded.available_from, available_until=excluded.available_until, updated_at=excluded.updated_at",
                (worker_id, status, available_from, available_until, now),
            )
        return self.worker_profile(actor, worker_id)["availability"]

    def request_worker_leave(self, actor: dict, worker_id: str, starts_at: int, ends_at: int, reason: str) -> dict:
        self._can_manage_worker(actor, worker_id)
        if ends_at <= starts_at:
            raise DomainError("Leave interval is invalid.")
        if not 3 <= len(reason.strip()) <= 240:
            raise DomainError("Leave reason is invalid.")
        leave_id = f"LEAVE-{secrets.token_hex(8)}"
        with transaction(self.database_path) as connection:
            self._require_worker(connection, worker_id)
            connection.execute("INSERT INTO worker_leaves(id, worker_id, starts_at, ends_at, reason, created_at) VALUES(?, ?, ?, ?, ?, ?)", (leave_id, worker_id, starts_at, ends_at, reason.strip(), platform_now()))
        return {"id": leave_id, "workerId": worker_id, "startsAt": starts_at, "endsAt": ends_at, "reason": reason.strip()}

    def configure_sla(self, actor: dict, department: str, severity: str, target_hours: int, warning_ratio: float = 0.75, escalation_level: int = 1) -> dict:
        self._require_admin(actor)
        if severity not in {"Critical", "High", "Medium", "Low"} or not 1 <= target_hours <= 8760 or not 0.1 <= warning_ratio <= 0.99 or not 1 <= escalation_level <= 3:
            raise DomainError("SLA policy values are invalid.")
        policy_id = f"SLA-{hash_token(department + ':' + severity)[:12]}"
        now = platform_now()
        with transaction(self.database_path) as connection:
            self._require_department(connection, department)
            connection.execute(
                "INSERT INTO sla_policies(id, department, severity, target_hours, warning_ratio, escalation_level, created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM sla_policies WHERE id=?), ?), ?) ON CONFLICT(department, severity) DO UPDATE SET target_hours=excluded.target_hours, warning_ratio=excluded.warning_ratio, escalation_level=excluded.escalation_level, updated_at=excluded.updated_at",
                (policy_id, department, severity, target_hours, warning_ratio, escalation_level, policy_id, now, now),
            )
        return self._sla_policy(policy_id)

    def sla_policies(self, actor: dict, department: str | None = None) -> list[dict]:
        self._require_permission(actor, "analytics.read")
        with read_connection(self.database_path) as connection:
            if department:
                rows = connection.execute("SELECT * FROM sla_policies WHERE department=? ORDER BY severity", (department,)).fetchall()
            else:
                rows = connection.execute("SELECT * FROM sla_policies ORDER BY department, severity").fetchall()
            return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Work orders and operational scheduling.
    # ------------------------------------------------------------------
    def create_work_order(self, actor: dict, report_id: str, instructions: str, estimated_minutes: int = 60, scheduled_start: int | None = None, scheduled_end: int | None = None) -> dict:
        self._require_manager(actor)
        if not 1 <= estimated_minutes <= 7_200:
            raise DomainError("Estimated work duration is invalid.")
        with transaction(self.database_path) as connection:
            report = self._report(connection, report_id)
            self._can_manage_report(actor, report)
            order = connection.execute("SELECT id FROM work_orders WHERE report_id=?", (report_id,)).fetchone()
            now = platform_now()
            order_id = order["id"] if order else f"WO-{secrets.token_hex(8)}"
            connection.execute(
                """INSERT INTO work_orders(id, report_id, department, supervisor_id, worker_id, title, instructions, estimated_minutes, status, scheduled_start, scheduled_end, created_at, updated_at)
                   VALUES(?, ?, ?, ?, (SELECT id FROM staff WHERE name=? COLLATE NOCASE LIMIT 1), ?, ?, ?, 'Created', ?, ?, ?, ?)
                   ON CONFLICT(report_id) DO UPDATE SET instructions=excluded.instructions, estimated_minutes=excluded.estimated_minutes, scheduled_start=excluded.scheduled_start, scheduled_end=excluded.scheduled_end, updated_at=excluded.updated_at""",
                (order_id, report_id, report["department"], actor["id"], report["worker"], report["title"], instructions.strip(), estimated_minutes, scheduled_start, scheduled_end, now, now),
            )
            self._order_event(connection, order_id, "Created", actor, instructions.strip())
            self._platform_audit(connection, actor, "work_order_created", "work_order", order_id, {"reportId": report_id})
        return self.work_order(actor, order_id)

    def work_order(self, actor: dict, order_id: str) -> dict:
        with read_connection(self.database_path) as connection:
            row = connection.execute("SELECT * FROM work_orders WHERE id=?", (order_id,)).fetchone()
            if row is None:
                raise DomainError("Work order not found.", 404)
            report = self._report(connection, row["report_id"])
            self._can_view_work_order(actor, row, report)
            events = connection.execute("SELECT status, actor_name AS actor, note, created_at AS createdAt FROM work_order_events WHERE work_order_id=? ORDER BY created_at", (order_id,)).fetchall()
            payload = dict(row)
            payload["materials"] = json.loads(payload.pop("materials_json"))
            payload["events"] = [dict(event) for event in events]
            return payload

    def list_work_orders(self, actor: dict, status: str | None = None, department: str | None = None, worker_id: str | None = None, page: int = 1, page_size: int = 25) -> dict:
        self._require_permission(actor, "workorder.read")
        self._ensure_page(page, page_size)
        clauses = []
        args: list[Any] = []
        if actor["role"] in {"worker"}:
            clauses.append("wo.worker_id=(SELECT id FROM staff WHERE name=(SELECT name FROM users WHERE id=?))")
            args.append(actor["id"])
        elif actor["role"] in {"supervisor", "staff", "department_admin"}:
            with read_connection(self.database_path) as connection:
                user = connection.execute("SELECT department FROM users WHERE id=?", (actor["id"],)).fetchone()
            if user and user["department"]:
                clauses.append("wo.department=?")
                args.append(user["department"])
        if status:
            clauses.append("wo.status=?")
            args.append(status)
        if department:
            clauses.append("wo.department=?")
            args.append(department)
        if worker_id:
            clauses.append("wo.worker_id=?")
            args.append(worker_id)
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        offset = (page - 1) * page_size
        with read_connection(self.database_path) as connection:
            total = connection.execute(f"SELECT COUNT(*) FROM work_orders wo {where}", args).fetchone()[0]
            rows = connection.execute(f"SELECT wo.id, wo.report_id, wo.department, wo.worker_id, wo.title, wo.status, wo.estimated_minutes, wo.actual_minutes, wo.scheduled_start, wo.scheduled_end, wo.updated_at FROM work_orders wo {where} ORDER BY wo.updated_at DESC LIMIT ? OFFSET ?", (*args, page_size, offset)).fetchall()
            return {"items": [dict(row) for row in rows], "page": page, "pageSize": page_size, "total": total}

    def update_work_order_status(self, actor: dict, order_id: str, status: str, note: str = "") -> dict:
        allowed = {"Created", "Assigned", "Accepted", "In Progress", "Blocked", "Awaiting Material", "Completed", "Verification", "Verified", "Rejected", "Cancelled"}
        status = status.strip()
        if status not in allowed:
            raise DomainError("Invalid work-order status.")
        with transaction(self.database_path) as connection:
            row = connection.execute("SELECT * FROM work_orders WHERE id=?", (order_id,)).fetchone()
            if row is None:
                raise DomainError("Work order not found.", 404)
            report = self._report(connection, row["report_id"])
            self._can_view_work_order(actor, row, report)
            now = platform_now()
            if actor["role"] == "worker" and status in {"Verified", "Cancelled"}:
                raise DomainError("Workers cannot perform this transition.", 403)
            started_at = row["started_at"] or (now if status == "In Progress" else None)
            completed_at = now if status == "Completed" else row["completed_at"]
            verified_at = now if status == "Verified" else row["verified_at"]
            connection.execute("UPDATE work_orders SET status=?, started_at=?, completed_at=?, verified_at=?, updated_at=? WHERE id=?", (status, started_at, completed_at, verified_at, now, order_id))
            self._order_event(connection, order_id, status, actor, note.strip())
            self._platform_audit(connection, actor, "work_order_status_changed", "work_order", order_id, {"status": status, "note": note.strip()})
        return self.work_order(actor, order_id)

    def assign_work_order(self, actor: dict, order_id: str, worker_id: str) -> dict:
        self._require_manager(actor)
        with transaction(self.database_path) as connection:
            order = connection.execute("SELECT * FROM work_orders WHERE id=?", (order_id,)).fetchone()
            if order is None:
                raise DomainError("Work order not found.", 404)
            report = self._report(connection, order["report_id"])
            self._can_manage_report(actor, report)
            worker = connection.execute("SELECT * FROM staff WHERE id=? AND active=1", (worker_id,)).fetchone()
            if worker is None or worker["department"] != order["department"]:
                raise DomainError("Worker is unavailable for this work order.")
            now = platform_now()
            connection.execute("UPDATE work_orders SET worker_id=?, status='Assigned', updated_at=? WHERE id=?", (worker_id, now, order_id))
            connection.execute("UPDATE reports SET worker=?, status='Assigned' WHERE id=?", (worker["name"], report["id"]))
            self._order_event(connection, order_id, "Assigned", actor, worker["name"])
            self._platform_audit(connection, actor, "work_order_assigned", "work_order", order_id, {"workerId": worker_id})
        return self.work_order(actor, order_id)

    # ------------------------------------------------------------------
    # Search, analytics, maps, reports and scheduled processing.
    # ------------------------------------------------------------------
    def search(self, actor: dict, query: str, document_types: Iterable[str] = ("report", "work_order", "comment"), limit: int = 50) -> list[dict]:
        self._ensure_limit(limit)
        tokens = tokenize(query)
        if not tokens:
            return []
        allowed_types = set(document_types)
        results: list[SearchResult] = []
        with read_connection(self.database_path) as connection:
            if "report" in allowed_types:
                rows = connection.execute("SELECT id, title, description, location, category, status FROM reports ORDER BY created_at DESC LIMIT 5000").fetchall()
                for row in rows:
                    if not self._actor_can_search_report(actor, row["id"], connection):
                        continue
                    score = self._search_score(tokens, (row["title"], row["description"], row["location"], row["category"], row["status"]))
                    if score:
                        results.append(SearchResult("report", row["id"], row["title"], score, self._snippet(row["description"], tokens)))
            if "work_order" in allowed_types:
                rows = connection.execute("SELECT id, report_id, title, instructions, status FROM work_orders ORDER BY updated_at DESC LIMIT 5000").fetchall()
                for row in rows:
                    report = connection.execute("SELECT id FROM reports WHERE id=?", (row["report_id"],)).fetchone()
                    if report and not self._actor_can_search_report(actor, report["id"], connection):
                        continue
                    score = self._search_score(tokens, (row["title"], row["instructions"], row["status"]))
                    if score:
                        results.append(SearchResult("work_order", row["id"], row["title"], score, self._snippet(row["instructions"], tokens)))
            if "comment" in allowed_types:
                rows = connection.execute("SELECT id, report_id, body FROM report_comments ORDER BY created_at DESC LIMIT 5000").fetchall()
                for row in rows:
                    if not self._actor_can_search_report(actor, row["report_id"], connection):
                        continue
                    score = self._search_score(tokens, (row["body"],))
                    if score:
                        results.append(SearchResult("comment", row["id"], f"Comment on {row['report_id']}", score, self._snippet(row["body"], tokens)))
        results.sort(key=lambda item: (-item.score, item.document_type, item.document_id))
        return [item.__dict__ for item in results[:limit]]

    def city_map_data(self, actor: dict, category: str | None = None, department: str | None = None, limit: int = 5000) -> dict:
        self._require_permission(actor, "analytics.read")
        self._ensure_limit(limit)
        clauses = ["latitude IS NOT NULL", "longitude IS NOT NULL"]
        args: list[Any] = []
        if category:
            clauses.append("category=?")
            args.append(category)
        if department:
            clauses.append("department=?")
            args.append(department)
        with read_connection(self.database_path) as connection:
            rows = connection.execute(f"SELECT id, title, category, status, severity, priority, department, latitude, longitude, created_at FROM reports WHERE {' AND '.join(clauses)} ORDER BY created_at DESC LIMIT ?", (*args, limit)).fetchall()
        points = [dict(row) for row in rows]
        return {"points": points, "count": len(points), "categories": Counter(row["category"] for row in rows), "bbox": self._bbox(points)}

    def hotspot_analysis(self, actor: dict, bucket_digits: int = 2) -> list[dict]:
        self._require_permission(actor, "analytics.read")
        if not 0 <= bucket_digits <= 4:
            raise DomainError("Hotspot precision must be between 0 and 4.")
        with read_connection(self.database_path) as connection:
            rows = connection.execute("SELECT id, category, department, severity, priority, latitude, longitude, status FROM reports WHERE latitude IS NOT NULL AND longitude IS NOT NULL").fetchall()
        groups: dict[tuple[float, float], dict[str, Any]] = {}
        for row in rows:
            key = (round(row["latitude"], bucket_digits), round(row["longitude"], bucket_digits))
            bucket = groups.setdefault(key, {"latitude": key[0], "longitude": key[1], "count": 0, "critical": 0, "open": 0, "categories": Counter()})
            bucket["count"] += 1
            bucket["critical"] += row["severity"] == "Critical"
            bucket["open"] += row["status"] not in ("Resolved", "Cancelled")
            bucket["categories"][row["category"]] += 1
        output = []
        for bucket in groups.values():
            bucket["categories"] = dict(bucket["categories"])
            bucket["riskScore"] = min(100, bucket["count"] * 4 + bucket["critical"] * 12 + bucket["open"] * 3)
            output.append(bucket)
        output.sort(key=lambda row: (-row["riskScore"], -row["count"]))
        return output[:100]

    def analytics_snapshot(self, actor: dict, scope_type: str, scope_id: str, period_start: int, period_end: int) -> dict:
        self._require_permission(actor, "analytics.read")
        if period_end <= period_start:
            raise DomainError("Analytics period is invalid.")
        with read_connection(self.database_path) as connection:
            clauses = ["created_at >= ?", "created_at <= ?"]
            args: list[Any] = [period_start, period_end]
            if scope_type == "department":
                clauses.append("department=?")
                args.append(scope_id)
            elif scope_type == "category":
                clauses.append("category=?")
                args.append(scope_id)
            elif scope_type not in {"city", "department", "category"}:
                raise DomainError("Unsupported analytics scope.")
            rows = connection.execute(f"SELECT * FROM reports WHERE {' AND '.join(clauses)}", args).fetchall()
        metrics = self._metrics(rows)
        now = platform_now()
        snapshot_id = f"SNAP-{hash_token(f'{scope_type}:{scope_id}:{period_start}:{period_end}')[:20]}"
        with transaction(self.database_path) as connection:
            connection.execute("INSERT OR REPLACE INTO analytics_snapshots(id, scope_type, scope_id, period_start, period_end, metrics_json, created_at) VALUES(?, ?, ?, ?, ?, ?, ?)", (snapshot_id, scope_type, scope_id, period_start, period_end, json.dumps(metrics, sort_keys=True), now))
        return {"id": snapshot_id, "scopeType": scope_type, "scopeId": scope_id, "periodStart": period_start, "periodEnd": period_end, "metrics": metrics}

    def export_report(self, actor: dict, fmt: str = "csv") -> str:
        self._require_permission(actor, "analytics.export")
        fmt = fmt.casefold()
        if fmt == "csv":
            return self.core.export_csv(actor)
        if fmt == "json":
            state = self.core.state(actor)
            return json.dumps(state["reports"], indent=2)
        if fmt == "txt":
            state = self.core.state(actor)
            lines = ["CivicFlow Report Export", "=======================", f"Generated: {datetime.now(timezone.utc).isoformat()}", f"Reports: {len(state['reports'])}", ""]
            for report in state["reports"]:
                lines.append(f"{report['id']} | {report['category']} | {report['status']} | {report['priority']} | {report['location']}")
            return "\n".join(lines)
        raise DomainError("Supported exports are csv, json and txt.")

    def run_scheduler(self) -> dict:
        stamp = platform_now()
        results = {
            "escalated": self.core.escalate_overdue(),
            "snapshots": 0,
            "jobs": 0,
        }
        with transaction(self.database_path) as connection:
            job_id = "JOB-sla-escalation"
            connection.execute("INSERT OR IGNORE INTO scheduled_jobs(id, job_name, schedule_key, enabled, created_at, updated_at) VALUES(?, 'SLA escalation', 'hourly-sla', 1, ?, ?)", (job_id, stamp, stamp))
            connection.execute("UPDATE scheduled_jobs SET last_run_at=?, next_run_at=?, updated_at=? WHERE id=?", (stamp, stamp + 3_600_000, stamp, job_id))
            results["jobs"] = 1
        return results

    def system_health(self, actor: dict) -> dict:
        self._require_permission(actor, "system.manage")
        with read_connection(self.database_path) as connection:
            tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
            checks = {
                "database": connection.execute("PRAGMA integrity_check").fetchone()[0],
                "foreignKeys": connection.execute("PRAGMA foreign_keys").fetchone()[0],
                "journalMode": connection.execute("PRAGMA journal_mode").fetchone()[0],
            }
            counts = {}
            for row in tables:
                name = row["name"]
                counts[name] = connection.execute(f"SELECT COUNT(*) FROM \"{name.replace(chr(34), chr(34)*2)}\"").fetchone()[0]
        return {"checks": checks, "tableCount": len(tables), "counts": counts}

    # ------------------------------------------------------------------
    # Internal helpers.
    # ------------------------------------------------------------------
    def _platform_audit(self, connection, actor: dict, action: str, entity_type: str, entity_id: str | None, details: dict) -> None:
        connection.execute(
            "INSERT INTO audit_log(actor_id, actor_name, action, entity_type, entity_id, details_json, created_at) VALUES(?, ?, ?, ?, ?, ?, ?)",
            (actor.get("id"), actor.get("name", "System"), action, entity_type, entity_id, json.dumps(details, sort_keys=True), platform_now()),
        )

    def _order_event(self, connection, order_id: str, status: str, actor: dict, note: str = "") -> None:
        connection.execute(
            "INSERT INTO work_order_events(work_order_id, status, actor_id, actor_name, note, created_at) VALUES(?, ?, ?, ?, ?, ?)",
            (order_id, status, actor.get("id"), actor.get("name", "System"), note, platform_now()),
        )

    def _report(self, connection, report_id: str):
        row = connection.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
        if row is None:
            raise DomainError("Report not found.", 404)
        return row

    def _report_payload(self, connection, report_id: str) -> dict:
        row = self._report(connection, report_id)
        return self.core._serialize_report(connection, row)

    def _require_user_row(self, connection, user_id: str):
        row = connection.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if row is None:
            raise DomainError("User not found.", 404)
        return row

    def _require_department(self, connection, department: str):
        row = connection.execute("SELECT * FROM departments WHERE name=?", (department,)).fetchone()
        if row is None:
            raise DomainError("Department not found.", 404)
        return row

    def _require_worker(self, connection, worker_id: str):
        row = connection.execute("SELECT * FROM staff WHERE id=?", (worker_id,)).fetchone()
        if row is None:
            raise DomainError("Worker not found.", 404)
        return row

    def _can_view_report(self, actor: dict, report) -> None:
        role = actor.get("role")
        if role == "citizen":
            if report["citizen_id"] != actor["id"]:
                raise DomainError("This report is not available to you.", 403)
        elif role == "worker":
            with read_connection(self.database_path) as connection:
                worker = connection.execute("SELECT name, department FROM users WHERE id=?", (actor["id"],)).fetchone()
            if worker is None or (report["worker"] != worker["name"] and report["department"] != worker["department"]):
                raise DomainError("This report is outside your work scope.", 403)

    def _can_manage_report(self, actor: dict, report) -> None:
        if actor.get("role") == "supervisor" and actor.get("department") and report["department"] != actor["department"]:
            raise DomainError("This report is outside your department.", 403)
        if actor.get("role") in {"citizen", "worker"}:
            raise DomainError("This action requires a manager role.", 403)

    def _can_edit_report(self, actor: dict, report) -> None:
        if actor.get("role") == "citizen":
            if report["citizen_id"] != actor["id"]:
                raise DomainError("You can only edit your own report.", 403)
            if report["status"] not in {"Awaiting review", "Reopened"}:
                raise DomainError("Only reports awaiting review can be edited.", 409)
        else:
            self._can_manage_report(actor, report)

    def _can_manage_worker(self, actor: dict, worker_id: str) -> None:
        if actor.get("role") == "worker":
            if actor.get("id") != worker_id:
                raise DomainError("You can only manage your own availability.", 403)
            return
        self._require_manager(actor)

    def _can_view_work_order(self, actor: dict, order, report) -> None:
        role = actor.get("role")
        if role == "citizen" and report["citizen_id"] != actor["id"]:
            raise DomainError("This work order is not available to you.", 403)
        if role == "worker":
            with read_connection(self.database_path) as connection:
                identity = connection.execute("SELECT name, department FROM users WHERE id=?", (actor["id"],)).fetchone()
                if identity is None:
                    raise DomainError("Worker identity was not found.", 403)
                if order["worker_id"] is not None:
                    assigned = connection.execute("SELECT id, name, department FROM staff WHERE id=?", (order["worker_id"],)).fetchone()
                    assigned_to_actor = bool(assigned and assigned["name"].casefold() == identity["name"].casefold())
                else:
                    assigned_to_actor = False
                same_department = order["department"] == identity["department"]
                if not assigned_to_actor and not same_department:
                    raise DomainError("This work order is outside your scope.", 403)

    def _actor_can_search_report(self, actor: dict, report_id: str, connection) -> bool:
        row = connection.execute("SELECT citizen_id, worker, department FROM reports WHERE id=?", (report_id,)).fetchone()
        if row is None:
            return False
        if actor.get("role") == "citizen":
            return row["citizen_id"] == actor["id"]
        if actor.get("role") == "worker":
            worker = connection.execute("SELECT name, department FROM users WHERE id=?", (actor["id"],)).fetchone()
            return bool(worker and (row["worker"] == worker["name"] or row["department"] == worker["department"]))
        if actor.get("role") == "supervisor" and actor.get("department"):
            return row["department"] == actor["department"]
        return True

    def _duplicate_candidates_for(self, connection, base, limit: int) -> list[dict]:
        rows = connection.execute("SELECT id, title, description, location, latitude, longitude, category, status, created_at FROM reports WHERE id<>? AND category=? AND status NOT IN ('Resolved','Cancelled') ORDER BY created_at DESC LIMIT 500", (base["id"], base["category"])).fetchall()
        output = []
        for row in rows:
            text_score = self._jaccard(tokenize(base["description"]), tokenize(row["description"]))
            location_score = 1.0 if normalize_text(base["location"]) == normalize_text(row["location"]) else 0.0
            distance_score = 0.0
            if base["latitude"] is not None and row["latitude"] is not None:
                distance = self._distance(base["latitude"], base["longitude"], row["latitude"], row["longitude"])
                distance_score = max(0.0, 1.0 - distance / 500.0)
            recency_score = max(0.0, 1.0 - abs(base["created_at"] - row["created_at"]) / (7 * 86_400_000))
            score = 0.45 * text_score + 0.25 * location_score + 0.25 * distance_score + 0.05 * recency_score
            if score >= 0.25:
                output.append({"candidate": row["id"], "title": row["title"], "score": round(score, 4), "textScore": round(text_score, 4), "locationScore": round(location_score, 4), "distanceScore": round(distance_score, 4), "recencyScore": round(recency_score, 4)})
        output.sort(key=lambda item: -item["score"])
        return output[:limit]

    @staticmethod
    def _search_score(tokens: tuple[str, ...], fields: Iterable[str]) -> float:
        content = normalize_text(" ".join(str(field or "") for field in fields))
        words = set(content.split())
        matches = sum(token in words for token in tokens)
        partials = sum(token in content for token in tokens) - matches
        if matches == 0 and partials == 0:
            return 0.0
        return matches * 2.0 + partials * 0.5 + len(set(tokens) & words) / max(1, len(tokens))

    @staticmethod
    def _snippet(value: str, tokens: tuple[str, ...], width: int = 180) -> str:
        text = str(value or "")
        lowered = text.casefold()
        positions = [lowered.find(token) for token in tokens if lowered.find(token) >= 0]
        if not positions:
            return text[:width]
        start = max(0, min(positions) - width // 3)
        end = min(len(text), start + width)
        return text[start:end]

    @staticmethod
    def _jaccard(left: Iterable[str], right: Iterable[str]) -> float:
        a, b = set(left), set(right)
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    @staticmethod
    def _distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = math.pi / 180
        dlat = (lat2 - lat1) * r
        dlon = (lon2 - lon1) * r
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1 * r) * math.cos(lat2 * r) * math.sin(dlon / 2) ** 2
        return 6_371_000 * 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1 - a)))

    @staticmethod
    def _coords(latitude, longitude) -> tuple[float | None, float | None]:
        if latitude in (None, "") and longitude in (None, ""):
            return None, None
        try:
            lat, lon = float(latitude), float(longitude)
        except (TypeError, ValueError) as exc:
            raise DomainError("Coordinates must be numeric.") from exc
        if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
            raise DomainError("Coordinates are outside valid ranges.")
        return lat, lon

    @staticmethod
    def _bbox(rows: Iterable[dict]) -> dict | None:
        rows = list(rows)
        if not rows:
            return None
        return {
            "minLat": min(row["latitude"] for row in rows),
            "maxLat": max(row["latitude"] for row in rows),
            "minLon": min(row["longitude"] for row in rows),
            "maxLon": max(row["longitude"] for row in rows),
        }

    @staticmethod
    def _metrics(rows) -> dict:
        total = len(rows)
        resolved = [row for row in rows if row["status"] == "Resolved"]
        priorities = [row["priority"] for row in rows]
        ratings = [row["feedback_rating"] for row in rows if row["feedback_rating"] is not None]
        return {
            "total": total,
            "resolved": len(resolved),
            "open": sum(row["status"] not in {"Resolved", "Cancelled"} for row in rows),
            "critical": sum(row["severity"] == "Critical" for row in rows),
            "averagePriority": round(sum(priorities) / len(priorities), 2) if priorities else 0,
            "satisfactionPercent": round(sum(ratings) / len(ratings) * 20, 2) if ratings else None,
            "categoryCounts": dict(Counter(row["category"] for row in rows)),
            "departmentCounts": dict(Counter(row["department"] for row in rows)),
            "statusCounts": dict(Counter(row["status"] for row in rows)),
        }

    def _sla_policy(self, policy_id: str) -> dict:
        with read_connection(self.database_path) as connection:
            row = connection.execute("SELECT * FROM sla_policies WHERE id=?", (policy_id,)).fetchone()
        if row is None:
            raise DomainError("SLA policy was not persisted.", 500)
        return dict(row)

    @staticmethod
    def _ensure_hours(hours: int) -> None:
        if not 1 <= hours <= 168:
            raise DomainError("Duration must be between 1 and 168 hours.")

    @staticmethod
    def _ensure_positive(value: int) -> None:
        if value <= 0:
            raise DomainError("Value must be positive.")

    @staticmethod
    def _ensure_limit(limit: int) -> None:
        if not 1 <= limit <= 5000:
            raise DomainError("Limit must be between 1 and 5,000.")

    @staticmethod
    def _ensure_page(page: int, page_size: int) -> None:
        if not 1 <= page <= 100000 or not 1 <= page_size <= 250:
            raise DomainError("Pagination parameters are invalid.")

    @staticmethod
    def _ensure_id(value: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_-]{3,80}", value):
            raise DomainError("Identifier is invalid.")

    @staticmethod
    def _validate_password(password: str) -> None:
        if not 10 <= len(password) <= 100 or not re.search(r"[a-z]", password) or not re.search(r"[A-Z]", password) or not re.search(r"\d", password):
            raise DomainError("Password must be 10-100 characters with upper, lower and numeric characters.")

    @staticmethod
    def _password_hash(password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 180_000)
        return f"pbkdf2$180000${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"

    @staticmethod
    def _require_admin(actor: dict) -> None:
        if actor.get("role") not in {"admin", "city_admin", "department_admin"}:
            raise DomainError("Administrator permission is required.", 403)

    @staticmethod
    def _require_manager(actor: dict) -> None:
        if actor.get("role") not in {"admin", "city_admin", "department_admin", "supervisor", "staff"}:
            raise DomainError("Manager permission is required.", 403)

    def _require_permission(self, actor: dict, permission: str) -> None:
        if actor.get("role") == "admin":
            return
        with read_connection(self.database_path) as connection:
            row = connection.execute("SELECT 1 FROM role_permissions WHERE role_name=? AND permission_name=?", (actor.get("role"), permission)).fetchone()
        if row is None:
            raise DomainError(f"Permission required: {permission}.", 403)


# ----------------------------------------------------------------------
# Local AI-free intelligence helpers.  These are intentionally deterministic
# so the application remains fully functional without a vendor API key.
# ----------------------------------------------------------------------
class OfflineIntelligence:
    """Deterministic language and prioritisation helpers for CivicFlow."""

    KEYWORDS = {
        "Pothole": ("pothole", "crater", "road hole"),
        "Road damage": ("cracked road", "pavement", "broken curb", "sidewalk"),
        "Streetlight": ("streetlight", "street light", "lamp post", "lamp is out"),
        "Garbage": ("garbage", "trash", "rubbish", "litter", "overflowing bin"),
        "Water leakage": ("water leak", "burst pipe", "water main", "leaking pipe"),
        "Drainage": ("drain", "flooding", "standing water", "blocked drain"),
        "Traffic signal": ("traffic signal", "traffic light", "signal is out"),
        "Public infrastructure": ("bench", "playground", "public facility", "bus shelter"),
        "Illegal dumping": ("dumping", "dumped waste", "construction waste"),
        "Tree hazard": ("fallen tree", "dangerous tree", "broken branch"),
        "Other": (),
    }

    SEVERITY_TERMS = {
        "Critical": ("emergency", "dangerous", "injury", "injured", "fire", "exposed wire", "major flood", "gas leak", "accident"),
        "High": ("blocked road", "deep", "large", "unsafe", "overflow", "burst"),
        "Medium": ("damaged", "broken", "poor", "overflowing"),
        "Low": ("cosmetic", "minor", "loose", "faded"),
    }

    @classmethod
    def categorize(cls, description: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        text = normalize_text(description)
        scores: dict[str, float] = {}
        for category, terms in cls.KEYWORDS.items():
            score = 0.0
            for term in terms:
                if term in text:
                    score += 1.0 + term.count(" ") * 0.25
            scores[category] = score
        metadata = metadata or {}
        location = normalize_text(str(metadata.get("location", "")))
        if "school" in location or "hospital" in location:
            for category in scores:
                scores[category] += 0.02
        best = max(scores, key=scores.get)
        return {"category": best, "scores": {key: round(value, 4) for key, value in scores.items()}, "confidence": round(min(1.0, scores[best] / max(1.0, sum(scores.values()))), 4)}

    @classmethod
    def severity(cls, description: str, category: str, affected_people: int = 0) -> dict[str, Any]:
        text = normalize_text(description)
        score = 0.0
        triggers: list[str] = []
        for level, terms in cls.SEVERITY_TERMS.items():
            for term in terms:
                if term in text:
                    triggers.append(term)
                    score += {"Critical": 45, "High": 30, "Medium": 18, "Low": 8}[level]
        score += min(20, max(0, affected_people) * 0.4)
        if category in {"Traffic signal", "Water leakage", "Pothole", "Tree hazard"}:
            score += 10
        level = "Critical" if score >= 60 else "High" if score >= 35 else "Medium" if score >= 18 else "Low"
        return {"level": level, "score": round(min(100, score), 2), "triggers": triggers}

    @classmethod
    def duplicate_score(cls, left: dict[str, Any], right: dict[str, Any]) -> dict[str, float]:
        text_score = CivicFlowPlatform._jaccard(tokenize(str(left.get("description", ""))), tokenize(str(right.get("description", ""))))
        location_score = 1.0 if normalize_text(str(left.get("location", ""))) == normalize_text(str(right.get("location", ""))) else 0.0
        return {"text": round(text_score, 4), "location": location_score, "overall": round(0.7 * text_score + 0.3 * location_score, 4)}
