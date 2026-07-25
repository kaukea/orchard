#!/usr/bin/env python3
"""Token-free question-popup broker (sidebar-polish item 12c-f).

An agent asks a question over the courier (`courier.py ask`); this script — a plain
long-running process, never an agent, never spending a token — is what makes
that ask() actually reach the operator and come back with an answer:

    watch loop -> finds a new question request sitting in the reserved
    `:session:operator` mailbox (tools/courier.py's orchard transport —
    `$XDG_RUNTIME_DIR/orchard/projects/<repo>.<project>/operator.<ts>.json`,
    one file per asker per project, scanned via tools/courier.py's own
    orchard_root() resolution, never a re-derived traversal) -> waits until
    the operator is not mid-input (12e) -> pops a native `tmux display-popup`
    over the operator's CURRENT window (12c) -> reads keypresses, accepting
    ONLY the defined option keys, no default/dismiss/timeout (12d) -> sends
    the answer back over the courier to the asking session (`courier.py
    reply --in-reply-to`) and deletes the handled mailbox file so it is
    never re-popped.

None of this is parameterizable by the asking agent (12f): `courier.py ask` has
no flag that skips deferral or widens the accepted keys — those rules live
entirely here.

Design split (mirrors tools/sidebar.py's render_lines()/curses split): every
decision is a pure function taking plain data — match_option_key(),
is_operator_busy(), pending_questions() — unit-testable with no tty, no
tmux, no live process. Only main()/_handle_question()/the tmux/termios calls
below them are I/O and need a live tmux session to exercise for real; that
part is NOT covered by tests/test_orchard_question_broker.py and needs a
human/live check (see the step's report).

ASSUMPTIONS flagged for the operator (this trial's HOW decisions):
  - "operator's current window" is resolved via the most recently active
    attached tmux CLIENT (`tmux list-clients`), then that client's current
    window — the best fleet-wide proxy available; a single-operator,
    possibly-multi-client tmux server is assumed.
  - "recent activity" (the idle fallback for typing outside a claude
    session, 12e) is tmux's own `client_activity` — updated on every
    keystroke sent to the server, independent of the harness. There is no
    per-keystroke Claude Code hook; the harness only exposes UserPromptSubmit
    (fires on SEND, not while typing), which is used here as the "just
    submitted, safe now" signal that overrides mere recency of pane activity
    for one instant, per is_operator_busy()'s docstring.
  - `courier.py ask` itself has no timeout (blocks until answered) — the
    no-timeout-auto-pick rule (12d) is about the POPUP's keypress handling,
    not about how long an agent's ask() may block.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import courier  # noqa: E402 — reuse its orchard_root()/XDG_RUNTIME_DIR resolution
                 # instead of re-deriving it (sidebar_model.py, its predecessor
                 # here, is retired)

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
_COURIER_PY = os.path.join(_TOOLS_DIR, "courier.py")

# Sender identity this script uses when it answers a question over the courier —
# it is not an agent session, so it has no CLAUDE_CODE_SESSION_ID of its own.
# The orchard `reply` command derives its sender via courier.py's whoami()
# (CLAUDE_CODE_SESSION_ID), so this identity is injected into the subprocess's
# environment rather than passed as a flag (unlike the retired legacy `send`,
# `reply` takes no --from at all).
BROKER_SENDER = "question-broker"

DEFAULT_POLL_SECONDS = 1.0
DEFAULT_IDLE_SECONDS = 5.0  # reuses item 9's "~5s" waiting threshold convention

# Item 12g: always-available gate keywords — recognised regardless of the
# specific question asked, closing the popup out with a distinct signal
# instead of forcing the operator through the narrower question first.
GATE_PHRASES = ("MAKE IT SO", "THAT IS ALL")

# Item 12g sizing: content-based popup dimensions, clamped to these bounds so
# a tiny terminal never gets an off-screen popup and a huge one never gets an
# absurdly stretched one. The upper bounds are further clamped at render time
# against the real tmux window size (see _window_size/_render_popup).
DEFAULT_MIN_WIDTH = 24
DEFAULT_MAX_WIDTH = 120
DEFAULT_MIN_HEIGHT = 8
DEFAULT_MAX_HEIGHT = 40
_POPUP_PADDING_W = 4  # left/right breathing room added to the longest line
_POPUP_PADDING_H = 4  # top/bottom breathing room added to the line count

# How long to hold the popup open after a closing keypress before tearing it
# down — long enough for the echoed key (or the final option state) to
# actually be visible, short enough that "instant" still feels instant.
_ECHO_LINGER_SECONDS = 0.2

# Item 12g colour: plain ANSI SGR (24-bit) — this is a standalone terminal
# script run inside a tmux popup, not curses, so there are no colour pairs to
# register. RGB values borrowed from tools/sidebar.py's ORCHID_PALETTE so the
# popup reads as the same colour family as the rest of the fleet's UI.
_ANSI_RESET = "\x1b[0m"
_ANSI_BOLD = "\x1b[1m"


def _fg(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    return f"\x1b[38;2;{r};{g};{b}m"


_COLOR_TITLE = _fg((0xC7, 0x1F, 0xA0))     # magenta  (ORCHID_PALETTE "magenta")
_COLOR_SUMMARY = _fg((0x9B, 0x59, 0xB6))   # purple   (ORCHID_PALETTE "purple")
_COLOR_MODE = _fg((0xF5, 0xD6, 0x42))      # yellow   (ORCHID_PALETTE "yellow")
_COLOR_QUESTION = _fg((0xF5, 0xF0, 0xF6))  # white    (ORCHID_PALETTE "white")
_COLOR_OPTION = _fg((0x4A, 0x7B, 0xC8))    # blue     (ORCHID_PALETTE "blue")
_COLOR_SELECTED = _fg((0x6A, 0xB0, 0x4F))  # green    (ORCHID_PALETTE "green")


# --------------------------------------------------------------------------
# Pure decision functions — unit-tested directly, no tty/tmux involved.
# --------------------------------------------------------------------------

def match_option_key(key: str, num_options: int) -> int | None:
    """Sidebar-polish item 12d: the popup responds ONLY to its defined
    option keys and ignores every other keypress — no default, no
    dismiss-on-any-key, no timeout auto-pick.

    Options are numbered 1..num_options; `key` is accepted iff it is exactly
    one of those digit characters. Returns the 0-based option index, or
    None for anything else (letters, arrows, enter, escape, punctuation,
    multi-char sequences, empty input) — the caller's loop simply keeps
    reading on None, never treating it as a selection.
    """
    if num_options <= 0 or len(key) != 1 or not key.isdigit():
        return None
    n = int(key)
    if 1 <= n <= num_options:
        return n - 1
    return None


def is_continue_key(key: str) -> bool:
    """Item 12g point 3: Escape means "continue the conversation" — never a
    refusal, never "no answer". The read loop below only ever reads one raw
    byte at a time, so a bare ESC (0x1b) and the FIRST byte of any arrow-key
    escape sequence are indistinguishable at this point — and since arrow-key
    navigation isn't part of this design, that's fine: ANY ESC-prefixed byte
    is treated identically, as "continue", without needing a peek/timeout
    read to disambiguate."""
    return key == "\x1b"


def is_confirm_key(key: str) -> bool:
    """Item 12g point 2: the multi-select confirm key. Enter, since it is
    otherwise free once digits stop auto-committing in multi-select mode.
    Raw tty mode can deliver either CR or LF depending on terminal, so both
    are accepted."""
    return key in ("\r", "\n")


def toggle_selection(selected: set[int], idx: int) -> set[int]:
    """Item 12g point 2: in multi-select mode, pressing a valid digit again
    TOGGLES that option's membership rather than committing immediately."""
    if idx in selected:
        return selected - {idx}
    return selected | {idx}


