"""Unit tests for tools/sidebar_nav.py.

The module's only shell-out point is `_tmux()` — patched here to return
canned `list-windows` output and record calls, so these tests never invoke a
real tmux server (there may not even be one available).

NAMING (operator ruling, 2026-08-10): session = bare repo name, window =
bare feature name, and the gardener's window is ALWAYS literally "Gardener"
— a fixed, known value. resolve_window() no longer guesses or normalises
anything: a bare target resolves to that session's "Gardener" window; a
"repo<SEP>feature" target resolves to that session's window named EXACTLY
`feature`. This replaces the earlier separator-tolerant / orchestrator-guess
design, which had no controlled name for the gardener window and never
reliably worked (operator, 2026-08-10).

Runs under both `python3 -m unittest discover` and `pytest`; stdlib only
(unittest.mock is stdlib).
"""
import os
import sys
import unittest
from unittest import mock

_TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools",
)
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import sidebar_nav  # noqa: E402


LIST_WINDOWS_OUTPUT = "\n".join([
    "orchids\t@1\tGardener\tclaude",
    "orchids\t@2\tfleet sidebar\tnode",
])


def _fake_tmux(canned_list_windows):
    """Stand-in for sidebar_nav._tmux: answers list-windows with canned text,
    switch-client/select-window with an arbitrary non-None success string,
    anything else with None (failure) -- matching _tmux's own contract."""
    def fake(*args):
        if args and args[0] == "list-windows":
            return canned_list_windows
        if args and args[0] in ("switch-client", "select-window"):
            return ""
        return None
    return fake


class ResolveWindowTests(unittest.TestCase):
    def test_feature_target_matches_bare_window_name(self):
        """The producer's target ("orchids" + TARGET_SEPARATOR + "fleet
        sidebar") resolves against a window named EXACTLY "fleet sidebar" —
        no repo prefix, no separator variant, no normalisation needed."""
        with mock.patch.object(sidebar_nav, "_tmux", side_effect=_fake_tmux(LIST_WINDOWS_OUTPUT)):
            self.assertEqual(
                sidebar_nav.resolve_window(f"orchids{sidebar_nav.TARGET_SEPARATOR}fleet sidebar"),
                ("orchids", "@2"),
            )

    def test_no_match_returns_none(self):
        with mock.patch.object(sidebar_nav, "_tmux", side_effect=_fake_tmux(LIST_WINDOWS_OUTPUT)):
            self.assertIsNone(sidebar_nav.resolve_window("orchids/missing"))

    def test_repo_target_resolves_to_gardener_window(self):
        """A repo-level target ("orchids", no separator) resolves by SESSION
        name to that session's window named literally "Gardener" — a fixed,
        known name, never a guess."""
        with mock.patch.object(sidebar_nav, "_tmux", side_effect=_fake_tmux(LIST_WINDOWS_OUTPUT)):
            self.assertEqual(
                sidebar_nav.resolve_window("orchids"), ("orchids", "@1"),
            )

    def test_repo_target_no_matching_session_returns_none(self):
        with mock.patch.object(sidebar_nav, "_tmux", side_effect=_fake_tmux(LIST_WINDOWS_OUTPUT)):
            self.assertIsNone(sidebar_nav.resolve_window("no-such-repo"))

    def test_repo_target_no_gardener_window_returns_none(self):
        """If a session has no window literally named "Gardener" (e.g. it
        hasn't been renamed yet), a repo-level target finds nothing — there
        is no fallback guess any more."""
        no_gardener_output = "\n".join([
            "orchids\t@5\talpha\tnode",
            "orchids\t@6\tbeta\tnode",
        ])
        with mock.patch.object(sidebar_nav, "_tmux", side_effect=_fake_tmux(no_gardener_output)):
            self.assertIsNone(sidebar_nav.resolve_window("orchids"))

    def test_duplicate_name_prefers_live_window(self):
        """Two windows can share a name within the SAME session (tmux does
        not enforce uniqueness) -- a stale leftover launcher shell beside the
        real live window. resolve_window() prefers the live one."""
        duplicate_name_output = "\n".join([
            "orchids\t@3\tfleet sidebar\tbash",
            "orchids\t@4\tfleet sidebar\tnode",
        ])
        with mock.patch.object(sidebar_nav, "_tmux", side_effect=_fake_tmux(duplicate_name_output)):
            self.assertEqual(
                sidebar_nav.resolve_window("orchids/fleet sidebar"), ("orchids", "@4"),
            )

    def test_duplicate_name_all_shell_falls_back_to_first(self):
        duplicate_name_output = "\n".join([
            "orchids\t@3\tfleet sidebar\tbash",
            "orchids\t@4\tfleet sidebar\tbash",
        ])
        with mock.patch.object(sidebar_nav, "_tmux", side_effect=_fake_tmux(duplicate_name_output)):
            self.assertEqual(
                sidebar_nav.resolve_window("orchids/fleet sidebar"), ("orchids", "@3"),
            )


class NavigateToTests(unittest.TestCase):
    def test_navigate_to_matching_window(self):
        with mock.patch.object(
            sidebar_nav, "_tmux", side_effect=_fake_tmux(LIST_WINDOWS_OUTPUT),
        ) as tmux:
            self.assertTrue(sidebar_nav.navigate_to("orchids/fleet sidebar"))
            calls = [c.args for c in tmux.call_args_list]

        self.assertIn(("list-windows", "-a", "-F", sidebar_nav.LIST_WINDOWS_FORMAT), calls)
        self.assertIn(("switch-client", "-t", "orchids"), calls)
        self.assertIn(("select-window", "-t", "@2"), calls)

    def test_navigate_to_repo_window(self):
        with mock.patch.object(
            sidebar_nav, "_tmux", side_effect=_fake_tmux(LIST_WINDOWS_OUTPUT),
        ) as tmux:
            self.assertTrue(sidebar_nav.navigate_to("orchids"))
            calls = [c.args for c in tmux.call_args_list]

        self.assertIn(("switch-client", "-t", "orchids"), calls)
        self.assertIn(("select-window", "-t", "@1"), calls)

    def test_navigate_to_returns_false_when_window_missing(self):
        with mock.patch.object(sidebar_nav, "_tmux", side_effect=_fake_tmux(LIST_WINDOWS_OUTPUT)):
            self.assertFalse(sidebar_nav.navigate_to("orchids/nope"))


if __name__ == "__main__":
    unittest.main()
