# 2026-07-25 — fleet roles renamed to orchard names; `bus` transport renamed `courier`

Under Decision-085 every fleet role took an orchard name: orchestrator→gardener,
architect→landscaper, builder→sower, housekeeper→groundskeeper, bus→courier
(bloomer unchanged). This renamed managed artifacts — agent definitions, the
`skills/orchestrator` skill directory, the `bus` hooks/tools — and the per-repo
message-transport state directory `the-works/bus`. `kauk sync` re-vendors the new
names; this migration drops the now-dangling old-name laydowns, converges any
copy/local install, and moves the transport state dir, leaving a transitional
`bus`→`courier` symlink so a session still running on the pre-rename tooling keeps
resolving. `tools/bus.py` remains as a thin shim that execs `courier.py` for one
release, so the old tool path is deliberately NOT removed here.

## Detect → convert
```sh
# 1. Drop dangling old-name laydowns (link-mode installs; kauk sync re-lays new names).
#    NOTE: .claude/tools/bus.py is intentionally kept — it is the transitional shim.
for d in \
  ".claude/agents/orchestrator.md" ".claude/agents/architect.md" \
  ".claude/agents/builder.md" ".claude/agents/housekeeper.md" ".claude/agents/bus.md" \
  ".claude/hooks/bus-init.sh" ".claude/hooks/bus-end.sh" \
  ".claude/tools/architect-teardown.sh" ".claude/skills/orchestrator"; do
  if [ -L "$d" ] && [ ! -e "$d" ]; then rm "$d"; fi
done

# 2. Move the message-transport state dir bus -> courier (per clone), then leave a
#    transitional symlink so a live pre-rename sidecar still resolves the old path.
gcd="$(git rev-parse --git-common-dir 2>/dev/null)"
if [ -n "$gcd" ]; then
  tw="$gcd/the-works"
  if [ -d "$tw/bus" ] && [ ! -L "$tw/bus" ] && [ ! -e "$tw/courier" ]; then
    mv -n "$tw/bus" "$tw/courier"
  fi
  if [ -d "$tw/courier" ] && [ ! -e "$tw/bus" ]; then
    ln -s courier "$tw/bus"
  fi
fi
true
```

## Then: reconcile a copy/local install (judgement)
If any renamed artifact is installed in **copy** or **local** mode (a real file/dir, not
a symlink, per `.ai.toml`), `kauk sync` will not move it. For each such surviving old
path — `.claude/agents/{orchestrator,architect,builder,housekeeper,bus}.md`,
`.claude/hooks/bus-{init,end}.sh`, `.claude/tools/architect-teardown.sh`,
`.claude/skills/orchestrator/` — move any local edits into the new-named path placed by
sync (gardener/landscaper/sower/groundskeeper/courier, `courier-{init,end}.sh`,
`landscaper-teardown.sh`, `skills/gardener/`), remove the old path, and update any
repo-local references (launchers, docs) to the new names. Leave `.claude/tools/bus.py`
in place until the shim is retired.

## Verify
- No dangling old-name symlink remains under `.claude/agents`, `.claude/hooks`,
  `.claude/tools/architect-teardown.sh`, or `.claude/skills/orchestrator`.
- The new-named artifacts resolve (`.claude/agents/gardener.md`, `…/courier.md`,
  `.claude/hooks/courier-init.sh`, `.claude/tools/courier.py`, `.claude/skills/gardener/`).
- `$(git rev-parse --git-common-dir)/the-works/courier/` holds the message inboxes;
  `…/the-works/bus` is either gone or a symlink to `courier`.
- `.claude/tools/bus.py` (the transitional shim) still execs `courier.py`.