def gate_phrase_match(buffer: str) -> str | None:
    """Item 12g point 4: exact (case-insensitive, whitespace-trimmed) match
    of a completed typed buffer against the two always-available gate
    phrases. Returns the canonical phrase string, or None if `buffer` is
    neither."""
    normalized = buffer.strip().upper()
    for phrase in GATE_PHRASES:
        if normalized == phrase:
            return phrase
    return None


def gate_phrase_could_complete(buffer: str) -> bool:
    """True while `buffer` (case-insensitive) is still a viable PREFIX of at
    least one gate phrase. The typed-buffer capture in _popup_read_main keeps
    growing the buffer while this holds, and resets the instant it goes
    False — a keystroke that can no longer lead to either phrase."""
    normalized = buffer.strip().upper()
    if not normalized:
        return True
    return any(phrase.startswith(normalized) for phrase in GATE_PHRASES)


def gate_buffer_step(buffer: str, key: str) -> tuple[str, str | None]:
    """One step of the typed-buffer gate-keyword state machine (item 12g
    point 4 — the most novel piece of this step, so its exact mechanics live
    entirely in this one pure, testable function):

    The popup only reads single characters for normal option keys. To also
    recognise the two multi-character gate phrases, starting to type a
    LETTER begins capturing a line buffer (see the ch.isalpha() gate in
    _popup_read_main — that trigger condition lives in the I/O loop, not
    here, since it also depends on whether a buffer is already open).
    Every subsequent keystroke is fed through this function:

      - Enter (CR/LF) completes the buffer: if it exactly matches a gate
        phrase (case-insensitively), that phrase is returned as the second
        tuple element and the buffer resets to "". If it does NOT match,
        the buffer still resets to "" (typed garbage is simply dropped —
        the operator can start over), with no match.
      - Any other keystroke is appended (case-folded) and kept ONLY if the
        result is still a viable prefix of some gate phrase
        (gate_phrase_could_complete); otherwise the buffer resets to ""
        with no match.

    Returns (new_buffer, matched_phrase_or_None). When new_buffer is ""
    and matched is None, the caller (the I/O loop) is expected to
    REPROCESS the same keystroke as if no buffer had been open — e.g. a
    digit that broke the buffer still becomes a normal option keypress,
    and a letter that broke it may start a fresh buffer of its own. This
    is what keeps the gate-phrase capture from silently swallowing a key
    meant for something else."""
    if key in ("\r", "\n"):
        return "", gate_phrase_match(buffer)
    if key.isprintable():
        candidate = (buffer + key).upper()
        if gate_phrase_could_complete(candidate):
            return candidate, None
    return "", None


