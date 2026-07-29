"""The agent activity quote and its attribution/citation text, pure strings
-- no curses. Builds the two citation layouts (operator ruling, 2026-07-28):
a one-line "quote em-dash role middle-dot model" rung when there is width
for it, and a two-line quote-then-citation-below rung otherwise -- each
degrading full model -> abbreviated -> dropped (never a dangling middle
dot) before the ordinary ellipsis rule ever touches the quote itself.
`compose_identity_line`/`identity_line_text` are the single-line predecessor
this ladder superseded; kept defined and tested, nothing in the live draw
path calls them any more.
"""
from __future__ import annotations

from sidebar_glyphs import NBSP, role_emoji  # noqa: E402
from sidebar_model import NO_LIVE_ACTIVITY  # noqa: E402
from sidebar_text import _cell_width, _truncate  # noqa: E402


def compose_identity_line(
    doing: str, role: str | None, model: str | None, width: int,
) -> tuple[str, str, str]:
    """(doing, role_text, model_text) — role_text is '' when `role` is None;
    otherwise it is `role_emoji(role)` glued to the role text with an NBSP
    (no leading space when there is no glyph for the role). model_text is
    `model` truncated (never wrapped) to whatever room is left after
    doing+role, '' if none is left or `model` is None."""
    sep = NBSP + "⋮" + NBSP
    emoji = role_emoji(role)
    role_text = (emoji + NBSP + role) if (role and emoji) else (role or "")
    used = _cell_width(doing) + (len(sep) + _cell_width(role_text) if role_text else 0)
    room = width - used - (len(sep) if model else 0)
    model_text = (model or "")[:max(room, 0)] if model else ""
    return doing, role_text, model_text


def identity_line_text(doing: str, role: str | None, model: str | None, width: int) -> str:
    doing_t, role_t, model_t = compose_identity_line(doing, role, model, width)
    sep = NBSP + "⋮" + NBSP
    parts = [doing_t]
    if role_t:
        parts.append(role_t)
    if model_t:
        parts.append(model_t)
    return sep.join(parts)

# --------------------------------------------------------------------------
# Identity BLOCK — a quote with a subordinate attribution, book-epigraph
# style (operator ruling, 2026-07-26, SUPERSEDES the single-line `identity_
# line_text` above as the agent row's live render; that function stays
# defined/tested but nothing in the draw path calls it any more). Citation
# punctuation restored 2026-07-28 (operator, verbatim: "the rulestays (or
# comes back): middle dot between then, full odel name (minus Claude) and
# version, if clipping use abreviatiob, if stil clipping remove model, if
# stilll clipping usual ellipsis rule" — a RESTORATION, not an invention).
#
# The status is volatile and is the thing being scanned for, so it carries
# the news as the quote; role/model are stable context, subordinate. TWO
# layouts (operator: "one line citation style if space... otherwise the
# citation is just below the text"), chosen by `expand` — the caller's
# real-available-height decision (`_agent_expansion_fits`), unchanged by
# this step:
#
#   tight (expand=False, the row's own WIDTH-driven ladder — the common
#   case, since a 1-line row costs no extra height):
#     "activity" — role · model            (full model, the rare case:
#                                            "It's all relative" — Albert
#                                            Einstein · Opus 14.2)
#     "activity" — role · shortmodel        (model doesn't fit -> abbreviate)
#     "activity" — role                    (still doesn't fit -> drop model
#                                            entirely — never a dangling
#                                            middle dot)
#     "activ…"                              (even quote+role doesn't fit ->
#                                            role drops too, ordinary
#                                            ellipsis rule on the quote
#                                            alone, ``_truncate``)
#   expand (2 lines, HEIGHT-permitting only):
#     "activity"
#         role · model                      (full, then short, then no
#                                            model — same ladder, NO dash:
#                                            "no ash obviuouys" once the
#                                            citation is its own line — EITHER
#                                            indented a few blanks OR flush
#                                            right (`identity_block`'s own
#                                            `align` parameter): BOTH rungs
#                                            are built for a real A/B
#                                            comparison (operator ruling,
#                                            2026-07-29), superseding an
#                                            earlier step's unilateral pick
#                                            of indented-only.
#
# The quote itself never drops in either layout. Which LAYOUT applies
# (tight vs expand) is HEIGHT-driven and untouched by this step; which RUNG
# within a layout applies is purely WIDTH-driven.
# --------------------------------------------------------------------------

