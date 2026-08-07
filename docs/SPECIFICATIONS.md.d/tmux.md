# tmux

## 1. Purpose
- Define how the terminal UI windowing model is organised and managed.
- Provide a pluggable component that understands the state of a council agent while it is running.
- Intercept relevant events to decide where windows, sessions, panes, and terminal views should be placed.

## 2. Principles
- The system should be pluggable and support multiple backends.
- It should observe the state of the council agent and react to meaningful events.
- It should define placement and lifecycle policies for windows, sessions, panes, and terminal views.
- The initial implementation should target tmux as the primary backend.
- The goal is to provide a simple, robust, and dependable terminal experience in the environment where the Claude TUI operates.
- In other words, the windowing system should be designed to work in whatever terminal environment the Claude TUI uses.

## 3. Core concepts
- Window
- Session
- Pane
- Terminal view
- Event
- Backend adapter
- Placement policy
- Lifecycle policy

## 4. Responsibilities
- Detect the state of the council agent while it is running.
- Intercept events such as creation, focus change, completion, and shutdown.
- Decide where to place new windows or panes.
- Decide when to close or reuse existing windows, sessions, or panes.
- Provide a predictable layout that remains easy to reason about.

## 5. Backend model
- The system should expose a backend interface that can be implemented for different terminal environments.
- The initial implementation should use tmux as the concrete backend.
- The backend adapter should translate internal decisions into backend-specific operations.

## 6. Event-driven behaviour
- Placement decisions should be driven by events rather than by hard-coded assumptions.
- The system should react to state transitions in the council agent and update the terminal layout accordingly.
- The layout should remain stable and understandable as agent state changes over time.

## 7. Expected behaviour
- The system should be able to open, organise, and close windows and panes based on agent state.
- The default implementation should work well with tmux without unnecessary complexity.
- The resulting experience should feel sturdy, dependable, and straightforward.

## 8. Workflow terminology
- Repository: the root container of the workflow, also referred to as the project.
- Feature: a unit of work contained within a repository.
- Task: a unit of work contained within a feature.
- Agent: an execution unit contained within a task.
- Subagent: a supporting execution unit contained within an agent.

These terms should be used consistently when describing the mapping between workflow components.

## 9. TMUX mapping
- The mapping is defined for the tmux backend and describes how workflow components are represented in the terminal UI.
- Each project is represented by a new tmux session.
- The session name should be the repository name.
- The first window in every session is reserved for the gardener.
- The gardener window is always the first window in the session and remains there for the lifetime of the session.
- When work is split into tasks, each task is represented by its own window.
- The window name should be the feature name.
- The pane name should be the task name.
- In practice, the pane name is used mainly for display and identification.
- For three tasks, the session contains three task windows, each with one pane.
- The window title should always correspond to the feature, while the pane title should correspond to the task.
- The tmux rename command should always reflect the currently running agent.

## 10. Subagent pane mapping
- When a sessionless subagent is created by an agent inside a window, a right-hand pane should be created for it.
- That pane should display the subagent content and allow interaction with the subagent.
- The pane should be attached to the same window as the parent agent.
- The right-hand pane should be used for this kind of sessionless subagent experience.
- When the subagent finishes its work, that right-hand pane should disappear.
- If multiple subagents are created, they should stack vertically in the right-hand pane area.
- The system should preserve the main workflow pane while exposing subagent activity in a separate, dedicated side area.

## 11. Session startup and shared sidebar
- On startup of any session, there should be a hook that runs as soon as the session is created and named after the repository or project.
- That startup hook should create the left-side pane that contains the shared sidebar.
- The sidebar should be attached once per session rather than replicated in every window.
- The current model of creating a separate sidebar pane for each window is inefficient and should be replaced.
- The system should investigate and prefer a shared-window or shared-pane approach when the backend supports it.
- There is no reason for each window to have its own copy of the same sidebar content.
- The sidebar should therefore be shared across windows in the same session wherever possible.

## 12. Agent lifecycle ownership
- The general rule should be that the component that opens an agent is also responsible for closing it.
- In other words, if the windowing system launches an agent, it should also be responsible for shutting that agent down.
- This simplifies ownership because the component that creates the terminal context can also tear it down.
- An alternative model is that an agent may be launched by some other component, and the startup event attaches the new agent to the relevant tmux window or session.
- In that model, the component that created the agent would remain responsible for closing it.
- This alternative should be investigated for feasibility.
- A decision should be made on who owns agent creation and teardown, because this responsibility should not be left ambiguous.
- The windowing system should not be responsible for creating agents in a way that makes lifecycle ownership unclear.
