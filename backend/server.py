"""Same-origin HTTP API and static-file server for the local CivicFlow app."""

from __future__ import annotations

import json
import logging
import mimetypes
import re
import secrets
import threading
import os
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .config import (
    DATABASE_PATH,
    MAX_REQUEST_BYTES,
    SESSION_COOKIE,
    SESSION_TTL_SECONDS,
    STATIC_ROOT,
)
from .database import initialize, read_connection
from .service import CivicFlowService, DomainError
from .platform import CivicFlowPlatform, OfflineIntelligence
from .decision_service import DecisionService

LOG = logging.getLogger("civicflow.http")
REPORT_ACTION = re.compile(r"^/api/reports/(CF-[0-9]+)/([a-z-]+)$")
SAFE_STATIC = {"index.html", "app.js", "styles.css", "favicon.ico"}


class CivicFlowHandler(BaseHTTPRequestHandler):
    """Serve static assets and JSON actions; intended for loopback development."""

    server_version = "CivicFlowLocal/1.0"

    @property
    def service(self) -> CivicFlowService:
        return self.server.civicflow_service

    @property
    def platform(self) -> CivicFlowPlatform:
        return self.server.civicflow_platform

    def log_message(self, fmt: str, *args) -> None:
        LOG.info("%s - %s", self.address_string(), fmt % args)

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'self' data:; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
        super().end_headers()

    def do_GET(self) -> None:
        if urlsplit(self.path).path == "/api/decisions/catalog":
            user = self._session_user()
            if user is None:
                return self._json(HTTPStatus.UNAUTHORIZED, {"error": "Please sign in."})
            from urllib.parse import parse_qs
            term = parse_qs(urlsplit(self.path).query).get("q", [""])[0]
            return self._json(HTTPStatus.OK, DecisionService().catalog(term))
        route = urlsplit(self.path).path
        if route == "/api/health":
            return self._json(HTTPStatus.OK, {"ok": True, "database": "sqlite"})
        user = self._session_user()
        if route == "/api/state":
            if user is None:
                return self._json(HTTPStatus.UNAUTHORIZED, {"error": "Please sign in."})
            return self._json(HTTPStatus.OK, self.service.state(user))
        if route == "/api/analytics":
            if user is None:
                return self._json(HTTPStatus.UNAUTHORIZED, {"error": "Please sign in."})
            try:
                return self._json(HTTPStatus.OK, self.service.analytics(user))
            except DomainError as error:
                return self._domain_error(error)
        if route == "/api/export.csv":
            if user is None:
                return self._json(HTTPStatus.UNAUTHORIZED, {"error": "Please sign in."})
            try:
                csv_text = self.service.export_csv(user)
            except DomainError as error:
                return self._domain_error(error)
            payload = csv_text.encode("utf-8-sig")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="civicflow-reports.csv"')
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if route == "/api/audit":
            if user is None:
                return self._json(HTTPStatus.UNAUTHORIZED, {"error": "Please sign in."})
            try:
                self._admin_only(user)
                return self._json(HTTPStatus.OK, self._audit_rows())
            except DomainError as error:
                return self._domain_error(error)
        if user is not None and route == "/api/profile":
            try:
                return self._json(HTTPStatus.OK, self.platform.get_profile(user))
            except DomainError as error:
                return self._domain_error(error)
        if user is not None and route == "/api/devices":
            try:
                return self._json(HTTPStatus.OK, self.platform.devices(user))
            except DomainError as error:
                return self._domain_error(error)
        if user is not None and route == "/api/search":
            try:
                from urllib.parse import parse_qs
                query = parse_qs(urlsplit(self.path).query).get("q", [""])[0]
                return self._json(HTTPStatus.OK, {"results": self.platform.search(user, query)})
            except DomainError as error:
                return self._domain_error(error)
        if user is not None and route == "/api/work-orders":
            try:
                from urllib.parse import parse_qs
                params = parse_qs(urlsplit(self.path).query)
                page = int(params.get("page", [1])[0])
                size = int(params.get("pageSize", [25])[0])
                return self._json(HTTPStatus.OK, self.platform.list_work_orders(user, params.get("status", [None])[0], params.get("department", [None])[0], params.get("workerId", [None])[0], page, size))
            except DomainError as error:
                return self._domain_error(error)
        if user is not None and route.startswith("/api/work-orders/") and route.count("/") == 3:
            try:
                return self._json(HTTPStatus.OK, self.platform.work_order(user, route.rsplit("/", 1)[-1]))
            except DomainError as error:
                return self._domain_error(error)
        if user is not None and route.startswith("/api/reports/") and route.endswith("/comments"):
            try:
                report_id = route.split("/")[3]
                return self._json(HTTPStatus.OK, {"comments": self.platform.comments(user, report_id)})
            except DomainError as error:
                return self._domain_error(error)
        if user is not None and route.startswith("/api/reports/") and route.endswith("/attachments"):
            try:
                report_id = route.split("/")[3]
                return self._json(HTTPStatus.OK, {"attachments": self.platform.attachments(user, report_id)})
            except DomainError as error:
                return self._domain_error(error)
        if user is not None and route == "/api/intelligence/hotspots":
            try:
                return self._json(HTTPStatus.OK, {"hotspots": self.platform.hotspot_analysis(user)})
            except DomainError as error:
                return self._domain_error(error)
        if user is not None and route == "/api/intelligence/map":
            try:
                from urllib.parse import parse_qs
                params = parse_qs(urlsplit(self.path).query)
                return self._json(HTTPStatus.OK, self.platform.city_map_data(user, params.get("category", [None])[0], params.get("department", [None])[0]))
            except DomainError as error:
                return self._domain_error(error)
        if user is not None and route == "/api/sla/policies":
            try:
                from urllib.parse import parse_qs
                department = parse_qs(urlsplit(self.path).query).get("department", [None])[0]
                return self._json(HTTPStatus.OK, {"policies": self.platform.sla_policies(user, department)})
            except DomainError as error:
                return self._domain_error(error)
        if user is not None and route.startswith("/api/workers/") and route.endswith("/profile"):
            try:
                worker_id = route.split("/")[3]
                return self._json(HTTPStatus.OK, self.platform.worker_profile(user, worker_id))
            except DomainError as error:
                return self._domain_error(error)
        if route == "/" or route.lstrip("/") in SAFE_STATIC:
            return self._static(route)
        return self._json(HTTPStatus.NOT_FOUND, {"error": "Not found."})

    def do_POST(self) -> None:
        if not self._same_origin():
            return self._json(HTTPStatus.FORBIDDEN, {"error": "Cross-origin requests are not accepted."})
        route = urlsplit(self.path).path
        try:
            body = self._read_json()
            if route == "/api/auth/verify":
                self.platform.verify_account(str(body.get("token", "")))
                return self._json(HTTPStatus.OK, {"ok": True})
            if route == "/api/auth/password-reset/request":
                token = self.platform.issue_password_reset(str(body.get("email", "")))
                return self._json(HTTPStatus.OK, {"requested": True, "token": token})
            if route == "/api/auth/password-reset/confirm":
                self.platform.reset_password(str(body.get("token", "")), str(body.get("password", "")))
                return self._json(HTTPStatus.OK, {"ok": True})
            if route == "/api/auth/demo":
                user, token = self.service.demo_session(str(body.get("role", "")))
                self._set_session_cookie(token)
                return self._json(HTTPStatus.OK, {"user": user})
            if route == "/api/auth/register":
                user, token = self.service.register(
                    str(body.get("name", "")), str(body.get("email", "")),
                    str(body.get("password", "")),
                )
                self._set_session_cookie(token)
                return self._json(HTTPStatus.CREATED, {"user": user})
            if route == "/api/auth/login":
                user, token = self.service.authenticate(
                    str(body.get("email", "")), str(body.get("password", ""))
                )
                self._set_session_cookie(token)
                return self._json(HTTPStatus.OK, {"user": user})
            if route == "/api/auth/logout":
                self.service.revoke_token(self._session_token())
                self._clear_session_cookie()
                return self._json(HTTPStatus.OK, {"ok": True})

            user = self._require_session()
            if route == "/api/decisions/evaluate":
                domain = str(body.get("domain", ""))
                try:
                    policy_index = int(body.get("policyIndex"))
                except (TypeError, ValueError):
                    raise DomainError("policyIndex must be an integer.")
                context = body.get("context", {})
                if not isinstance(context, dict):
                    raise DomainError("context must be an object.")
                return self._json(HTTPStatus.OK, DecisionService().evaluate(domain, policy_index, context))
            if route == "/api/reports":
                result = self.service.create_report(user, body)
                return self._json(HTTPStatus.CREATED, result)
            if route == "/api/departments":
                self.service.create_department(
                    user, str(body.get("name", "")), str(body.get("description", "")),
                    self._integer(body.get("slaHours", 48), "SLA hours"),
                )
                return self._json(HTTPStatus.CREATED, {"ok": True})
            if route == "/api/staff":
                skills = body.get("skills")
                if not isinstance(skills, list):
                    raise DomainError("Skills must be a list.")
                self.service.create_staff(
                    user, str(body.get("name", "")), str(body.get("department", "")), skills
                )
                return self._json(HTTPStatus.CREATED, {"ok": True})
            if route == "/api/notifications/read":
                self.service.mark_notifications_read(user)
                return self._json(HTTPStatus.OK, {"ok": True})
            if route == "/api/escalations/run":
                if user["role"] != "admin":
                    raise DomainError("Only administrators can run SLA escalations.", 403)
                return self._json(HTTPStatus.OK, {"escalated": self.service.escalate_overdue()})
            if route == "/api/profile":
                return self._json(HTTPStatus.OK, self.platform.update_profile(user, body))
            if route == "/api/profile/preferences":
                return self._json(HTTPStatus.OK, self.platform.update_notification_preferences(user, body))
            if route == "/api/profile/addresses":
                return self._json(HTTPStatus.CREATED, self.platform.add_address(user, body))
            if route.startswith("/api/profile/addresses/"):
                address_id = route.rsplit("/", 1)[-1]
                self.platform.remove_address(user, address_id)
                return self._json(HTTPStatus.OK, {"ok": True})
            if route == "/api/devices":
                result = self.platform.register_device(user, str(body.get("label", "")), str(body.get("fingerprint", "")))
                return self._json(HTTPStatus.CREATED, result)
            if route.startswith("/api/devices/"):
                self.platform.revoke_device(user, route.rsplit("/", 1)[-1])
                return self._json(HTTPStatus.OK, {"ok": True})
            if route == "/api/reports/search/duplicates":
                return self._json(HTTPStatus.OK, {"candidates": self.platform.scan_duplicate_candidates(user, body.get("reportId"), int(body.get("limit", 100)))})
            if route == "/api/reports/comments":
                return self._json(HTTPStatus.CREATED, self.platform.add_comment(user, str(body.get("reportId", "")), str(body.get("body", ""))))
            if route == "/api/work-orders":
                result = self.platform.create_work_order(user, str(body.get("reportId", "")), str(body.get("instructions", "")), int(body.get("estimatedMinutes", 60)), body.get("scheduledStart"), body.get("scheduledEnd"))
                return self._json(HTTPStatus.CREATED, result)
            if route == "/api/work-orders/status":
                result = self.platform.update_work_order_status(user, str(body.get("workOrderId", "")), str(body.get("status", "")), str(body.get("note", "")))
                return self._json(HTTPStatus.OK, result)
            if route == "/api/work-orders/assign":
                result = self.platform.assign_work_order(user, str(body.get("workOrderId", "")), str(body.get("workerId", "")))
                return self._json(HTTPStatus.OK, result)
            if route == "/api/admin/roles":
                return self._json(HTTPStatus.OK, self.platform.list_roles(user))
            if route == "/api/admin/users/role":
                self.platform.set_role(user, str(body.get("userId", "")), str(body.get("role", "")))
                return self._json(HTTPStatus.OK, {"ok": True})
            if route == "/api/admin/users/lock":
                self.platform.set_account_lock(user, str(body.get("userId", "")), bool(body.get("locked", True)), int(body.get("minutes", 60)))
                return self._json(HTTPStatus.OK, {"ok": True})
            if route == "/api/admin/departments/update":
                return self._json(HTTPStatus.OK, self.platform.update_department(user, str(body.get("department", "")), body))
            if route == "/api/admin/departments/categories":
                return self._json(HTTPStatus.OK, {"categories": self.platform.set_department_categories(user, str(body.get("department", "")), body.get("categories", []))})
            if route == "/api/admin/sla":
                result = self.platform.configure_sla(user, str(body.get("department", "")), str(body.get("severity", "")), int(body.get("targetHours", 48)), float(body.get("warningRatio", 0.75)), int(body.get("escalationLevel", 1)))
                return self._json(HTTPStatus.OK, result)
            if route == "/api/admin/system-health":
                return self._json(HTTPStatus.OK, self.platform.system_health(user))
            if route == "/api/admin/departments/region":
                return self._json(HTTPStatus.OK, self.platform.set_department_region(user, str(body.get("department", "")), body))
            if route == "/api/admin/departments/policy":
                return self._json(HTTPStatus.OK, self.platform.set_department_policy(user, str(body.get("department", "")), body.get("policy", {})))
            if route == "/api/admin/workers/availability":
                result = self.platform.update_worker_availability(user, str(body.get("workerId", "")), str(body.get("status", "available")), body.get("availableFrom"), body.get("availableUntil"))
                return self._json(HTTPStatus.OK, result)
            if route == "/api/admin/workers/leave":
                result = self.platform.request_worker_leave(user, str(body.get("workerId", "")), int(body.get("startsAt")), int(body.get("endsAt")), str(body.get("reason", "")))
                return self._json(HTTPStatus.CREATED, result)
            if route == "/api/reports/update":
                return self._json(HTTPStatus.OK, self.platform.update_report(user, str(body.get("reportId", "")), body))
            if route == "/api/reports/cancel":
                self.platform.cancel_report(user, str(body.get("reportId", "")), str(body.get("reason", "")))
                return self._json(HTTPStatus.OK, {"ok": True})
            if route == "/api/reports/attachments":
                return self._json(HTTPStatus.CREATED, self.platform.add_attachment(user, str(body.get("reportId", "")), str(body.get("filename", "attachment")), str(body.get("mimeType", "")), str(body.get("data", "")), str(body.get("kind", "report"))))
            if route == "/api/reports/duplicates/verify":
                return self._json(HTTPStatus.OK, self.platform.verify_duplicate(user, str(body.get("sourceReportId", "")), str(body.get("duplicateReportId", "")), bool(body.get("confirmed", False)), float(body.get("score", 0))))
            if route == "/api/reports/duplicates/merge":
                return self._json(HTTPStatus.OK, self.platform.merge_duplicate_group(user, str(body.get("groupId", "")), str(body.get("primaryReportId", ""))))
            if route == "/api/analytics/snapshot":
                return self._json(HTTPStatus.OK, self.platform.analytics_snapshot(user, str(body.get("scopeType", "city")), str(body.get("scopeId", "city")), int(body.get("periodStart")), int(body.get("periodEnd"))))
            if route == "/api/intelligence/categorize":
                return self._json(HTTPStatus.OK, OfflineIntelligence.categorize(str(body.get("description", "")), body.get("metadata", {})))
            if route == "/api/intelligence/severity":
                return self._json(HTTPStatus.OK, OfflineIntelligence.severity(str(body.get("description", "")), str(body.get("category", "Other")), int(body.get("affectedPeople", 0))))
            if route == "/api/scheduler/run":
                if user["role"] not in {"admin", "city_admin"}:
                    raise DomainError("Only city administrators can run the scheduler.", 403)
                return self._json(HTTPStatus.OK, self.platform.run_scheduler())
            if route == "/api/reports/export":
                return self._json(HTTPStatus.OK, {"format": str(body.get("format", "csv")), "content": self.platform.export_report(user, str(body.get("format", "csv")))})
            match = REPORT_ACTION.fullmatch(route)
            if match:
                report_id, action = match.groups()
                return self._report_action(user, report_id, action, body)
            return self._json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
        except DomainError as error:
            return self._domain_error(error)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._json(HTTPStatus.BAD_REQUEST, {"error": "Request body must be valid JSON."})
        except ValueError as error:
            return self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except Exception:
            LOG.exception("Unhandled request error for %s", route)
            return self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "The server could not complete this request."})

    def _report_action(self, user: dict, report_id: str, action: str, body: dict) -> None:
        if action == "approve":
            self.service.approve_report(
                user, report_id, str(body.get("department", "")), str(body.get("worker", ""))
            )
        elif action == "start":
            self.service.start_work(user, report_id)
        elif action == "complete":
            self.service.submit_work(
                user, report_id, str(body.get("notes", "")), str(body.get("image", ""))
            )
        elif action == "verify":
            approve = body.get("approve")
            if not isinstance(approve, bool):
                raise DomainError("Approval decision must be true or false.")
            self.service.verify_work(user, report_id, approve, str(body.get("note", "")))
        elif action == "feedback":
            self.service.leave_feedback(
                user, report_id, self._integer(body.get("rating"), "rating"),
                str(body.get("comment", "")),
            )
        elif action == "reopen":
            self.service.reopen_report(user, report_id, str(body.get("reason", "")))
        else:
            return self._json(HTTPStatus.NOT_FOUND, {"error": "Unknown report action."})
        self._json(HTTPStatus.OK, {"ok": True})

    def _read_json(self) -> dict:
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except ValueError as error:
            raise DomainError("Invalid content length.") from error
        if length <= 0 or length > MAX_REQUEST_BYTES:
            raise DomainError("Request body must be between 1 byte and 4 MB.", 413)
        content_type = self.headers.get_content_type()
        if content_type != "application/json":
            raise DomainError("Requests must use application/json.", 415)
        data = json.loads(self.rfile.read(length))
        if not isinstance(data, dict):
            raise DomainError("Request body must be a JSON object.")
        return data

    def _session_token(self) -> str | None:
        cookie = SimpleCookie()
        cookie.load(self.headers.get("Cookie", ""))
        morsel = cookie.get(SESSION_COOKIE)
        return morsel.value if morsel else None

    def _session_user(self) -> dict | None:
        return self.service.user_for_token(self._session_token())

    def _require_session(self) -> dict:
        user = self._session_user()
        if user is None:
            raise DomainError("Please sign in to continue.", 401)
        return user

    def _set_session_cookie(self, token: str) -> None:
        self.pending_cookie = (
            f"{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={SESSION_TTL_SECONDS}"
        )

    def _clear_session_cookie(self) -> None:
        self.pending_cookie = f"{SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0"

    def _same_origin(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin:
            return True
        expected = f"http://{self.headers.get('Host', '')}"
        return secrets.compare_digest(origin.rstrip("/"), expected.rstrip("/"))

    def _static(self, route: str) -> None:
        requested = "index.html" if route == "/" else unquote(route.lstrip("/"))
        if requested not in SAFE_STATIC:
            return self._json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
        path = (STATIC_ROOT / requested).resolve()
        if path.parent != STATIC_ROOT.resolve() or not path.is_file():
            return self._json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
        payload = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {"application/javascript"}:
            content_type += "; charset=utf-8"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _json(self, status: int, payload: dict) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        if hasattr(self, "pending_cookie"):
            self.send_header("Set-Cookie", self.pending_cookie)
            del self.pending_cookie
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _domain_error(self, error: DomainError) -> None:
        self._json(error.status, {"error": error.message})

    def _admin_only(self, user: dict) -> None:
        if user["role"] != "admin":
            raise DomainError("Only administrators can view the audit log.", 403)

    def _audit_rows(self) -> list[dict]:
        with read_connection(self.server.civicflow_service.database_path) as connection:
            rows = connection.execute(
                """SELECT actor_name, action, entity_type, entity_id, details_json, created_at
                   FROM audit_log ORDER BY created_at DESC LIMIT 500"""
            ).fetchall()
        return [
            {
                "actor": row["actor_name"], "action": row["action"],
                "entityType": row["entity_type"], "entityId": row["entity_id"],
                "details": json.loads(row["details_json"]), "createdAt": row["created_at"],
            } for row in rows
        ]

    def _integer(self, value, label: str) -> int:
        if isinstance(value, bool):
            raise DomainError(f"{label} must be a whole number.")
        try:
            number = int(value)
        except (TypeError, ValueError) as error:
            raise DomainError(f"{label} must be a whole number.") from error
        if str(number) != str(value).strip() and not isinstance(value, int):
            raise DomainError(f"{label} must be a whole number.")
        return number


class CivicFlowHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], database_path: Path) -> None:
        initialize(database_path)
        self.civicflow_service = CivicFlowService(database_path)
        self.civicflow_platform = CivicFlowPlatform(database_path, self.civicflow_service)
        super().__init__(address, CivicFlowHandler)


