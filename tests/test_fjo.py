"""Offline tests for fjo's parsing and formatting. No network: nothing here calls the API."""
import importlib.machinery
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
loader = importlib.machinery.SourceFileLoader("fjo", os.path.join(HERE, "..", "bin", "fjo"))
fjo = importlib.util.module_from_spec(importlib.util.spec_from_loader("fjo", loader))
loader.exec_module(fjo)


class Remotes(unittest.TestCase):
    def test_spellings(self):
        for url in ["ssh://git@git.example.org:2222/Org/repo.git", "git@git.example.org:Org/repo.git",
                    "https://git.example.org/Org/repo.git", "https://git.example.org/Org/repo", "ssh://git@git.example.org/Org/repo"]:
            self.assertEqual(fjo.parse_remote(url), ("git.example.org", "Org/repo"), url)

    def test_junk(self):
        self.assertEqual(fjo.parse_remote("not a url"), (None, None))


class Formatting(unittest.TestCase):
    def test_pr_line_uses_label_when_branch_is_gone(self):
        p = {"number": 7, "state": "closed", "merged": True, "title": "fix it", "updated_at": "2026-10-25T18:00:00Z",
             "head": {"ref": "refs/pull/7/head", "label": "ESP-90/needs-you", "sha": "cb28f32abc"}, "base": {"ref": "main"},
             "user": {"login": "miguel"}}
        self.assertEqual(fjo.fmt_pr(p), "#7  merged  ESP-90/needs-you -> main  cb28f32  @miguel  2026-10-25  fix it")

    def test_pr_line_with_ci_and_review(self):
        p = {"number": 9, "state": "open", "title": "t", "updated_at": "2026-10-25T18:00:00Z",
             "head": {"ref": "b", "sha": "142e5b69e"}, "base": {"ref": "main"}, "user": {"login": "u"}}
        self.assertEqual(fjo.fmt_pr(p, "success", "approved(r)"), "#9  open  b -> main  142e5b6  ci success  review approved(r)  @u  2026-10-25  t")

    def test_pr_line_marks_a_draft(self):
        p = {"number": 4, "state": "open", "draft": True, "title": "WIP: feat: x", "updated_at": "2026-10-26T18:00:00Z",
             "head": {"ref": "b", "sha": "142e5b69e"}, "base": {"ref": "main"}, "user": {"login": "u"}}
        self.assertEqual(fjo.fmt_pr(p), "#4  open,draft  b -> main  142e5b6  @u  2026-10-26  WIP: feat: x")

    def test_draft_titles(self):
        for t in ["WIP: feat: x", "wip: feat: x", "[WIP] feat: x", "[wip]feat: x"]:
            self.assertTrue(fjo.is_draft_title(t), t)
            self.assertEqual(fjo.ready_title(t), "feat: x", t)
        self.assertFalse(fjo.is_draft_title("feat: wip handling"))
        self.assertFalse(fjo.is_draft_title(" WIP: x"))  # Forgejo matches the prefix at the start only
        self.assertFalse(fjo.is_draft_title(None))
        self.assertEqual(fjo.ready_title("WIP: [WIP] feat: x"), "feat: x")
        self.assertEqual(fjo.draft_title("feat: x"), "WIP: feat: x")
        self.assertEqual(fjo.draft_title("[WIP] feat: x"), "[WIP] feat: x")

    def test_review_summary(self):
        rs = [{"state": "REQUEST_CHANGES", "user": {"login": "r"}, "submitted_at": "2026-10-25T01:00:00Z", "dismissed": True},
              {"state": "COMMENT", "user": {"login": "r"}, "submitted_at": "2026-10-25T02:00:00Z"},
              {"state": "APPROVED", "user": {"login": "r"}, "submitted_at": "2026-10-25T03:00:00Z"}]
        self.assertEqual(fjo.review_summary(rs), "approved(r)")
        rs.append({"state": "REQUEST_CHANGES", "user": {"login": "s"}, "submitted_at": "2026-10-25T04:00:00Z"})
        self.assertEqual(fjo.review_summary(rs), "changes requested(s)")
        self.assertEqual(fjo.review_summary([]), "")

    def test_clip(self):
        self.assertEqual(fjo.clip("a\n\nb\nc"), "a\nb ...")
        self.assertEqual(fjo.clip("a\nb"), "a\nb")
        self.assertEqual(fjo.clip("x" * 300)[-4:], " ...")
        self.assertEqual(fjo.clip("a\nb\nc", full=True), "a\nb\nc")

    def test_duration(self):
        self.assertEqual(fjo.duration(34e9), "34s")
        self.assertEqual(fjo.duration(175e9), "2m55s")

    def test_tail_strips_timestamps(self):
        text = "2026-10-26T01:15:04.5678633Z one\n2026-10-26T01:15:05.0Z two\n2026-10-26T01:15:06.0Z three\n"
        self.assertEqual(fjo.tail_log(text, 2), (["two", "three"], 3))
        self.assertEqual(fjo.tail_log(text, 0), (["one", "two", "three"], 3))
        self.assertEqual(fjo.tail_log(text, 1, raw=True), (["2026-10-26T01:15:06.0Z three"], 3))
        self.assertEqual(fjo.tail_log("", 5), ([], 0))

    def test_error_pattern(self):
        for line in ["::error::a required job failed", "--- FAIL: TestX", "panic: boom", "exitcode '1': failure", "Process completed with exit code 2"]:
            self.assertTrue(fjo.ERR.search(line), line)
        self.assertFalse(fjo.ERR.search("Success - Post actions/checkout"))