def popup_content_lines(title: str | None, summary: str | None, question: str,
                         options: list[str], multi: bool = False) -> list[str]:
    """The exact (uncoloured) lines the popup renders, in order — shared by
    the real renderer (_popup_read_main) and the sizing calculation
    (compute_popup_size) so the two can never drift apart: whatever text is
    actually shown is exactly what was sized for."""
    lines: list[str] = []
    if title:
        lines.append(title)
    if summary:
        lines.append(summary)
    lines.append(
        "select any, Enter to confirm  (or type MAKE IT SO / THAT IS ALL, Esc to keep talking)"
        if multi else
        "press a number to choose  (or type MAKE IT SO / THAT IS ALL, Esc to keep talking)"
    )
    lines.append(question)
    for i, opt in enumerate(options):
        prefix = "[ ] " if multi else ""
        lines.append(f"{prefix}{i + 1}. {opt}")
    return lines


def compute_popup_size(title: str | None, summary: str | None, question: str,
                        options: list[str], multi: bool = False,
                        min_width: int = DEFAULT_MIN_WIDTH, max_width: int = DEFAULT_MAX_WIDTH,
                        min_height: int = DEFAULT_MIN_HEIGHT,
                        max_height: int = DEFAULT_MAX_HEIGHT) -> tuple[int, int]:
    """Item 12g point 7: size to the actual content, not a fixed fraction of
    the screen. Width is the longest rendered line plus padding; height is
    the line count plus padding; both are clamped to [min, max] so the popup
    can never go off-screen on a tiny terminal nor balloon absurdly on a huge
    one. `max_width`/`max_height` are expected to already reflect the real
    terminal size when the caller has one available (see _render_popup)."""
    lines = popup_content_lines(title, summary, question, options, multi)
    longest = max((len(line) for line in lines), default=0)
    width = max(min_width, min(max_width, longest + _POPUP_PADDING_W))
    height = max(min_height, min(max_height, len(lines) + _POPUP_PADDING_H))
    return width, height


