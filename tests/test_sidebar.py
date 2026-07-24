"""Unit tests for tools/sidebar.py's pure presentation layer: flatten(),
render_lines(), and the display-grammar composition helpers added for the
mock's visual contract (bus-message-specifying B5). No curses involved —
these are plain functions over dataclasses, exactly the split the module's
own docstring calls out as what gets tested.

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
                         (1, "feature", "repoA/feat one"))
        self.assertEqual(feature_row.repo_name, "repoA")
        # a subagent row's target is its OWNING feature's target, not its own
        # label -- navigation from a subagent row targets the feature window.
        self.assertEqual((sub_row.depth, sub_row.kind, sub_row.target),
                         (2, "subagent", "repoA/feat one"))
        self.assertTrue(sub_row.is_subagent)
        self.assertFalse(feature_row.is_subagent)
        self.assertFalse(repo_row.is_subagent)

    def test_feature_row_carries_display_grammar_fields(self):
        # bus-message-specifying B5: flatten() copies the wire-grammar
        # fields onto the Row so the curses draw path never reaches back
        # into the model, plus a `source` pointer for optional fields.
        fleet = _fleet()
        feature = fleet.repos[0].features[0]
        feature.phase = "building"
        feature.progress_pct = 62
        feature.subagents_running = 3
        feature.subagents_queued = 2
        feature.question_count = 1
        feature.first_question_subject = "scope fork"
        feature.status_word = "writing"

        feature_row = next(r for r in sidebar.flatten(fleet) if r.kind == "feature")
        self.assertEqual(feature_row.phase, "building")
        self.assertEqual(feature_row.progress_pct, 62)
        self.assertEqual(feature_row.subagents_running, 3)
        self.assertEqual(feature_row.subagents_queued, 2)
        self.assertEqual(feature_row.question_count, 1)
        self.assertEqual(feature_row.first_question_subject, "scope fork")
        self.assertEqual(feature_row.status_word, "writing")
        self.assertIs(feature_row.source, feature)

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
        self.assertEqual(rows[3].target, "repoA/feat one")

    def test_no_bus_row_when_absent(self):
        rows = sidebar.flatten(_fleet())
        self.assertNotIn("bus", [r.kind for r in rows])

    def test_repo_without_session_is_skipped_entirely(self):
        # sidebar-titling item 3: an empty project (no live session) has
        # nothing to show -- header AND group both disappear.
        fleet = sm.Fleet(repos=[
            sm.Repo(path="/tmp/empty", name="empty-repo", activity="",
                     status="idle", waiting_on_operator=False, has_session=False),
        ])
        self.assertEqual(sidebar.flatten(fleet), [])

    def test_only_repos_with_a_session_render(self):
        fleet = sm.Fleet(repos=[
            sm.Repo(path="/tmp/a", name="a", activity="", status="idle",
                     waiting_on_operator=False, has_session=False),
            sm.Repo(path="/tmp/b", name="b", activity="", status="idle",
                     waiting_on_operator=False, has_session=True),
        ])
        rows = sidebar.flatten(fleet)
        self.assertEqual([r.target for r in rows], ["b"])

    def test_done_features_sort_first_within_their_repo_group(self):
        # sidebar-titling item 7: done-first, stable sort -- relative order
        # among the still-live features (and among the done ones) is kept.
        fleet = sm.Fleet(repos=[
            sm.Repo(path="/tmp/r", name="r", activity="", status="idle",
                     waiting_on_operator=False, features=[
                sm.Feature(feature_id="a", name="a-working", activity="",
                           status="working", waiting_on_operator=False),
                sm.Feature(feature_id="b", name="b-done", activity="",
                           status="done", waiting_on_operator=False),
                sm.Feature(feature_id="c", name="c-idle", activity="",
                           status="idle", waiting_on_operator=False),
                sm.Feature(feature_id="d", name="d-done", activity="",
                           status="done", waiting_on_operator=False),
            ]),
        ])
        feature_rows = [r for r in sidebar.flatten(fleet) if r.kind == "feature"]
        self.assertEqual(
            [r.label for r in feature_rows],
            ["b-done", "d-done", "a-working", "c-idle"],
        )


class RenderLinesTests(unittest.TestCase):
    def test_status_emoji_per_feature_row(self):
        # status glyphs live on FEATURE rows -- a repo header carries none
        # (sidebar-titling item 4). Looked up by which line contains the
        # feature's name rather than by position, since done-first sorting
        # (item 7) reorders the "done" row ahead of the others.
        statuses = ["working", "waiting", "idle", "awaiting_agent", "done", "failed"]
        fleet = sm.Fleet(repos=[
            sm.Repo(path="/r", name="r", activity="", status="idle",
                    waiting_on_operator=False, features=[
                sm.Feature(feature_id=s, name=s, activity="", status=s,
                           waiting_on_operator=False)
                for s in statuses
            ]),
        ])
        lines = sidebar.render_lines(fleet, width=64)
        for status in statuses:
            line = next(l for l in lines if status in l)
            self.assertIn(sidebar.STATUS_EMOJI[status], line)

    def test_repo_header_has_no_leading_status_glyph(self):
        # sidebar-titling item 4: --dump used to prepend a status glyph to
        # the repo header row via _row_text; curses never drew one (it uses
        # _draw_header instead) -- the pure path now matches curses.
        fleet = _fleet()  # repo status="working"
        lines = sidebar.render_lines(fleet, width=64)
        for glyph in sidebar.STATUS_EMOJI.values():
            self.assertNotIn(glyph, lines[0])

    def test_feature_row_renders_the_name_without_a_repo_prefix(self):
        # bus-message-specifying B5: the mock's feature row shows only the
        # feature's own name -- the repo is already named by the header
        # block above its group, so the row no longer repeats it (this
        # replaces the sidebar-titling "<repo>/<name>" row composition).
        lines = sidebar.render_lines(_fleet(), width=64)
        self.assertIn("feat one", lines[1])
        self.assertNotIn("repoA/feat one", lines[1])

    def test_done_feature_row_shows_check_and_percentage(self):
        fleet = _fleet()
        fleet.repos[0].features[0].status = "done"
        fleet.repos[0].features[0].progress_pct = 100
        lines = sidebar.render_lines(fleet, width=64)
        self.assertIn(sidebar.STATUS_EMOJI["done"], lines[1])
        self.assertIn("100%", lines[1])

    def test_question_count_badge_appears_before_percentage(self):
        fleet = _fleet()
        fleet.repos[0].features[0].question_count = 1
        fleet.repos[0].features[0].progress_pct = 40
        lines = sidebar.render_lines(fleet, width=64)
        self.assertIn("?1", lines[1])
        self.assertLess(lines[1].index("?1"), lines[1].index("40%"))

    def test_no_badge_when_no_open_questions(self):
        lines = sidebar.render_lines(_fleet(), width=64)
        self.assertNotIn("?", lines[1])

    def test_done_and_failed_glyphs_are_distinct(self):
        # explicit operator correction: never the same encoding for done vs
        # failed ("can't put green for fail, same as you can't have green
        # and green at a traffic light")
        self.assertNotEqual(sidebar.STATUS_EMOJI["done"], sidebar.STATUS_EMOJI["failed"])

    def test_idle_waiting_and_awaiting_agent_intentionally_share_the_hollow_circle(self):
        # visual contract (sidebar-titling OVERRIDE 2, reaffirmed by the
        # mock -- bus-message-specifying B5 item 7): one circle family --
        # idle/component-wait/awaiting-agent collapse to the same glyph, and
        # there is no longer a separate operator-wait glyph variant either.
        self.assertEqual(sidebar.STATUS_EMOJI["idle"], "○")
        self.assertEqual(sidebar.STATUS_EMOJI["waiting"], "○")
        self.assertEqual(sidebar.STATUS_EMOJI["awaiting_agent"], "○")

    def test_working_done_and_failed_glyphs_stay_distinct_from_each_other_and_the_circle(self):
        distinguishable = {
            sidebar.STATUS_EMOJI["working"], sidebar.STATUS_EMOJI["done"],
            sidebar.STATUS_EMOJI["failed"], sidebar.STATUS_EMOJI["idle"],
        }
        self.assertEqual(len(distinguishable), 4)

    def test_waiting_rows_render_the_same_hollow_circle_regardless_of_operator_flag(self):
        # bus-message-specifying B5 item 7: "hollow circle only -- no
        # watch/timer glyphs anywhere in row status" -- waiting_on_operator
        # no longer selects a different glyph (that distinction moved to the
        # ?N badge / question-detail lines).
        fleet = _fleet()
        fleet.repos[0].features[0].status = "waiting"

        fleet.repos[0].features[0].waiting_on_operator = True
        operator_wait_line = sidebar.render_lines(fleet, width=64)[1]

        fleet.repos[0].features[0].waiting_on_operator = False
        component_wait_line = sidebar.render_lines(fleet, width=64)[1]

        self.assertIn(sidebar.STATUS_EMOJI["waiting"], operator_wait_line)
        self.assertIn(sidebar.STATUS_EMOJI["waiting"], component_wait_line)

    def test_no_animation_same_state_renders_identically_across_calls(self):
        # a repeated render of the SAME fleet must be byte-identical -- the
        # band sweep and every other display-grammar addition is
        # curses-only (see render_lines()'s docstring).
        fleet = _fleet()
        first = sidebar.render_lines(fleet, width=64)
        second = sidebar.render_lines(fleet, width=64)
        third = sidebar.render_lines(fleet, width=64)
        self.assertEqual(first, second)
        self.assertEqual(second, third)

    def test_subagent_row_shows_presence_glyph(self):
        # sidebar-titling item 4: presence in the model is the only
        # verifiable subagent state -- a filled circle, never the "working"
        # glyph (an unverifiable claim) and never an "idle" counterpart.
        lines = sidebar.render_lines(_fleet(), width=64)
        self.assertIn(sidebar.SUBAGENT_GLYPH, lines[2])
        self.assertNotIn(sidebar.STATUS_EMOJI["working"], lines[2])
        # identical on a second call -- no spinner advance in the pure path
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


def _many_repos_fleet(n):
    """A fleet with exactly `n` rows — one repo row each, no features/bus —
    so row count is trivial to reason about in scroll-offset tests."""
    return sm.Fleet(repos=[
        sm.Repo(
            path=f"/tmp/repo{i}", name=f"repo{i}", activity="", status="idle",
            waiting_on_operator=False,
        )
        for i in range(n)
    ])


class ScrollOffsetTests(unittest.TestCase):
    """sidebar-polish item 3 resolution: scroll-follows-selection viewport
    clamping, the pure logic behind the curses draw loop's persisted
    scroll offset."""

    def test_no_scroll_when_all_rows_fit_the_viewport(self):
        # count (5) <= height (5): offset always 0, regardless of selected
        # or a stale prior offset.
        self.assertEqual(sidebar.clamp_scroll_offset(0, 0, 5, 5), 0)
        self.assertEqual(sidebar.clamp_scroll_offset(3, 4, 5, 8), 0)

    def test_selection_below_viewport_shifts_offset_down(self):
        # 10 rows, viewport of 3, currently showing [0, 3); selecting row 5
        # must shift the window down just enough to keep it visible.
        offset = sidebar.clamp_scroll_offset(0, 5, 10, 3)
        self.assertEqual(offset, 3)  # window becomes [3, 6) -> 5 is last visible

    def test_selection_above_viewport_shifts_offset_up(self):
        # window currently [4, 7); selecting row 2 (above it) must pull the
        # offset up to exactly the selected row.
        offset = sidebar.clamp_scroll_offset(4, 2, 10, 3)
        self.assertEqual(offset, 2)

    def test_selection_inside_viewport_leaves_offset_untouched(self):
        offset = sidebar.clamp_scroll_offset(4, 5, 10, 3)
        self.assertEqual(offset, 4)

    def test_offset_never_negative(self):
        offset = sidebar.clamp_scroll_offset(-7, 0, 10, 3)
        self.assertGreaterEqual(offset, 0)
        self.assertEqual(offset, 0)

    def test_offset_never_scrolls_past_showing_the_last_row(self):
        # selecting the very last row must clamp the offset to count-height,
        # never further -- there is nothing more to scroll to.
        offset = sidebar.clamp_scroll_offset(0, 9, 10, 3)
        self.assertEqual(offset, 7)  # window [7, 10) shows the last row
        # a stale offset already past that must also be pulled back.
        offset = sidebar.clamp_scroll_offset(50, 9, 10, 3)
        self.assertEqual(offset, 7)

    def test_render_lines_windows_to_offset_and_height(self):
        fleet = _many_repos_fleet(10)
        lines = sidebar.render_lines(fleet, selected=5, width=32, offset=0, height=3)
        self.assertEqual(len(lines), 3)
        # selection at 5 forces the window to [3, 6): repo3, repo4, repo5
        self.assertIn("repo3", lines[0])
        self.assertIn("repo4", lines[1])
        self.assertIn("repo5", lines[2])
        self.assertTrue(lines[2].startswith(">"))  # repo5 is selected

    def test_render_lines_small_fleet_is_not_windowed(self):
        fleet = _many_repos_fleet(2)
        lines = sidebar.render_lines(fleet, selected=1, width=32, offset=0, height=5)
        self.assertEqual(len(lines), 2)  # fewer rows than height -- no scroll

    def test_render_lines_without_height_is_unwindowed(self):
        # default behaviour (no height given) renders every row -- unchanged
        # from before scroll support was added.
        fleet = _many_repos_fleet(10)
        lines = sidebar.render_lines(fleet, selected=9, width=32)
        self.assertEqual(len(lines), 10)


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


class FeatureRowLayoutTests(unittest.TestCase):
    """bus-message-specifying B5 item 2: glyph + name drawn over the
    progress fill, right-aligned dim percentage, optional "?N" badge before
    it. `_feature_row_layout` is the single source of truth shared by the
    plain-text compose and the curses per-column painter."""

    def test_compose_feature_row_text_lays_out_glyph_name_and_percentage(self):
        text = sidebar.compose_feature_row_text("⠧", "sidebar titling", 62, 27)
        self.assertTrue(text.startswith("⠧ sidebar titling"))
        self.assertTrue(text.endswith("62%"))
        self.assertEqual(len(text), 27)

    def test_badge_is_inserted_before_the_percentage(self):
        text = sidebar.compose_feature_row_text("○", "focus returning", 40, 40, badge="?1")
        self.assertIn("?1 40%", text)

    def test_long_name_is_truncated_before_the_tail_is_sacrificed(self):
        text = sidebar.compose_feature_row_text(
            "⠧", "a very very long feature name indeed", 62, 24,
        )
        self.assertTrue(text.endswith("62%"))
        self.assertEqual(len(text), 24)

    def test_layout_pad_width_fills_exactly_to_the_requested_width(self):
        glyph, shown_name, pad_width, badge_text, pct_text = sidebar._feature_row_layout(
            "✓", "bloomer v1", 100, 27, None,
        )
        used = len(glyph) + 1 + len(shown_name) + pad_width + len(badge_text) + len(pct_text)
        self.assertEqual(used, 27)


class FillColsTests(unittest.TestCase):
    """bus-message-specifying B5 item 3: fill_cols(pct, width) math, mirrors
    the mock's `round(WIDTH * pct / 100)` exactly."""

    def test_zero_percent_fills_nothing(self):
        self.assertEqual(sidebar.fill_cols(0, 27), 0)

    def test_hundred_percent_fills_the_whole_width(self):
        self.assertEqual(sidebar.fill_cols(100, 27), 27)

    def test_partial_percent_rounds_to_nearest_column(self):
        self.assertEqual(sidebar.fill_cols(62, 27), round(27 * 62 / 100))
        self.assertEqual(sidebar.fill_cols(50, 10), 5)