_ATTRIBUTION_INDENT = "    "


def _role_text(role: str | None) -> str:
    emoji = role_emoji(role)
    return (emoji + NBSP + role) if (role and emoji) else (role or "")


def _strip_claude_prefix(model: str) -> str:
    """The model string exactly as it arrives on the bus, minus a leading
    "claude"/"claude-" (operator, 2026-07-28: "full odel name (minus
    Claude) and version" — the FULL citation rung is the bus string
    verbatim otherwise, never re-cased or re-punctuated; that transform is
    `short_model_name`'s job, one rung further down the ladder)."""
    lowered = model.lower()
    if lowered.startswith("claude-"):
        return model[len("claude-"):]
    if lowered.startswith("claude"):
        return model[len("claude"):].lstrip("-")
    return model


def short_model_name(model: str | None) -> str | None:
    """The version-elided short form of a model string ("claude-opus-5" ->
    "opus5", "claude-sonnet-5-20260101" -> "sonnet5") — family name plus
    its leading numeric version component, dropping any "claude-" prefix
    and any later date/build suffix. None when there's nothing to shorten
    to (an empty or unparseable string)."""
    if not model:
        return None
    parts = model.split("-")
    if parts and parts[0] == "claude":
        parts = parts[1:]
    if not parts:
        return None
    family = parts[0]
    version = next((p for p in parts[1:] if p.isdigit()), "")
    return f"{family}{version}"


def _with_effort(model_text: str, effort: str | None) -> str:
    """`model_text` with `effort` bolted on (M2, spec §3's "model and
    effort" ruled metric — "surface effort alongside the model where the
    citation/identity ladder shows the model, smallest honest placement"):
    appended as `/<effort>`, the SAME width budget as the model text it
    rides with, rather than a new independent field/rung of its own. This
    is the smallest change that puts effort on screen — the ladder's
    existing full->short->dropped degradation already governs the result,
    since effort now travels WITH whichever model-text candidate that
    ladder picks (dropped once the model itself is dropped, never
    lingering alone). The "/" separator and the "ride with model, drop
    with model" behaviour are this function's own implementer choice, not
    themselves a ruling."""
    return f"{model_text}/{effort}" if (model_text and effort) else model_text


def attribution_text(
    role: str | None, model: str | None, width: int, effort: str | None = None,
) -> tuple[str, str]:
    """(role_text, model_text) for the BELOW-QUOTE citation at `width`
    columns — role_text never empties (callers only reach this once
    `role` is truthy); model_text is the full model string (minus its
    "Claude" prefix, `_strip_claude_prefix` — operator: "full odel name
    (minus Claude) and version"), its short form, or '' once neither fits
    — the model degrades, role never does, in the 2-line (expand) form.
    `effort` (M2), when given, rides bolted onto whichever model-text
    candidate fits (`_with_effort`) — it is measured as part of that
    candidate's own width, so a model+effort pair that doesn't fit falls
    through to the short form, then to '', exactly like a bare model would.
    `width` here is the room for "role · model" — no dash, this rung sits
    on its own line (see the module section docstring)."""
    role_text = _role_text(role)
    if not model:
        return role_text, ""
    model = _strip_claude_prefix(model)
    room = width - _cell_width(role_text) - _cell_width(" · ")
    full_text = _with_effort(model, effort)
    if _cell_width(full_text) <= max(room, 0):
        return role_text, full_text
    short = short_model_name(model)
    short_text = _with_effort(short, effort) if short else ""
    if short_text and _cell_width(short_text) <= max(room, 0):
        return role_text, short_text
    return role_text, ""


def _citation_line(
    role: str | None, model: str | None, width: int, effort: str | None = None,
) -> str:
    """The below-quote citation (the expand layout's second line) — role
    then model(+effort, M2), middle-dot separated, NO leading dash (operator:
    "no ash obviuouys" — the dash marks an INLINE attribution; once the
    citation is its own, positioned line, it is redundant). Falls through
    `_truncate` as the final safety net if even the role alone overruns
    `width` (the ordinary ellipsis rule, same as every other rung)."""
    role_text, model_text = attribution_text(role, model, width, effort)
    text = f"{role_text} · {model_text}" if model_text else role_text
    return _truncate(text, width)


