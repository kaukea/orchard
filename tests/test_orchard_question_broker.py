"""Unit tests for tools/orchard-question-broker.py's PURE decision logic
(sidebar-polish item 12) — match_option_key(), is_operator_busy(), and
pending_questions(). These are exactly the pieces separable from tty/tmux
I/O (mirroring tools/sidebar.py's render_lines()/curses split), so they run
with no live tmux session and no real keypress.

What this file deliberately does NOT cover — and cannot, without a live
tmux session and a real terminal — is documented in the module docstring
of tools/orchard-question-broker.py and repeated in this step's report:
an actual `tmux display-popup` rendering, and a genuine keypress being read
by _popup_read_main(). Those need a human/live check.

Runs under both `python3 -m unittest discover` and `pytest`.
"""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools",
)
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

# The module's filename has hyphens, so it cannot be `import`ed directly.
_SPEC = importlib.util.spec_from_file_location(
    "orchard_question_broker", os.path.join(_TOOLS_DIR, "orchard-question-broker.py"),
)
broker = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(broker)

from support import make_repo, envelope, write_message  # noqa: E402
import sidebar_model  # noqa: E402


class MatchOptionKeyTests(unittest.TestCase):
    """Item 12d: only the defined numbered-option keys register; every
    other keypress is ignored — no default, no dismiss-on-any-key."""

    def test_valid_digit_keys_map_to_zero_based_index(self):
        self.assertEqual(broker.match_option_key("1", 3), 0)
        self.assertEqual(broker.match_option_key("2", 3), 1)
        self.assertEqual(broker.match_option_key("3", 3), 2)

    def test_digit_outside_range_is_ignored(self):
        self.assertIsNone(broker.match_option_key("4", 3))
        self.assertIsNone(broker.match_option_key("0", 3))

    def test_non_digit_keys_are_ignored(self):
        for key in ("a", "\r", "\x1b", " ", "y", "Y", "\t"):
            self.assertIsNone(broker.match_option_key(key, 3), f"key={key!r}")

    def test_multi_char_input_is_ignored(self):
        self.assertIsNone(broker.match_option_key("12", 3))

    def test_empty_input_is_ignored(self):
        self.assertIsNone(broker.match_option_key("", 3))

    def test_feed_non_option_keys_then_a_valid_one_only_the_valid_one_registers(self):
        """Direct test of the required scenario: non-option keys first, then
        an option key — only the option key registers (the actual read loop
        lives in _popup_read_main and needs a live tty; this exercises the
        same per-keystroke decision it relies on, one call per keystroke)."""
        stream = ["x", "\r", "9", "a", "2"]
        result = None
        for key in stream:
            result = broker.match_option_key(key, 3)
            if result is not None:
                break
        self.assertEqual(result, 1)  # "2" -> option index 1, first valid key seen


class IsOperatorBusyTests(unittest.TestCase):
    """Item 12e: defer while input is in flight; clear on idle recency OR a
    just-completed submit."""

    def test_no_activity_ever_seen_is_not_busy(self):
        self.assertFalse(broker.is_operator_busy(now=100.0, last_submit_ts=None,
                                                  last_activity_ts=None, idle_seconds=5.0))

    def test_recent_activity_with_no_submit_is_busy(self):
        self.assertTrue(broker.is_operator_busy(now=100.0, last_submit_ts=None,
                                                 last_activity_ts=99.0, idle_seconds=5.0))

    def test_activity_older_than_idle_window_is_not_busy(self):
        self.assertFalse(broker.is_operator_busy(now=100.0, last_submit_ts=None,
                                                  last_activity_ts=90.0, idle_seconds=5.0))

    def test_submit_at_or_after_last_activity_clears_busy(self):
        # the submit keystroke IS the most recent activity too — clear
        self.assertFalse(broker.is_operator_busy(now=100.0, last_submit_ts=99.0,
                                                  last_activity_ts=99.0, idle_seconds=5.0))

    def test_activity_after_an_older_submit_is_busy_again(self):
        # they submitted a while ago, then started typing something new
        self.assertTrue(broker.is_operator_busy(now=100.0, last_submit_ts=95.0,
                                                 last_activity_ts=99.0, idle_seconds=5.0))