def is_operator_busy(now: float, last_submit_ts: float | None,
                      last_activity_ts: float | None, idle_seconds: float) -> bool:
    """Sidebar-polish item 12e: True means DEFER (do not pop yet).

    Clear to pop (returns False) when either:
      - there has been no raw input activity for `idle_seconds` (the idle
        fallback, for typing outside a claude session), or
      - the most recent signal is a submit (UserPromptSubmit fired at or
        after the last observed activity) — a submit is the harness's
        explicit "I just sent it" signal and takes precedence over mere
        recency, since the send keystroke itself is also "activity".

    Otherwise (recent activity with no submit since) the operator is taken
    to have input in flight, and the caller must not pop.
    """
    if last_activity_ts is None:
        return False
    if now - last_activity_ts >= idle_seconds:
        return False
    if last_submit_ts is not None and last_submit_ts >= last_activity_ts:
        return False
    return True


def _orchard_projects_root() -> Path | None:
    """`$XDG_RUNTIME_DIR/orchard/projects` — the directory holding one
    subdirectory per project slug, each possibly carrying a reserved
    `operator.<ts>.json` mailbox (tools/courier.py orchard_send, `:session:
    operator`). None when XDG_RUNTIME_DIR is unset, mirroring
    courier.py's own orchard_receive_own()'s empty-on-unset behaviour
    rather than that function's own hard sys.exit — the watch loop should
    idle, not crash, when the runtime dir isn't there yet."""
    if not os.environ.get("XDG_RUNTIME_DIR"):
        return None
    return courier.orchard_root() / "projects"


def pending_questions(projects_root: Path | None, seen_ids: set[str]) -> list[dict]:
    """Scan every project's reserved operator mailbox for question requests
    not in `seen_ids`.

    Non-destructive peek: a discovered file is left on disk until answered
    (`_handle_question` deletes it once handled, so it is never re-popped).
    Each project gets its OWN `operator.<ts>.json` per asker
    (`$XDG_RUNTIME_DIR/orchard/projects/<repo>.<project>/operator.<ts>.json`,
    tools/courier.py orchard_send/cmd_ask) — a question is a directed
    request, never a fan-out, so there is exactly one file per question, not
    one-per-peer as the retired broadcast used to write. De-dup is still by
    `question_id` (now nested in the envelope's `body`, not top-level) so a
    question re-observed across polls before it is handled is not re-queued
    — the caller folds the returned question_ids into `seen_ids` once
    enqueued.

    Returns dicts sorted by `ts`: {id, question_id, question, options,
    asker, title, summary, multi, project, path}. `id` is the envelope's
    OWN id — the field a reply's `--in-reply-to` must match
    (tools/courier.py _find_orchard_reply), distinct from `question_id`
    which only rides the body for bookkeeping. `path` is the mailbox file
    to delete once the question has been handled.
    """
    found: dict[str, dict] = {}
    if projects_root is None or not projects_root.is_dir():
        return []
    for project_dir in projects_root.iterdir():
        if not project_dir.is_dir():
            continue
        for f in project_dir.glob("operator.*.json"):
            try:
                env = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            body = env.get("body")
            if not isinstance(body, dict):
                continue
            qid = body.get("question_id")
            if not qid or qid in seen_ids or qid in found:
                continue
            found[qid] = {
                "id": env.get("id"),
                "question_id": qid,
                "question": body.get("question"),
                "options": body.get("options") or [],
                "asker": env.get("from"),
                "ts": env.get("ts") or "",
                "title": body.get("title"),
                "summary": body.get("summary"),
                "multi": bool(body.get("multi", False)),
                "project": project_dir.name,
                "path": f,
            }
    return sorted(found.values(), key=lambda q: q["ts"])


# --------------------------------------------------------------------------
# I/O glue — needs a live tmux session / real tty; not unit-tested.
# --------------------------------------------------------------------------

