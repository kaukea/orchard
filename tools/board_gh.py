#!/usr/bin/env python3
"""Two-way sync between a repo's board (docs/TODO.md + sidecars) and GitHub.

Files are canonical. `push` projects active tasks as issues (gh# written back
onto the badge) and as rows of the user-level Project; `pull` ingests
GitHub-born changes (new issues -> sidecar stubs + board lines, issues closed
on GitHub -> board status) before files rule again.

Usage:
  board_gh.py push [--repo-root PATH] [--no-project]
  board_gh.py pull [--repo-root PATH]

Requires: gh CLI authenticated; the `project` scope for Project operations.
"""

import argparse
import json
import re
import subprocess
from datetime import date
from pathlib import Path

PROJECT_TITLE = "Orchidarium"
PROJECT_OWNER = "serialseb"
ACTIVE = {"todo", "doing", "blocked", "paused"}
CLOSED = {"done", "functional", "cancelled"}
LINE_RE = re.compile(
    r"^(?P<indent>\s*)- `(?P<badge>[^`]*)` \[(?P<title>.+?)\]"
    r"\((?P<path>TODO\.md\.d/[\w-]+\.md)\)(?P<edges>.*)$"
)

# Label vocabulary — mirror of AGENTS.files.md §TODO (single source there).
LABEL_DEFS = {
    "board":              ("6f42c1", "Projected from the file board"),
    "\u2728 feature":     ("1d76db", "additive capability"),
    "\U0001f41b bug":     ("d73a4a", "corrective work"),
    "\u267b\ufe0f refactor": ("cfd3d7", "restructure, no behaviour change"),
    "\U0001f9f9 housekeeping": ("bfdadc", "cleanup, removal, doc tidy"),
    "\U0001f3c1 completion": ("c2e0c6", "takes a functional feature to done"),
    "\U0001f525 critical": ("b60205", "urgency: critical"),
    "\U0001f352 nice-to-have": ("fef2c0", "urgency: nice to have"),
    "\U0001f4ad idea":    ("fbca04", "urgency: idea (daydream)"),
    "\u2699\ufe0f area/process": ("0e8a16", "area: process machinery"),
    "\U0001f504 area/sync": ("5319e7", "area: sync / distribution"),
    "\U0001f393 area/skills": ("0052cc", "area: skills"),
    "\U0001f4e2 area/publication": ("006b75", "area: publication"),
    "\U0001f4cb todo":    ("ededed", "progress: not started"),
    "\U0001f6a7 doing":   ("f9d0c4", "progress: being built"),
    "\u2705 done":        ("0e8a16", "progress: done or functional"),
    "\u26d4 blocked":     ("000000", "blocked by another open task"),
    "\u26fd\U0001f918 madmax": ("e99695", "runs unrestricted (operator-set only)"),
    "\u2601\ufe0f cloud": ("c5def5", "was built in the cloud"),
    "\U0001f6f0\ufe0f analyzable": ("bfd4f2", "can go to the cloud"),
    "\U0001f6cb\ufe0f house-bound": ("d4c5f9", "local-only from inception"),
}
TYPE_LABELS = {"feature": "\u2728 feature", "bug": "\U0001f41b bug",
               "refactor": "\u267b\ufe0f refactor",
               "housekeeping": "\U0001f9f9 housekeeping",
               "completion": "\U0001f3c1 completion"}
TYPE_ISSUE_TYPES = {"bug": "Bug", "feature": "Feature", "refactor": "Refactor",
                     "housekeeping": "Housekeeping", "completion": "Completion",
                     "decision": "Decision"}
URGENCY_LABELS = {"critical": "\U0001f525 critical",
                  "nice-to-have": "\U0001f352 nice-to-have",
                  "idea": "\U0001f4ad idea"}
URGENCY_PRIORITY = {"": "Medium", "critical": "Urgent", "nice-to-have": "Low",
                     "idea": "Low"}
AREA_LABELS = {"process": "\u2699\ufe0f area/process", "sync": "\U0001f504 area/sync",
               "skills": "\U0001f393 area/skills",
               "publication": "\U0001f4e2 area/publication"}
TAG_LABELS = {"madmax": "\u26fd\U0001f918 madmax", "cloud": "\u2601\ufe0f cloud",
              "analyzable": "\U0001f6f0\ufe0f analyzable",
              "house-bound": "\U0001f6cb\ufe0f house-bound"}


