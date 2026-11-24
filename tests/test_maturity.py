import unittest
from chronology.maturity import assess, review_churn


def item(dimension, status="OBSERVED", revision="a"):
    return {"subject": "example/repo", "dimension": dimension, "status": status,
            "revision": revision, "environment": "ci", "source": "fixture",
            "claim": "synthetic observation", "method": "reviewed fixture"}


class MaturityTest(unittest.TestCase):
    def test_ci_is_not_runtime_or_utility(self):
        result = assess("example/repo", [item("verification")])
        self.assertEqual(result["dimensions"]["runtime"]["status"], "UNKNOWN")
        self.assertEqual(result["dimensions"]["deployment"]["status"], "UNKNOWN")
        self.assertEqual(result["utility"], "UNASSESSED")

    def test_keep_failed_and_successful_revisions(self):
        a, b = item("verification"), item("verification", "FAILED", "b")
        result = assess("example/repo", [a, b, a])
        self.assertEqual(len(result["dimensions"]["verification"]["evidence"]), 2)
        self.assertEqual(result, assess("example/repo", [b, a]))

    def test_scope_required(self):
        a = item("runtime")
        del a["environment"]
        with self.assertRaises(ValueError):
            assess("example/repo", [a])

    def test_churn_requires_evidence(self):
        with self.assertRaises(ValueError):
            review_churn("a", "b", "latency", [])
        result = review_churn("a", "b", "latency", ["fixture"])
        self.assertEqual(result["status"], "PENDING_REVIEW")
