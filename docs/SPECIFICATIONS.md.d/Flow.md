# Flow v4

## Principles
- The component that creates something on starting cleans it up on cleaning. No agent or process should go and clean up what was created by another component (Encupsulation)

## Agents

### Gardener
**responsible for the WHAT**
 - Knows about all pending tasks
 - Understansd blocked and parent/child relationships
 - Suggests next tasks to users
 - Keep trackof high level functional specifications to avoid overlapping work and enable work in order and paralllel work
- Creates new tasks with the user or froun outcomes of discovery in other featurework at ingest time
- Launches the work
- Absorbs the work once the work has returned

### BeeKeeper

**responsible for coordinating the HOW**
 - Knows very little about the tsk
- Knows about the workflow of agents involved (order, handlver)
- knows when to launch the net phase based on the result of the previous phase
- Is resonsinle for letting the gardener know when work has completed and is eady to inhest

## Subagents
### Valve
- Loaded as a side car to agents doing the work, with a different context:
 - Inject in the agent prompt advice, warnings to prevent work drifting from stated goals
 - Judges the work before passing the gates, causing a new round if failure with additional information

### Truss
 - The truss prepares the environment for work to start and is called to launch sub agents based on their posiitoning: background|new|sibling|popup. Depending on a plugin or configuration, SSH, TMUX, GHOSTTY, Kitty, the environment isprepared
based on the capacit of the terminal. Only implementation currently: TMUX
 - Once declared closed, Truss cleans the UI component
 - In future iterations, an SSH version would mostly be noop for example
