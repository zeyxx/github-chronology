import unittest
from chronology.cli import collect
from chronology.domain import project
from chronology.ledger import build_ledger
from test_g1 import fake


class TestLedger(unittest.TestCase):
    def test_neutral_candidates(self):
        b, _ = collect("example/repo", 1, fake)
        p = project(b)
        l = build_ledger([p])
        self.assertEqual(len(l["entries"]), 3)
        self.assertEqual(l, build_ledger([p, p]))
        for e in l["entries"]:
            self.assertEqual(e["status"], "PENDING_HUMAN_REVIEW")
            self.assertEqual(e["attribution"], "UNKNOWN_INDIVIDUAL_AUTONOMY")
            self.assertTrue(e["source_fact"]["evidence"])

    def test_no_inference_from_failed_check(self):
        def read(path, paginated):
            r = fake(path, paginated)
            if "/check-runs?" in path:
                r[0]["check_runs"][0]["conclusion"] = "failure"
            return r
        b, _ = collect("example/repo", 1, read)
        l = build_ledger([project(b)])
        self.assertEqual(len(l["entries"]), 1)
        self.assertEqual(l["entries"][0]["claim_type"], "delivery")

    def test_order_independent(self):
        a, _ = collect("example/a", 1, fake)
        b, _ = collect("example/b", 1, fake)
        self.assertEqual(build_ledger([project(a), project(b)]),
                         build_ledger([project(b), project(a)]))
