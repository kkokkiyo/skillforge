import unittest
from backend.app import Database
from backend.engine import WorkflowService, digest
from backend.skill_export import guidance


class RegenerationTests(unittest.TestCase):
    def test_policy_refresh_collects_new_isolated_evidence(self):
        db = Database()
        service = WorkflowService(db)
        old = service.discover()["new_runs"]
        self.assertEqual(len(old), 30)
        self.assertEqual(service.discover()["new_runs"], [])
        self.assertEqual(db.one("SELECT COUNT(*) FROM orders")[0], 3)
        a = service.compile()
        service.verify(a["id"])
        service.activate(a["id"])
        ph = digest({"revision": "new"})
        with db.transaction():
            db.conn.execute("UPDATE policies SET active=0")
            db.conn.execute("INSERT INTO policies VALUES (?,500000,1)", (ph,))
        self.assertEqual(service.get(a["id"])["state"], "STALE")
        new = service.discover()["new_runs"]
        self.assertEqual(len(new), 30)
        self.assertFalse(set(new) & set(old))
        b = service.compile()
        self.assertEqual(b["artifact"]["policy_hash"], ph)
        self.assertTrue(set(b["artifact"]["source_trace_ids"]) <= set(new))
        service.verify(b["id"])
        active = service.activate(b["id"])
        self.assertEqual(active["state"], "ACTIVE")
        exported = guidance(active)
        self.assertIn(active["artifact_hash"], exported)
        self.assertIn("Not a verified NemoClaw/OpenClaw runtime skill", exported)

    def test_non_active_guidance_cannot_claim_activation(self):
        db = Database()
        service = WorkflowService(db)
        service.discover()
        item = service.compile()
        with self.assertRaises(ValueError):
            guidance(item)