class BandSweepTests(unittest.TestCase):
    """bus-message-specifying B5 item 3: the bidirectional lifted-band sweep
    -- band width (abs(col-pos)<=2), a triangular wave over [0, span], and
    lifted colour = lerp(fill, white, 0.18)."""

    def test_band_position_ramps_up_then_back_down(self):
        span = 5
        positions = [sidebar.band_position(t, span) for t in range(2 * span + 1)]
        self.assertEqual(positions, [0, 1, 2, 3, 4, 5, 4, 3, 2, 1, 0])

    def test_band_position_is_periodic(self):
        span = 4
        first_cycle = [sidebar.band_position(t, span) for t in range(2 * span)]
        second_cycle = [sidebar.band_position(t + 2 * span, span) for t in range(2 * span)]
        self.assertEqual(first_cycle, second_cycle)

    def test_band_span_is_never_less_than_one(self):
        self.assertEqual(sidebar.band_span(0), 1)
        self.assertEqual(sidebar.band_span(1), 1)
        self.assertEqual(sidebar.band_span(6), 5)

    def test_band_column_colour_is_lifted_only_within_two_columns_of_the_band(self):
        fill = (40, 31, 54)
        pos = 10
        self.assertEqual(sidebar.band_column_colour(pos, pos, 27, fill), sidebar.lifted_fill_colour(fill))
        self.assertEqual(sidebar.band_column_colour(pos + 2, pos, 27, fill), sidebar.lifted_fill_colour(fill))
        self.assertEqual(sidebar.band_column_colour(pos + 3, pos, 27, fill), fill)

    def test_band_column_colour_is_none_past_travel_end(self):
        self.assertIsNone(sidebar.band_column_colour(20, 10, 20, (40, 31, 54)))

    def test_lifted_fill_colour_is_18_percent_toward_white(self):
        fill = (40, 31, 54)
        self.assertEqual(sidebar.lifted_fill_colour(fill), sidebar.lerp(fill, sidebar.WHITE, 0.18))


