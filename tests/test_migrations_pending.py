"""Unit tests for hooks/migrations-pending.sh and the migration that converts the
watermark to one file per package.

A clone installs several packages, each with its own migrations/. The watermark
lives at <git-common-dir>/the-works/migrated/<owner>/<repo>; absent = everything
pending for that package. Both the hook and the conversion are pure filesystem
work, so they are exercised against throwaway repos and asserted on directly.

The conversion script is EXTRACTED FROM THE MIGRATION DOCUMENT rather than
copied here, so these tests cover the text that actually ships.
"""
import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_HOOK = _ROOT / "hooks" / "migrations-pending.sh"
_MIGRATION = _ROOT / "migrations" / "2026-08-11-per-package-watermark.md"

_ORCHIDS_MIGRATIONS = [
    "2026-07-11-uncommittable-dot-git",
    "2026-07-20-ripen-tasks-rename",
    "2026-08-10-arborist-to-beekeeper",
]


def _convert_script() -> str:
    """The shell block shipped inside the migration document."""
    block = re.search(r"```sh\n(.*?)\n```", _MIGRATION.read_text(), re.S)
    assert block, "migration document has no shell block"
    return block.group(1)


class _Repo:
    """A throwaway consuming repo with orchids vendored under .ai/repositories."""

    def __init__(self, tmp_root: str, origin: str = "https://github.com/serialseb/consumer.git"):
        self.path = Path(tempfile.mkdtemp(dir=tmp_root))
        self._git("init", "--quiet")
        self._git("remote", "add", "origin", origin)
        self.add_package("serialseb", "orchids", _ORCHIDS_MIGRATIONS)
        (self.path / ".git" / "the-works").mkdir(parents=True, exist_ok=True)

    def _git(self, *args) -> None:
        subprocess.run(["git", "-C", str(self.path), *args], check=True, capture_output=True)

    def add_package(self, owner: str, repo: str, migrations) -> None:
        d = self.path / ".ai" / "repositories" / owner / repo / "migrations"
        d.mkdir(parents=True, exist_ok=True)
        for name in migrations:
            (d / f"{name}.md").write_text(f"# {name}\n")

    def own_migrations(self, migrations) -> None:
        d = self.path / "migrations"
        d.mkdir(exist_ok=True)
        for name in migrations:
            (d / f"{name}.md").write_text(f"# {name}\n")

    @property
    def watermark(self) -> Path:
        return self.path / ".git" / "the-works" / "migrated"

    def set_bare_watermark(self, name: str) -> None:
        self.watermark.write_text(f"{name}\n")

    def set_watermark(self, owner: str, repo: str, name: str) -> None:
        f = self.watermark / owner / repo
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(f"{name}\n")

    def read_watermark(self, owner: str, repo: str) -> str:
        return (self.watermark / owner / repo).read_text().strip()

    def convert(self) -> str:
        r = subprocess.run(["bash", "-c", _convert_script()], cwd=str(self.path),
                           capture_output=True, text=True, check=False)
        assert r.returncode == 0, r.stderr
        return r.stdout

    def notice(self) -> str:
        """The hook's additionalContext, or '' when it stays silent."""
        r = subprocess.run([str(_HOOK)], cwd=str(self.path),
                           capture_output=True, text=True, check=False)
        self_assert = r.returncode == 0
        assert self_assert, r.stderr
        if not r.stdout.strip():
            return ""
        return json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]

    @staticmethod
    def pending_for(notice: str, owner_repo: str):
        """The basenames listed as pending for one package, watermark echo excluded."""
        for line in notice.splitlines():
            if line.startswith(f"- {owner_repo} "):
                return line.split("): ", 1)[1].split()
        return []


