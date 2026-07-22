"""Unit tests for tools/sidebar.py's pure presentation layer: flatten() and
render_lines(). No curses involved — these are plain functions over
dataclasses, exactly the split the module's own docstring calls out as what
gets tested.

Runs under both `python3 -m unittest discover` and `pytest`; stdlib only.
"""
import os
import sys
import unittest

_TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools",
)
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import sidebar  # noqa: E402
import sidebar_model as sm  # noqa: E402


def _fleet():
    return sm.Fleet(repos=[
        sm.Repo(
            path="/tmp/repoA", name="repoA", activity="", status="working",
            waiting_on_operator=False,
            features=[
                sm.Feature(
                    feature_id="feat-1", name="feat one", activity="doing work",
                    status="working", waiting_on_operator=False,
                    subagents=[sm.Subagent(label="sub-a")],
                ),
            ],
        ),
    ])


class FlattenTests(unittest.TestCase):
    def test_depth_kind_and_target_per_row(self):
        rows = sidebar.flatten(_fleet())
        self.assertEqual(len(rows), 3)

        repo_row, feature_row, sub_row = rows
        self.assertEqual((repo_row.depth, repo_row.kind, repo_row.target),
                         (0, "repo", "repoA"))
        self.assertEqual((feature_row.depth, feature_row.kind, feature_row.target),
                         (1, "feature", "repoA ▸ feat one"))
        # a subagent row's target is its OWNING feature's target, not its own
        # label -- navigation from a subagent row targets the feature window.
        self.assertEqual((sub_row.depth, sub_row.kind, sub_row.target),
                         (2, "subagent", "repoA ▸ feat one"))
        self.assertTrue(sub_row.is_subagent)
        self.assertFalse(feature_row.is_subagent)
        self.assertFalse(repo_row.is_subagent)

    def test_bus_row_is_first_in_its_parents_group(self):
        fleet = _fleet()
        fleet.repos[0].bus = sm.Bus()
        fleet.repos[0].features[0].bus = sm.Bus()

        rows = sidebar.flatten(fleet)
        kinds = [r.kind for r in rows]
        # repo, repo-bus, feature, feature-bus, subagent
        self.assertEqual(kinds, ["repo", "bus", "feature", "bus", "subagent"])
        # each bus row sits at the top of ITS OWN parent's group -- the
        # repo's bus comes right after the repo row (before the feature),
        # the feature's bus comes right after the feature row (before its
        # subagent)
        self.assertEqual(rows[1].target, "repoA")
        self.assertEqual(rows[3].target, "repoA ▸ feat one")

    def test_no_bus_row_when_absent(self):
        rows = sidebar.flatten(_fleet())
        self.assertNotIn("bus", [r.kind for r in rows])