class SmallCapsTests(unittest.TestCase):
    """bus-message-specifying B5 item 4: the phase label is small-caps
    Unicode, matching the mock's literal "ʙᴜɪʟᴅɪɴɢ" for "building"."""

    def test_building_matches_the_mocks_literal_small_caps(self):
        self.assertEqual(sidebar.small_caps("building"), "ʙᴜɪʟᴅɪɴɢ")

    def test_releasing_converts_every_letter(self):
        self.assertEqual(sidebar.small_caps("releasing"), "ʀᴇʟᴇᴀꜱɪɴɢ")

    def test_non_letters_pass_through_unchanged(self):
        self.assertEqual(sidebar.small_caps("a b-c"), "ᴀ ʙ-ᴄ")


class IdentityLineTests(unittest.TestCase):
    """bus-message-specifying B5 item 4: "status_word plain ⋮ role
    dim-italic ⋮ model coloured", glued with NBSP around ⋮, model truncated
    rather than ever wrapped alone."""

    def test_full_identity_glues_segments_with_nbsp_around_the_separator(self):
        text = sidebar.identity_line_text("writing", "architect", "opus-4.8", 100)
        sep = sidebar.NBSP + "⋮" + sidebar.NBSP
        self.assertEqual(text, "writing" + sep + "architect" + sep + "opus-4.8")

    def test_model_is_truncated_to_the_remaining_room_not_wrapped(self):
        doing, role, model = sidebar.compose_identity_line("writing", "architect", "opus-4.8", 24)
        self.assertEqual(doing, "writing")
        self.assertEqual(role, "architect")
        self.assertTrue(model == "" or "opus-4.8".startswith(model))
        self.assertNotIn("\n", model)

    def test_role_none_omits_the_role_segment_entirely(self):
        doing, role, model = sidebar.compose_identity_line("writing", None, "opus-4.8", 100)
        self.assertEqual(role, "")
        text = sidebar.identity_line_text("writing", None, "opus-4.8", 100)
        self.assertNotIn(sidebar.NBSP + "⋮" + sidebar.NBSP + sidebar.NBSP, text)
        self.assertIn("opus-4.8", text)

    def test_model_none_omits_the_model_segment_entirely(self):
        text = sidebar.identity_line_text("writing", "architect", None, 100)
        self.assertEqual(text, "writing" + sidebar.NBSP + "⋮" + sidebar.NBSP + "architect")

    def test_model_tier_colour_keys_off_the_family_prefix(self):
        self.assertEqual(sidebar.model_tier_colour("opus-4.8"), sidebar.MODEL_TIERS["opus"])
        self.assertEqual(sidebar.model_tier_colour("sonnet-5"), sidebar.MODEL_TIERS["sonnet"])
        self.assertEqual(sidebar.model_tier_colour(None), sidebar.TEXT)
        self.assertEqual(sidebar.model_tier_colour("unknown-model"), sidebar.TEXT)


