"""CivicFlow use cases, policy checks, authentication, and SQLite queries."""

from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import math
import re
import secrets
import time
from pathlib import Path
from typing import Any

from .database import read_connection, transaction

CATEGORIES = (
    "Pothole", "Streetlight", "Garbage", "Water leakage", "Road damage",
    "Drainage", "Traffic signal", "Public infrastructure", "Other",
)
ROLE_VALUES = {"citizen", "admin", "supervisor", "worker", "staff", "department_admin", "city_admin"}
MANAGER_ROLES = {"admin", "supervisor", "staff", "department_admin", "city_admin"}
SEVERITY_POINTS = {"Low": 20, "Medium": 42, "High": 68, "Critical": 88}
PASSWORD_ITERATIONS = 310_000
PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{10,100}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]{1,64}@[^@\s.]+(?:\.[^@\s.]+)+$")


class DomainError(Exception):
    """An expected, user-visible service error with an HTTP status."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


def now_ms() -> int:
    return int(time.time() * 1000)


def json_value(value: str, default: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        ).hex()
        return hmac.compare_digest(candidate, digest_hex)
    except (ValueError, TypeError):
        return False


class CivicFlowService:
    """Use-case layer; every write is validated and committed in a DB transaction."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def _user(self, connection, user_id: str, required: bool = True):
        row = connection.execute(
            "SELECT id, name, email, role, department, active FROM users WHERE id=?",
            (user_id,),
        ).fetchone()
        if row is None or not row["active"]:
            if required:
                raise DomainError("Please sign in to continue.", 401)
            return None
        return dict(row)

    def _require_role(self, user: dict, roles: set[str]) -> None:
        if user["role"] not in roles:
            raise DomainError("You do not have permission to perform this action.", 403)

    def _audit(self, connection, user: dict, action: str, entity_type: str,
               entity_id: str | None, details: dict | None = None) -> None:
        connection.execute(
            """INSERT INTO audit_log(
                actor_id, actor_name, action, entity_type, entity_id, details_json, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?)""",
            (user["id"], user["name"], action, entity_type, entity_id,
             json.dumps(details or {}, ensure_ascii=False), now_ms()),
        )

    def _event(self, connection, report_id: str, status: str, actor: str,
               note: str = "") -> None:
        connection.execute(
            """INSERT INTO report_events(report_id, status, actor, note, created_at)
               VALUES(?, ?, ?, ?, ?)""",
            (report_id, status, actor, note, now_ms()),
        )

    def _notify(self, connection, message: str, report_id: str,
                recipient_id: str | None) -> None:
        connection.execute(
            """INSERT INTO notifications(id, message, report_id, recipient_id, created_at)
               VALUES(?, ?, ?, ?, ?)""",
            (f"notice-{secrets.token_urlsafe(12)}", message, report_id, recipient_id, now_ms()),
        )

    def _report_row(self, connection, report_id: str):
        row = connection.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
        if row is None:
            raise DomainError("Report not found.", 404)
        return row

    def _visible_report(self, connection, user: dict, report_id: str):
        report = self._report_row(connection, report_id)
        if user["role"] == "citizen" and report["citizen_id"] != user["id"]:
            raise DomainError("You can only access reports you submitted.", 403)
        if user["role"] == "worker" and report["worker"] != user["name"]:
            raise DomainError("This report is not assigned to you.", 403)
        if user["role"] == "supervisor" and user["department"] and report["department"] != user["department"]:
            raise DomainError("This report is outside your department.", 403)
        return report

    def authenticate(self, email: str, password: str) -> tuple[dict, str]:
        with read_connection(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE email=? COLLATE NOCASE AND active=1", (email,)
            ).fetchone()
        if row is None or not verify_password(password, row["password_hash"]):
            raise DomainError("Email or password is incorrect.", 401)
        return self._create_session(row["id"])

    def register(self, name: str, email: str, password: str) -> tuple[dict, str]:
        name, email = name.strip(), email.strip().lower()
        if len(name) < 2 or len(name) > 60:
            raise DomainError("Name must be between 2 and 60 characters.")
        if not EMAIL_PATTERN.fullmatch(email):
            raise DomainError("Enter a valid email address.")
        if not PASSWORD_PATTERN.fullmatch(password):
            raise DomainError("Password must be 10–100 characters with uppercase, lowercase, and a number.")
        user_id = f"citizen-{secrets.token_urlsafe(12)}"
        try:
            with transaction(self.database_path) as connection:
                connection.execute(
                    """INSERT INTO users(id, name, email, role, password_hash, created_at)
                       VALUES(?, ?, ?, 'citizen', ?, ?)""",
                    (user_id, name, email, hash_password(password), now_ms()),
                )
        except Exception as error:
            if "UNIQUE constraint failed: users.email" in str(error):
                raise DomainError("An account with this email already exists.", 409) from error
            raise
        return self._create_session(user_id)

    def demo_session(self, role: str) -> tuple[dict, str]:
        if role not in ROLE_VALUES:
            raise DomainError("Unknown demo role.")
        with read_connection(self.database_path) as connection:
            row = connection.execute("SELECT id FROM users WHERE id=?", (f"demo-{role}",)).fetchone()
        if row is None:
            raise DomainError("The demo account is unavailable.", 503)
        return self._create_session(row["id"])

    def _create_session(self, user_id: str) -> tuple[dict, str]:
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        stamp = now_ms()
        with transaction(self.database_path) as connection:
            user = self._user(connection, user_id)
            connection.execute("DELETE FROM sessions WHERE expires_at < ?", (stamp,))
            connection.execute(
                "INSERT INTO sessions(token_hash, user_id, created_at, expires_at) VALUES(?, ?, ?, ?)",
                (token_hash, user_id, stamp, stamp + 14 * 24 * 60 * 60 * 1000),
            )
        return user, token

    def user_for_token(self, token: str | None) -> dict | None:
        if not token:
            return None
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        stamp = now_ms()
        with read_connection(self.database_path) as connection:
            row = connection.execute(
                """SELECT u.id, u.name, u.email, u.role, u.department, u.active
                   FROM sessions s JOIN users u ON u.id=s.user_id
                   WHERE s.token_hash=? AND s.expires_at>?""",
                (token_hash, stamp),
            ).fetchone()
        return dict(row) if row and row["active"] else None

    def revoke_token(self, token: str | None) -> None:
        if token:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            with transaction(self.database_path) as connection:
                connection.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash,))

    def state(self, user: dict) -> dict:
        with read_connection(self.database_path) as connection:
            if user["role"] == "citizen":
                rows = connection.execute(
                    "SELECT * FROM reports WHERE citizen_id=? ORDER BY created_at DESC", (user["id"],)
                ).fetchall()
            elif user["role"] == "worker":
                rows = connection.execute(
                    "SELECT * FROM reports WHERE worker=? ORDER BY priority DESC, created_at DESC",
                    (user["name"],),
                ).fetchall()
            elif user["role"] == "supervisor" and user["department"]:
                rows = connection.execute(
                    """SELECT * FROM reports
                       WHERE department=?
                       ORDER BY priority DESC, created_at DESC""",
                    (user["department"],),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM reports ORDER BY priority DESC, created_at DESC"
                ).fetchall()
            reports = [self._serialize_report(connection, row) for row in rows]
            department_rows = connection.execute(
                "SELECT name, description, icon, sla_hours FROM departments WHERE active=1 ORDER BY name"
            ).fetchall()
            staff_rows = connection.execute(
                """SELECT s.id, s.name, s.department, s.skills_json,
                          (SELECT COUNT(*) FROM reports r WHERE r.worker=s.name
                           AND r.status NOT IN ('Resolved', 'Cancelled')) AS active
                   FROM staff s WHERE s.active=1 ORDER BY s.name"""
            ).fetchall()
            notification_query = (
                "SELECT * FROM notifications WHERE recipient_id IS NULL OR recipient_id=?"
            )
            notifications = connection.execute(
                notification_query + " ORDER BY created_at DESC LIMIT 100", (user["id"],)
            ).fetchall()
            if user["role"] == "citizen":
                activity = connection.execute(
                    """SELECT action, entity_type, entity_id, actor_name, created_at
                       FROM audit_log
                       WHERE entity_id IN (SELECT id FROM reports WHERE citizen_id=?)
                       ORDER BY created_at DESC LIMIT 12""",
                    (user["id"],),
                ).fetchall()
            elif user["role"] == "worker":
                activity = connection.execute(
                    """SELECT action, entity_type, entity_id, actor_name, created_at
                       FROM audit_log
                       WHERE entity_id IN (SELECT id FROM reports WHERE worker=?)
                       ORDER BY created_at DESC LIMIT 12""",
                    (user["name"],),
                ).fetchall()
            elif user["role"] == "supervisor" and user["department"]:
                activity = connection.execute(
                    """SELECT action, entity_type, entity_id, actor_name, created_at
                       FROM audit_log
                       WHERE entity_id IN (SELECT id FROM reports WHERE department=?)
                       ORDER BY created_at DESC LIMIT 12""",
                    (user["department"],),
                ).fetchall()
            else:
                activity = connection.execute(
                    """SELECT action, entity_type, entity_id, actor_name, created_at
                       FROM audit_log ORDER BY created_at DESC LIMIT 12"""
                ).fetchall()
            audit = []
            if user["role"] == "admin":
                audit = connection.execute(
                    """SELECT actor_name, action, entity_type, entity_id, details_json, created_at
                       FROM audit_log ORDER BY created_at DESC LIMIT 500"""
                ).fetchall()
        payload = {
            "user": user,
            "reports": reports,
            "departments": [dict(row) for row in department_rows],
            "staff": [
                {**dict(row), "skills": json_value(row["skills_json"], [])}
                for row in staff_rows
            ],
            "notifications": [
                {
                    "id": row["id"], "message": row["message"], "reportId": row["report_id"],
                    "recipientId": row["recipient_id"], "createdAt": row["created_at"],
                    "read": bool(row["is_read"]),
                } for row in notifications
            ],
            "activity": [
                {
                    "message": self._activity_message(row), "icon": self._activity_icon(row["action"]),
                    "createdAt": row["created_at"],
                } for row in activity
            ],
            "metrics": {
                "total": len(reports),
                "resolved": sum(report["status"] == "Resolved" for report in reports),
                "open": sum(report["status"] not in ("Resolved", "Cancelled") for report in reports),
                "critical": sum(report["severity"] == "Critical" and report["status"] not in ("Resolved", "Cancelled") for report in reports),
            },
        }
        if user["role"] in MANAGER_ROLES:
            payload["analytics"] = self.analytics(user)
        if user["role"] == "admin":
            payload["audit"] = [
                {
                    "actor": row["actor_name"], "action": row["action"],
                    "entityType": row["entity_type"], "entityId": row["entity_id"],
                    "details": json_value(row["details_json"], {}),
                    "createdAt": row["created_at"],
                } for row in audit
            ]
        return payload

    def _activity_message(self, row) -> str:
        return f"{row['actor_name']} {row['action'].replace('_', ' ')} {row['entity_id'] or row['entity_type']}"

    def _activity_icon(self, action: str) -> str:
        return {
            "report_created": "＋", "work_started": "↗", "work_submitted": "◷",
            "report_resolved": "✓", "report_reopened": "↻", "report_assigned": "✓",
            "department_created": "▦", "staff_created": "♙",
        }.get(action, "✓")

    def _serialize_report(self, connection, row) -> dict:
        events = connection.execute(
            """SELECT status, actor, note, created_at FROM report_events
               WHERE report_id=? ORDER BY created_at, id""",
            (row["id"],),
        ).fetchall()
        feedback = None
        if row["feedback_rating"] is not None:
            feedback = {
                "rating": row["feedback_rating"], "comment": row["feedback_comment"] or "",
                "at": row["feedback_at"],
            }
        return {
            "id": row["id"], "title": row["title"], "category": row["category"],
            "description": row["description"], "location": row["location"],
            "createdAt": row["created_at"], "reportedDate": row["reported_at"],
            "citizen": row["citizen_name"], "citizenId": row["citizen_id"],
            "status": row["status"], "severity": row["severity"], "priority": row["priority"],
            "department": row["department"], "worker": row["worker"],
            "latitude": row["latitude"], "longitude": row["longitude"],
            "duplicateOf": row["duplicate_of"], "image": row["image"],
            "resolution": row["resolution"], "resolutionImage": row["resolution_image"],
            "feedback": feedback,
            "history": [
                {"status": event["status"], "by": event["actor"], "note": event["note"],
                 "at": event["created_at"]} for event in events
            ],
        }

    def create_report(self, user: dict, payload: dict) -> dict:
        self._require_role(user, {"citizen"})
        category = str(payload.get("category", "Other")).strip()
        description = str(payload.get("description", "")).strip()
        location = str(payload.get("location", "")).strip()
        if category not in CATEGORIES:
            raise DomainError("Choose a valid report category.")
        if not 12 <= len(description) <= 1000:
            raise DomainError("Description must be between 12 and 1,000 characters.")
        if not location or len(location) > 140:
            raise DomainError("Enter a location up to 140 characters.")
        reported_at = payload.get("reportedDate", now_ms())
        try:
            reported_at = int(reported_at)
        except (TypeError, ValueError) as error:
            raise DomainError("Enter a valid date and time.") from error
        stamp = now_ms()
        if reported_at > stamp + 60_000 or reported_at < stamp - 366 * 24 * 60 * 60 * 1000:
            raise DomainError("Report date cannot be in the future or more than one year ago.")
        latitude, longitude = self._coordinates(payload.get("latitude"), payload.get("longitude"))
        image = str(payload.get("image") or "")
        if image and (not image.startswith(("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/webp;base64,")) or len(image) > 2_900_000):
            raise DomainError("Photo must be PNG, JPEG, or WebP and no larger than 2 MB.")
        if category == "Other":
            category = self._classify(description)
        severity = self._severity(category, description)
        priority = self._priority(severity, stamp, latitude is not None)
        department = self._department_for(category)
        title = self._title(category, description)
        with transaction(self.database_path) as connection:
            duplicate = self._find_duplicate(connection, category, location, description, latitude, longitude)
            report_id = self._next_report_id(connection)
            connection.execute(
                """INSERT INTO reports(
                    id, title, category, description, location, created_at, reported_at,
                    citizen_name, citizen_id, status, severity, priority, department,
                    latitude, longitude, duplicate_of, image
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, 'Awaiting review', ?, ?, ?, ?, ?, ?, ?)""",
                (report_id, title, category, description, location, stamp, reported_at,
                 user["name"], user["id"], severity, priority, department, latitude,
                 longitude, duplicate["id"] if duplicate else None, image),
            )
            self._event(connection, report_id, "Reported", user["name"])
            if duplicate:
                self._event(connection, report_id, "Possible duplicate", "CivicFlow",
                            f"Related report: {duplicate['id']}")
            self._audit(connection, user, "report_created", "report", report_id,
                        {"category": category, "severity": severity})
            message = (
                f"Your report may be related to {duplicate['id']}; a city team will review it."
                if duplicate else f"Your report {report_id} was received and is awaiting review."
            )
            self._notify(connection, message, report_id, user["id"])
        return {"reportId": report_id, "duplicateOf": duplicate["id"] if duplicate else None}

    def approve_report(self, user: dict, report_id: str, department: str, worker: str) -> None:
        self._require_role(user, MANAGER_ROLES)
        with transaction(self.database_path) as connection:
            report = self._report_row(connection, report_id)
            self._manager_can_manage_report(user, report)
            if report["status"] not in ("Awaiting review", "Reopened"):
                raise DomainError("This report is no longer awaiting review.", 409)
            department_row = connection.execute(
                "SELECT name FROM departments WHERE name=? COLLATE NOCASE AND active=1",
                (department,),
            ).fetchone()
            staff = connection.execute(
                """SELECT name, department FROM staff
                   WHERE name=? COLLATE NOCASE AND active=1""", (worker,)
            ).fetchone()
            if department_row is None or staff is None or staff["department"].casefold() != department.casefold():
                raise DomainError("Choose an active worker in the selected department.")
            connection.execute(
                """UPDATE reports SET department=?, worker=?, status='Assigned'
                   WHERE id=?""", (department_row["name"], staff["name"], report_id)
            )
            self._event(connection, report_id, "Assigned", user["name"],
                        f"{department_row['name']} · {staff['name']}")
            self._audit(connection, user, "report_assigned", "report", report_id,
                        {"department": department_row["name"], "worker": staff["name"]})
            self._notify(connection, f"{report_id} was approved and assigned to {department_row['name']}.",
                          report_id, report["citizen_id"])

    def start_work(self, user: dict, report_id: str) -> None:
        self._require_role(user, {"worker"})
        with transaction(self.database_path) as connection:
            report = self._visible_report(connection, user, report_id)
            if report["status"] != "Assigned":
                raise DomainError("Only assigned work orders can be started.", 409)
            connection.execute("UPDATE reports SET status='In progress' WHERE id=?", (report_id,))
            self._event(connection, report_id, "In progress", user["name"])
            self._audit(connection, user, "work_started", "report", report_id)
            self._notify(connection, f"Field work has started on {report_id}.",
                          report_id, report["citizen_id"])

    def submit_work(self, user: dict, report_id: str, notes: str, image: str = "") -> None:
        self._require_role(user, {"worker"})
        notes = notes.strip()
        if not 8 <= len(notes) <= 700:
            raise DomainError("Work notes must be between 8 and 700 characters.")
        if image and (not image.startswith(("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/webp;base64,")) or len(image) > 2_900_000):
            raise DomainError("Photo must be PNG, JPEG, or WebP and no larger than 2 MB.")
        with transaction(self.database_path) as connection:
            report = self._visible_report(connection, user, report_id)
            if report["status"] != "In progress":
                raise DomainError("Only in-progress work can be submitted for verification.", 409)
            connection.execute(
                """UPDATE reports SET resolution=?, resolution_image=?, status='Awaiting verification'
                   WHERE id=?""", (notes, image, report_id)
            )
            self._event(connection, report_id, "Awaiting verification", user["name"])
            self._audit(connection, user, "work_submitted", "report", report_id)
            self._notify(connection, f"{report_id} is repaired and waiting for supervisor verification.",
                          report_id, None)

    def verify_work(self, user: dict, report_id: str, approve: bool, note: str = "") -> None:
        self._require_role(user, MANAGER_ROLES)
        if not approve and len(note.strip()) < 8:
            raise DomainError("Add a rejection reason of at least 8 characters.")
        with transaction(self.database_path) as connection:
            report = self._report_row(connection, report_id)
            self._manager_can_manage_report(user, report)
            if report["status"] != "Awaiting verification":
                raise DomainError("This repair is no longer awaiting verification.", 409)
            if approve:
                stamp = now_ms()
                connection.execute("UPDATE reports SET status='Resolved', resolved_at=? WHERE id=?", (stamp, report_id))
                self._event(connection, report_id, "Resolved", user["name"], note.strip())
                self._audit(connection, user, "report_resolved", "report", report_id)
                self._notify(
                    connection,
                    f"Your report {report_id} has been resolved. Thank you for helping improve your neighborhood.",
                    report_id, report["citizen_id"],
                )
            else:
                worker = self._recommend_worker(connection, report["department"], report["category"], exclude=report["worker"])
                if not worker:
                    worker = self._recommend_worker(connection, report["department"], report["category"])
                if not worker:
                    raise DomainError("No active worker is available for reassignment.", 409)
                connection.execute(
                    "UPDATE reports SET status='Assigned', worker=? WHERE id=?",
                    (worker, report_id),
                )
                self._event(connection, report_id, "Rejected", user["name"], note.strip())
                self._event(connection, report_id, "Reassigned", user["name"],
                            f"{report['worker']} → {worker}")
                self._audit(connection, user, "work_rejected", "report", report_id,
                            {"previous_worker": report["worker"], "worker": worker})
                self._notify(connection, f"The repair for {report_id} needs more work. The city team has been notified.",
                              report_id, report["citizen_id"])

    def leave_feedback(self, user: dict, report_id: str, rating: int, comment: str) -> None:
        self._require_role(user, {"citizen"})
        if not isinstance(rating, int) or not 1 <= rating <= 5:
            raise DomainError("Choose a rating from 1 to 5.")
        if len(comment) > 500:
            raise DomainError("Feedback must be 500 characters or fewer.")
        with transaction(self.database_path) as connection:
            report = self._visible_report(connection, user, report_id)
            if report["status"] != "Resolved":
                raise DomainError("Feedback is available after a report is resolved.", 409)
            if report["feedback_rating"] is not None:
                raise DomainError("Feedback has already been submitted.", 409)
            connection.execute(
                """UPDATE reports SET feedback_rating=?, feedback_comment=?, feedback_at=?
                   WHERE id=?""", (rating, comment.strip(), now_ms(), report_id)
            )
            self._audit(connection, user, "feedback_submitted", "report", report_id,
                        {"rating": rating})

    def reopen_report(self, user: dict, report_id: str, reason: str) -> None:
        self._require_role(user, {"citizen"})
        reason = reason.strip()
        if not 8 <= len(reason) <= 500:
            raise DomainError("Follow-up reason must be between 8 and 500 characters.")
        with transaction(self.database_path) as connection:
            report = self._visible_report(connection, user, report_id)
            if report["status"] != "Resolved":
                raise DomainError("Only resolved reports can be reopened.", 409)
            connection.execute(
                """UPDATE reports SET status='Awaiting review', worker=NULL, resolution=NULL,
                   resolution_image='', resolved_at=NULL, feedback_rating=NULL, feedback_comment=NULL, feedback_at=NULL
                   WHERE id=?""", (report_id,)
            )
            self._event(connection, report_id, "Reopened", user["name"], reason)
            self._event(connection, report_id, "Awaiting review", "CivicFlow")
            self._audit(connection, user, "report_reopened", "report", report_id)
            self._notify(connection, f"{report_id} was reopened and sent to the city team for follow-up.",
                          report_id, None)

    def create_department(self, user: dict, name: str, description: str, sla_hours: int) -> None:
        self._require_role(user, {"admin"})
        name, description = name.strip(), description.strip()
        if not 2 <= len(name) <= 60 or not 8 <= len(description) <= 120:
            raise DomainError("Enter a department name and description within the listed limits.")
        if not isinstance(sla_hours, int) or not 1 <= sla_hours <= 8760:
            raise DomainError("SLA must be between 1 and 8,760 hours.")
        try:
            with transaction(self.database_path) as connection:
                connection.execute(
                    """INSERT INTO departments(name, description, icon, sla_hours, created_at)
                       VALUES(?, ?, '◇', ?, ?)""", (name, description, sla_hours, now_ms())
                )
                self._audit(connection, user, "department_created", "department", name)
        except Exception as error:
            if "UNIQUE constraint failed" in str(error):
                raise DomainError("That department already exists.", 409) from error
            raise

    def create_staff(self, user: dict, name: str, department: str, skills: list[str]) -> None:
        self._require_role(user, {"admin"})
        name = name.strip()
        if not 2 <= len(name) <= 60:
            raise DomainError("Staff name must be between 2 and 60 characters.")
        if not skills or len(skills) > len(CATEGORIES) or any(skill not in CATEGORIES for skill in skills):
            raise DomainError("Select one or more valid skills.")
        try:
            with transaction(self.database_path) as connection:
                department_row = connection.execute(
                    "SELECT name FROM departments WHERE name=? COLLATE NOCASE AND active=1",
                    (department,),
                ).fetchone()
                if department_row is None:
                    raise DomainError("Choose an active department.")
                staff_id = f"worker-{secrets.token_urlsafe(10)}"
                connection.execute(
                    """INSERT INTO staff(id, name, department, skills_json, created_at)
                       VALUES(?, ?, ?, ?, ?)""",
                    (staff_id, name, department_row["name"], json.dumps(skills), now_ms()),
                )
                self._audit(connection, user, "staff_created", "staff", staff_id,
                            {"department": department_row["name"]})
        except Exception as error:
            if "UNIQUE constraint failed: staff.name" in str(error):
                raise DomainError("A team member with that name already exists.", 409) from error
            raise

    def mark_notifications_read(self, user: dict) -> None:
        with transaction(self.database_path) as connection:
            connection.execute(
                "UPDATE notifications SET is_read=1 WHERE recipient_id IS NULL OR recipient_id=?",
                (user["id"],),
            )

    def escalate_overdue(self) -> int:
        """Create one notification/audit event per breached SLA threshold."""
        stamp = now_ms()
        escalated = 0
        with transaction(self.database_path) as connection:
            overdue = connection.execute(
                """SELECT r.id, r.title, r.department, r.citizen_id, r.created_at,
                          d.sla_hours,
                          COALESCE((SELECT MAX(e.level) FROM escalation_records e
                                    WHERE e.report_id=r.id), 0) AS level
                   FROM reports r JOIN departments d ON d.name=r.department
                   WHERE r.status NOT IN ('Resolved', 'Cancelled')
                   AND d.active=1
                   AND r.created_at + d.sla_hours * 3600000 *
                       (COALESCE((SELECT MAX(e.level) FROM escalation_records e
                                  WHERE e.report_id=r.id), 0) + 1) < ?
                   AND COALESCE((SELECT MAX(e.level) FROM escalation_records e
                                 WHERE e.report_id=r.id), 0) < 3
                   ORDER BY r.created_at""",
                (stamp,),
            ).fetchall()
            for report in overdue:
                next_level = report["level"] + 1
                reason = f"Open beyond {report['sla_hours'] * next_level}-hour department service target."
                cursor = connection.execute(
                    """INSERT OR IGNORE INTO escalation_records(report_id, level, reason, created_at)
                       VALUES(?, ?, ?, ?)""",
                    (report["id"], next_level, reason, stamp),
                )
                if cursor.rowcount != 1:
                    continue
                escalated += 1
                recipients = connection.execute(
                    """SELECT id FROM users WHERE active=1 AND
                       (role='admin' OR (role='supervisor' AND department=?))""",
                    (report["department"],),
                ).fetchall()
                message = (
                    f"SLA escalation {next_level}/3: {report['id']} is overdue in "
                    f"{report['department']} ({reason.lower()})"
                )
                for recipient in recipients:
                    self._notify(connection, message, report["id"], recipient["id"])
                if report["citizen_id"]:
                    self._notify(
                        connection,
                        f"Your report {report['id']} is taking longer than the department service target. The city team has been alerted.",
                        report["id"], report["citizen_id"],
                    )
                connection.execute(
                    """INSERT INTO audit_log(
                         actor_id, actor_name, action, entity_type, entity_id, details_json, created_at
                       ) VALUES(NULL, 'CivicFlow Scheduler', 'sla_escalated', 'report', ?, ?, ?)""",
                    (report["id"], json.dumps({"level": next_level, "reason": reason}), stamp),
                )
        return escalated

    def analytics(self, user: dict) -> dict:
        self._require_role(user, MANAGER_ROLES)
        with read_connection(self.database_path) as connection:
            if user["role"] == "supervisor" and user["department"]:
                where, args = "WHERE department=?", (user["department"],)
            else:
                where, args = "", ()
            rows = connection.execute(
                f"""SELECT department, status, severity, created_at, resolved_at, priority,
                           feedback_rating, reported_at
                    FROM reports {where}""", args
            ).fetchall()
            performance = connection.execute(
                f"""SELECT d.name, d.description, d.sla_hours,
                    COUNT(r.id) AS total,
                    SUM(CASE WHEN r.status='Resolved' THEN 1 ELSE 0 END) AS resolved,
                    SUM(CASE WHEN r.status NOT IN ('Resolved', 'Cancelled') THEN 1 ELSE 0 END) AS open
                    FROM departments d LEFT JOIN reports r ON r.department=d.name
                    WHERE d.active=1 {"AND d.name=?" if args else ""}
                    GROUP BY d.name ORDER BY d.name""",
                (user["department"],) if args else (),
            ).fetchall()
            overdue_filter = " AND r.department=?" if user["role"] == "supervisor" and user["department"] else ""
            overdue_args = (now_ms(), user["department"]) if overdue_filter else (now_ms(),)
            overdue = connection.execute(
                f"""SELECT r.id, r.title, r.department, r.status,
                           d.sla_hours, r.created_at,
                           COALESCE((SELECT MAX(e.level) FROM escalation_records e
                                     WHERE e.report_id=r.id), 0) AS escalation_level
                    FROM reports r JOIN departments d ON d.name=r.department
                    WHERE r.status NOT IN ('Resolved', 'Cancelled')
                    AND r.created_at + d.sla_hours * 3600000 < ? {overdue_filter}
                    ORDER BY r.priority DESC, r.created_at LIMIT 50""", overdue_args
            ).fetchall()
        resolved = [row for row in rows if row["status"] == "Resolved"]
        duration_days = [
            max(0, (row["resolved_at"] - row["created_at"]) / 86_400_000)
            for row in resolved if row["resolved_at"] is not None
        ]
        ratings = [row["feedback_rating"] for row in rows if row["feedback_rating"] is not None]
        heatmap = self._hotspots(user)
        return {
            "total": len(rows),
            "resolved": len(resolved),
            "open": sum(row["status"] not in ("Resolved", "Cancelled") for row in rows),
            "critical": sum(row["severity"] == "Critical" and row["status"] not in ("Resolved", "Cancelled") for row in rows),
            "overdue": len(overdue),
            "overdueReports": [
                {
                    "id": row["id"], "title": row["title"], "department": row["department"],
                    "status": row["status"], "slaHours": row["sla_hours"],
                    "overdueHours": max(0, (now_ms() - row["created_at"]) // 3_600_000 - row["sla_hours"]),
                    "escalationLevel": row["escalation_level"],
                } for row in overdue
            ],
            "averageResolutionDays": round(sum(duration_days) / len(duration_days), 1) if duration_days else None,
            "satisfactionPercent": round(sum(ratings) / len(ratings) * 20) if ratings else None,
            "ratings": len(ratings),
            "departments": [dict(row) for row in performance],
            "hotspots": heatmap,
            "weekly": self._weekly_counts(rows),
        }

    def _hotspots(self, user: dict) -> list[dict]:
        clauses, args = ["latitude IS NOT NULL", "longitude IS NOT NULL"], []
        if user["role"] == "supervisor" and user["department"]:
            clauses.append("department=?")
            args.append(user["department"])
        with read_connection(self.database_path) as connection:
            rows = connection.execute(
                f"""SELECT ROUND(latitude, 2) AS lat, ROUND(longitude, 2) AS lon,
                           COUNT(*) AS count, category
                    FROM reports WHERE {' AND '.join(clauses)}
                    GROUP BY lat, lon, category ORDER BY count DESC LIMIT 50""",
                args,
            ).fetchall()
        return [dict(row) for row in rows]

    def _weekly_counts(self, rows) -> list[dict]:
        stamp = now_ms()
        return [
            {
                "week": index,
                "count": sum(start < row["created_at"] <= end for row in rows),
            }
            for index in range(7)
            for end in [stamp - (6 - index) * 7 * 86_400_000]
            for start in [end - 7 * 86_400_000]
        ]

    def export_csv(self, user: dict) -> str:
        self._require_role(user, MANAGER_ROLES)
        state = self.state(user)
        output = io.StringIO(newline="")
        fields = ("id", "title", "category", "description", "location", "status",
                  "severity", "priority", "department", "worker", "createdAt")
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for report in state["reports"]:
            writer.writerow(report)
        return output.getvalue()

    def _manager_can_manage_report(self, user: dict, report) -> None:
        if user["role"] == "supervisor" and user["department"] and report["department"] != user["department"]:
            raise DomainError("This report is outside your department.", 403)

    def _coordinates(self, latitude, longitude) -> tuple[float | None, float | None]:
        if latitude in (None, "") and longitude in (None, ""):
            return None, None
        try:
            latitude, longitude = float(latitude), float(longitude)
        except (TypeError, ValueError) as error:
            raise DomainError("Coordinates must be numeric.") from error
        if not math.isfinite(latitude) or not math.isfinite(longitude) or not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise DomainError("Coordinates are outside valid latitude or longitude ranges.")
        return latitude, longitude

    def _next_report_id(self, connection) -> str:
        numbers = [
            int(row[0][3:]) for row in connection.execute(
                "SELECT id FROM reports WHERE id GLOB 'CF-[0-9]*'"
            ) if row[0][3:].isdigit()
        ]
        return f"CF-{max([1000, *numbers]) + 1}"

    def _department_for(self, category: str) -> str:
        name = {
            "Pothole": "Roads", "Road damage": "Roads",
            "Streetlight": "Electrical", "Traffic signal": "Electrical",
            "Garbage": "Sanitation", "Water leakage": "Water Supply",
            "Drainage": "Water Supply",
            "Public infrastructure": "Public Works", "Other": "Public Works",
        }.get(category, "Public Works")
        with read_connection(self.database_path) as connection:
            row = connection.execute(
                "SELECT name FROM departments WHERE name=? COLLATE NOCASE AND active=1", (name,)
            ).fetchone()
            if row:
                return row["name"]
            fallback = connection.execute(
                "SELECT name FROM departments WHERE active=1 ORDER BY name LIMIT 1"
            ).fetchone()
        if fallback is None:
            raise DomainError("No active departments are configured.", 503)
        return fallback["name"]

    def _classify(self, description: str) -> str:
        patterns = (
            ("Pothole", r"\bpothole|road crater\b"),
            ("Streetlight", r"\bstreet.?light|lamp post|light is out\b"),
            ("Garbage", r"\btrash|garbage|rubbish|overflowing bin|litter\b"),
            ("Water leakage", r"\bleak|burst pipe|water main\b"),
            ("Drainage", r"\bdrain|flood|standing water\b"),
            ("Traffic signal", r"\btraffic light|signal\b"),
            ("Road damage", r"\broad damage|cracked road|sidewalk|pavement\b"),
        )
        for category, pattern in patterns:
            if re.search(pattern, description, re.IGNORECASE):
                return category
        return "Other"

    def _severity(self, category: str, description: str) -> str:
        if re.search(r"\b(urgent|dangerous|emergency|injur|flood|major|severe|exposed wire|gas leak|accident)\b", description, re.IGNORECASE):
            return "Critical"
        if category in {"Water leakage", "Traffic signal", "Pothole", "Road damage", "Streetlight"}:
            return "High"
        if category == "Public infrastructure":
            return "Low"
        return "Medium"

    def _priority(self, severity: str, created_at: int, has_location: bool) -> int:
        age = min(12, max(0, (now_ms() - created_at) // 86_400_000 * 2))
        return min(100, SEVERITY_POINTS[severity] + age + (5 if has_location else 0) + 5)

    def _title(self, category: str, description: str) -> str:
        first = re.split(r"[.!?\n]", description.strip(), maxsplit=1)[0]
        return first if len(first) <= 62 else first[:59].rstrip() + "…"

    def _find_duplicate(self, connection, category: str, location: str, description: str,
                        latitude: float | None, longitude: float | None):
        candidates = connection.execute(
            """SELECT id, description, location, latitude, longitude
               FROM reports WHERE category=? AND status NOT IN ('Resolved', 'Cancelled')
               ORDER BY created_at DESC LIMIT 500""",
            (category,),
        ).fetchall()
        normalized = re.sub(r"[^a-z0-9]+", " ", location.casefold()).strip()
        words = {word for word in re.split(r"\W+", description.casefold()) if len(word) > 3}
        for row in candidates:
            existing_location = re.sub(r"[^a-z0-9]+", " ", row["location"].casefold()).strip()
            same_location = normalized and existing_location and (
                normalized == existing_location or normalized in existing_location or existing_location in normalized
            )
            close_coordinates = False
            if latitude is not None and longitude is not None and row["latitude"] is not None:
                close_coordinates = self._distance(
                    latitude, longitude, row["latitude"], row["longitude"]
                ) <= 100
            existing_words = {
                word for word in re.split(r"\W+", row["description"].casefold()) if len(word) > 3
            }
            score = len(words & existing_words) / min(len(words), len(existing_words)) if words and existing_words else 0
            if (same_location or close_coordinates) and score >= 0.25:
                return row
        return None

    def _distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        radians = math.pi / 180
        d_lat, d_lon = (lat2 - lat1) * radians, (lon2 - lon1) * radians
        a = math.sin(d_lat / 2) ** 2 + math.cos(lat1 * radians) * math.cos(lat2 * radians) * math.sin(d_lon / 2) ** 2
        return 6_371_000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _recommend_worker(self, connection, department: str, category: str,
                          exclude: str | None = None) -> str | None:
        rows = connection.execute(
            """SELECT s.name, s.skills_json,
                 (SELECT COUNT(*) FROM reports r WHERE r.worker=s.name
                  AND r.status NOT IN ('Resolved', 'Cancelled')) AS workload
               FROM staff s WHERE s.department=? AND s.active=1 AND (? IS NULL OR s.name<>?)
               ORDER BY workload, s.name""",
            (department, exclude, exclude),
        ).fetchall()
        rows = sorted(rows, key=lambda row: (
            category not in json_value(row["skills_json"], []), row["workload"], row["name"]
        ))
        return rows[0]["name"] if rows else None