def serve(host: str = "127.0.0.1", port: int = 8000,
          database_path: Path = DATABASE_PATH) -> None:
    allowed_hosts = {"127.0.0.1", "localhost", "::1"}
    if os.getenv("CIVICFLOW_ALLOW_NONLOOPBACK") == "1":
        allowed_hosts.add("0.0.0.0")
    if host not in allowed_hosts:
        raise ValueError("The development server must bind to loopback only unless CIVICFLOW_ALLOW_NONLOOPBACK=1 is set.")
    server = CivicFlowHTTPServer((host, port), database_path)
    LOG.info("CivicFlow running at http://%s:%s", host, server.server_port)
    LOG.info("SQLite database: %s", database_path)
    stop_scheduler = threading.Event()

    def escalation_loop() -> None:
        while not stop_scheduler.is_set():
            try:
                count = server.civicflow_service.escalate_overdue()
                if count:
                    LOG.info("Created %s automatic SLA escalation(s).", count)
            except Exception:
                LOG.exception("Automatic SLA escalation check failed.")
            stop_scheduler.wait(60)

    scheduler = threading.Thread(target=escalation_loop, name="civicflow-sla", daemon=True)
    scheduler.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOG.info("Shutting down CivicFlow.")
    finally:
        stop_scheduler.set()
        server.server_close()
