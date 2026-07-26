"""Unit tests for tools/orchard-question-broker.py's PURE decision logic
(sidebar-polish item 12) — match_option_key(), is_operator_busy(), and
pending_questions() — plus _handle_question()'s courier-reply/file-delete
side effects (popup mechanism stubbed) and one live end-to-end round trip
through a real `courier.py ask` subprocess.

pending_questions()/_handle_question() were rewritten for the operator-
mailbox broker (bus-finishing): the broker no longer imports sidebar_model
or scans per-peer courier inboxes. It scans
`$XDG_RUNTIME_DIR/orchard/projects/*/operator.*.json` — one DIRECTED request
file per asker per project (tools/courier.py cmd_ask -> orchard_send), never
a fan-out — and _handle_question() answers by shelling out to
`courier.py reply` and deleting the handled file.

What this file deliberately does NOT cover — and cannot, without a live tmux
session and a real terminal — is documented in the module docstring of
tools/orchard-question-broker.py and repeated in this step's report: an
actual `tmux display-popup` rendering, and a genuine keypress being read by
_popup_read_main(). Those need a human/live check. `_render_popup` is
stubbed in every test below for exactly that reason.

Runs under both `python3 -m unittest discover` and `pytest`.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

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

import courier  # noqa: E402 — reused directly for envelope shape fidelity
                 # (make_orchard_envelope/stamp) and to drive real
                 # reply/ask subprocesses, exactly as the broker itself does.

from support import make_repo  # noqa: E402

_COURIER_PY = os.path.join(_TOOLS_DIR, "courier.py")


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


def _question_body(question_id, question, options, *, title=None, summary=None, multi=False):
    body = {"question_id": question_id, "question": question, "options": options}
    if title:
        body["title"] = title
    if summary:
        body["summary"] = summary
    if multi:
        body["multi"] = True
    return body


def _write_operator_question(projects_root, slug, asker, question_id, question, options,
                              *, title=None, summary=None, multi=False, ts=None):
    """Hand-build `projects/<slug>/operator.<ts>.json` exactly as
    tools/courier.py's `cmd_ask` -> `orchard_send` writes it: an
    orchard-transport envelope (courier.make_orchard_envelope — the SAME
    builder cmd_ask's own orchard_send call uses) whose `body` is a dict
    carrying question_id/question/options/title/summary/multi, addressed
    `:session:<asker>` -> `:session:operator`, filed under the reserved
    per-asker `operator.<ts>.json` name (courier.py's `_stamp_filename`,
    file_sid="operator" for the :session:operator address).
    """
    body = _question_body(question_id, question, options, title=title, summary=summary, multi=multi)
    env = courier.make_orchard_envelope(
        f":session:{asker}", ":session:operator", "orchard:agent:message:request",
        body=body, repo=slug, project=slug,
    )
    if ts is not None:
        env["ts"] = ts
    project_dir = Path(projects_root) / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    path = project_dir / f"operator.{ts or courier.stamp()}.json"
    path.write_text(json.dumps(env, indent=2), encoding="utf-8")
    return path, env


class PendingQuestionsTests(unittest.TestCase):
    """pending_questions() scans every project's reserved operator mailbox
    (one directed `operator.<ts>.json` request file per asker per project —
    never a fan-out/broadcast) and de-dupes by `question_id` (nested in the
    envelope's `body`, not top-level). Non-destructive: a discovered file is
    left on disk until `_handle_question` deletes it."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.projects_root = Path(self._tmp.name) / "orchard" / "projects"

    def test_finds_a_new_question(self):
        path, env = _write_operator_question(
            self.projects_root, "acme.repo", "askerX", "q1", "Proceed?", ["Yes", "No"])

        found = broker.pending_questions(self.projects_root, seen_ids=set())

        self.assertEqual(len(found), 1)
        q = found[0]
        self.assertEqual(q["question_id"], "q1")
        self.assertEqual(q["question"], "Proceed?")
        self.assertEqual(q["options"], ["Yes", "No"])
        self.assertEqual(q["asker"], ":session:askerX")
        self.assertEqual(q["id"], env["id"])
        self.assertEqual(q["project"], "acme.repo")
        self.assertEqual(q["path"], path)

    def test_already_seen_question_id_is_not_returned_again(self):
        _write_operator_question(
            self.projects_root, "acme.repo", "askerX", "q1", "Proceed?", ["Yes", "No"])
        first = broker.pending_questions(self.projects_root, seen_ids=set())
        seen_ids = {q["question_id"] for q in first}

        second = broker.pending_questions(self.projects_root, seen_ids=seen_ids)

        self.assertEqual(second, [])

    def test_never_deletes_the_files_it_scans(self):
        path, _env = _write_operator_question(
            self.projects_root, "acme.repo", "askerX", "q1", "Proceed?", ["Yes", "No"])

        broker.pending_questions(self.projects_root, seen_ids=set())

        self.assertTrue(path.exists())

    def test_title_summary_multi_surfaced_when_present(self):
        _write_operator_question(
            self.projects_root, "acme.repo", "askerX", "q1", "Proceed?", ["Yes", "No"],
            title="Deploy gate", summary="Ship the release now or wait.", multi=True)

        found = broker.pending_questions(self.projects_root, seen_ids=set())

        self.assertEqual(found[0]["title"], "Deploy gate")
        self.assertEqual(found[0]["summary"], "Ship the release now or wait.")
        self.assertTrue(found[0]["multi"])

    def test_title_summary_absent_and_multi_false_by_default(self):
        _write_operator_question(
            self.projects_root, "acme.repo", "askerX", "q1", "Proceed?", ["Yes", "No"])

        found = broker.pending_questions(self.projects_root, seen_ids=set())

        self.assertIsNone(found[0]["title"])
        self.assertIsNone(found[0]["summary"])
        self.assertFalse(found[0]["multi"])

    def test_messages_with_no_question_id_in_body_are_ignored(self):
        env = courier.make_orchard_envelope(
            ":session:someoneX", ":session:operator", "orchard:agent:message:content",
            body={"foo": "bar"}, repo="acme.repo", project="acme.repo",
        )
        project_dir = self.projects_root / "acme.repo"
        project_dir.mkdir(parents=True)
        (project_dir / f"operator.{courier.stamp()}.json").write_text(
            json.dumps(env), encoding="utf-8")

        found = broker.pending_questions(self.projects_root, seen_ids=set())

        self.assertEqual(found, [])

    def test_messages_with_a_non_dict_body_are_ignored(self):
        env = courier.make_orchard_envelope(
            ":session:someoneX", ":session:operator", "orchard:agent:status",
            body="identity", repo="acme.repo", project="acme.repo",
        )
        project_dir = self.projects_root / "acme.repo"
        project_dir.mkdir(parents=True)
        (project_dir / f"operator.{courier.stamp()}.json").write_text(
            json.dumps(env), encoding="utf-8")

        found = broker.pending_questions(self.projects_root, seen_ids=set())

        self.assertEqual(found, [])

    def test_a_personal_mailbox_file_alongside_is_not_picked_up(self):
        """Only `operator.*.json` is a question mailbox — a peer's own
        `<session>.<ts>.json` file sitting in the same project dir (e.g. a
        reply already delivered to some other session) is not a question."""
        _write_operator_question(
            self.projects_root, "acme.repo", "askerX", "q1", "Proceed?", ["Yes", "No"])
        other = self.projects_root / "acme.repo" / f"someoneY.{courier.stamp()}.json"
        other.write_text(json.dumps({"id": "x", "ts": "t", "from": "a", "to": "b"}),
                          encoding="utf-8")

        found = broker.pending_questions(self.projects_root, seen_ids=set())

        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["question_id"], "q1")

    def test_multiple_projects_are_all_scanned(self):
        _write_operator_question(
            self.projects_root, "acme.repoA", "askerX", "q1", "Proceed?", ["Yes", "No"])
        _write_operator_question(
            self.projects_root, "acme.repoB", "askerY", "q2", "Ship?", ["Yes", "No"])

        found = broker.pending_questions(self.projects_root, seen_ids=set())

        self.assertEqual({q["question_id"] for q in found}, {"q1", "q2"})
        by_qid = {q["question_id"]: q for q in found}
        self.assertEqual(by_qid["q1"]["project"], "acme.repoA")
        self.assertEqual(by_qid["q2"]["project"], "acme.repoB")

    def test_sorted_by_ts(self):
        _write_operator_question(
            self.projects_root, "acme.repo", "askerX", "later", "B?", ["Yes", "No"],
            ts="2026-01-02T00-00-00.000000")
        _write_operator_question(
            self.projects_root, "acme.repo", "askerY", "earlier", "A?", ["Yes", "No"],
            ts="2026-01-01T00-00-00.000000")

        found = broker.pending_questions(self.projects_root, seen_ids=set())

        self.assertEqual([q["question_id"] for q in found], ["earlier", "later"])

    def test_missing_projects_root_returns_nothing(self):
        found = broker.pending_questions(self.projects_root / "does-not-exist", seen_ids=set())
        self.assertEqual(found, [])

    def test_none_projects_root_returns_nothing(self):
        self.assertEqual(broker.pending_questions(None, seen_ids=set()), [])


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


class _LiveOrchardTestCase(unittest.TestCase):
    """Shared fixture for the tests below that need `_handle_question()` to
    actually shell out to a real `courier.py reply` (or `ask`) subprocess:
    a private XDG_RUNTIME_DIR/HOME/XDG_CACHE_HOME (patched into the real
    process environment, since `_handle_question` builds its subprocess env
    from the live `os.environ`, not a caller-supplied dict), a throwaway git
    repo standing in for the asker's project, and that repo's slug
    pre-authorized in the cross-project registry — needed because
    `_handle_question`'s own `courier.py reply` subprocess computes its own
    `repo` from ITS cwd (this test process's cwd, generally a different repo
    than the throwaway asker one), which then differs from the explicit
    `--target-project` it is given, tripping the cross-project allowlist
    check unless the throwaway slug is registered."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.runtime_dir = base / "run"
        self.runtime_dir.mkdir()
        self.cache_home = base / "cache"
        self.cache_home.mkdir()
        self.home = base / "home"
        self.home.mkdir()
        self.repo = make_repo(str(base))

        self._env_patch = mock.patch.dict(os.environ, {
            "XDG_RUNTIME_DIR": str(self.runtime_dir),
            "XDG_CACHE_HOME": str(self.cache_home),
            "HOME": str(self.home),
        })
        self._env_patch.start()
        self.addCleanup(self._env_patch.stop)

        self.slug = self._probe_slug()
        self._allow(self.slug)
        self.projects_root = self.runtime_dir / "orchard" / "projects"

    def _probe_slug(self) -> str:
        proc = subprocess.run(
            [sys.executable, "-c", "import courier; print(courier.project_slug())"],
            cwd=self.repo, capture_output=True, text=True,
            env=dict(os.environ, PYTHONPATH=_TOOLS_DIR), check=True,
        )
        return proc.stdout.strip()

    def _allow(self, *slugs: str) -> None:
        cfg_dir = self.home / ".config" / "orchids"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "sidebar-registry.json").write_text(
            json.dumps(list(slugs)), encoding="utf-8")

    def _receive_as(self, session_id: str) -> list:
        recv = subprocess.run(
            [sys.executable, _COURIER_PY, "receive"], cwd=self.repo,
            capture_output=True, text=True,
            env=dict(os.environ, CLAUDE_CODE_SESSION_ID=session_id, PYTHONPATH=_TOOLS_DIR),
        )
        self.assertEqual(recv.returncode, 0, recv.stderr)
        return json.loads(recv.stdout)


class HandleQuestionTests(_LiveOrchardTestCase):
    """`_handle_question()` pops the popup (stubbed here — its rendering
    needs a live tmux session, out of scope for this file), then invokes
    `courier.py reply` with the answer and deletes the handled mailbox
    file. The popup mechanism is the only thing mocked; the reply itself is
    a REAL subprocess so both the exact invocation and its real effect
    (the asker actually receiving the answer) are verified."""

    def setUp(self) -> None:
        super().setUp()
        self.path, self.env = _write_operator_question(
            self.projects_root, self.slug, "askerX", "q1", "Proceed?", ["Yes", "No"])
        found = broker.pending_questions(self.projects_root, seen_ids=set())
        self.assertEqual(len(found), 1)
        self.q = found[0]

    def test_invokes_courier_reply_with_the_right_arguments_and_deletes_the_file(self):
        with mock.patch.object(broker, "_render_popup",
                                return_value={"index": 0, "option": "Yes"}) as popup_mock, \
             mock.patch.object(broker.subprocess, "run",
                                wraps=broker.subprocess.run) as run_spy:
            broker._handle_question(self.q)

        popup_mock.assert_called_once()
        # `_operator_current_window()` (called before the popup) also shells
        # out to `broker.subprocess.run` for its own tmux probes when a real
        # tmux session is present in the test environment — so pick out the
        # ONE call that actually invokes `courier.py reply`, rather than
        # assuming it is the only call recorded.
        reply_calls = [c for c in run_spy.call_args_list if "reply" in c.args[0]]
        self.assertEqual(len(reply_calls), 1, run_spy.call_args_list)
        cmd, kwargs = reply_calls[0].args[0], reply_calls[0].kwargs
        self.assertIn("reply", cmd)
        self.assertEqual(cmd[cmd.index("--to") + 1], ":session:askerX")
        self.assertEqual(cmd[cmd.index("--in-reply-to") + 1], self.env["id"])
        self.assertEqual(cmd[cmd.index("--subject") + 1], "orchard:operator:message:response")
        self.assertEqual(cmd[cmd.index("--target-project") + 1], self.slug)
        self.assertEqual(kwargs["env"]["CLAUDE_CODE_SESSION_ID"], "question-broker")

        self.assertFalse(self.path.exists())

    def test_the_asker_actually_receives_the_answer(self):
        with mock.patch.object(broker, "_render_popup",
                                return_value={"index": 0, "option": "Yes"}):
            broker._handle_question(self.q)

        messages = self._receive_as("askerX")
        self.assertEqual(len(messages), 1)
        msg = messages[0]
        self.assertEqual(msg["from"], ":session:question-broker")
        self.assertEqual(msg["subject"], "orchard:operator:message:response")
        self.assertEqual(msg["in_reply_to"], self.env["id"])
        self.assertEqual(msg["body"], {"index": 0, "option": "Yes"})

    def test_a_failed_popup_leaves_the_mailbox_file_standing(self):
        """`_render_popup` returning None (tmux/popup failed) must not lose
        the question: no reply is sent and the file is left for a retry."""
        with mock.patch.object(broker, "_render_popup", return_value=None):
            broker._handle_question(self.q)

        self.assertTrue(self.path.exists())
        self.assertEqual(self._receive_as("askerX"), [])


class LiveAskEndToEndTest(_LiveOrchardTestCase):
    """The full round trip: a real `courier.py ask` subprocess (the asker),
    the broker's real `pending_questions()` scan discovering it, and a real
    `_handle_question()` (popup stubbed) answering it — asserting the asker
    actually unblocks with the broker's answer."""

    def test_ask_subprocess_unblocks_with_the_brokers_answer(self):
        proc = subprocess.Popen(
            [sys.executable, _COURIER_PY, "ask", "--question", "Proceed?",
             "--option", "Yes", "--option", "No", "--poll-interval", "0.1"],
            cwd=self.repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env=dict(os.environ, CLAUDE_CODE_SESSION_ID="askerLive", PYTHONPATH=_TOOLS_DIR),
        )
        try:
            q = None
            deadline = time.time() + 10
            while time.time() < deadline and q is None:
                found = broker.pending_questions(self.projects_root, seen_ids=set())
                if found:
                    q = found[0]
                else:
                    time.sleep(0.05)
            self.assertIsNotNone(q, "ask's question never appeared in the operator mailbox")
            self.assertEqual(q["asker"], ":session:askerLive")
            self.assertEqual(q["question"], "Proceed?")

            with mock.patch.object(broker, "_render_popup",
                                    return_value={"index": 1, "option": "No"}):
                broker._handle_question(q)

            stdout, stderr = proc.communicate(timeout=10)
        finally:
            if proc.poll() is None:      # pragma: no cover - only on a genuine hang
                proc.kill()
                proc.communicate()

        self.assertEqual(proc.returncode, 0, stderr)
        self.assertEqual(json.loads(stdout.strip()), {"index": 1, "option": "No"})
        self.assertFalse(q["path"].exists())


if __name__ == "__main__":
    unittest.main()
