import unittest
from chronology.forks import collect_fork

P, F, W = "a"*40, "b"*40, "c"*40


def fake(url, paginated):
    if url == "/repos/me/fork":
        return [{"id": 2, "fork": True, "parent": {"id": 1, "full_name": "up/base"},
                 "default_branch": "main", "owner": {"login": "me"}}]
    if url == "/repos/up/base":
        return [{"id": 1, "default_branch": "main", "owner": {"login": "up"}}]
    if "/commits/" in url:
        return [{"sha": P if "/up/base/" in url else F}]
    if "/branches?" in url:
        return [[{"name": "main", "commit": {"sha": F}},
                 {"name": "work", "commit": {"sha": W}},
                 {"name": "work-copy", "commit": {"sha": W}}]]
    if "/compare/" in url:
        return [{"base_commit": {"sha": P}, "merge_base_commit": {"sha": P},
                 "ahead_by": 3 if W in url else 1, "behind_by": 0, "status": "ahead"}]
    raise ValueError("unexpected path")


class ForkTest(unittest.TestCase):
    def test_pinned_and_duplicate_tip(self):
        b = collect_fork("me/fork", fake)
        self.assertFalse(b["partial"])
        self.assertEqual(len(b["branches"]), 3)
        self.assertEqual(len([k for k in b["records"] if k.startswith("compare:")]), 2)
        self.assertEqual(b["branches"][1]["comparison"]["ahead"], 3)
        self.assertIn(P, b["records"]["compare:"+W]["source"])

    def test_budget(self):
        b = collect_fork("me/fork", fake, 1)
        self.assertTrue(b["partial"])
        self.assertEqual(len(b["branches"]), 1)

    def test_unknown_is_not_zero(self):
        def read(url, paginated):
            if "/compare/" in url:
                raise RuntimeError("unavailable")
            return fake(url, paginated)
        b = collect_fork("me/fork", read)
        self.assertTrue(b["partial"])
        self.assertIsNone(b["branches"][0]["comparison"])
