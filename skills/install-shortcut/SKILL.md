---
name: install-shortcut
description: Use whenever a built .shortcut must reach the operator's phone — delivering a component or experiment, triggering the on-device installer, or (re)sending the install email. Defines the delivery folders, the email trigger contract, the ONE working send path (local SMTP script), and the send paths that are forbidden because they failed.
categories: [development/file-formats]
metadata:
  tags: [ shortcut, install, installer, deliver, phone, email, trigger, smtp ]
---

# Intent (install-shortcut)

Get a signed `.shortcut` from the Pi onto the operator's phone with two taps and
no re-derivation: file lands in the served FastCut folder, one email triggers the
on-device installer, the operator taps Add. This skill pins the delivery layout,
the trigger contract, and the only send mechanism that works.

## Checklist

- [ ] Artifact delivered to its CORRECT folder (component vs experiment, below)
- [ ] Trigger sent with the LOCAL SMTP SCRIPT — never Thunderbird MCP, never exim
- [ ] Subject AND body are the full `smb://` URL of the artifact
- [ ] ONE send per install — never resend while one is in flight
- [ ] Install validated by the OPERATOR's on-device report, nothing else

## Delivery layout (operator rulings, 2026-08-10)

- Components: `/home/sudoku/backup/FastCut/iCloud/<name>.shortcut` — flat, signed.
- Experiments and test suites: `/home/sudoku/backup/FastCut/experiments/<what-is-being-tested>/<name>.shortcut`.
- ONE self-contained file per experiment and per test suite — **NEVER** a pile of
  imports. Internal structure is the agent's choice; file count is not.

## Trigger contract

Mail to `keepthebot@gmail.com`; a mail automation on the phone runs the installer
with the message as input. Subject = body = the artifact's full URL:
`smb://192.168.168.13/backup/FastCut/<path-relative-to-FastCut>`.

The installer takes the URL's path component, reads the file from the once-picked
FastCut folder, and opens it in Shortcuts. The operator taps Add. There is no
self-report channel in the installer: the agent **CANNOT** observe the install —
only the operator validates it, per his standing rule that only he validates
on-device behaviour.

## Send mechanism

**MUST** use the SMTP sender script in the fastcut repo:
`experiments/installer/send_install_email.py <path-relative-to-FastCut>`.
It authenticates against Gmail with an app password read from
`/home/sudoku/backup-verify/gmail-smtp-credentials.txt` (two lines: account,
app password; created by `store_smtp_credential.sh` beside the sender — rerun it
if auth fails or the password is rotated).

Forbidden paths, each proven broken on 2026-08-11:

- **Local exim/sendmail** — the Pi's exim is configured local-only; every remote
  send bounces `R=nonlocal: Mailing to remote domains not supported` while the
  script reports success.
- **Thunderbird MCP `sendMail`** — returns `"Message sent"` unconditionally.
  Most identities have S/MIME `sign_mail=true`, so sends stall in signature
  prompts that hammer the operator's desktop; the `from` identity override was
  not honored reliably even when naming the unsigned identity. Success reports
  from this tool are worthless: the only proof of a send is the Sent-folder copy
  or the operator saying it arrived — and the Sent copy can lag many minutes.

**NEVER** resend because the sent copy is not visible yet — in-flight and failed
look identical from the Pi; wait for the operator or the Sent copy. One install,
one email (operator order).