class MigrationsPendingTests(unittest.TestCase):

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def repo(self, **kw) -> _Repo:
        return _Repo(self._tmp.name, **kw)

    # --- the conversion -------------------------------------------------

    def test_bare_watermark_becomes_a_directory(self) -> None:
        r = self.repo()
        r.set_bare_watermark("2026-07-20-ripen-tasks-rename")
        r.convert()
        self.assertTrue(r.watermark.is_dir())

    def test_bare_watermark_is_attributed_to_the_owning_package(self) -> None:
        r = self.repo()
        r.set_bare_watermark("2026-07-20-ripen-tasks-rename")
        r.convert()
        self.assertEqual(r.read_watermark("serialseb", "orchids"),
                         "2026-07-20-ripen-tasks-rename")

    def test_conversion_is_idempotent(self) -> None:
        r = self.repo()
        r.set_bare_watermark("2026-07-20-ripen-tasks-rename")
        r.convert()
        out = r.convert()
        self.assertIn("nothing to do", out)
        self.assertEqual(r.read_watermark("serialseb", "orchids"),
                         "2026-07-20-ripen-tasks-rename")

    def test_unattributable_watermark_is_discarded(self) -> None:
        r = self.repo()
        r.set_bare_watermark("2026-01-01-belongs-to-nothing")
        out = r.convert()
        self.assertIn("matches no installed package", out)
        # discarding is safe: state-guarded steps re-apply as no-ops
        self.assertCountEqual(
            _Repo.pending_for(r.notice(), "serialseb/orchids"), _ORCHIDS_MIGRATIONS)

    # --- what the hook reports ------------------------------------------

    def test_only_migrations_newer_than_the_watermark_are_pending(self) -> None:
        r = self.repo()
        r.set_watermark("serialseb", "orchids", "2026-07-20-ripen-tasks-rename")
        self.assertEqual(_Repo.pending_for(r.notice(), "serialseb/orchids"),
                         ["2026-08-10-arborist-to-beekeeper"])

    def test_consumer_without_its_own_migrations_is_still_told(self) -> None:
        """The defect this replaces: the old hook only read the repo's own
        migrations/, so a pure consumer was never told about any package."""
        r = self.repo()
        self.assertFalse((r.path / "migrations").exists())
        notice = r.notice()
        self.assertIn("serialseb/orchids", notice)
        self.assertIn("watermark: none", notice)
        self.assertCountEqual(
            _Repo.pending_for(notice, "serialseb/orchids"), _ORCHIDS_MIGRATIONS)

    def test_packages_are_reported_independently(self) -> None:
        r = self.repo()
        r.add_package("serialseb", "kauk", ["2026-08-11-convention-packages"])
        r.set_watermark("serialseb", "orchids", "2026-08-10-arborist-to-beekeeper")
        notice = r.notice()
        self.assertIn("serialseb/kauk", notice)
        self.assertNotIn("serialseb/orchids", notice)

    def test_a_current_clone_stays_silent(self) -> None:
        r = self.repo()
        r.set_watermark("serialseb", "orchids", "2026-08-10-arborist-to-beekeeper")
        self.assertEqual(r.notice(), "")

    def test_own_migrations_are_keyed_by_the_origin_remote(self) -> None:
        r = self.repo()
        r.own_migrations(["2026-08-11-own-change"])
        self.assertEqual(_Repo.pending_for(r.notice(), "serialseb/consumer"),
                         ["2026-08-11-own-change"])

    def test_local_path_remotes_key_the_same_way(self) -> None:
        """Ten repos vendor from a local path, not a URL — same owner/repo rule."""
        r = self.repo(origin="/home/sudoku/src/serialseb/consumer")
        r.own_migrations(["2026-08-11-own-change"])
        self.assertIn("serialseb/consumer", r.notice())

    def test_notice_is_valid_json(self) -> None:
        r = self.repo()
        result = subprocess.run([str(_HOOK)], cwd=str(r.path),
                                capture_output=True, text=True, check=False)
        json.loads(result.stdout)  # raises if the payload is malformed


if __name__ == "__main__":
    unittest.main()