def _run(cmd: list[str]) -> str:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def _broker_dir() -> Path | None:
    common = _run(["git", "rev-parse", "--git-common-dir"])
    if not common:
        return None
    return Path(common).resolve() / "the-works" / "broker"


def _last_submit_ts() -> float | None:
    d = _broker_dir()
    if d is None:
        return None
    marker = d / "last-submit-ts"
    try:
        return float(marker.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _last_client_activity_ts() -> float | None:
    """Most recent `client_activity` (epoch seconds) across attached tmux
    clients — tmux's own raw-input-recency signal, independent of the
    harness (see module ASSUMPTIONS)."""
    out = _run(["tmux", "list-clients", "-F", "#{client_activity}"])
    values = [float(v) for v in out.splitlines() if v.strip().isdigit()]
    return max(values) if values else None


def _operator_current_window() -> str | None:
    """The window of the most recently active attached tmux client — the
    best fleet-wide proxy for "wherever the operator currently is" (see
    module ASSUMPTIONS)."""
    out = _run(["tmux", "list-clients", "-F", "#{client_activity} #{client_session}"])
    best_ts, best_session = None, None
    for line in out.splitlines():
        parts = line.split(" ", 1)
        if len(parts) != 2 or not parts[0].isdigit():
            continue
        ts, session = float(parts[0]), parts[1]
        if best_ts is None or ts > best_ts:
            best_ts, best_session = ts, session
    if best_session is None:
        return None
    return _run(["tmux", "display-message", "-p", "-t", best_session, "#{window_id}"]) or None


def _popup_read_main(question: str, options: list[str], answer_file: str,
                      title: str | None = None, summary: str | None = None,
                      multi: bool = False) -> None:
    """Runs INSIDE the tmux popup: prints the title/summary/question +
    numbered options (coloured, item 12g point 6), then a raw-mode key
    reader that exits on one of FOUR outcomes:

      - a valid option key (single-select: instant, unchanged from before —
        item 12d/12g point 1 echoes the digit back before returning)
      - Enter in multi-select mode, confirming the toggled selection
        (item 12g point 2)
      - Escape, meaning "continue the conversation" (item 12g point 3)
      - the typed gate phrase MAKE IT SO / THAT IS ALL, always available
        regardless of the question's own options (item 12g point 4)

    No default, no dismiss-on-any-other-key, no timeout — every keystroke
    that is none of the above is ignored (or, for a gate-buffer keystroke
    that breaks the prefix match, reprocessed fresh per gate_buffer_step's
    contract) and the loop keeps reading.
    """
    import termios
    import tty

    selected: set[int] = set()
    gate_buffer = ""

    def header_lines() -> str:
        parts = []
        if title:
            parts.append(f"{_ANSI_BOLD}{_COLOR_TITLE}{title}{_ANSI_RESET}")
        if summary:
            parts.append(f"{_COLOR_SUMMARY}{summary}{_ANSI_RESET}")
        mode_line = ("select any, Enter to confirm" if multi
                     else "press a number to choose — instant")
        parts.append(f"{_COLOR_MODE}{mode_line}  "
                      f"(or type MAKE IT SO / THAT IS ALL, Esc to keep talking){_ANSI_RESET}")
        parts.append(f"{_COLOR_QUESTION}{question}{_ANSI_RESET}")
        return "\r\n".join(parts)

    def option_lines() -> list[str]:
        lines = []
        for i, opt in enumerate(options):
            is_sel = multi and i in selected
            marker = "[x] " if is_sel else ("[ ] " if multi else "")
            color = _COLOR_SELECTED if is_sel else _COLOR_OPTION
            lines.append(f"{color}{marker}{i + 1}. {opt}{_ANSI_RESET}")
        return lines

    def redraw_options() -> None:
        # Cursor sits just below the last option line (each was written
        # ending in \r\n); move up over the whole block and rewrite it in
        # place so a toggle updates its [x]/[ ] marker live (item 12g
        # point 1) without disturbing the header above it.
        sys.stdout.write(f"\x1b[{len(options)}A")
        for line in option_lines():
            sys.stdout.write("\x1b[2K" + line + "\r\n")
        sys.stdout.flush()

    def write_answer(payload: dict) -> None:
        Path(answer_file).write_text(json.dumps(payload), encoding="utf-8")

    sys.stdout.write(header_lines() + "\r\n\r\n")
    sys.stdout.write("\r\n".join(option_lines()) + "\r\n")
    sys.stdout.flush()

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            # os.read(fd, 1), NOT sys.stdin.read(1): Python's io.TextIOWrapper
            # sits on a BufferedReader that can still hold a keypress back
            # until more bytes (or a newline) arrive, even after tty.setraw()
            # takes the fd out of canonical mode — a well-known gotcha that
            # makes a raw-mode reader silently behave like it's waiting for
            # Enter. Reading the fd directly bypasses that buffering, so a
            # single option keypress registers immediately (item 12d).
            raw = os.read(fd, 1)
            ch = raw.decode("ascii", errors="ignore")

            if is_continue_key(ch):
                write_answer({"continue": True})
                return

            if gate_buffer:
                new_buffer, matched = gate_buffer_step(gate_buffer, ch)
                if matched:
                    time.sleep(_ECHO_LINGER_SECONDS)
                    write_answer({"gate": matched})
                    return
                gate_buffer = new_buffer
                if gate_buffer:
                    sys.stdout.write(ch)
                    sys.stdout.flush()
                    continue
                # buffer died without matching (or Enter completed it with no
                # match) — fall through and reprocess this SAME keystroke as
                # a fresh one below, per gate_buffer_step's contract: it is
                # never silently swallowed.

            if multi and is_confirm_key(ch):
                time.sleep(_ECHO_LINGER_SECONDS)
                write_answer({
                    "indices": sorted(selected),
                    "options": [options[i] for i in sorted(selected)],
                })
                return

            idx = match_option_key(ch, len(options))
            if idx is not None:
                sys.stdout.write(ch)  # item 12g point 1: echo the keypress
                sys.stdout.flush()
                if multi:
                    selected = toggle_selection(selected, idx)
                    redraw_options()
                    continue
                # Linger a moment so the echoed digit above is actually
                # perceptible — without this, write_answer()+return tears
                # down the popup (tmux display-popup -E) in the same
                # instant as the echo write, so the character never has
                # time to render before the pane vanishes (operator-
                # reported: "missing showing the key I typed").
                time.sleep(_ECHO_LINGER_SECONDS)
                write_answer({"index": idx, "option": options[idx]})
                return

            if ch.isalpha():
                candidate = ch.upper()
                if gate_phrase_could_complete(candidate):
                    gate_buffer = candidate
                    sys.stdout.write(ch)
                    sys.stdout.flush()
                # else: a letter that can't lead to either gate phrase —
                # dead on arrival, ignored, same as any other unknown key.
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _shell_quote(s: str) -> str:
    import shlex
    return shlex.quote(s)


def _window_size(window: str | None) -> tuple[int, int] | None:
    """The tmux window's current cell dimensions (columns, rows) — used to
    clamp the popup's content-based size (item 12g point 7) so it can never
    exceed the real terminal, on top of the generic DEFAULT_MAX_* bounds."""
    cmd = ["tmux", "display-message", "-p"]
    if window:
        cmd += ["-t", window]
    cmd += ["#{window_width} #{window_height}"]
    out = _run(cmd)
    parts = out.split()
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        return None
    return int(parts[0]), int(parts[1])


def _render_popup(window: str, question: str, options: list[str],
                   title: str | None = None, summary: str | None = None,
                   multi: bool = False) -> dict | None:
    """Pops a native tmux popup over `window` (item 12c) running the inner
    reader above; blocks until it exits (a valid outcome was reached — the
    inner reader itself never returns early), then reads the answer file it
    wrote. Size is computed from the actual content (item 12g point 7), not
    a fixed screen percentage, and clamped against the real window size when
    it can be determined.
    """
    win_size = _window_size(window)
    max_w = DEFAULT_MAX_WIDTH if win_size is None else max(
        DEFAULT_MIN_WIDTH, min(DEFAULT_MAX_WIDTH, win_size[0] - 2))
    max_h = DEFAULT_MAX_HEIGHT if win_size is None else max(
        DEFAULT_MIN_HEIGHT, min(DEFAULT_MAX_HEIGHT, win_size[1] - 2))
    width, height = compute_popup_size(title, summary, question, options, multi,
                                        max_width=max_w, max_height=max_h)

    answer_file = f"/tmp/.orchard-question-answer-{os.getpid()}-{int(time.time() * 1000)}.json"
    inner = [
        sys.executable, os.path.abspath(__file__), "_popup-read",
        "--question", question, "--answer-file", answer_file,
    ]
    if title:
        inner += ["--title", title]
    if summary:
        inner += ["--summary", summary]
    if multi:
        inner += ["--multi"]
    for opt in options:
        inner += ["--option", opt]
    cmd = ["tmux", "display-popup", "-E", "-w", str(width), "-h", str(height)]
    if window:
        cmd += ["-t", window]
    cmd += ["-T", " orchid question ", " ".join(_shell_quote(c) for c in inner)]
    try:
        subprocess.run(cmd, timeout=None)
    except (FileNotFoundError, OSError):
        return None
    try:
        data = json.loads(Path(answer_file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    finally:
        Path(answer_file).unlink(missing_ok=True)
    return data


def _handle_question(q: dict) -> None:
    window = _operator_current_window()
    answer = _render_popup(window, q["question"] or "", q["options"],
                            title=q.get("title"), summary=q.get("summary"),
                            multi=bool(q.get("multi", False)))
    if answer is None:
        return  # tmux/popup failed — leave the mailbox file standing, no crash
    body = json.dumps(answer)
    # `reply` (unlike the retired legacy `send`) takes no --from: its sender
    # is always courier.py's own whoami() (CLAUDE_CODE_SESSION_ID), so the
    # broker's identity rides the subprocess environment instead. --to is
    # already the full `:session:<asker>` address (the request envelope's
    # own `from`); --target-project is required since the broker watches
    # every project's mailbox, not just the one its own cwd resolves to.
    env = {**os.environ, "CLAUDE_CODE_SESSION_ID": BROKER_SENDER}
    subprocess.run(
        [sys.executable, _COURIER_PY, "reply",
         "--to", q["asker"], "--in-reply-to", q["id"],
         "--subject", "orchard:operator:message:response",
         "--body", body, "--target-project", q["project"]],
        capture_output=True, text=True, env=env,
    )
    q["path"].unlink(missing_ok=True)  # delete-on-handled: never re-popped


def watch(poll_interval: float = DEFAULT_POLL_SECONDS,
          idle_seconds: float = DEFAULT_IDLE_SECONDS) -> None:
    seen_ids: set[str] = set()
    pending: list[dict] = []
    while True:
        roots = _orchard_projects_root()
        for q in pending_questions(roots, seen_ids):
            seen_ids.add(q["question_id"])
            pending.append(q)
        if pending:
            now = time.time()
            busy = is_operator_busy(now, _last_submit_ts(), _last_client_activity_ts(),
                                     idle_seconds)
            if not busy:
                _handle_question(pending.pop(0))
        time.sleep(poll_interval)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("watch", help="run the long-lived broker loop")
    w.add_argument("--poll-interval", type=float, default=DEFAULT_POLL_SECONDS)
    w.add_argument("--idle-seconds", type=float, default=DEFAULT_IDLE_SECONDS)

    r = sub.add_parser("_popup-read", help=argparse.SUPPRESS)  # internal, run by the popup itself
    r.add_argument("--question", required=True)
    r.add_argument("--option", dest="option", action="append", required=True)
    r.add_argument("--answer-file", required=True)
    r.add_argument("--title")
    r.add_argument("--summary")
    r.add_argument("--multi", action="store_true")

    args = p.parse_args()
    if args.cmd == "watch":
        watch(args.poll_interval, args.idle_seconds)
    elif args.cmd == "_popup-read":
        _popup_read_main(args.question, args.option, args.answer_file,
                          title=args.title, summary=args.summary, multi=args.multi)


if __name__ == "__main__":
    main()
