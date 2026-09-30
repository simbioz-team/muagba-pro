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

    def test_background_ampersand_is_a_separator(self) -> None:
        # Фоновый & не считался разделителем, и allow пуша протаскивал
        # соседнюю команду целиком.
        self.assertEqual(verdict("git push origin feat/x & rm -rf ~/x"), "deny")

    def test_hidden_push_is_denied_not_asked(self) -> None:
        # Нашёл ревьюер narta: скобки, обёртки и перенос строки прятали
        # склейку, и она уходила в вопрос человеку — ночью до утра.
        for cmd in ("(git push)", 'bash -c "git push origin feat/x"', "sh -c 'git push'",
                    "git status\ngit push origin feat/x", "git push origin feat/x 2>&1"):
            with self.subTest(cmd=cmd):
                self.assertEqual(verdict(cmd), "deny")

    def test_word_push_in_other_command_is_not_a_push(self) -> None:
        # Раньше слово push где угодно в составной команде давало запрет.
        self.assertIsNone(verdict("git status && grep -rn push docs"))
        self.assertIsNone(verdict('git log --oneline | grep "pr merge"'))

    def test_global_flags_and_path_do_not_hide_push(self) -> None:
        self.assertEqual(verdict("git -C . push origin feat/x"), "allow")
        self.assertEqual(verdict("git -c push.default=current push origin feat/x"), "allow")
        self.assertEqual(verdict("/usr/bin/git push origin feat/x"), "allow")
        self.assertEqual(verdict("git -C . push origin develop"), "ask")

    def test_git_c_path_is_used_for_current_branch(self) -> None:
        with RepoOnBranch("feat/y") as repo:
            self.assertEqual(verdict(f"git -C {repo} push", "/"), "allow")
        with RepoOnBranch("develop") as repo:
            self.assertEqual(verdict(f"git -C {repo} push", "/"), "ask")

    def test_body_text_with_operators_is_not_a_chain(self) -> None:
        self.assertEqual(verdict('gh pr create --base develop --head feat/x --title "a; b && c | d"'), "allow")


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

    def test_repo_flag_is_passed_to_view(self) -> None:
        with mock.patch.object(bp.subprocess, "run", return_value=fake_pr("develop", "feat/x")) as run:
            self.assertEqual(verdict("gh -R o/r pr merge 5 --merge"), "allow")
            self.assertEqual(run.call_args[0][0][:3], ["gh", "-R", "o/r"])

    def test_admin_asks(self) -> None:
        self.assertEqual(verdict("gh pr merge 5 --merge --admin"), "ask")


if __name__ == "__main__":
    unittest.main()