class PendingQuestionsTests(unittest.TestCase):
    """pending_questions() scans courier roots non-destructively (never deletes,
    mirroring tools/sidebar_model.py's own scan) and de-dupes by
    question_id, since a broadcast lands one copy per peer inbox."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = make_repo(self._tmp.name)
        self.courier_root = sidebar_model.iter_courier_roots([self.repo])[0]

    def _put(self, folder, msg_id, sender, question_id, question, options):
        env = envelope(msg_id, sender, body=f"orchid:activity:{question}", notify_user=True)
        env["question_id"] = question_id
        env["question"] = question
        env["options"] = options
        write_message(self.courier_root, folder, env)

    def test_finds_a_new_question(self):
        self._put("peerA", "m1", "askerX", "q1", "Proceed?", ["Yes", "No"])

        found = broker.pending_questions([self.courier_root], seen_ids=set())

        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["question_id"], "q1")
        self.assertEqual(found[0]["question"], "Proceed?")
        self.assertEqual(found[0]["options"], ["Yes", "No"])
        self.assertEqual(found[0]["asker"], "askerX")

    def test_same_question_id_in_multiple_peer_inboxes_is_reported_once(self):
        self._put("peerA", "m1", "askerX", "q1", "Proceed?", ["Yes", "No"])
        self._put("peerB", "m2", "askerX", "q1", "Proceed?", ["Yes", "No"])

        found = broker.pending_questions([self.courier_root], seen_ids=set())

        self.assertEqual(len(found), 1)

    def test_already_seen_question_id_is_not_returned_again(self):
        self._put("peerA", "m1", "askerX", "q1", "Proceed?", ["Yes", "No"])

        found = broker.pending_questions([self.courier_root], seen_ids={"q1"})

        self.assertEqual(found, [])

    def test_messages_without_question_id_are_ignored(self):
        write_message(self.courier_root, "peerA",
                      envelope("m1", "someoneX", body="orchid:activity:just working"))

        found = broker.pending_questions([self.courier_root], seen_ids=set())

        self.assertEqual(found, [])

    def test_never_deletes_the_files_it_scans(self):
        self._put("peerA", "m1", "askerX", "q1", "Proceed?", ["Yes", "No"])

        broker.pending_questions([self.courier_root], seen_ids=set())

        self.assertTrue((Path(self.courier_root) / "peerA" / "m1.json").exists())

    def test_title_summary_multi_surfaced_when_present(self):
        env = envelope("m1", "askerX", body="orchid:activity:Proceed?", notify_user=True)
        env["question_id"] = "q1"
        env["question"] = "Proceed?"
        env["options"] = ["Yes", "No"]
        env["title"] = "Deploy gate"
        env["summary"] = "Ship the release now or wait."
        env["multi"] = True
        write_message(self.courier_root, "peerA", env)

        found = broker.pending_questions([self.courier_root], seen_ids=set())

        self.assertEqual(found[0]["title"], "Deploy gate")
        self.assertEqual(found[0]["summary"], "Ship the release now or wait.")
        self.assertTrue(found[0]["multi"])

    def test_title_summary_absent_and_multi_false_by_default(self):
        self._put("peerA", "m1", "askerX", "q1", "Proceed?", ["Yes", "No"])

        found = broker.pending_questions([self.courier_root], seen_ids=set())

        self.assertIsNone(found[0]["title"])
        self.assertIsNone(found[0]["summary"])
        self.assertFalse(found[0]["multi"])


class IsContinueKeyTests(unittest.TestCase):
    """Item 12g point 3: Escape (and, by construction of the single-byte
    read loop, any ESC-prefixed sequence) means "continue the conversation",
    never a refusal."""

    def test_bare_escape_is_continue(self):
        self.assertTrue(broker.is_continue_key("\x1b"))

    def test_ordinary_keys_are_not_continue(self):
        for key in ("1", "a", "\r", "\n", " ", ""):
            self.assertFalse(broker.is_continue_key(key), f"key={key!r}")


class IsConfirmKeyTests(unittest.TestCase):
    """Item 12g point 2: Enter (CR or LF) is the multi-select confirm key."""

    def test_cr_and_lf_are_confirm(self):
        self.assertTrue(broker.is_confirm_key("\r"))
        self.assertTrue(broker.is_confirm_key("\n"))

    def test_other_keys_are_not_confirm(self):
        for key in ("1", "a", "\x1b", " "):
            self.assertFalse(broker.is_confirm_key(key), f"key={key!r}")


class ToggleSelectionTests(unittest.TestCase):
    """Item 12g point 2: multi-select digits TOGGLE membership."""

    def test_toggling_an_unselected_index_selects_it(self):
        self.assertEqual(broker.toggle_selection(set(), 0), {0})

    def test_toggling_a_selected_index_deselects_it(self):
        self.assertEqual(broker.toggle_selection({0, 2}, 0), {2})

    def test_toggling_leaves_other_selections_untouched(self):
        self.assertEqual(broker.toggle_selection({1}, 2), {1, 2})

    def test_does_not_mutate_the_input_set(self):
        original = {0}
        broker.toggle_selection(original, 0)
        self.assertEqual(original, {0})


class GatePhraseMatchTests(unittest.TestCase):
    """Item 12g point 4: exact, case-insensitive match of a completed typed
    buffer against the two always-available gate phrases."""

    def test_exact_uppercase_matches(self):
        self.assertEqual(broker.gate_phrase_match("MAKE IT SO"), "MAKE IT SO")
        self.assertEqual(broker.gate_phrase_match("THAT IS ALL"), "THAT IS ALL")

    def test_case_insensitive_matches(self):
        self.assertEqual(broker.gate_phrase_match("make it so"), "MAKE IT SO")
        self.assertEqual(broker.gate_phrase_match("ThAt Is AlL"), "THAT IS ALL")

    def test_surrounding_whitespace_is_trimmed(self):
        self.assertEqual(broker.gate_phrase_match("  make it so  "), "MAKE IT SO")

    def test_non_matching_buffer_does_not_false_trigger(self):
        for buf in ("MAKE IT", "MAKE IT SOMETHING", "THAT IS", "", "hello"):
            self.assertIsNone(broker.gate_phrase_match(buf), f"buf={buf!r}")


class GatePhraseCouldCompleteTests(unittest.TestCase):
    """Item 12g point 4: the typed-buffer capture keeps growing only while
    still a viable prefix of one of the two phrases."""

    def test_valid_partial_prefixes_could_complete(self):
        for buf in ("M", "MA", "MAKE", "MAKE IT", "T", "THAT", "THAT IS"):
            self.assertTrue(broker.gate_phrase_could_complete(buf), f"buf={buf!r}")

    def test_case_insensitive(self):
        self.assertTrue(broker.gate_phrase_could_complete("make"))

    def test_a_broken_prefix_cannot_complete(self):
        for buf in ("X", "MAKE ITX", "MAQ", "THAZ"):
            self.assertFalse(broker.gate_phrase_could_complete(buf), f"buf={buf!r}")

    def test_empty_buffer_could_complete(self):
        self.assertTrue(broker.gate_phrase_could_complete(""))


class GateBufferStepTests(unittest.TestCase):
    """Item 12g point 4: the full typed-buffer state machine, one keystroke
    at a time — case-insensitivity, partial-input-then-complete, a
    non-matching phrase not false-triggering, and a broken buffer resetting
    without swallowing the breaking keystroke (the caller reprocesses it)."""

    def _type(self, buffer, keys):
        matched = None
        for key in keys:
            buffer, matched = broker.gate_buffer_step(buffer, key)
            if matched:
                break
        return buffer, matched

    def test_typing_make_it_so_then_enter_matches(self):
        buffer, matched = self._type("M", list("AKE IT SO") + ["\r"])
        self.assertEqual(matched, "MAKE IT SO")
        self.assertEqual(buffer, "")

    def test_typing_that_is_all_then_enter_matches(self):
        buffer, matched = self._type("T", list("HAT IS ALL") + ["\r"])
        self.assertEqual(matched, "THAT IS ALL")

    def test_lowercase_typing_still_matches(self):
        buffer, matched = self._type("m", list("ake it so") + ["\r"])
        self.assertEqual(matched, "MAKE IT SO")

    def test_incomplete_phrase_then_enter_does_not_match_and_resets(self):
        new_buffer, matched = broker.gate_buffer_step("MAKE IT", "\r")
        self.assertIsNone(matched)
        self.assertEqual(new_buffer, "")

    def test_unrelated_text_then_enter_does_not_false_trigger(self):
        buffer, matched = self._type("M", list("ake believe") + ["\r"])
        self.assertIsNone(matched)

    def test_a_keystroke_that_breaks_the_prefix_resets_the_buffer(self):
        # "MAKE " is a valid prefix of "MAKE IT SO"; 'X' next breaks it
        new_buffer, matched = broker.gate_buffer_step("MAKE ", "X")
        self.assertEqual(new_buffer, "")
        self.assertIsNone(matched)


class PopupContentLinesTests(unittest.TestCase):
    """Item 12g point 7: the exact lines rendered — shared with the sizing
    calculation so the two can never drift apart."""

    def test_includes_title_and_summary_when_given(self):
        lines = broker.popup_content_lines("Deploy gate", "Ship now or wait.",
                                            "Proceed?", ["Yes", "No"])
        self.assertIn("Deploy gate", lines)
        self.assertIn("Ship now or wait.", lines)

    def test_omits_title_and_summary_when_absent(self):
        lines = broker.popup_content_lines(None, None, "Proceed?", ["Yes", "No"])
        self.assertNotIn("Deploy gate", lines)
        self.assertEqual(sum(1 for l in lines if l == "Proceed?"), 1)

    def test_multi_select_options_carry_a_checkbox_prefix(self):
        lines = broker.popup_content_lines(None, None, "Proceed?", ["Yes", "No"], multi=True)
        self.assertIn("[ ] 1. Yes", lines)
        self.assertIn("[ ] 2. No", lines)

    def test_single_select_options_have_no_checkbox_prefix(self):
        lines = broker.popup_content_lines(None, None, "Proceed?", ["Yes", "No"], multi=False)
        self.assertIn("1. Yes", lines)

    def test_single_and_multi_mode_lines_are_visibly_different(self):
        single = broker.popup_content_lines(None, None, "Proceed?", ["Yes", "No"], multi=False)
        multi = broker.popup_content_lines(None, None, "Proceed?", ["Yes", "No"], multi=True)
        self.assertNotEqual(single, multi)


class ComputePopupSizeTests(unittest.TestCase):
    """Item 12g point 7: content-based sizing, clamped to [min, max]."""

    def test_width_fits_the_longest_line_plus_padding(self):
        width, _height = broker.compute_popup_size(
            None, None, "Proceed?", ["Yes", "No"],
        )
        longest = max(len(l) for l in
                      broker.popup_content_lines(None, None, "Proceed?", ["Yes", "No"]))
        self.assertEqual(width, longest + broker._POPUP_PADDING_W)

    def test_height_fits_the_line_count_plus_padding(self):
        _width, height = broker.compute_popup_size(
            None, None, "Proceed?", ["Yes", "No"],
        )
        line_count = len(broker.popup_content_lines(None, None, "Proceed?", ["Yes", "No"]))
        self.assertEqual(height, line_count + broker._POPUP_PADDING_H)

    def test_width_is_clamped_to_the_minimum_for_short_content(self):
        natural_width, _height = broker.compute_popup_size(None, None, "Hi?", ["A", "B"])
        floor = natural_width + 20  # well above what the content itself needs

        width, _height = broker.compute_popup_size(
            None, None, "Hi?", ["A", "B"], min_width=floor,
        )

        self.assertEqual(width, floor)

    def test_width_is_clamped_to_the_maximum_for_long_content(self):
        long_option = "x" * 500
        width, _height = broker.compute_popup_size(
            None, None, "Proceed?", [long_option, "No"], max_width=80,
        )
        self.assertEqual(width, 80)

    def test_height_is_clamped_to_the_maximum_for_many_options(self):
        many_options = [f"option {i}" for i in range(100)]
        _width, height = broker.compute_popup_size(
            None, None, "Proceed?", many_options, max_height=30,
        )
        self.assertEqual(height, 30)

    def test_title_and_summary_grow_the_computed_height(self):
        _width, without = broker.compute_popup_size(None, None, "Proceed?", ["Yes", "No"])
        _width, with_both = broker.compute_popup_size(
            "Deploy gate", "Ship now or wait.", "Proceed?", ["Yes", "No"],
        )
        self.assertGreater(with_both, without)


if __name__ == "__main__":
    unittest.main()