class PhaseChecklistTests(unittest.TestCase):
    """bus-message-specifying B5 item 4: five-phase vertical checklist (done
    / active / todo), the word in accent only while active."""

    def test_phases_before_the_active_one_are_done(self):
        states = dict(sidebar.phase_states("building"))
        self.assertEqual(states["ideation"], "done")
        self.assertEqual(states["scoping"], "done")
        self.assertEqual(states["designing"], "done")
        self.assertEqual(states["building"], "active")
        self.assertEqual(states["releasing"], "todo")

    def test_all_phases_are_todo_when_no_phase_is_active(self):
        states = dict(sidebar.phase_states(None))
        self.assertTrue(all(state == "todo" for state in states.values()))

    def test_unknown_phase_name_is_treated_as_no_active_phase(self):
        states = dict(sidebar.phase_states("not-a-real-phase"))
        self.assertTrue(all(state == "todo" for state in states.values()))

    def test_phase_order_matches_the_canonical_five_phases(self):
        words = [word for word, _state in sidebar.phase_states("scoping")]
        self.assertEqual(words, list(sidebar.PHASES))

    def test_phase_mark_per_state(self):
        self.assertEqual(sidebar.phase_mark("done"), "●")
        self.assertEqual(sidebar.phase_mark("active"), "⠧")
        self.assertEqual(sidebar.phase_mark("todo"), "○")

    def test_inline_dot_counts_running_then_queued(self):
        self.assertEqual(sidebar.phase_dot_suffix(3, 2), "●●●○○")
        self.assertEqual(sidebar.phase_dot_suffix(0, 0), "")
        self.assertEqual(sidebar.phase_dot_suffix(1, 0), "●")
        self.assertEqual(sidebar.phase_dot_suffix(0, 1), "○")


