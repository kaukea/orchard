#!/usr/bin/env python3
"""Parse + lint the slim-index board (docs/TODO.md) against AGENTS.files.md §TODO.

The single deterministic reader of the board: extracts the badge/title/edges the
staleness walk and blooming need, and validates the format + glossary. Vocabulary is
sourced from ARCHITECTURE.md → Taxonomy (single source). Exit 0 = clean, 1 = errors.

Usage: python3 .claude/tools/board_lint.py [--json]
"""
import re, sys, os, json

def find_root() -> str:
    """Walk up from this file until the board is found — works from the source
    location (repo/tools/) and the vendored one (repo/.claude/tools/) alike."""
    d = os.path.dirname(os.path.abspath(__file__))
    while d != os.path.dirname(d):
        if os.path.exists(os.path.join(d, 'docs/TODO.md')):
            return d
        d = os.path.dirname(d)
    sys.exit("board_lint: no docs/TODO.md above " + __file__)


ROOT = find_root()
BOARD = os.path.join(ROOT, 'docs/TODO.md')
SIDECARS = os.path.join(ROOT, 'docs/TODO.md.d')
ARCH = os.path.join(ROOT, 'ARCHITECTURE.md')

TYPES = {'bug', 'feature', 'refactor', 'housekeeping', 'completion'}
STATUSES = {'todo', 'functional', 'done', 'cancelled'}
STAGES = {'queued', 'working', 'blocked-on-answers', 'plan-ready', 'complete'}
ORIGINS = {'interactive', 'autonomous'}
URGENCIES = {'', 'critical', 'nice-to-have', 'idea'}


def load_glossary():
    """functionality -> set(components), from the ARCHITECTURE.md Taxonomy table.

    None when the repository has no ARCHITECTURE.md: not every project has an
    architecture to describe (a repo that only analyses crashes has none), and
    the board must still lint. Areas are then required to be empty."""
    if not os.path.exists(ARCH):
        return None
    gloss, in_tax, in_table = {}, False, False
    for line in open(ARCH):
        if line.startswith('## '):
            in_tax = line.strip() == '## Taxonomy'
            continue
        if in_tax and line.lstrip().startswith('|'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if len(cells) != 2 or set(cells[0]) <= {'-', ' '}:
                in_table = True
                continue
            if in_table:
                fn = re.match(r'\*\*([A-Za-z][A-Za-z-]*)\*\*', cells[0])
                if not fn:
                    continue
                # components: ·-separated tokens, each optionally bold, ignore "(was X)" notes
                names = []
                for c in re.split(r'\s*·\s*', cells[1]):
                    m = re.match(r'\*{0,2}([a-zA-Z][a-zA-Z-]*)', c.strip())
                    if m:
                        names.append(m.group(1))
                gloss[fn.group(1)] = set(names)
    return gloss


def parse_board():
    """Yield task dicts: id, fn, depth, badge fields, edges, raw line no."""
    fn = None
    tasks = []
    for n, line in enumerate(open(BOARD), 1):
        h = re.match(r'^## (\S+)', line)
        if h:
            fn = h.group(1)
            continue
        m = re.match(r'^(\s*)- `([^`]*)`\s*\[(.*?)\]\((TODO\.md\.d/([a-z0-9-]+)\.md)\)(.*)$', line)
        if not m:
            continue
        indent, badge, title, url, tid, rest = m.groups()
        fields = [f.strip() for f in badge.split('·')]
        edges_bl = re.findall(r'⊘([a-z0-9-]+)', rest)
        edges_rel = re.findall(r'~([a-z0-9-]+)', rest)
        tasks.append(dict(line=n, id=tid, fn=fn, depth=len(indent) // 2, title=title,
                          fields=fields, blocked_by=edges_bl, related=edges_rel))
    return tasks


def main():
    gloss = load_glossary()
    tasks = parse_board()
    ids = {t['id'] for t in tasks}
    errors = []
    # parent = the nearest task at depth-1 above (nesting); leaf = has no children
    has_child = set()
    stack = {}
    for t in tasks:
        stack[t['depth']] = t['id']
        if t['depth'] > 0:
            has_child.add(stack.get(t['depth'] - 1))
    for t in tasks:
        tid, f = t['id'], t['fields']
        if len(f) != 6:
            errors.append(f"{tid}: badge has {len(f)} fields, want 6"); continue
        typ, status, urg, ready, comp, gh = f
        if typ not in TYPES: errors.append(f"{tid}: bad type {typ!r}")
        if status not in STATUSES: errors.append(f"{tid}: bad status {status!r}")
        if urg not in URGENCIES: errors.append(f"{tid}: bad urgency {urg!r}")
        stage = ready.split('/')[0]
        origin = ready.split('/')[1] if '/' in ready else ''
        if stage not in STAGES: errors.append(f"{tid}: bad stage {stage!r}")
        if origin and origin not in ORIGINS: errors.append(f"{tid}: bad origin {origin!r}")
        if gh and not re.match(r'gh#\d+$', gh): errors.append(f"{tid}: bad gh# {gh!r}")
        is_leaf = tid not in has_child
        if gloss is None:
            if comp:
                errors.append(f"{tid}: area {comp!r} but this repo has no ARCHITECTURE.md Taxonomy")
        elif is_leaf:
            if t['fn'] not in gloss or comp not in gloss.get(t['fn'], set()):
                errors.append(f"{tid}: area {comp!r} not in {t['fn']} taxonomy")
        elif comp:
            errors.append(f"{tid}: spanning parent must have empty component, got {comp!r}")
        if not os.path.exists(os.path.join(SIDECARS, tid + '.md')):
            errors.append(f"{tid}: sidecar file missing")
        for b in t['blocked_by']:
            if b not in ids: errors.append(f"{tid}: blocked_by {b} unresolved")
        for r in t['related']:
            if r not in ids: errors.append(f"{tid}: related {r} unresolved")

    if '--json' in sys.argv:
        print(json.dumps([{k: t[k] for k in ('id', 'fn', 'depth', 'fields',
              'blocked_by', 'related')} for t in tasks], indent=1))
    taxonomy = "no ARCHITECTURE.md" if gloss is None else f"{len(gloss)} functionalities"
    print(f"board: {len(tasks)} tasks, {taxonomy}, {len(errors)} errors",
          file=sys.stderr)
    for e in errors:
        print(f"  ! {e}", file=sys.stderr)
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
