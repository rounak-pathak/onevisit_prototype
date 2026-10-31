import os
import sys
import unittest
from datetime import date

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)
import app


class OneVisitEngineTests(unittest.TestCase):
    def test_sample_scholarship_detects_expired_certificate(self):
        report = app.analyze("Scholarship", app.DEMO_DOCS)
        messages = [item["message"].lower() for item in report["issues"]]
        self.assertTrue(any("appears expired" in message for message in messages))
        self.assertEqual(len(report["documents"]), 4)

    def test_sample_detects_name_variation(self):
        report = app.analyze("Scholarship", app.DEMO_DOCS)
        self.assertTrue(any("name differs" in item["message"].lower() for item in report["issues"]))

    def test_missing_required_documents_are_flagged(self):
        report = app.analyze("Scholarship", [app.DEMO_DOCS[0]])
        self.assertIn("Income certificate", report["missing"])
        self.assertIn("Bank passbook", report["missing"])
        self.assertIn("Student / bonafide certificate", report["missing"])

    def test_service_checklist_changes_by_service(self):
        pension = app.analyze("Pension", [app.DEMO_DOCS[0]])
        self.assertIn("Age proof", pension["missing"])
        self.assertNotIn("Student / bonafide certificate", pension["missing"])

    def test_unknown_document_does_not_satisfy_checklist(self):
        report = app.analyze("Scholarship", [("notes.txt", "hello world")])
        self.assertEqual(report["documents"][0]["type"], "unknown")
        self.assertEqual(len(report["missing"]), 4)

    def test_readiness_score_bounded(self):
        report = app.analyze("Scholarship", [])
        self.assertGreaterEqual(report["score"], 0)
        self.assertLessEqual(report["score"], 100)


if __name__ == "__main__":
    unittest.main()