def _citation_line_indented(
    role: str | None, model: str | None, width: int, effort: str | None = None,
) -> str:
    """Rung A of the NORMAL (below-quote) citation layout — indented a few
    blanks (`_ATTRIBUTION_INDENT`), operator ruling 2026-07-28: "the
    citation is just below the text itself either right alined or indented
    by a few blans". `width` is the room for the indent PLUS the citation
    text (mirrors `_draw_identity_block`'s own `attribution_width` calc)."""
    text_width = max(width - len(_ATTRIBUTION_INDENT), 0)
    return _ATTRIBUTION_INDENT + _citation_line(role, model, text_width, effort)


def _citation_line_right_aligned(
    role: str | None, model: str | None, width: int, effort: str | None = None,
) -> str:
    """Rung B of the NORMAL (below-quote) citation layout — flush against
    the row's right edge instead of indented from its left (operator
    ruling, 2026-07-28, the other half of the same "right alined or
    indented" choice — built here alongside the indented rung so both are
    on hand for an A/B comparison, operator ruling 2026-07-29, rather than
    the indented rung being the only one ever built). Left-padded with
    spaces to `width` so the text itself ends flush right; the padding
    shrinks to 0, never negative, once the citation alone fills `width`."""
    text = _citation_line(role, model, width, effort)
    pad = max(width - _cell_width(text), 0)
    return " " * pad + text


def _quoted_activity(activity: str) -> str:
    """The agent's activity, quoted for display — an empty string renders
    as the words "no activity" rather than a bare pair of smart quotes
    (sidebar-teamwork defect 5: idle is a legitimate state, Decision-058,
    not a blank to paper over). The model layer already substitutes
    `NO_LIVE_ACTIVITY` for every `Agent.activity` it builds, so this is
    defensive rather than the primary guard — but it is the ONE place
    every quote-building call site goes through, so the render side never
    depends on the model never slipping one through."""
    return f"“{activity or NO_LIVE_ACTIVITY}”"

# The floor a squeezed quote is still allowed to shrink to in the tight
# rung (`tight_line_parts`) before the ROLE is given up on instead
# (sidebar-teamwork defect 2, 2026-07-27: at 29 columns an agent's activity
# was truncating to almost nothing — "no ac… — 🌿 landscaper" — because the
# role's emoji+NBSP+word took a fixed share off the top and the quote got
# whatever was left, unconditionally, down to a near-useless sliver. The
# quote is the one genuinely LIVE piece of information on the line; the
# role is stable context already visible via the row's own colour lineage
# (Decision-110) — so the floor is no longer a bare few cells, it is
# `_TIGHT_QUOTE_FLOOR`, at least half of the row's own budget. Below that
# floor the role tail drops instead, same "none" rung `identity_block`'s
# own docstring already names — this raises how EASILY that rung is
# reached, it does not invent it.
_MIN_TIGHT_QUOTE_WIDTH = 8


