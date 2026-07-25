#!/usr/bin/env python3
"""git-date staleness walk over the board — the `make`-style blooming check.

A parked, bloomable task is STALE when a hard dependency's sidecar was committed more
recently than the task's own sidecar: `max(commit-date of parent + blocked_by) > commit-date
of this task's sidecar`. Pure git, zero model tokens. `related` edges are soft (excluded).
Decisions are out of the graph for now (§Sidecar staleness-walk finding).

Bloomable = a parked task (status todo|functional; done/cancelled are terminal).

Usage:
  python3 .claude/tools/board_stale.py [--n N] [--json]
     list the N stalest bloomable tasks (default: all stale, stalest first)
  python3 .claude/tools/board_stale.py --since <sha>
     list bloomable tasks whose sidecar OR a hard dep changed since <sha>
     (the gardener's change-signal cue)
"""
import re, os, sys, json, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BOARD = os.path.join(ROOT, 'docs/TODO.md')
SC = 'docs/TODO.md.d'
BLOOMABLE = {'todo', 'functional'}


def commit_ct(relpath):
    """Unix commit time of the last commit touching relpath; 0 if untracked/never."""
    r = subprocess.run(['git', '-C', ROOT, 'log', '-1', '--format=%ct', '--', relpath],
                       capture_output=True, text=True)
    out = r.stdout.strip()
    return int(out) if out else 0


def changed_since(relpath, sha):
    r = subprocess.run(['git', '-C', ROOT, 'log', '--oneline', f'{sha}..HEAD', '--', relpath],
                       capture_output=True, text=True)
    return bool(r.stdout.strip())


def parse_board():
    fn = None
    tasks = []
    stack = {}
    for line in open(BOARD):
        h = re.match(r'^## (\S+)', line)
        if h:
            fn = h.group(1); continue
        m = re.match(r'^(\s*)- `([^`]*)`\s*\[.*?\]\(TODO\.md\.d/([a-z0-9-]+)\.md\)(.*)$', line)
        if not m:
            continue
        indent, badge, tid, rest = m.groups()
        depth = len(indent) // 2
        stack[depth] = tid
        parent = stack.get(depth - 1) if depth else None
        f = [x.strip() for x in badge.split('·')]
        status = f[1] if len(f) > 1 else ''
        tasks.append(dict(id=tid, fn=fn, status=status, parent=parent,
                          blocked_by=re.findall(r'⊘([a-z0-9-]+)', rest)))
    return tasks


def main():
    tasks = parse_board()
    by_id = {t['id']: t for t in tasks}
    args = sys.argv[1:]
    since = None
    if '--since' in args:
        since = args[args.index('--since') + 1]
    n = None
    if '--n' in args:
        n = int(args[args.index('--n') + 1])

    rows = []
    for t in tasks:
        if t['status'] not in BLOOMABLE:
            continue
        own_rel = f"{SC}/{t['id']}.md"
        deps = [d for d in ([t['parent']] if t['parent'] else []) + t['blocked_by'] if d in by_id]
        if since is not None:
            hit = changed_since(own_rel, since) or any(
                changed_since(f"{SC}/{d}.md", since) for d in deps)
            if hit:
                rows.append((t['id'], t['fn'], 'changed'))
            continue
        own = commit_ct(own_rel)
        dep_ct = max([commit_ct(f"{SC}/{d}.md") for d in deps], default=0)
        if dep_ct > own:
            rows.append((t['id'], t['fn'], dep_ct - own))

    if since is None:
        rows.sort(key=lambda r: r[2], reverse=True)
        if n:
            rows = rows[:n]

    if '--json' in args:
        print(json.dumps([{'id': i, 'fn': f, 'stale_by_s': s} for i, f, s in rows], indent=1))
    else:
        label = 'changed since ' + since if since else 'stale (stalest first)'
        print(f"# {len(rows)} bloomable tasks {label}")
        for i, f, s in rows:
            extra = '' if since else f"  (+{s // 86400}d{(s % 86400) // 3600}h behind dep)"
            print(f"  {f:12} {i}{extra}")


if __name__ == '__main__':
    main()
