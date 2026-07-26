"""Unit tests for tools/sidebar_nav.py.

The module's only shell-out point is `_tmux()` — patched here to return
canned `list-windows` output and record calls, so these tests never invoke a
real tmux server (there may not even be one available).

RESOLVER INPUT vs WINDOW-LIST FORMAT: resolve_window()/navigate_to() are
always called with the target string tools/sidebar.py PRODUCES (repo and
feature names joined with "/", TARGET_SEPARATOR) — never with a hand-picked
name that happens to already match tmux's own display convention. The
canned `list-windows` output below uses the separator REAL tmux windows are
actually named with (" ▸ "). Before the separator-tolerant normalisation in
resolve_window(), a "/"-joined target could never match a " ▸ "-named
window, and every feature-row navigation silently failed — this file
previously masked that by feeding "▸"-separated names straight into
resolve_window(), which trivially match a "▸"-separated window list and
never exercised the real mismatch.

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
    "sess-orch\t@1\torchids\tbash",
    "sess-arch\t@2\torchids ▸ fleet sidebar\tnode",
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
    def test_producer_format_matches_real_window_name(self):
        """THE REGRESSION TEST: this is the producer's actual target string
        (repo + "/" + feature, tools/sidebar.py TARGET_SEPARATOR) resolved
        against the REAL window-list format (repo + " ▸ " + feature). Before
        the separator-tolerant normalisation, this returned None for every
        feature row on a live tmux server — confirmed by running this exact
        assertion against the pre-fix resolve_window() (plain `==`
        comparison) and observing the failure."""
        with mock.patch.object(sidebar_nav, "_tmux", side_effect=_fake_tmux(LIST_WINDOWS_OUTPUT)):
            self.assertEqual(
                sidebar_nav.resolve_window("orchids/fleet sidebar"), ("sess-arch", "@2"),
            )

    def test_exact_window_name_match_still_works(self):
        with mock.patch.object(sidebar_nav, "_tmux", side_effect=_fake_tmux(LIST_WINDOWS_OUTPUT)):
            self.assertEqual(
                sidebar_nav.resolve_window("orchids ▸ fleet sidebar"), ("sess-arch", "@2"),
            )

    def test_no_match_returns_none(self):
        with mock.patch.object(sidebar_nav, "_tmux", side_effect=_fake_tmux(LIST_WINDOWS_OUTPUT)):
            self.assertIsNone(sidebar_nav.resolve_window("orchids/missing"))

    def test_duplicate_name_prefers_live_window(self):
        duplicate_name_output = "\n".join([
            "sess-launcher\t@3\torchids ▸ fleet sidebar\tbash",
            "sess-arch\t@4\torchids ▸ fleet sidebar\tnode",
        ])
        with mock.patch.object(sidebar_nav, "_tmux", side_effect=_fake_tmux(duplicate_name_output)):
            self.assertEqual(
                sidebar_nav.resolve_window("orchids/fleet sidebar"), ("sess-arch", "@4"),
            )

    def test_duplicate_name_all_shell_falls_back_to_first(self):
        duplicate_name_output = "\n".join([
            "sess-launcher\t@3\torchids ▸ fleet sidebar\tbash",
            "sess-other\t@4\torchids ▸ fleet sidebar\tbash",
        ])
        with mock.patch.object(sidebar_nav, "_tmux", side_effect=_fake_tmux(duplicate_name_output)):
            self.assertEqual(
                sidebar_nav.resolve_window("orchids/fleet sidebar"), ("sess-launcher", "@3"),
            )


class NavigateToTests(unittest.TestCase):
    def test_navigate_to_matching_window(self):
        """Called with the producer's own target format ("/"), against the
        real ("▸") window-list format — see ResolveWindowTests for why that
        distinction is the point."""
        with mock.patch.object(
            sidebar_nav, "_tmux", side_effect=_fake_tmux(LIST_WINDOWS_OUTPUT),
        ) as tmux:
            self.assertTrue(sidebar_nav.navigate_to("orchids/fleet sidebar"))
            calls = [c.args for c in tmux.call_args_list]

        self.assertIn(("list-windows", "-a", "-F", sidebar_nav.LIST_WINDOWS_FORMAT), calls)
        self.assertIn(("switch-client", "-t", "sess-arch"), calls)
        self.assertIn(("select-window", "-t", "@2"), calls)

    def test_navigate_to_repo_window(self):
        with mock.patch.object(
            sidebar_nav, "_tmux", side_effect=_fake_tmux(LIST_WINDOWS_OUTPUT),
        ) as tmux:
            self.assertTrue(sidebar_nav.navigate_to("orchids"))
            calls = [c.args for c in tmux.call_args_list]

        self.assertIn(("switch-client", "-t", "sess-orch"), calls)
        self.assertIn(("select-window", "-t", "@1"), calls)

    def test_navigate_to_returns_false_when_window_missing(self):
        with mock.patch.object(sidebar_nav, "_tmux", side_effect=_fake_tmux(LIST_WINDOWS_OUTPUT)):
            self.assertFalse(sidebar_nav.navigate_to("orchids/nope"))


if __name__ == "__main__":
    unittest.main()