def sh(*args, check=True):
    r = subprocess.run(args, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def gh_json(*args):
    out = sh("gh", *args)
    return json.loads(out) if out.strip() else None


class Task:
    def __init__(self, idx: int, m: re.Match):
        self.idx, self.title, self.path, self.edges = \
            idx, m["title"], m["path"], m["edges"]
        self.depth = len(m["indent"]) // 2
        self.blocked_by = re.findall(r"\u2298([a-z0-9-]+)", self.edges)
        self.related = re.findall(r"~([a-z0-9-]+)", self.edges)
        self.tags = re.findall(r"#([a-z0-9-]+)", self.edges)
        self.children = []
        parts = [p.strip() for p in m["badge"].split("·")]
        parts += [""] * (6 - len(parts))
        (self.type, self.status, self.urgency,
         self.readiness, self.component, gh) = parts[:6]
        self.gh = int(gh[3:]) if gh.startswith("gh#") else None

    def line(self) -> str:
        gh = f"gh#{self.gh}" if self.gh else ""
        badge = " · ".join([self.type, self.status, self.urgency,
                            self.readiness, self.component, gh])
        badge = re.sub("  +", " ", badge).rstrip()
        return f"{'  ' * self.depth}- `{badge}` [{self.title}]({self.path}){self.edges}"


class Board:
    def __init__(self, root: Path):
        self.root = root
        self.todo = root / "docs" / "TODO.md"
        self.lines = self.todo.read_text().splitlines()
        self.repo = self._detect_repo()

    def _detect_repo(self):
        url = sh("git", "-C", str(self.root), "remote", "get-url", "origin").strip()
        m = re.search(r"github\.com[:/]([^/]+/.+?)(?:\.git)?/?$", url)
        if not m:
            raise RuntimeError(f"cannot derive owner/repo from origin '{url}'")
        return m.group(1)

    def tasks(self):
        out, stack = [], {}
        for i, line in enumerate(self.lines):
            m = LINE_RE.match(line)
            if not m:
                continue
            t = Task(i, m)
            stack[t.depth] = t
            parent = stack.get(t.depth - 1)
            if t.depth > 0 and parent:
                parent.children.append(t)
            out.append(t)
        return out

    def write(self, task: Task):
        self.lines[task.idx] = task.line()

    def append_line(self, line: str):
        while self.lines and not self.lines[-1].strip():
            self.lines.pop()
        self.lines.append(line)

    def save(self):
        self.todo.write_text("\n".join(self.lines) + "\n")


def sidecar_questions(root: Path, rel: str) -> str:
    p = root / "docs" / rel
    if not p.exists():
        return ""
    m = re.search(r"## Questions\n(.*?)(?=\n## |\Z)", p.read_text(), re.S)
    return m.group(1).strip() if m else ""


def issue_body(board: Board, t: Task, by_id: dict) -> str:
    lines = [
        f"`{t.type} · {t.status} · {t.urgency or '—'} · "
        f"{t.readiness} · {t.component or '—'}`",
        "",
        f"Source of truth: `docs/{t.path}` — this issue is a projection; "
        "edits here are ingested at the next sync, then the board rules.",
    ]
    q = sidecar_questions(board.root, t.path)
    if q and q.lower().strip("- .") not in {"none", "none known yet"}:
        lines += ["", "### Open questions", q]
    if t.children:
        subs = [f"- {'#' + str(c.gh) if c.gh else c.title}" for c in t.children]
        lines += ["", "### Sub-tasks"] + subs
    if t.related:
        rel = [by_id[r] for r in t.related if r in by_id]
        if rel:
            links = [f"- {'#' + str(r.gh) if r.gh else r.title}" for r in rel]
            lines += ["", "### Related"] + links
    return "\n".join(lines)


def list_board_issues(repo: str, state="all"):
    return gh_json("issue", "list", "-R", repo, "--state", state,
                   "--label", "board", "--limit", "500",
                   "--json", "number,title,state,body,url") or []


def ensure_labels(repo: str):
    for name, (color, desc) in LABEL_DEFS.items():
        subprocess.run(["gh", "label", "create", name, "-R", repo,
                        "-c", f"#{color}", "-d", desc, "--force"],
                       capture_output=True, text=True)


def labels_for(t: Task, by_id: dict) -> list:
    labels = ["board"]
    if t.type in TYPE_LABELS:
        labels.append(TYPE_LABELS[t.type])
    if t.urgency in URGENCY_LABELS:
        labels.append(URGENCY_LABELS[t.urgency])
    if t.component in AREA_LABELS:
        labels.append(AREA_LABELS[t.component])
    if t.status in ("done", "functional"):
        labels.append("\u2705 done")
    elif t.readiness.split("/")[0] == "working":
        labels.append("\U0001f6a7 doing")
    else:
        labels.append("\U0001f4cb todo")
    if any(b in by_id and by_id[b].status not in ("done", "cancelled")
           for b in t.blocked_by):
        labels.append("\u26d4 blocked")
    labels += [TAG_LABELS[tag] for tag in t.tags if tag in TAG_LABELS]
    return labels


def set_labels(repo: str, number: int, labels: list):
    args = ["api", "-X", "PUT", f"repos/{repo}/issues/{number}/labels"]
    for l in labels:
        args += ["-f", f"labels[]={l}"]
    gh_json(*args)


def push(board: Board, with_project: bool):
    ensure_labels(board.repo)
    existing = {i["number"]: i for i in list_board_issues(board.repo)}
    tasks = board.tasks()
    by_id = {t.path.split("/")[-1][:-3]: t for t in tasks}
    created, updated, closed = 0, 0, 0
    # pass 1 — every active task gets an issue (children included), so pass 2
    # can link parents to child issue numbers.
    for t in tasks:
        if t.status in ACTIVE and t.gh is None:
            out = sh("gh", "issue", "create", "-R", board.repo,
                     "--title", t.title, "--label", "board",
                     "--body", "(projecting\u2026)")
            t.gh = int(out.strip().rsplit("/", 1)[1])
            board.write(t)
            created += 1
    # pass 2 — bodies, labels, state.
    for t in tasks:
        if t.gh is None:
            continue
        if t.status in ACTIVE:
            body = issue_body(board, t, by_id)
            issue = existing.get(t.gh)
            if issue is None or issue["body"] != body or issue["title"] != t.title:
                sh("gh", "issue", "edit", "-R", board.repo, str(t.gh),
                   "--title", t.title, "--body", body)
                if issue is not None:
                    updated += 1
            set_labels(board.repo, t.gh, labels_for(t, by_id))
            if issue is not None and issue["state"] != "OPEN":
                sh("gh", "issue", "reopen", "-R", board.repo, str(t.gh))
        elif t.status in CLOSED and t.gh in existing:
            issue = existing[t.gh]
            set_labels(board.repo, t.gh, labels_for(t, by_id))
            if issue["state"] == "OPEN":
                sh("gh", "issue", "close", "-R", board.repo, str(t.gh),
                   "-c", f"Board: task reached `{t.status}`.")
                closed += 1
    board.save()
    sync_issue_types(board)
    sync_priority(board)
    sync_relationships(board, by_id)
    decision_result = sync_decisions(board)
    print(f"push {board.repo}: {created} created, {updated} updated, "
          f"{closed} closed")
    if with_project:
        project_sync(board)
        decision_project_sync(board, decision_result)


# ---------- Projects v2 ----------

def gql(query: str, **vars):
    args = ["api", "graphql", "-f", f"query={query}"]
    for k, v in vars.items():
        args += ["-f", f"{k}={v}"]
    return gh_json(*args)


def issue_node_id(repo: str, number: int) -> str:
    return gql("""query($u:URI!){resource(url:$u){... on Issue{id}}}""",
               u=f"https://github.com/{repo}/issues/{number}"
               )["data"]["resource"]["id"]


# ---------- Issue Types (org-level) ----------

def owner_is_organization(owner: str) -> bool:
    data = gql("""query($login:String!){repositoryOwner(login:$login){
        __typename}}""", login=owner)["data"]["repositoryOwner"]
    return data is not None and data["__typename"] == "Organization"


def ensure_issue_types(org: str) -> dict:
    data = gql("""query($login:String!){organization(login:$login){id
        issueTypes(first:50){nodes{id name}}}}""", login=org)["data"]["organization"]
    have = {n["name"]: n["id"] for n in data["issueTypes"]["nodes"]}
    for name in TYPE_ISSUE_TYPES.values():
        if name in have:
            continue
        gql("""mutation($owner:ID!,$name:String!){createIssueType(input:{
            ownerId:$owner,name:$name,isEnabled:true}){clientMutationId}}""",
            owner=data["id"], name=name)
    data = gql("""query($login:String!){organization(login:$login){
        issueTypes(first:50){nodes{id name}}}}""", login=org)["data"]["organization"]
    return {n["name"]: n["id"] for n in data["issueTypes"]["nodes"]}


def set_issue_type(issue_id: str, issue_type_id: str):
    gql("""mutation($i:ID!,$t:ID!){updateIssueIssueType(input:{
        issueId:$i,issueTypeId:$t}){clientMutationId}}""", i=issue_id, t=issue_type_id)


def sync_issue_types(board: Board):
    org = board.repo.split("/")[0]
    if not owner_is_organization(org):
        return
    issue_types = ensure_issue_types(org)
    for t in board.tasks():
        if t.gh is None or t.status not in ACTIVE or t.type not in TYPE_ISSUE_TYPES:
            continue
        native = TYPE_ISSUE_TYPES[t.type]
        if native not in issue_types:
            continue
        node_id = issue_node_id(board.repo, t.gh)
        set_issue_type(node_id, issue_types[native])


# ---------- Priority (org-level native issue field) ----------

def priority_field(org: str) -> dict:
    data = gql("""query($login:String!){organization(login:$login){
        issueFields(first:20){nodes{... on IssueFieldSingleSelect{
        id name options{id name}}}}}}""", login=org)["data"]["organization"]
    for f in data["issueFields"]["nodes"]:
        if f and f.get("name") == "Priority":
            return f
    raise RuntimeError(f"org '{org}' has no native 'Priority' issue field — "
                        "expected one to already exist (see Decision-051)")


def set_priority(issue_id: str, field_id: str, option_id: str):
    gql("""mutation($i:ID!,$f:ID!,$o:ID!){setIssueFieldValue(input:{
        issueId:$i,issueFields:[{fieldId:$f,singleSelectOptionId:$o}]}){
        clientMutationId}}""", i=issue_id, f=field_id, o=option_id)


def sync_priority(board: Board):
    org = board.repo.split("/")[0]
    if not owner_is_organization(org):
        return
    field = priority_field(org)
    options = {o["name"]: o["id"] for o in field["options"]}
    for t in board.tasks():
        if t.gh is None or t.status not in ACTIVE:
            continue
        native = URGENCY_PRIORITY.get(t.urgency)
        if native is None or native not in options:
            continue
        node_id = issue_node_id(board.repo, t.gh)
        set_priority(node_id, field["id"], options[native])


# ---------- Relationships (native blocked-by / blocking) ----------

def blocked_by_ids(issue_node_id_: str) -> set:
    data = gql("""query($id:ID!){node(id:$id){... on Issue{
        blockedBy(first:50){nodes{number}}}}}""", id=issue_node_id_)
    return {n["number"] for n in data["data"]["node"]["blockedBy"]["nodes"]}


def sync_relationships(board: Board, by_id: dict):
    for t in board.tasks():
        if t.gh is None or t.status not in ACTIVE:
            continue
        desired = {by_id[b].gh for b in t.blocked_by
                   if b in by_id and by_id[b].gh is not None}
        node_id = issue_node_id(board.repo, t.gh)
        current = blocked_by_ids(node_id)
        for gh_num in desired - current:
            gql("""mutation($i:ID!,$b:ID!){addBlockedBy(input:{
                issueId:$i,blockingIssueId:$b}){clientMutationId}}""",
                i=node_id, b=issue_node_id(board.repo, gh_num))
        for gh_num in current - desired:
            gql("""mutation($i:ID!,$b:ID!){removeBlockedBy(input:{
                issueId:$i,blockingIssueId:$b}){clientMutationId}}""",
                i=node_id, b=issue_node_id(board.repo, gh_num))


FIELDS_QUERY = """query($id:ID!){node(id:$id){... on ProjectV2{
  fields(first:50){nodes{... on ProjectV2FieldCommon{id name}
  ... on ProjectV2SingleSelectField{id name options{id name}}}}}}}"""

SELECT_FIELDS = {
    "Status": ["todo", "functional", "done", "cancelled"],
    "Urgency": ["critical", "nice-to-have", "idea"],
    "Readiness": ["queued", "working", "blocked-on-answers", "plan-ready",
                  "complete"],
}
TEXT_FIELDS = ["Area", "Decision Number", "Decision Title"]


def ensure_project():
    data = gql("""query($login:String!){user(login:$login){
        projectsV2(first:50){nodes{id title number}}}}""", login=PROJECT_OWNER)
    for p in data["data"]["user"]["projectsV2"]["nodes"]:
        if p["title"] == PROJECT_TITLE:
            return p
    owner = gql("query($login:String!){user(login:$login){id}}",
                login=PROJECT_OWNER)["data"]["user"]["id"]
    made = gql("""mutation($owner:ID!,$title:String!){
        createProjectV2(input:{ownerId:$owner,title:$title}){
        projectV2{id title number}}}""", owner=owner, title=PROJECT_TITLE)
    return made["data"]["createProjectV2"]["projectV2"]


def ensure_fields(project_id: str):
    have = {f["name"] for f in
            gql(FIELDS_QUERY, id=project_id)["data"]["node"]["fields"]["nodes"]
            if f}
    for name, opts in SELECT_FIELDS.items():
        if name in have:
            continue
        opts_gql = ",".join(
            '{name:"%s",color:GRAY,description:""}' % o for o in opts)
        gql("""mutation($id:ID!){createProjectV2Field(input:{projectId:$id,
            dataType:SINGLE_SELECT,name:"%s",singleSelectOptions:[%s]})
            {clientMutationId}}""" % (name, opts_gql), id=project_id)
    for name in TEXT_FIELDS:
        if name not in have:
            gql("""mutation($id:ID!){createProjectV2Field(input:{projectId:$id,
                dataType:TEXT,name:"%s"}){clientMutationId}}""" % name,
                id=project_id)
    return {f["name"]: f for f in
            gql(FIELDS_QUERY, id=project_id)["data"]["node"]["fields"]["nodes"]
            if f}


def project_items(project_id: str):
    items, cursor = {}, None
    while True:
        data = gql("""query($id:ID!,$after:String){node(id:$id){
            ... on ProjectV2{items(first:100,after:$after){
            pageInfo{hasNextPage endCursor}
            nodes{id content{... on Issue{url}}}}}}}""",
            id=project_id, after=cursor or "")
        page = data["data"]["node"]["items"]
        for n in page["nodes"]:
            if n["content"]:
                items[n["content"]["url"]] = n["id"]
        if not page["pageInfo"]["hasNextPage"]:
            return items
        cursor = page["pageInfo"]["endCursor"]


def set_field(project_id, item_id, field, value):
    if "options" in field:
        opt = next((o["id"] for o in field["options"]
                    if o["name"] == value), None)
        if not opt:
            return
        val = '{singleSelectOptionId:"%s"}' % opt
    else:
        val = '{text:"%s"}' % value
    gql("""mutation($p:ID!,$i:ID!,$f:ID!){updateProjectV2ItemFieldValue(
        input:{projectId:$p,itemId:$i,fieldId:$f,value:%s})
        {clientMutationId}}""" % val,
        p=project_id, i=item_id, f=field["id"])


def project_sync(board: Board):
    project = ensure_project()
    fields = ensure_fields(project["id"])
    items = project_items(project["id"])
    issues = {i["number"]: i for i in list_board_issues(board.repo)}
    n = 0
    for t in board.tasks():
        if t.gh is None or t.status not in ACTIVE or t.gh not in issues:
            continue
        url = issues[t.gh]["url"]
        item_id = items.get(url)
        if not item_id:
            node = gql("query($u:URI!){resource(url:$u){... on Issue{id}}}",
                       u=url)["data"]["resource"]["id"]
            item_id = gql("""mutation($p:ID!,$c:ID!){addProjectV2ItemById(
                input:{projectId:$p,contentId:$c}){item{id}}}""",
                p=project["id"], c=node
                )["data"]["addProjectV2ItemById"]["item"]["id"]
        set_field(project["id"], item_id, fields["Status"], t.status)
        if t.urgency:
            set_field(project["id"], item_id, fields["Urgency"], t.urgency)
        stage = t.readiness.split("/")[0]
        if stage:
            set_field(project["id"], item_id, fields["Readiness"], stage)
        if t.component:
            set_field(project["id"], item_id, fields["Component"], t.component)
        n += 1
    print(f"project {PROJECT_TITLE}: {n} rows ensured for {board.repo}")


# ---------- pull ----------

STUB = """- created: {today}
- created_by: gh-ingest
- created_during: interactive

## Blockers
- None known yet.

## Questions
- Ingested from GitHub issue #{num} — needs triage: type, component,
  urgency, scope.

## Findings
- Filed on GitHub ({url}); original body preserved below.

{body}
"""


def slugify(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s[:48] or "gh-task"


def pull(board: Board):
    tasks = board.tasks()
    by_gh = {t.gh: t for t in tasks if t.gh is not None}
    closed_from_gh, ingested = 0, 0
    for issue in list_board_issues(board.repo):
        t = by_gh.get(issue["number"])
        if t and t.status in ACTIVE and issue["state"] != "OPEN":
            t.status = "done"
            board.write(t)
            closed_from_gh += 1
    all_open = gh_json("issue", "list", "-R", board.repo, "--state", "open",
                       "--limit", "500",
                       "--json", "number,title,body,url,labels") or []
    for issue in all_open:
        if issue["number"] in by_gh:
            continue
        # already board-labelled but unknown here = a projection in flight
        # (gh# commit not yet visible to this checkout) — never re-ingest
        if any(l["name"] == "board" for l in issue["labels"]):
            continue
        # decision mirrors are board-born, never intake — the title is their
        # stateless identity (Decision-067); belt for mirrors that predate
        # the board label riding decision issues
        if DECISION_ISSUE_TITLE_RE.match(issue["title"]):
            continue
        slug = slugify(issue["title"])
        sidecar = board.root / "docs" / "TODO.md.d" / f"{slug}.md"
        if sidecar.exists():
            slug = f"{slug}-gh{issue['number']}"
            sidecar = board.root / "docs" / "TODO.md.d" / f"{slug}.md"
        sidecar.write_text(STUB.format(
            today=date.today().isoformat(), num=issue["number"],
            url=issue["url"], body=issue["body"] or "(no body)"))
        board.append_line(
            f"- `feature · todo · · queued · · gh#{issue['number']}` "
            f"[{issue['title']}](TODO.md.d/{slug}.md)")
        ensure_labels(board.repo)
        sh("gh", "issue", "edit", "-R", board.repo, str(issue["number"]),
           "--add-label", "board")
        ingested += 1
    board.save()
    print(f"pull {board.repo}: {ingested} ingested, "
          f"{closed_from_gh} closed-from-GitHub")


# ---------- Decisions ----------

DECISION_HEADING_RE = re.compile(
    r"^## (?P<struck>~~)?\[.+?\] Decision-(?P<number>\d+): "
    r"(?P<title>.+?)(?(struck)~~)$"
)
SUPERSEDED_RE = re.compile(r"^> Superseded by Decision-(\d+)\b")
HASHTAG_RE = re.compile(r"#([\w-]+)")


class DecisionEntry:
    def __init__(self, number: str, title: str, struck: bool,
                 superseded_by, hashtags: list, body: str):
        self.number = number
        self.title = title
        self.struck = struck
        self.superseded_by = superseded_by
        self.hashtags = hashtags
        self.body = body


def _parse_decision_block(heading: re.Match, block_lines: list) -> DecisionEntry:
    struck = heading["struck"] is not None
    superseded_by = None
    hashtags = []
    for line in block_lines:
        m = SUPERSEDED_RE.match(line)
        if m:
            superseded_by = m.group(1)
        if line.startswith("#") and not hashtags:
            hashtags = HASHTAG_RE.findall(line)
    body = "\n".join(block_lines).strip("\n")
    return DecisionEntry(
        number=heading["number"], title=heading["title"], struck=struck,
        superseded_by=superseded_by, hashtags=hashtags, body=body,
    )


def parse_decisions(path: Path) -> list:
    lines = path.read_text().splitlines()
    entries = []
    heading, block = None, []
    for line in lines:
        m = DECISION_HEADING_RE.match(line)
        if m:
            if heading is not None:
                entries.append(_parse_decision_block(heading, block))
            heading, block = m, []
        elif heading is not None:
            block.append(line)
    if heading is not None:
        entries.append(_parse_decision_block(heading, block))
    return entries


DECISION_ISSUE_TITLE_RE = re.compile(r"^Decision-(\d+): ")


def list_decision_issues(repo: str) -> dict:
    issues = gh_json("issue", "list", "-R", repo, "--search", "Decision- in:title",
                     "--state", "all", "--limit", "500",
                     "--json", "number,title,state,body,labels") or []
    by_number = {}
    for issue in issues:
        m = DECISION_ISSUE_TITLE_RE.match(issue["title"])
        if not m:
            continue
        by_number.setdefault(m.group(1), []).append(issue)
    return by_number


def sync_decisions(board: Board) -> dict:
    org = board.repo.split("/")[0]
    issue_types = ensure_issue_types(org) if owner_is_organization(org) else {}
    decision_type_id = issue_types.get("Decision")
    entries = parse_decisions(board.root / "docs" / "decisions.md")
    existing = list_decision_issues(board.repo)
    state = {}   # number -> {"gh_num": int, "node_id": str, "was_open": bool}
    created = updated = closed = reopened = skipped_ambiguous = 0

    # pass 1: every entry gets an issue (create or update title/body), so
    # every target node id exists before pass 2 needs to reference it for
    # the superseded-by-duplicate close.
    for e in entries:
        matches = existing.get(e.number, [])
        if len(matches) > 1:
            print(f"warn: {len(matches)} issues match title 'Decision-{e.number}:' "
                  "— skipping, resolve manually")
            skipped_ambiguous += 1
            continue
        title = f"Decision-{e.number}: {e.title}"
        if not matches:
            out = sh("gh", "issue", "create", "-R", board.repo,
                     "--title", title, "--label", "board", "--body", e.body)
            gh_num = int(out.strip().rsplit("/", 1)[1])
            was_open = True
            created += 1
        else:
            issue = matches[0]
            gh_num = issue["number"]
            was_open = issue["state"] == "OPEN"
            if issue["title"] != title or issue["body"] != e.body:
                sh("gh", "issue", "edit", "-R", board.repo, str(gh_num),
                   "--title", title, "--body", e.body)
                updated += 1
            # board-born marker: a decision mirror without the board label is
            # what pull() re-ingests as a GitHub-born task (the echo loop)
            if not any(l["name"] == "board" for l in issue.get("labels", [])):
                sh("gh", "issue", "edit", "-R", board.repo, str(gh_num),
                   "--add-label", "board")
        node_id = issue_node_id(board.repo, gh_num)
        state[e.number] = {"gh_num": gh_num, "node_id": node_id, "was_open": was_open}
        if decision_type_id:
            set_issue_type(node_id, decision_type_id)

    # pass 2: open/closed state — struck+superseded closes natively as a
    # duplicate of the superseding decision; everything else stays/reopens.
    for e in entries:
        if e.number not in state:
            continue  # skipped as ambiguous above
        s = state[e.number]
        if e.struck and e.superseded_by:
            target = state.get(e.superseded_by)
            if target is None:
                print(f"warn: Decision-{e.number} superseded by "
                      f"Decision-{e.superseded_by}, but that entry wasn't synced "
                      "this run — leaving open")
                continue
            if s["was_open"]:
                gql("""mutation($i:ID!,$d:ID!){closeIssue(input:{
                    issueId:$i,stateReason:DUPLICATE,duplicateIssueId:$d}){
                    clientMutationId}}""", i=s["node_id"], d=target["node_id"])
                closed += 1
        else:
            if not s["was_open"]:
                sh("gh", "issue", "reopen", "-R", board.repo, str(s["gh_num"]))
                reopened += 1

    print(f"decisions {board.repo}: {created} created, {updated} updated, "
          f"{closed} closed, {reopened} reopened, {skipped_ambiguous} ambiguous-skipped")
    return {"entries": entries, "state": state}


def decision_project_sync(board: Board, sync_result: dict):
    project = ensure_project()
    fields = ensure_fields(project["id"])
    items = project_items(project["id"])
    n = 0
    for e in sync_result["entries"]:
        s = sync_result["state"].get(e.number)
        if s is None:
            continue
        url = f"https://github.com/{board.repo}/issues/{s['gh_num']}"
        item_id = items.get(url)
        if not item_id:
            item_id = gql("""mutation($p:ID!,$c:ID!){addProjectV2ItemById(
                input:{projectId:$p,contentId:$c}){item{id}}}""",
                p=project["id"], c=s["node_id"]
                )["data"]["addProjectV2ItemById"]["item"]["id"]
        set_field(project["id"], item_id, fields["Decision Number"], e.number)
        set_field(project["id"], item_id, fields["Decision Title"], e.title)
        n += 1
    print(f"project {PROJECT_TITLE}: {n} decision rows ensured for {board.repo}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("verb", choices=["push", "pull"])
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--no-project", action="store_true")
    a = ap.parse_args()
    board = Board(Path(a.repo_root).resolve())
    if a.verb == "push":
        push(board, with_project=not a.no_project)
    else:
        pull(board)


if __name__ == "__main__":
    main()
