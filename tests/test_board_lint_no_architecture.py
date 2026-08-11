"""board_lint.py must lint a repository that has no ARCHITECTURE.md.

Not every project has an architecture to describe — a repo that only analyses
crashes has none (operator ruling, 2026-08-11) — so ARCHITECTURE.md is optional
and `area` is empty where there is no Taxonomy to draw from. Until this was
fixed the lint raised FileNotFoundError, which is why several boards had never
been linted at all.

board_lint resolves its paths from its own location at import time, so it is
exercised as a subprocess against a staged tree.
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LINT = _ROOT / "tools" / "board_lint.py"

_BOARD = """# TODO — a board

## Machinery

- `feature · todo · · queued · {area} ·` [A task](TODO.md.d/a-task.md)
"""

_ARCH = """# Architecture

## Taxonomy

| Functionality | Areas |
|---|---|
| **Machinery** | widgets |
"""


class BoardLintWithoutArchitectureTests(unittest.TestCase):

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def _stage(self, area: str, architecture: bool) -> Path:
        root = Path(tempfile.mkdtemp(dir=self._tmp.name))
        (root / "docs" / "TODO.md.d").mkdir(parents=True)
        (root / "tools").mkdir()
        (root / "docs" / "TODO.md").write_text(_BOARD.format(area=area))
        (root / "docs" / "TODO.md.d" / "a-task.md").write_text("# A task\n")
        if architecture:
            (root / "ARCHITECTURE.md").write_text(_ARCH)
        shutil.copy(_LINT, root / "tools" / "board_lint.py")
        return root

    def _lint(self, root: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["python3", str(root / "tools" / "board_lint.py")],
            capture_output=True, text=True, check=False,
        )

    def test_missing_architecture_does_not_crash(self) -> None:
        result = self._lint(self._stage(area="", architecture=False))
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("1 tasks", result.stderr)

    def test_missing_architecture_with_empty_area_is_clean(self) -> None:
        result = self._lint(self._stage(area="", architecture=False))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("0 errors", result.stderr)

    def test_area_without_a_taxonomy_is_an_error(self) -> None:
        result = self._lint(self._stage(area="widgets", architecture=False))
        self.assertEqual(result.returncode, 1)
        self.assertIn("no ARCHITECTURE.md Taxonomy", result.stderr)

    def test_taxonomy_is_still_enforced_when_present(self) -> None:
        self.assertEqual(self._lint(self._stage(area="widgets", architecture=True)).returncode, 0)
        bad = self._lint(self._stage(area="sprockets", architecture=True))
        self.assertEqual(bad.returncode, 1)
        self.assertIn("not in Machinery taxonomy", bad.stderr)

    def test_urgent_is_not_a_valid_urgency(self) -> None:
        """Everything is always urgent, so it says nothing — operator ruling."""
        root = self._stage(area="widgets", architecture=True)
        board = root / "docs" / "TODO.md"
        board.write_text(board.read_text().replace("todo · ·", "todo · urgent ·"))
        result = self._lint(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("bad urgency 'urgent'", result.stderr)


if __name__ == "__main__":
    unittest.main()
