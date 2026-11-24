import json
from pathlib import Path
import tempfile
import unittest
from github_chronology import Store, scan, entity_key, safe_root


class FakeAPI:
    def __init__(self, fail=False):
        self.fail = fail

    def pages(self, endpoint):
        for i in (1, 2):
            if i == 2 and self.fail:
                raise TimeoutError
            items = [{"id": 17, "body": "revision " + str(i)}]
            yield "https://api.github.com" + endpoint + "?page=" + str(i), json.dumps(items).encode(), items


class TestEvidence(unittest.TestCase):
    def test_snapshot_history_and_receipts(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            store = Store(root)
            try:
                a = store.run({})
                b = store.run({})
                scan(store, FakeAPI(), a, 1, "/test", "issue")
                scan(store, FakeAPI(), b, 1, "/test", "issue")
                self.assertEqual(store.db.execute("SELECT count(*) FROM snapshots").fetchone()[0], 2)
                self.assertEqual(store.db.execute("SELECT count(*) FROM observations").fetchone()[0], 4)
                self.assertEqual(store.db.execute("SELECT count(*) FROM blobs").fetchone()[0], 2)
                store.export(root)
                self.assertEqual(len((root / "evidence.jsonl").read_text().splitlines()), 4)
            finally:
                store.close()

    def test_partial_never_complete(self):
        with tempfile.TemporaryDirectory() as d:
            store = Store(Path(d))
            try:
                run = store.run({})
                scan(store, FakeAPI(True), run, 1, "/test", "issue")
                self.assertEqual(store.db.execute("SELECT status,pages,items,error FROM coverage").fetchone(),
                                 ("partial", 1, 1, "TimeoutError"))
            finally:
                store.close()

    def test_entity_identity(self):
        self.assertEqual(entity_key({"id": 42, "sha": "abc"}), "42")
        self.assertEqual(entity_key({"sha": "abc"}), "abc")

    def test_worktree_guard(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / ".git").mkdir()
            with self.assertRaises(ValueError):
                safe_root(root / "corpus")


if __name__ == "__main__":
    unittest.main()
