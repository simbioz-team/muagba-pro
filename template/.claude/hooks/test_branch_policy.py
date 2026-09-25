"""Тесты образца branch_policy: python3 -m unittest discover -s .claude/hooks"""

import json
import subprocess
import tempfile
import unittest
from unittest import mock

import branch_policy as bp

# Тесты гоняют схему с интеграционной веткой — ту, на которой образец
# работал вживую. Своя схема — поправь здесь вместе с константами хука.
bp.PROTECTED = {"develop", "main"}
bp.BASE = "develop"


def verdict(cmd: str, cwd: str | None = None) -> str | None:
    result = bp.judge(cmd, cwd)
    return result["hookSpecificOutput"]["permissionDecision"] if result else None


class RepoOnBranch:
    """Временный репозиторий, стоящий на заданной ветке."""

    def __init__(self, branch: str) -> None:
        self.dir = tempfile.TemporaryDirectory()
        subprocess.run(["git", "init", "-q", "-b", branch, self.dir.name], check=True)

    def __enter__(self) -> str:
        return self.dir.name

    def __exit__(self, *exc: object) -> None:
        self.dir.cleanup()


class GitPush(unittest.TestCase):
    def test_push_to_feature_branch_allowed(self) -> None:
        self.assertEqual(verdict("git push -u origin setup/e7"), "allow")

    def test_bare_push_from_feature_branch_allowed(self) -> None:
        with RepoOnBranch("feat/x") as repo:
            self.assertEqual(verdict("git push", repo), "allow")

    def test_push_to_develop_asks(self) -> None:
        self.assertEqual(verdict("git push origin develop"), "ask")

    def test_bare_push_from_develop_asks(self) -> None:
        with RepoOnBranch("develop") as repo:
            self.assertEqual(verdict("git push", repo), "ask")

    def test_refspec_into_main_asks(self) -> None:
        self.assertEqual(verdict("git push origin feat/x:main"), "ask")

    def test_force_asks(self) -> None:
        self.assertEqual(verdict("git push --force-with-lease origin feat/x"), "ask")
        self.assertEqual(verdict("git push origin +feat/x"), "ask")

    def test_delete_asks(self) -> None:
        self.assertEqual(verdict("git push origin --delete feat/x"), "ask")
        self.assertEqual(verdict("git push origin :feat/x"), "ask")

    def test_feature_push_chained_with_other_command_not_allowed(self) -> None:
        # Запрет с подсказкой, а не вопрос: вопрос ночью висит до утра.
        self.assertEqual(verdict("git push origin feat/x && rm -rf build"), "deny")

    def test_push_and_pr_chained_denied_with_hint(self) -> None:
        result = bp.judge("git push -u origin feat/x && gh pr create --base develop --title t", None)
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("отдельными вызовами", result["hookSpecificOutput"]["permissionDecisionReason"])

    def test_other_commands_untouched(self) -> None:
        self.assertIsNone(verdict("git status --short"))


class GhPrCreate(unittest.TestCase):
    def test_feature_into_develop_allowed(self) -> None:
        self.assertEqual(verdict('gh pr create --base develop --head feat/x --title "t" --body "b"'), "allow")

    def test_without_explicit_base_asks(self) -> None:
        self.assertEqual(verdict('gh pr create --head feat/x --title "t"'), "ask")

    def test_into_main_asks(self) -> None:
        self.assertEqual(verdict("gh pr create --base main --head develop"), "ask")


def fake_pr(base: str, head: str) -> mock.MagicMock:
    return mock.MagicMock(stdout=json.dumps({"baseRefName": base, "headRefName": head}))


class GhPrMerge(unittest.TestCase):
    def test_feature_into_develop_allowed(self) -> None:
        with mock.patch.object(bp.subprocess, "run", return_value=fake_pr("develop", "feat/x")):
            self.assertEqual(verdict("gh pr merge 5 --merge"), "allow")

    def test_develop_into_main_asks(self) -> None:
        with mock.patch.object(bp.subprocess, "run", return_value=fake_pr("main", "develop")):
            self.assertEqual(verdict("gh pr merge 2 --merge"), "ask")

    def test_admin_asks(self) -> None:
        self.assertEqual(verdict("gh pr merge 5 --merge --admin"), "ask")


if __name__ == "__main__":
    unittest.main()