class QuestionBadgeTests(unittest.TestCase):
    """bus-message-specifying B5 item 2/5: the "?N" badge, amber, never red;
    presence keyed strictly on question_count > 0."""

    def test_badge_absent_when_no_open_questions(self):
        self.assertIsNone(sidebar.question_badge(0))

    def test_badge_present_and_formatted_with_count(self):
        self.assertEqual(sidebar.question_badge(1), "?1")
        self.assertEqual(sidebar.question_badge(3), "?3")

    def test_badge_colour_is_amber_never_red(self):
        self.assertEqual(sidebar.AMBER, (0xC6, 0x98, 0x54))
        red = (255, 0, 0)
        self.assertNotEqual(sidebar.AMBER, red)

    def test_question_count_text_pluralises(self):
        self.assertEqual(sidebar.question_count_text(1), "1 question")
        self.assertEqual(sidebar.question_count_text(2), "2 questions")
        self.assertEqual(sidebar.question_count_text(0), "0 questions")


class FooterLinesTests(unittest.TestCase):
    """bus-message-specifying B5 item 4: footer lines render only when the
    model actually exposes age/worked/tokens/dollars -- this step invents no
    collection mechanism, so absent data means the lines are omitted."""

    def test_footer_omitted_entirely_when_no_data_is_available(self):
        feature = sm.Feature(
            feature_id="f", name="f", activity="", status="working",
            waiting_on_operator=False,
        )
        self.assertEqual(sidebar.footer_lines(feature), [])

    def test_footer_omitted_when_source_is_none(self):
        self.assertEqual(sidebar.footer_lines(None), [])

    def test_footer_renders_both_lines_when_all_four_values_are_present(self):
        class _Stats:
            age = "3h12"
            worked = "1h47"
            tokens = "212k"
            dollars = "4.12"

        lines = sidebar.footer_lines(_Stats())
        self.assertEqual(lines, ["⏱ 3h12 ⋮ worked 1h47", "⚡ 212k ⋮ $4.12"])

    def test_footer_first_line_needs_both_age_and_worked(self):
        class _PartialStats:
            age = "3h12"
            worked = None
            tokens = "212k"
            dollars = "4.12"

        lines = sidebar.footer_lines(_PartialStats())
        self.assertEqual(lines, ["⚡ 212k ⋮ $4.12"])


