"""Placement tests for subagent rows in `tools/sidebar_rows.py`'s
flatten()/_agent_and_subagent_rows()/_task_rows(): a fleet built directly
from model-level `Agent(subagents=[...])` objects (no marker, no live
event file) must flatten with the subagent row landing immediately after
its owning agent's own identity row, both nested one depth below their
step's own accordion row, and beneath the task -- never sprinkled between
two step rows.

Ruled sources this checks against (per this step's scope guard --
nothing here is agent-invented):

  - docs/sidebar-spec.md §1: subagents come from delegation events,
    scheduled/running/done only -- no session, no identity, no model.
  - docs/sidebar-spec.md §6, Decision-098: "The agent identity subscript
    sits BENEATH its task ... never injected between step rows."

This is the test `tools/sidebar_paint_identity.py`'s `_draw_subagent_row`
docstring cites by name (`SubagentPlacementTests`) -- it did not exist
before this step; the docstring's earlier citation to it was written
ahead of the test actually landing.

Imports `sidebar` the same way `tests/test_sidebar.py` does (the
consolidated module re-exporting the model dataclasses and `flatten`),
so this file's model construction matches that file's own conventions
(see its `_agent`/`_fleet` helpers).
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


def _agent(session_id="s1", role="sower", activity="doing work", subagents=None):
    return sidebar.Agent(session_id=session_id, role=role, model=None, activity=activity,
                          status="working", step="building", subagents=subagents or [])


def _fleet_with_subagents(subagents, task_id="t", feature_id="f", session_id="s1"):
    """One repo, one feature, one task, one active "building" step
    carrying one agent built directly with `subagents=[...]` -- the exact
    construction the docstring under test describes."""
    agent = _agent(session_id=session_id, subagents=subagents)
    step = sidebar.Step(name="building", state="active", agents=[agent])
    task = sidebar.Task(task_id=task_id, name=f"task {task_id}", status="working", steps=[step])
    feature = sidebar.Feature(feature_id=feature_id, name=f"feature {feature_id}",
                               status="working", tasks=[task])
    return feature


class SubagentPlacementTests(unittest.TestCase):
    """Placement invariants for `sidebar_rows.flatten()`: a fleet built
    directly from `Agent(subagents=[...])` flattens the subagent row
    immediately after its agent's row, both one depth below their step's
    own accordion row, beneath the task -- never between two step rows."""

    def test_subagent_row_follows_directly_after_its_agent_row(self):
        sub = sidebar.Subagent(label="grep-scan", state="doing")
        feature = _fleet_with_subagents([sub])
        fleet = sidebar.Fleet(repos=[
            sidebar.Repo(name="r", activity="", status="working",
                         waiting_on_operator=False, features=[feature]),
        ])
        rows = sidebar.flatten(fleet)
        agent_idx = next(i for i, r in enumerate(rows) if r.kind == "agent")
        self.assertEqual(rows[agent_idx + 1].kind, "subagent")
        self.assertEqual(rows[agent_idx + 1].label, "grep-scan")

    def test_agent_and_subagent_sit_one_depth_below_the_step_row_beneath_the_task(self):
        subs = [sidebar.Subagent(label="grep-scan", state="done"),
                sidebar.Subagent(label="docs-audit", state="scheduled")]
        feature = _fleet_with_subagents(subs)
        fleet = sidebar.Fleet(repos=[
            sidebar.Repo(name="r", activity="", status="working",
                         waiting_on_operator=False, features=[feature]),
        ])
        rows = sidebar.flatten(fleet)
        task_row = next(r for r in rows if r.kind == "task")
        accordion_row = next(r for r in rows if r.kind == "accordion")
        agent_row = next(r for r in rows if r.kind == "agent")
        subagent_rows = [r for r in rows if r.kind == "subagent"]
        self.assertEqual(len(subagent_rows), 2)
        self.assertEqual(accordion_row.depth, task_row.depth + 1)
        self.assertEqual(agent_row.depth, accordion_row.depth + 1)
        for r in subagent_rows:
            self.assertEqual(r.depth, accordion_row.depth + 1)
        # beneath the task, never above it (Decision-098) -- both the
        # agent row and every subagent row it owns come after the task's
        # own row in the depth-first flatten order.
        self.assertGreater(rows.index(agent_row), rows.index(task_row))
        for r in subagent_rows:
            self.assertGreater(rows.index(r), rows.index(task_row))

    def test_subagent_rows_never_sit_between_two_step_rows(self):
        # Two separate features, each with its own active "building" step
        # carrying an agent with a subagent -- a regression that hoisted
        # subagent rows out to any shared, top-level placement (instead of
        # nesting each strictly under its own agent) would put a subagent
        # row directly after an accordion (step) row instead of after its
        # agent row. This is the general form of §6's "never injected
        # between step rows" ruling.
        sub_a = sidebar.Subagent(label="sub-a", state="doing")
        sub_b = sidebar.Subagent(label="sub-b", state="done")
        feature_a = _fleet_with_subagents([sub_a], task_id="t1", feature_id="f1", session_id="s1")
        feature_b = _fleet_with_subagents([sub_b], task_id="t2", feature_id="f2", session_id="s2")
        fleet = sidebar.Fleet(repos=[
            sidebar.Repo(name="r", activity="", status="working",
                         waiting_on_operator=False, features=[feature_a, feature_b]),
        ])
        rows = sidebar.flatten(fleet)
        subagent_indices = [i for i, r in enumerate(rows) if r.kind == "subagent"]
        self.assertEqual(len(subagent_indices), 2)
        for i in subagent_indices:
            # a subagent row's immediate predecessor is always its own
            # agent row or a sibling subagent row of the same agent --
            # never a step (accordion) row of any kind, own step or
            # another's.
            self.assertIn(rows[i - 1].kind, ("agent", "subagent"))
            self.assertNotEqual(rows[i - 1].kind, "accordion")