def _tight_quote_floor(width: int) -> int:
    """The minimum cell budget the quote must keep before the role tail is
    even considered — half of this row's own width, floored at
    `_MIN_TIGHT_QUOTE_WIDTH` so a very narrow row still asks for something
    (never zero, never a single character)."""
    return max(width // 2, _MIN_TIGHT_QUOTE_WIDTH)


def _model_rungs(model: str | None, effort: str | None = None) -> list[str | None]:
    """Model(+effort, M2) candidates for the ONE-LINE citation, widest
    first: the full string (minus "Claude", `_strip_claude_prefix`, with
    `effort` bolted on via `_with_effort`), its abbreviated form
    (`short_model_name`, skipped if identical, effort bolted on the same
    way), then None (dropped entirely — effort along with it, since it
    never rides without the model it sits "alongside") — operator: "if
    clipping use abreviatiob, if stil clipping remove model". Always ends
    in None so a caller's loop always has a final candidate to fall back
    to."""
    if not model:
        return [None]
    full = _strip_claude_prefix(model)
    candidates: list[str | None] = [_with_effort(full, effort)]
    short = short_model_name(full)
    if short and short != full:
        candidates.append(_with_effort(short, effort))
    candidates.append(None)
    return candidates


def tight_line_parts(
    activity: str, role: str | None, width: int, model: str | None = None,
    effort: str | None = None,
) -> tuple[str, str]:
    """(shown_quote, tail) for the tight (1-line) rung — the ONE-LINE
    citation's home (operator: "one line citation style if space" — rare,
    since it costs the most width, but tried FIRST, widest candidate
    first). `tail` is ` — role · model[/effort]` (full), ` — role ·
    shortmodel[/effort]` (abbreviated, M2's `effort` riding bolted onto
    either), ` — role` (model dropped — never a dangling middle dot, since
    the dot is only ever emitted alongside a model string, and effort never
    lingers alone once the model it rides with is dropped), or "" (role
    dropped too) — whichever is the WIDEST one that still keeps the quote
    at or above `_tight_quote_floor(width)` (sidebar-teamwork defect 2: the
    quote is what a reader scans this line for, so IT is the last thing to
    yield, not the first). `shown_quote` alone is never truncated below the
    plain quote unless making room for a tail actually requires it."""
    quote = _quoted_activity(activity)
    if not role:
        return _truncate(quote, width), ""
    role_text = _role_text(role)
    floor = _tight_quote_floor(width)

    for candidate_model in _model_rungs(model, effort):
        tail = f" — {role_text} · {candidate_model}" if candidate_model else f" — {role_text}"
        quote_budget = width - _cell_width(tail)
        if quote_budget >= floor:
            shown_quote = quote if _cell_width(quote) <= quote_budget else _truncate(quote, quote_budget)
            return shown_quote, tail
    return _truncate(quote, width), ""


def tight_line(
    activity: str, role: str | None, width: int, model: str | None = None,
    effort: str | None = None,
) -> str:
    quote, tail = tight_line_parts(activity, role, width, model, effort)
    return f"{quote}{tail}"


def identity_block(activity: str, role: str | None, model: str | None,
                    width: int, expand: bool, align: str = "indent",
                    effort: str | None = None) -> list[str]:
    """[quote] or [quote, citation] — see the module section docstring
    above for the exact two-layout, per-layout-ladder degradation.
    `expand` is the caller's real-height decision (`_agent_expansion_
    fits`); `width` is this row's own column budget. `align` picks which
    of the two NORMAL-layout rungs the citation line uses — "indent"
    (`_citation_line_indented`, the default, unchanged from before this
    parameter existed) or "right" (`_citation_line_right_aligned`) — both
    built side by side for an A/B comparison (operator ruling, 2026-07-29);
    no effect on the tight (non-`expand`) rung, which has never carried a
    dash-vs-indent choice to make. `effort` (M2, spec §3's "model and
    effort" ruled metric) rides bolted onto `model` wherever the ladder
    below shows it (`_model_rungs`/`attribution_text`'s own `_with_effort`)
    — the smallest placement that puts it on screen, per the step-spec's
    own instruction, rather than a new field of its own. Lines are
    returned WITHOUT the row's own depth indent — callers prepend that
    uniformly; the indented rung's extra `_ATTRIBUTION_INDENT` beneath the
    quote is already baked in."""
    if not role:
        return [_quoted_activity(activity)]
    if expand:
        quote = _quoted_activity(activity)
        citation = (_citation_line_right_aligned(role, model, width, effort) if align == "right"
                    else _citation_line_indented(role, model, width, effort))
        return [quote, citation]
    return [tight_line(activity, role, width, model, effort)]


def _agent_expansion_fits(rows: list[Row], height: int | None) -> bool:
    """Whether there is genuine room to give an agent row its own
    attribution line, rather than folding it onto the quote line.

    "Very compact form" (operator ruling, 2026-07-26) supersedes the
    original bare-fits check: compactness wins at EVERY choice point, so
    the tight 1-line form (role riding the quote line) is the DEFAULT, and
    2-line expansion is reserved for a frame with real slack to spare —
    never "just doesn't overflow". In practice that makes the 2-line form
    unreachable through today's callers; it stays defined (and `height`/
    `rows` kept as parameters) as a seam for a future roomier/wide-pane
    mode rather than deleted, per `identity_block`'s own degradation
    ladder, which a caller may still drive directly."""
    return False
