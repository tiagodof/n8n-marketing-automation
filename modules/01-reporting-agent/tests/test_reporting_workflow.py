"""Structural tests for the importable n8n reporting workflow."""

import json
import unittest
from pathlib import Path

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1] / "workflows" / "reporting_agent.json"
)


class TestReportingWorkflowDefinition(unittest.TestCase):
    """Verify essential workflow invariants without requiring an n8n instance."""

    @classmethod
    def setUpClass(cls):
        cls.workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
        cls.nodes = {node["name"]: node for node in cls.workflow["nodes"]}

    def test_workflow_json_has_required_top_level_fields(self):
        self.assertEqual(self.workflow["name"], "AI Marketing Reporting Agent")
        self.assertIn("nodes", self.workflow)
        self.assertIn("connections", self.workflow)
        self.assertFalse(self.workflow["active"])

    def test_weekly_schedule_is_set_for_monday_at_seven(self):
        schedule = self.nodes["Weekly schedule"]
        interval = schedule["parameters"]["rule"]["interval"][0]
        self.assertEqual(schedule["type"], "n8n-nodes-base.scheduleTrigger")
        self.assertEqual(interval["field"], "weeks")
        self.assertEqual(interval["triggerAtDay"], [1])
        self.assertEqual(interval["triggerAtHour"], 7)
        self.assertEqual(interval["triggerAtMinute"], 0)

    def test_private_service_is_called_over_internal_network(self):
        request = self.nodes["Generate weekly report"]
        parameters = request["parameters"]
        self.assertEqual(request["type"], "n8n-nodes-base.httpRequest")
        self.assertEqual(parameters["method"], "POST")
        self.assertIn("$env.REPORTING_SERVICE_URL", parameters["url"])
        self.assertNotIn("localhost", parameters["url"])
        headers = parameters["headerParameters"]["parameters"]
        self.assertEqual(headers[0]["name"], "Authorization")
        self.assertIn("$env.REPORTING_SERVICE_TOKEN", headers[0]["value"])

    def test_email_uses_pdf_binary_attachment(self):
        email = self.nodes["Email report"]
        self.assertEqual(email["type"], "n8n-nodes-base.emailSend")
        self.assertEqual(email["parameters"]["options"]["fileAttachments"], "report_pdf")
        self.assertIn("$env.REPORT_RECIPIENT_EMAIL", email["parameters"]["toEmail"])
        self.assertIn("$env.SMTP_USER", email["parameters"]["fromEmail"])

    def test_all_connection_targets_exist(self):
        node_names = set(self.nodes)
        for source, outputs in self.workflow["connections"].items():
            self.assertIn(source, node_names)
            for output in outputs["main"]:
                for connection in output:
                    self.assertIn(connection["node"], node_names)


if __name__ == "__main__":
    unittest.main()
