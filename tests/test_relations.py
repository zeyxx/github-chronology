import unittest
from chronology.relations import collect_account, project_relations


def fake(path, paginated):
    actor = {"id": 1, "login": "example"}
    owned = {"id": 2, "owner": actor, "full_name": "example/fork"}
    if path == "/user":
        return [actor]
    if path.startswith("/user/repos?"):
        return [[owned]]
    if path == "/repos/example/fork":
        return [{**owned, "fork": True, "parent": {"id": 3, "full_name": "other/base"},
                 "source": {"id": 3, "full_name": "other/base"}}]
    item = {"id": 5, "user": actor, "repository_url": "https://api.github.com/repos/other/base",
            "html_url": "https://github.com/other/base/issues/1", "state": "closed"}
    if "is%3Apr" in path:
        return [{"items": [item], "total_count": 1, "incomplete_results": False}]
    return [{"items": [item], "total_count": 1, "incomplete_results": False}]


class Relations(unittest.TestCase):
    def test_fork_and_external_type(self):
        b = collect_account(fake)
        g = project_relations(b)
        self.assertEqual(g["counts"]["forks"], 1)
        self.assertEqual(g["counts"]["external_issues"], 1)
        self.assertEqual(g["counts"]["external_prs"], 0)
        self.assertIn("FORKED_FROM", [x["type"] for x in g["edges"]])
        self.assertTrue(g["warnings"])
        self.assertEqual(g, project_relations(b))

    def test_unknown_not_nonfork(self):
        def read(path, paginated):
            if path == "/repos/example/fork":
                raise RuntimeError("unavailable")
            return fake(path, paginated)
        g = project_relations(collect_account(read))
        self.assertEqual(g["counts"]["fork_unknown"], 1)
        self.assertEqual(g["counts"]["nonforks"], 0)

    def test_tampering(self):
        b = collect_account(fake)
        b["records"]["account"]["pages"][0]["id"] = 999
        with self.assertRaises(ValueError):
            project_relations(b)
