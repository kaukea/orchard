# Digest identity: the telemetry routine publishes as callabloom

- created: 2026-07-22
- created_by: Sebastien Lambla

## Blockers

- None — the callabloom[bot] app identity exists and is live on the cloud path.

## Questions

- ~~Destination?~~ RULED (operator, 2026-07-22): **GitHub Discussions** —
  callabloom posts each digest as a discussion (reuses the existing app;
  no machine-user, no PAT). Discussions ENABLED on the repo the same day
  (default categories present; "Announcements" is the natural reports
  category — maintainer-posted, non-answerable — unless the operator
  prefers a renamed/custom category, which is UI-only to create).
- Route, sharpened by the ruling: the poster must hold a callabloom
  installation token. (a) app private key as a claude.ai cloud-env secret
  — the routine mints and posts directly; (b) the routine hands off (push
  or workflow_dispatch) to a repo Action that already mints callabloom
  tokens on the cloud path and posts the discussion — no secrets leave
  GitHub, analysis stays on the routine's subscription billing. (b) looks
  cleanest; operator to confirm.
- One-time operator step pending: add the **Discussions: Read and write**
  repository permission to the callabloom app and approve the updated
  permissions on the kaukea installation (web-only).

## Findings

- Wiki state verified live (2026-07-22, gardener, operator-sanctioned):
  the wiki EXISTS, is initialized (Home + one page, "Initial Home page"
  commits), and is writable with the operator's local credentials — the
  routine's 403 is purely a CREDENTIAL limitation of the cloud session's
  GitHub grant, not initialization or enablement (has_wiki true).
- Destination hard fact: GitHub wikis accept pushes only from USER
  credentials — GitHub App installation tokens (callabloom) and Actions'
  GITHUB_TOKEN cannot push wiki repos. A wiki destination therefore
  requires a machine-user account + PAT (creation is web-only, operator
  action), and is INCOMPATIBLE with the callabloom-only identity goal;
  PR delivery works with every credential.

- The 2026-07-21 digest (PR #60, opened 2026-07-22T00:11:57Z) was
  published under the operator's own GitHub grant: PR author `serialseb`,
  commit 8fc7c2d author "Claude". The scheduled claude.ai routine pushes
  with the operator's credentials.
- The routine's wiki push returned 403 (permission denied); the PR was its
  fallback delivery.
- To verify during discovery: GitHub App installation tokens are believed
  not to work for wiki git operations (wikis sit outside the App
  permissions model), so switching identity to callabloom likely does NOT
  recover the wiki destination on its own — the wiki would need a machine
  credential of another kind.

## Proposal

The nightly telemetry digest publishes under the callabloom[bot] identity
instead of the operator's personal credentials — no digest artifact
(commit, branch, PR, comment) authored as the operator. The delivery
destination (PR vs wiki vs other) is settled by the Questions above and
becomes part of this task's scope.

## Testing

Observe the next scheduled digest run end-to-end: the digest branch,
commit, and PR are authored by callabloom[bot]; nothing in the run is
authored as the operator; delivery lands at the agreed destination.
