import unittest
from chronology.inventory import inventory, select_prs


def reader(url, paginated):
    if "/pulls?" in url:
        return [[{"number": i, "created_at": f"2026-01-{i:02d}", "merged_at": "yes" if i < 7 else None}
                 for i in range(1, 9)]]
    if "/commits?" in url:
        return [[{"sha": "a"*40}]]
    if "/commits/" in url:
        return [{"sha": "a"*40}]
    return [{"default_branch": "main"}]


class TestInventory(unittest.TestCase):
    def test_small_and_sample(self):
        inv = inventory("example/repo", reader)
        self.assertEqual(inv["counts"], {"prs": 8, "default_branch_commits": 1})
        self.assertEqual(select_prs(inv, 12)["numbers"], list(range(1, 9)))
        sample = select_prs(inv, 3)
        self.assertEqual(sample["numbers"], [1, 7, 8])
        self.assertEqual(sample["not_selected"], 5)

    def test_page_budget(self):
        def read(url, paginated):
            if "/pulls?" in url:
                return [[{"number": i} for i in range(100)]]
            return reader(url, paginated)
        inv = inventory("example/repo", read, 1)
        self.assertEqual(inv["records"]["prs"]["status"], "partial")
        self.assertEqual(inv["records"]["prs"]["error"], "page_budget_exhausted")

    def test_preserve_partial_pages(self):
        def read(url, paginated):
            if "/pulls?" in url:
                if url.endswith("page=1"):
                    return [[{"number": i} for i in range(100)]]
                raise RuntimeError("unavailable")
            return reader(url, paginated)
        inv = inventory("example/repo", read, 3)
        self.assertEqual(inv["counts"]["prs"], 100)
        self.assertEqual(inv["records"]["prs"]["status"], "partial")
