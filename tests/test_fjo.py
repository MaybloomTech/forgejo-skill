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