class DraftCommands(unittest.TestCase):
    """cmd_pr_ready and cmd_pr_draft with the API stubbed: the no-op paths and the PATCH they send."""

    def run_cmd(self, f, pr, number=4):
        import contextlib, io, types
        sent = []
        saved = fjo.rp, fjo.get_pr, fjo.call
        fjo.rp = lambda a: "/repos/o/r"
        fjo.get_pr = lambda prefix, n: dict(pr)
        fjo.call = lambda m, path, body=None, **kw: sent.append((m, path, body)) or {**pr, **(body or {})}
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                f(types.SimpleNamespace(number=number, repo=None))
        finally:
            fjo.rp, fjo.get_pr, fjo.call = saved
        return out.getvalue(), sent

    PR = {"number": 4, "state": "open", "title": "feat: x", "updated_at": "2026-10-26T18:00:00Z",
          "head": {"ref": "b", "sha": "142e5b69e"}, "base": {"ref": "main"}, "user": {"login": "u"}}

    def test_ready_is_a_noop_on_a_ready_pr(self):
        out, sent = self.run_cmd(fjo.cmd_pr_ready, self.PR)
        self.assertIn("already ready for review", out)
        self.assertEqual(sent, [])

    def test_ready_strips_the_prefix(self):
        out, sent = self.run_cmd(fjo.cmd_pr_ready, {**self.PR, "draft": True, "title": "WIP: feat: x"})
        self.assertEqual(sent, [("PATCH", "/repos/o/r/pulls/4", {"title": "feat: x"})])

    def test_ready_refuses_a_prefix_it_does_not_know(self):
        with self.assertRaises(SystemExit):
            self.run_cmd(fjo.cmd_pr_ready, {**self.PR, "draft": True, "title": "Draft: feat: x"})

    def test_draft_is_a_noop_on_a_draft(self):
        out, sent = self.run_cmd(fjo.cmd_pr_draft, {**self.PR, "draft": True, "title": "WIP: feat: x"})
        self.assertIn("already a draft", out)
        self.assertEqual(sent, [])

    def test_draft_adds_the_prefix(self):
        out, sent = self.run_cmd(fjo.cmd_pr_draft, self.PR)
        self.assertEqual(sent, [("PATCH", "/repos/o/r/pulls/4", {"title": "WIP: feat: x"})])


class Args(unittest.TestCase):
    def test_pr_number(self):
        self.assertEqual(fjo.pr_number("#9"), 9)
        self.assertEqual(fjo.pr_number("9"), 9)
        with self.assertRaises(Exception):
            fjo.pr_number("nine")

    def test_text_arg_literal(self):
        self.assertEqual(fjo.text_arg("hello"), "hello")
        self.assertIsNone(fjo.text_arg(None))


if __name__ == "__main__":
    unittest.main()
