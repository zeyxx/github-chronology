import copy
import unittest
from chronology.cli import collect, parse_pages
from chronology.domain import project

HEAD = "a" * 40
MERGE = "b" * 40


def fake(path, paginated):
    if "/check-runs?" in path:
        return [{"total_count": 1, "check_runs": [{"id": 5, "name": "tests",
                 "head_sha": HEAD if HEAD in path else MERGE,
                 "status": "completed", "conclusion": "success"}]}]
    if "/commits?" in path:
        return [[{"sha": HEAD, "author": {"login": "someone"}, "commit": {"message": "change"}}]]
    if "/files?" in path:
        return [[{"filename": "src/example.py", "status": "added"}]]
    if "/reviews?" in path:
        return [[{"id": 3, "state": "APPROVED", "commit_id": HEAD}]]
    return [{"number": 1, "head": {"sha": HEAD}, "merged": True, "merge_commit_sha": MERGE,
             "user": {"login": "someone"}, "commits": 1, "changed_files": 1,
             "created_at": "2026-01-01T00:00:00Z", "merged_at": "2026-01-02T00:00:00Z"}]


class TestEvidence(unittest.TestCase):
    def test_pages(self):
        self.assertEqual(parse_pages('[1]\n[2]'), [[1], [2]])

    def test_projection_and_replay(self):
        bundle, metrics = collect("example/repo", 1, fake)
        p = project(bundle)
        self.assertEqual(p, project(copy.deepcopy(bundle)))
        self.assertEqual(p["utility"], "UNKNOWN")
        self.assertEqual(p["cv_candidates"], [])
        self.assertEqual(len([f for f in p["facts"] if f["kind"] == "check"]), 2)
        self.assertTrue(all(f["evidence"] for f in p["facts"]))
        self.assertEqual(metrics["api_commands"], 7)

    def test_duplicate_commit(self):
        def read(path, paginated):
            pages = fake(path, paginated)
            return pages + pages if "/commits?" in path else pages
        b, _ = collect("example/repo", 1, read)
        self.assertEqual(b["records"]["commits"]["status"], "partial")
        self.assertEqual(len([f for f in project(b)["facts"] if f["kind"] == "commit"]), 1)

    def test_failed_checks(self):
        def read(path, paginated):
            if "/check-runs?" in path:
                raise RuntimeError("unavailable")
            return fake(path, paginated)
        b, _ = collect("example/repo", 1, read)
        p = project(b)
        self.assertEqual(p["coverage"]["checks_head"]["status"], "failed")
        self.assertFalse(any(f["kind"] == "check" for f in p["facts"]))

    def test_mismatched_sha(self):
        def read(path, paginated):
            result = fake(path, paginated)
            if "/check-runs?" in path:
                result[0]["check_runs"][0]["head_sha"] = "c" * 40
            return result
        b, _ = collect("example/repo", 1, read)
        p = project(b)
        self.assertEqual(len(p["warnings"]), 2)
        self.assertFalse(any(f["kind"] == "check" for f in p["facts"]))


if __name__ == "__main__":
    unittest.main()
