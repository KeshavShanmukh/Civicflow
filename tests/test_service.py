"""Focused integration tests for SQLite-backed CivicFlow use cases."""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from backend.database import initialize, read_connection, transaction
from backend.service import CivicFlowService, DomainError


class CivicFlowServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "civicflow-test.sqlite3"
        initialize(self.database_path)
        self.service = CivicFlowService(self.database_path)
        self.citizen, self.citizen_token = self.service.demo_session("citizen")
        self.admin, self.admin_token = self.service.demo_session("admin")
        self.worker, self.worker_token = self.service.demo_session("worker")
        self.supervisor, self.supervisor_token = self.service.demo_session("supervisor")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def create_report(self, location: str = "Test Avenue block 700") -> str:
        result = self.service.create_report(self.citizen, {
            "category": "Pothole",
            "description": "A deep pothole creates a dangerous hazard near this crosswalk.",
            "location": location,
        })
        return result["reportId"]

    def test_seeded_database_is_idempotent_and_session_tokens_are_private(self) -> None:
        initialize(self.database_path)
        with read_connection(self.database_path) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM reports").fetchone()[0], 5)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM departments").fetchone()[0], 5)
            token_hash = connection.execute("SELECT token_hash FROM sessions LIMIT 1").fetchone()[0]
            self.assertNotEqual(token_hash, self.citizen_token)
        self.assertEqual(self.service.user_for_token(self.citizen_token)["id"], self.citizen["id"])
        self.assertIsNone(self.service.user_for_token("invalid"))

    def test_report_validation_and_duplicate_detection(self) -> None:
        with self.assertRaises(DomainError):
            self.service.create_report(self.citizen, {"category": "Unknown", "description": "short"})
        first_id = self.create_report()
        second = self.service.create_report(self.citizen, {
            "category": "Pothole",
            "description": "Deep pothole creates a hazard close to this crosswalk.",
            "location": "Test Avenue block 700",
        })
        self.assertNotEqual(first_id, second["reportId"])
        self.assertEqual(second["duplicateOf"], first_id)
        report = next(item for item in self.service.state(self.citizen)["reports"] if item["id"] == second["reportId"])
        self.assertEqual(report["status"], "Awaiting review")
        self.assertEqual(report["history"][-1]["status"], "Possible duplicate")

    def test_full_review_work_verification_feedback_and_reopen_cycle(self) -> None:
        report_id = self.create_report("Lifecycle Street 18")
        self.service.approve_report(self.admin, report_id, "Roads", "Taylor Brooks")
        self.service.start_work(self.worker, report_id)
        self.service.submit_work(self.worker, report_id, "Filled the pothole and restored the road surface.")
        self.service.verify_work(self.supervisor, report_id, True, "Repair checked on site.")
        self.service.leave_feedback(self.citizen, report_id, 5, "The road is safe again.")
        self.service.reopen_report(self.citizen, report_id, "A section beside the repair is still unsafe.")
        report = next(item for item in self.service.state(self.citizen)["reports"] if item["id"] == report_id)
        self.assertEqual(report["status"], "Awaiting review")
        self.assertEqual(report["history"][-2]["status"], "Reopened")
        self.assertIsNone(report["feedback"])
        with read_connection(self.database_path) as connection:
            actions = {
                row[0] for row in connection.execute("SELECT action FROM audit_log")
            }
        self.assertTrue({"report_created", "report_assigned", "work_started", "work_submitted", "report_resolved", "report_reopened"} <= actions)

    def test_role_boundaries_and_rejection_require_reason(self) -> None:
        report_id = self.create_report("Boundary Street 11")
        with self.assertRaises(DomainError) as denied:
            self.service.approve_report(self.worker, report_id, "Roads", "Taylor Brooks")
        self.assertEqual(denied.exception.status, 403)
        self.service.approve_report(self.admin, report_id, "Roads", "Taylor Brooks")
        self.service.start_work(self.worker, report_id)
        self.service.submit_work(self.worker, report_id, "Completed the repair and cleared the site.")
        with self.assertRaises(DomainError):
            self.service.verify_work(self.admin, report_id, False, "no")
        self.service.verify_work(self.admin, report_id, False, "The repair needs additional compaction.")
        report = next(item for item in self.service.state(self.admin)["reports"] if item["id"] == report_id)
        self.assertEqual(report["status"], "Assigned")

    def test_department_sla_staff_and_analytics(self) -> None:
        self.service.create_department(self.admin, "Parks & Recreation", "Park grounds and recreation assets.", 96)
        self.service.create_staff(self.admin, "Robin Park", "Parks & Recreation", ["Public infrastructure"])
        state = self.service.state(self.admin)
        custom = next(item for item in state["departments"] if item["name"] == "Parks & Recreation")
        self.assertEqual(custom["sla_hours"], 96)
        member = next(item for item in state["staff"] if item["name"] == "Robin Park")
        self.assertEqual(member["skills"], ["Public infrastructure"])
        analytics = self.service.analytics(self.admin)
        self.assertEqual(analytics["total"], 5)
        self.assertEqual(len(analytics["weekly"]), 7)
        self.assertIn("overdue", analytics)

    def test_sla_escalations_are_staged_idempotent_and_notified(self) -> None:
        report_id = self.create_report("SLA Street 44")
        with transaction(self.database_path) as connection:
            connection.execute(
                "UPDATE reports SET created_at=? WHERE id=?",
                (int(time.time() * 1000) - 49 * 60 * 60 * 1000, report_id),
            )
        self.assertEqual(self.service.escalate_overdue(), 1)
        self.assertEqual(self.service.escalate_overdue(), 0)
        with transaction(self.database_path) as connection:
            connection.execute(
                "UPDATE reports SET created_at=? WHERE id=?",
                (int(time.time() * 1000) - 7 * 24 * 60 * 60 * 1000, report_id),
            )
        self.assertEqual(self.service.escalate_overdue(), 1)
        self.assertEqual(self.service.escalate_overdue(), 1)
        with read_connection(self.database_path) as connection:
            levels = [
                row[0] for row in connection.execute(
                    "SELECT level FROM escalation_records WHERE report_id=? ORDER BY level",
                    (report_id,),
                )
            ]
            notices = connection.execute(
                "SELECT COUNT(*) FROM notifications WHERE report_id=?", (report_id,)
            ).fetchone()[0]
        self.assertEqual(levels, [1, 2, 3])
        self.assertGreaterEqual(notices, 6)

    def test_registration_uses_hash_and_duplicate_email_is_rejected(self) -> None:
        user, token = self.service.register("New Citizen", "new@example.local", "SecureCitizen1")
        self.assertEqual(user["role"], "citizen")
        self.assertTrue(token)
        self.assertIsNone(self.service.user_for_token(user.get("password_hash")))
        with read_connection(self.database_path) as connection:
            encoded = connection.execute("SELECT password_hash FROM users WHERE id=?", (user["id"],)).fetchone()[0]
        self.assertNotIn("SecureCitizen1", encoded)
        with self.assertRaises(DomainError):
            self.service.register("Another Citizen", "NEW@example.local", "SecureCitizen1")


if __name__ == "__main__":
    unittest.main()
