import unittest
from chronology.contributions import collect_issue, classify_issue
from chronology.domain import digest


def fake(path, paginated):
    if "/comments" in path:
        return [[{"id": 3, "user": {"id": 2}, "author_association": "OWNER",
                  "body": "Fixed."}]]
    return [{"number": 1, "state": "closed", "state_reason": "completed",
             "user": {"id": 1}, "comments": 1}]


class ContributionTest(unittest.TestCase):
    def test_closed_is_not_fixed(self):
        b = collect_issue("example/repo", 1, fake)
        self.assertEqual(classify_issue(b)["disposition"], "UNASSESSED")
        self.assertEqual(classify_issue(b)["fix_evidence"], "UNVERIFIED")

    def test_explicit_scoped_review(self):
        b = collect_issue("example/repo", 1, fake)
        a = {"bundle_sha256": digest(b), "comment_id": 3, "disposition": "FIX_REPORTED",
             "reviewer": "operator", "scope": "reported issue", "rationale": "Owner reports fix"}
        result = classify_issue(b, a)
        self.assertEqual(result["fix_evidence"], "MAINTAINER_REPORTED")
        self.assertEqual(result["impact"], "UNKNOWN")
        a["bundle_sha256"] = "stale"
        with self.assertRaises(ValueError):
            classify_issue(b, a)

    def test_missing_comments_not_silence(self):
        def read(path, paginated):
            if "/comments" in path:
                raise RuntimeError("unavailable")
            return fake(path, paginated)
        b = collect_issue("example/repo", 1, read)
        self.assertTrue(classify_issue(b)["partial"])
        self.assertEqual(classify_issue(b)["response_observation"], "UNKNOWN")

    def test_author_cannot_confirm_own_report(self):
        def read(path, paginated):
            p = fake(path, paginated)
            if "/comments" in path:
                p[0][0]["user"]["id"] = 1
            return p
        b = collect_issue("example/repo", 1, read)
        a = {"bundle_sha256": digest(b), "comment_id": 3, "disposition": "FIX_REPORTED",
             "reviewer": "operator", "scope": "issue", "rationale": "claim"}
        with self.assertRaises(ValueError):
            classify_issue(b, a)