class DoneFooterLineTests(unittest.TestCase):
    """bus-message-specifying B5b: the collapsed one-line footer under a DONE
    feature row ("⚡ 384k ⋮ $7.90 ⋮ 6h02", mock frame line under the 100%
    feature) — omitted entirely when nothing is available."""

    def test_composes_tokens_dollars_and_age_in_mock_order(self):
        class _Stats:
            tokens = "384k"
            dollars = "7.90"
            age = "6h02"

        self.assertEqual(sidebar.done_footer_line(_Stats()), "⚡ 384k ⋮ $7.90 ⋮ 6h02")

    def test_omitted_when_source_is_none(self):
        self.assertIsNone(sidebar.done_footer_line(None))

    def test_omitted_when_no_value_is_available(self):
        feature = sm.Feature(
            feature_id="f", name="f", activity="", status="done",
            waiting_on_operator=False,
        )
        self.assertIsNone(sidebar.done_footer_line(feature))

    def test_renders_with_only_age_when_tokens_and_dollars_are_absent(self):
        class _AgeOnly:
            tokens = None
            dollars = None
            age = "6h02"

        self.assertEqual(sidebar.done_footer_line(_AgeOnly()), "6h02")

    def test_renders_with_only_tokens_and_dollars_when_age_is_absent(self):
        class _StatsOnly:
            tokens = "384k"
            dollars = "7.90"
            age = None

        self.assertEqual(sidebar.done_footer_line(_StatsOnly()), "⚡ 384k ⋮ $7.90")

    def test_dollars_alone_without_tokens_never_renders(self):
        class _DollarsOnly:
            tokens = None
            dollars = "7.90"
            age = None

        self.assertIsNone(sidebar.done_footer_line(_DollarsOnly()))


