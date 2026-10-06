"""Integration tests for CivicFlow's extended platform services."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from backend.database import initialize
from backend.platform import CivicFlowPlatform, OfflineIntelligence
from backend.service import CivicFlowService, DomainError


class PlatformTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = Path(self.tempdir.name) / "platform.sqlite3"
        initialize(self.db)
        self.core = CivicFlowService(self.db)
        self.platform = CivicFlowPlatform(self.db, self.core)
        self.admin, _ = self.core.demo_session("admin")
        self.city_admin, _ = self.core.demo_session("city_admin")
        self.manager, _ = self.core.demo_session("supervisor")
        self.worker, _ = self.core.demo_session("worker")
        self.citizen, _ = self.core.demo_session("citizen")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_profile_address_and_preferences_round_trip(self):
        result = self.platform.update_profile(self.citizen, {
            "phone": "+91 98765 43210",
            "addressLine1": "12 Civic Road",
            "city": "Vijayawada",
            "postalCode": "520001",
            "preferredLanguage": "en-IN",
            "latitude": 16.51,
            "longitude": 80.64,
        })
        self.assertEqual(result["profile"]["city"], "Vijayawada")
        address = self.platform.add_address(self.citizen, {"label": "Home", "address": "12 Civic Road", "primary": True})
        self.assertTrue(address["id"].startswith("ADDR-"))
        preferences = self.platform.update_notification_preferences(self.citizen, {"reportUpdates": False, "feedback": False})
        self.assertEqual(preferences["report_updates"], 0)
        self.platform.remove_address(self.citizen, address["id"])

    def test_device_lifecycle(self):
        device = self.platform.register_device(self.citizen, "Office PC", "device-fingerprint-unique-001")
        devices = self.platform.devices(self.citizen)
        self.assertTrue(any(item["id"] == device["id"] for item in devices))
        self.platform.revoke_device(self.citizen, device["id"])
        self.assertEqual(self.platform.devices(self.citizen)[0]["active"], 0)

    def test_password_reset_and_verification_tokens(self):
        verification = self.platform.issue_verification_token(self.citizen["id"])
        self.platform.verify_account(verification)
        reset = self.platform.issue_password_reset(self.citizen["email"])
        self.assertIsNotNone(reset)
        self.platform.reset_password(reset, "BetterPass123")
        refreshed, _ = self.core.authenticate(self.citizen["email"], "BetterPass123")
        self.assertEqual(refreshed["id"], self.citizen["id"])

    def test_account_lock_and_role_catalog(self):
        self.platform.set_account_lock(self.admin, self.citizen["id"], True, 10)
        security = self.platform.account_security(self.citizen["id"])
        self.assertIsNotNone(security["locked_until"])
        self.platform.set_account_lock(self.admin, self.citizen["id"], False)
        self.assertIsNone(self.platform.account_security(self.citizen["id"])["locked_until"])
        roles = self.platform.list_roles(self.admin)
        names = {row["name"] for row in roles}
        self.assertTrue({"citizen", "worker", "supervisor", "staff", "department_admin", "city_admin", "admin"}.issubset(names))

    def test_report_comments_and_attachments(self):
        created = self.core.create_report(self.citizen, {"category": "Pothole", "description": "A deep pothole outside the school crossing is dangerous for children.", "location": "Civic Road"})
        report_id = created["reportId"]
        comment = self.platform.add_comment(self.citizen, report_id, "Please inspect this location soon.")
        self.assertEqual(comment["reportId"], report_id)
        comments = self.platform.comments(self.citizen, report_id)
        self.assertEqual(len(comments), 1)
        attachment = self.platform.add_attachment(self.citizen, report_id, "evidence.txt", "text/plain", "Y2l2aWNmbG93")
        self.assertEqual(attachment["reportId"], report_id)
        self.assertEqual(len(self.platform.attachments(self.citizen, report_id)), 1)

    def test_duplicate_group_verification_and_merge(self):
        first = self.core.create_report(self.citizen, {"category": "Pothole", "description": "Deep pothole outside the school crossing is forcing traffic to swerve.", "location": "Civic Road"})
        second = self.core.create_report(self.citizen, {"category": "Pothole", "description": "A deep pothole outside the school crossing makes cars swerve.", "location": "Civic Road"})
        result = self.platform.verify_duplicate(self.admin, first["reportId"], second["reportId"], True, 0.92)
        merged = self.platform.merge_duplicate_group(self.admin, result["groupId"], first["reportId"])
        self.assertEqual(merged["primaryReportId"], first["reportId"])

    def test_work_order_create_assign_and_status(self):
        created = self.core.create_report(self.citizen, {"category": "Pothole", "description": "Deep pothole beside the hospital gate needs a repair crew.", "location": "Hospital Road"})
        report_id = created["reportId"]
        order = self.platform.create_work_order(self.admin, report_id, "Barricade the area, fill the pothole and photograph the result.", 90)
        worker_row = self.platform.worker_profile(self.admin, "worker-1")
        order = self.platform.assign_work_order(self.admin, order["id"], worker_row["worker"]["id"])
        self.assertEqual(order["status"], "Assigned")
        updated = self.platform.update_work_order_status(self.worker, order["id"], "In Progress", "Crew arrived at the site.")
        self.assertEqual(updated["status"], "In Progress")

    def test_search_and_analytics_endpoints_have_results(self):
        self.core.create_report(self.citizen, {"category": "Streetlight", "description": "Streetlight lamp is out beside the park entrance.", "location": "Park Road"})
        self.core.create_report(self.citizen, {"category": "Garbage", "description": "Garbage bins are overflowing near the market entrance.", "location": "Market Road"})
        results = self.platform.search(self.admin, "streetlight")
        self.assertTrue(results)
        self.assertIn("report", {item["document_type"] for item in results})
        metrics = self.platform.analytics_snapshot(self.admin, "city", "city", 0, 9_999_999_999_999)
        self.assertGreaterEqual(metrics["metrics"]["total"], 2)

    def test_offline_intelligence_is_deterministic(self):
        result = OfflineIntelligence.categorize("There is a broken streetlight near the school crossing.")
        self.assertEqual(result["category"], "Streetlight")
        severity = OfflineIntelligence.severity("Emergency exposed wire beside traffic signal", "Traffic signal", 20)
        self.assertEqual(severity["level"], "Critical")
        self.assertEqual(self.platform.search(self.citizen, "nothing"), [])


if __name__ == "__main__":
    unittest.main()
