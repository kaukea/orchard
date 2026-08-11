"""The unvendor-self migration must only uninstall the package in the repository
that IS the orchids source.

Steps 2 and 3 of `migrations/2026-07-27-unvendor-self.md` delete the source line
from `.ai.toml` and `rm -rf` the vendored clone. Unguarded, a consuming
repository running the migration uninstalls orchids from itself — and the
migration was pending in every consumer on the machine.

The guard is observable state: the vendored clone's origin resolves to this very
repository, either as the same remote URL or as a local path that is this root.

The shell block is extracted from the migration document, so the shipped text is
what is covered.
"""
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_MIGRATION = _ROOT / "migrations" / "2026-07-27-unvendor-self.md"

_AI_TOML = """# managed by kauk
[sources."serialseb/orchids"]
origin = "{origin}"
[sources."serialseb/kauk"]
origin = "/somewhere/kauk"
"""


def _convert_script() -> str:
    block = re.search(r"```sh\n(.*?)\n```", _MIGRATION.read_text(), re.S)
    assert block, "migration document has no shell block"
    return block.group(1)


class UnvendorSelfGuardTests(unittest.TestCase):

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def _git(self, path: Path, *args) -> None:
        subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)

    def _repo(self, origin: str) -> Path:
        path = Path(tempfile.mkdtemp(dir=self._tmp.name))
        self._git(path, "init", "--quiet")
        self._git(path, "remote", "add", "origin", origin)
        return path

    def _with_clone(self, repo: Path, clone_origin: str) -> Path:
        clone = repo / ".ai" / "repositories" / "serialseb" / "orchids"
        clone.mkdir(parents=True)
        self._git(clone, "init", "--quiet")
        self._git(clone, "remote", "add", "origin", clone_origin)
        (repo / ".ai.toml").write_text(_AI_TOML.format(origin=clone_origin))
        return clone

    def _run(self, repo: Path) -> str:
        r = subprocess.run(["bash", "-c", _convert_script()], cwd=str(repo),
                           capture_output=True, text=True, check=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_consumer_keeps_its_clone_and_its_source_line(self) -> None:
        """The defect: a consumer would have uninstalled orchids from itself."""
        repo = self._repo("https://github.com/serialseb/consumer.git")
        clone = self._with_clone(repo, "https://github.com/kaukea/orchids.git")
        out = self._run(repo)
        self.assertIn("not the orchids source", out)
        self.assertTrue(clone.is_dir(), "consumer's vendored clone was deleted")
        self.assertIn('[sources."serialseb/orchids"]', (repo / ".ai.toml").read_text())

    def test_self_source_by_matching_remote_url_is_unvendored(self) -> None:
        url = "https://github.com/kaukea/orchids.git"
        repo = self._repo(url)
        clone = self._with_clone(repo, url)
        out = self._run(repo)
        self.assertIn("unvendored self", out)
        self.assertFalse(clone.exists())
        self.assertNotIn('[sources."serialseb/orchids"]', (repo / ".ai.toml").read_text())

    def test_self_source_by_local_path_is_unvendored(self) -> None:
        """Ten repos vendor from a local path, so the URL comparison alone is not enough."""
        repo = self._repo("https://github.com/kaukea/orchids.git")
        clone = self._with_clone(repo, str(repo))
        out = self._run(repo)
        self.assertIn("unvendored self", out)
        self.assertFalse(clone.exists())

    def test_no_clone_at_all_is_a_no_op(self) -> None:
        repo = self._repo("https://github.com/serialseb/consumer.git")
        (repo / ".ai.toml").write_text(_AI_TOML.format(origin="/somewhere/orchids"))
        out = self._run(repo)
        self.assertIn("not the orchids source", out)
        self.assertIn('[sources."serialseb/orchids"]', (repo / ".ai.toml").read_text())

    def test_running_twice_changes_nothing_further(self) -> None:
        url = "https://github.com/kaukea/orchids.git"
        repo = self._repo(url)
        self._with_clone(repo, url)
        self._run(repo)
        after_first = (repo / ".ai.toml").read_text()
        self._run(repo)
        self.assertEqual(after_first, (repo / ".ai.toml").read_text())


if __name__ == "__main__":
    unittest.main()