class RepoHueTests(unittest.TestCase):
    """sidebar-titling OVERRIDE 1, hue values updated by bus-message-
    specifying B5 to the mock's exact triples: each repo gets a fixed SOLID
    hue triple, not a gradient. `orchids`/`signmc` get their named triple
    (case-insensitive); everything else gets a stable, repeatable triple
    derived from the fallback palette."""

    def test_orchids_maps_to_the_mocks_exact_triple(self):
        self.assertEqual(sidebar._repo_hue("orchids"), sidebar.REPO_HUES["orchids"])
        self.assertEqual(sidebar.REPO_HUES["orchids"]["header"], (0x2C, 0x18, 0x3E))
        self.assertEqual(sidebar.REPO_HUES["orchids"]["fill"], (0x28, 0x1F, 0x36))
        self.assertEqual(sidebar.REPO_HUES["orchids"]["accent"], (0xAC, 0x88, 0xD6))

    def test_signmc_maps_to_the_mocks_exact_triple(self):
        self.assertEqual(sidebar._repo_hue("signmc"), sidebar.REPO_HUES["signmc"])
        self.assertEqual(sidebar.REPO_HUES["signmc"]["header"], (0x09, 0x2A, 0x2D))
        self.assertEqual(sidebar.REPO_HUES["signmc"]["fill"], (0x16, 0x2A, 0x2E))
        self.assertEqual(sidebar.REPO_HUES["signmc"]["accent"], (0x6E, 0xB4, 0xB0))

    def test_named_hue_match_is_case_insensitive(self):
        self.assertEqual(sidebar._repo_hue("Orchids"), sidebar.REPO_HUES["orchids"])
        self.assertEqual(sidebar._repo_hue("SIGNMC"), sidebar.REPO_HUES["signmc"])

    def test_unknown_repo_gets_a_stable_repeatable_fallback_triple(self):
        first = sidebar._repo_hue("some-other-repo")
        second = sidebar._repo_hue("some-other-repo")
        self.assertEqual(first, second)
        self.assertIn(first["header"], sidebar.FALLBACK_HEADER_HUES)

    def test_unknown_repo_never_collides_with_a_named_hue(self):
        hue = sidebar._repo_hue("some-other-repo")
        named_headers = {h["header"] for h in sidebar.REPO_HUES.values()}
        self.assertNotIn(hue["header"], named_headers)

    def test_different_unknown_repos_can_get_different_triples(self):
        # not a strict requirement (hash collisions are allowed), but the
        # fallback set has more than one entry so this should hold for the
        # names actually exercised in practice.
        hues = {sidebar._repo_hue(f"repo-{i}")["header"] for i in range(4)}
        self.assertGreater(len(hues), 1)


