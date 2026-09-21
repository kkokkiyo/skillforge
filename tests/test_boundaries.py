import os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from backend.app import Database, load_case, redact
from backend.engine import execute
from backend.config import load_env


class BoundaryTests(unittest.TestCase):
    def test_exact_approval_boundary(self):
        for amount, expected in [(499999, "SUCCEEDED"), (500000, "AWAITING_APPROVAL")]:
            db = Database()
            load_case(
                db,
                {"order_id": "boundary", "amount_krw": amount, "return_received": True},
            )
            result = execute(db, "boundary")
            self.assertEqual(result["status"], expected)
            self.assertEqual(
                db.one("SELECT COUNT(*) FROM refunds")[0], int(expected == "SUCCEEDED")
            )

    def test_redaction_preserves_numeric_usage_not_credentials(self):
        r = redact(
            {
                "tokens": 128,
                "total_tokens": 128,
                "NVIDIA_API_KEY": "do-not-log",
                "access_token": "do-not-log",
                "nested": {"secret": "hidden"},
            }
        )
        self.assertEqual(r["tokens"], 128)
        self.assertEqual(r["total_tokens"], 128)
        self.assertEqual(r["access_token"], "[REDACTED]")
        self.assertNotIn("do-not-log", str(r))

    def test_enc_api_and_empty_environment_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / ".env").write_text("NVIDIA_API_KEY=\n")
            (p / ".enc.API").write_text("NVIDIA_API_KEY=local-test-value\n")
            with patch("backend.config.ROOT", p), patch.dict(
                os.environ, {"NVIDIA_API_KEY": ""}
            ):
                load_env()
                self.assertEqual(os.environ["NVIDIA_API_KEY"], "local-test-value")