class RenderLinesTests(unittest.TestCase):
    def test_status_emoji_per_row(self):
        fleet = sm.Fleet(repos=[
            sm.Repo(path="/r", name="r-working", activity="", status="working",
                    waiting_on_operator=False),
            sm.Repo(path="/r", name="r-waiting", activity="", status="waiting",
                    waiting_on_operator=False),
            sm.Repo(path="/r", name="r-idle", activity="", status="idle",
                    waiting_on_operator=False),
            sm.Repo(path="/r", name="r-awaiting-agent", activity="", status="awaiting_agent",
                    waiting_on_operator=False),
            sm.Repo(path="/r", name="r-done", activity="", status="done",
                    waiting_on_operator=False),
            sm.Repo(path="/r", name="r-failed", activity="", status="failed",
                    waiting_on_operator=False),
        ])
        lines = sidebar.render_lines(fleet, width=64)
        self.assertIn("🚧", lines[0])
        self.assertIn("⌚", lines[1])
        self.assertIn("⚪", lines[2])
        self.assertIn("🪷", lines[3])
        self.assertIn("✅", lines[4])
        self.assertIn("❌", lines[5])

    def test_done_and_failed_glyphs_are_distinct(self):
        # explicit operator correction: never the same encoding for done vs
        # failed ("can't put green for fail, same as you can't have green
        # and green at a traffic light")
        self.assertNotEqual(sidebar.STATUS_EMOJI["done"], sidebar.STATUS_EMOJI["failed"])

    def test_all_six_status_glyphs_are_distinct(self):
        glyphs = list(sidebar.STATUS_EMOJI.values())
        self.assertEqual(len(glyphs), len(set(glyphs)))
        self.assertEqual(len(glyphs), 6)

    def test_waiting_on_operator_shows_question_mark_variant(self):
        fleet = _fleet()
        fleet.repos[0].features[0].status = "waiting"
        fleet.repos[0].features[0].waiting_on_operator = True
        lines = sidebar.render_lines(fleet, width=64)
        self.assertIn(sidebar.WAITING_ON_OPERATOR_EMOJI, lines[1])
        self.assertNotIn(sidebar.STATUS_EMOJI["waiting"], lines[1])

    def test_waiting_without_operator_flag_shows_watch_glyph(self):
        fleet = _fleet()
        fleet.repos[0].features[0].status = "waiting"
        fleet.repos[0].features[0].waiting_on_operator = False
        lines = sidebar.render_lines(fleet, width=64)
        self.assertIn(sidebar.STATUS_EMOJI["waiting"], lines[1])
        self.assertNotIn(sidebar.WAITING_ON_OPERATOR_EMOJI, lines[1])

    def test_no_animation_same_state_renders_identically_across_calls(self):
        # no spinner_frame/flash_on parameters exist any more -- a repeated
        # render of the SAME fleet must be byte-identical, and no row's
        # glyph column may ever go blank (as the old odd-frame flash did).
        fleet = _fleet()
        first = sidebar.render_lines(fleet, width=64)
        second = sidebar.render_lines(fleet, width=64)
        third = sidebar.render_lines(fleet, width=64)
        self.assertEqual(first, second)
        self.assertEqual(second, third)

    def test_subagent_row_shows_fixed_working_glyph(self):
        lines = sidebar.render_lines(_fleet(), width=64)
        self.assertIn(sidebar.STATUS_EMOJI["working"], lines[2])
        # identical on a second call -- no spinner advance
        lines_again = sidebar.render_lines(_fleet(), width=64)
        self.assertEqual(lines[2], lines_again[2])

    def test_indentation_increases_with_depth(self):
        lines = sidebar.render_lines(_fleet(), width=64)
        # strip the leading selection-marker column (always ' ' or '>')
        bodies = [line[1:] for line in lines]
        indents = [len(b) - len(b.lstrip(" ")) for b in bodies]
        self.assertEqual(indents, [0, 2, 4])

    def test_selected_row_has_leading_marker(self):
        lines = sidebar.render_lines(_fleet(), selected=1, width=64)
        self.assertTrue(lines[1].startswith(">"))
        self.assertTrue(lines[0].startswith(" "))
        self.assertTrue(lines[2].startswith(" "))

    def test_lines_truncated_to_width(self):
        lines = sidebar.render_lines(_fleet(), width=6)
        for line in lines:
            self.assertLessEqual(len(line), 6)

    def test_bus_row_renders_with_message_glyph(self):
        fleet = _fleet()
        fleet.repos[0].bus = sm.Bus()
        lines = sidebar.render_lines(fleet, width=64)
        self.assertIn(sidebar.BUS_GLYPH, lines[1])
        self.assertIn(sm.BUS_LABEL, lines[1])


class TruncateEllipsisTests(unittest.TestCase):
    def test_short_text_is_unaffected(self):
        self.assertEqual(sidebar._truncate("short", 10), "short")

    def test_long_text_ends_with_ellipsis_not_a_hard_cut(self):
        text = "agent-closing Done, awaiting operator"
        truncated = sidebar._truncate(text, 12)
        self.assertEqual(len(truncated), 12)
        self.assertTrue(truncated.endswith(sidebar.ELLIPSIS))
        self.assertEqual(truncated, text[:11] + sidebar.ELLIPSIS)

    def test_ellipsis_counts_toward_width_budget(self):
        truncated = sidebar._truncate("abcdefghij", 5)
        self.assertEqual(len(truncated), 5)
        self.assertTrue(truncated.endswith(sidebar.ELLIPSIS))


class HeaderGradientTests(unittest.TestCase):
    def test_paused_is_flat_light_gray(self):
        colours = sidebar.header_gradient(8, paused=True)
        self.assertEqual(len(colours), 8)
        self.assertTrue(all(c == sidebar.PAUSED_HEADER_GRAY for c in colours))

    def test_active_project_gradient_varies_across_width(self):
        colours = sidebar.header_gradient(8, paused=False)
        self.assertEqual(len(colours), 8)
        self.assertGreater(len(set(colours)), 1)  # not flat -- a real gradient
        self.assertEqual(colours[0], sidebar.ORCHID_GRADIENT_DARK)
        self.assertEqual(colours[-1], sidebar.ORCHID_GRADIENT_LIGHT)

    def test_gradient_is_static_across_repeated_calls(self):
        # no tick/frame parameter exists -- same input always yields the
        # same output (sidebar-polish item 10: STATIC, not animated)
        first = sidebar.header_gradient(8, paused=False)
        second = sidebar.header_gradient(8, paused=False)
        self.assertEqual(first, second)

    def test_paused_and_active_never_share_colours(self):
        active = set(sidebar.header_gradient(8, paused=False))
        paused = set(sidebar.header_gradient(8, paused=True))
        self.assertTrue(active.isdisjoint(paused))

    def test_header_line_centres_title(self):
        line = sidebar.render_header_line("orchids", 15)
        self.assertEqual(len(line), 15)
        self.assertIn("orchids", line)
        self.assertEqual(line.strip(), "orchids")

    def test_header_line_truncates_with_ellipsis_when_too_narrow(self):
        line = sidebar.render_header_line("a very long project title", 10)
        self.assertEqual(len(line), 10)
        self.assertTrue(line.endswith(sidebar.ELLIPSIS))


if __name__ == "__main__":
    unittest.main()