class Xterm256Tests(unittest.TestCase):
    """sidebar-titling item 1: the RGB -> nearest-xterm256-index helper that
    lets a colour render on a 256-colour terminal without can_change_color()
    support."""

    def test_black_maps_to_cube_origin(self):
        self.assertEqual(sidebar._rgb_to_xterm256((0, 0, 0)), 16)

    def test_white_maps_to_cube_far_corner(self):
        self.assertEqual(sidebar._rgb_to_xterm256((255, 255, 255)), 231)

    def test_saturated_colour_maps_into_the_colour_cube_range(self):
        # the accent hues are the mock's brightest, most saturated colours
        # (used for the active-phase glyph/text) -- they land in the 6x6x6
        # cube; the dark header/fill hues are low-saturation enough to be
        # closer to the grayscale ramp instead (both are valid outcomes of
        # "nearest palette index", covered together by
        # test_every_repo_hue_maps_into_a_valid_xterm256_index).
        for rgb in (sidebar.REPO_HUES["orchids"]["accent"], sidebar.REPO_HUES["signmc"]["accent"]):
            index = sidebar._rgb_to_xterm256(rgb)
            self.assertGreaterEqual(index, 16)
            self.assertLessEqual(index, 231)

    def test_every_repo_hue_maps_into_a_valid_xterm256_index(self):
        for hue in list(sidebar.REPO_HUES.values()):
            for rgb in hue.values():
                index = sidebar._rgb_to_xterm256(rgb)
                self.assertGreaterEqual(index, 16)
                self.assertLessEqual(index, 255)

    def test_neutral_gray_maps_into_the_grayscale_ramp(self):
        index = sidebar._rgb_to_xterm256((128, 128, 128))
        self.assertGreaterEqual(index, 232)
        self.assertLessEqual(index, 255)


class RoleEmojiTests(unittest.TestCase):
    """bus-message-specifying B5 item 8: ROLE_EMOJI/LOCATION_BADGES are
    data-driven and exported even where the mock's frame shows no emoji --
    None means "pending operator pick", rendering as no emoji rather than a
    placeholder or a crash."""

    def test_known_roles_map_to_their_emoji(self):
        self.assertEqual(sidebar.ROLE_EMOJI["bloomer"], "🌸")
        self.assertEqual(sidebar.ROLE_EMOJI["housekeeper"], "🍂")
        self.assertEqual(sidebar.ROLE_EMOJI["bus"], "📯")
        self.assertEqual(sidebar.ROLE_EMOJI["builder"], "🌾")

    def test_pending_pick_roles_are_none(self):
        self.assertIsNone(sidebar.ROLE_EMOJI["orchestrator"])
        self.assertIsNone(sidebar.ROLE_EMOJI["architect"])

    def test_role_emoji_helper_returns_none_without_crashing(self):
        self.assertIsNone(sidebar.role_emoji("orchestrator"))
        self.assertIsNone(sidebar.role_emoji("architect"))
        self.assertIsNone(sidebar.role_emoji("unknown-role"))
        self.assertIsNone(sidebar.role_emoji(None))

    def test_location_badges_are_exported(self):
        self.assertEqual(sidebar.LOCATION_BADGES["local"], "💻")
        self.assertEqual(sidebar.LOCATION_BADGES["cloud"], "☁️")


class HeaderLineTests(unittest.TestCase):
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
