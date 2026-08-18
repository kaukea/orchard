---
name: diagnostics
description: Use whenever something is broken, failing, erroring, or not behaving as expected — for any troubleshooting, debugging, or investigation task. Defines how the model produces diagnostic scripts (one script in `diagnostics/`, paths relative to repo root, streamed output + log file the model reads directly), handles secrets through macOS Keychain, runs code on remote hosts over SSH, keeps system changes reversible, and stops after 5 unsuccessful attempts.
categories: [development]
metadata:
  tags: [diagnostics, troubleshooting, debugging, diagnostic-script, ssh-debug, keychain-secrets, reversible-changes]
  share: github
---

# Diagnostics

How the model investigates failures: one script, streamed to the operator's terminal,
log file the model reads directly when it appears. No "run this then that" sequences.
No "paste-this-and-paste-that-result" ping-pong. No silent system changes.

## Checklist

- [ ] One script generated, placed under `<repo>/diagnostics/`, documented header
- [ ] Script finds the repo root (via `.git/`) and uses repo-root-relative paths
- [ ] Script streams each operation + its result to the terminal as it happens
- [ ] Full log written atomically to a known path when the script completes; model polls
      for the file's appearance and reads it directly
- [ ] No copy-paste micro-exchanges; no "is it finished?" question
- [ ] Any system change is reversible; if an attempt does not solve the problem, the
      model asks whether to revert before the next attempt
- [ ] Secrets retrieved via the platform secret store (macOS Keychain / Linux
      libsecret `secret-tool`); keys documented; setup command shown on a miss
- [ ] Remote SSH execution: script written locally; operator handed exact `scp` + `ssh`
      + run commands via the clipboard
- [ ] After 5 unsuccessful attempts, stop and present alternatives

## Don't ping-pong on copy-paste

The pattern to avoid: "copy this, run it, paste the result back, then copy the next
command, run that, paste that result..." A long sequence of small copy-paste exchanges
costs the operator far more than a single up-front handoff.

- One larger copy-paste once in a while is fine.
- Many small copy-pastes in a row are not.
- The diagnostic-script flow below is the standard replacement: one script the operator
  runs once, streamed to their terminal, logged to a file the model reads directly.

## Clipboard handling

The model puts content into the clipboard when the operator needs to paste it directly
into a terminal or another tool (typically the SSH handoff text).

- Place content into the clipboard using platform-aware tools:
  - macOS: `pbcopy`
  - Linux (X11): `xclip` or `xsel`
  - Linux (Wayland): `wl-copy`
- Terminal escape sequences (e.g. OSC52) MAY be used for portability.
- Always print to stdout as well — the clipboard is an additional channel.
- Treat the clipboard as output only — never assume its contents are valid input.

## Diagnostic scripts

The primary mechanism. One script, run once, streamed to the operator and read by the
model when complete.

- **One script, not steps.** Generate a single script that runs every check the model
  needs. Never issue a "run X, then Y, then Z" sequence.
- **Located under `<repo>/diagnostics/`.** Scripts live in the repository's
  `diagnostics/` directory.
- **Find the repo root.** The script must not assume the operator's working directory.
  Locate the repository root by walking upward until a `.git/` entry is found, then
  use paths relative to that root.
- **Documented header.** Each script declares, at the top of the file: purpose, inputs
  (arguments, environment variables, Keychain keys), expected output, log file path,
  and any side-effects.
- **Stream each operation to the terminal.** As the script runs, print two lines per
  operation: one describing the operation, one describing its result. Live, not
  buffered until the end.
- **Log file is written once, atomically, on completion.** When the script finishes,
  it writes its full output to a temporary file and `mv`s it into place at the
  documented log path. The log file does NOT exist until the script is done. The log
  format is the model's choice.
- **Model polls for the log file's appearance — does not ask.** The model watches the
  documented log path; the file appearing means the script has finished. The model
  then reads it directly. Do not ask the operator "is it finished?".

## System changes

Any change the model makes to the system while diagnosing — OS configuration, code,
configuration files, server state, installed packages, anything — must be reversible.

- Track every change as it is made (commit, snapshot, saved original).
- If an attempt does not solve the problem, ask the operator whether to revert the
  changes from that attempt before moving on. Do not carry changes silently across
  attempts.

## Secrets

The model does not register secret values. Secrets come from the operator's
environment.

- **macOS: Keychain.** Scripts retrieve secrets from Keychain at runtime
  (e.g. `security find-generic-password`).
- **Linux: libsecret.** Scripts retrieve secrets via `secret-tool lookup` where a
  keyring is available; otherwise the operator handles secret operations manually.
- **Other hosts: operator handles manually.** The script does not automate secret
  storage or retrieval there.
- **Document the keys.** The script's header lists the secret-store item names it expects.
- **Show the setup command on a miss.** If a required Keychain item is absent, the
  script prints the operator-side command to add it and exits. The operator runs the
  command manually; re-running the script then succeeds.
- **Never hardcode, never log, never copy a secret.** The model does not place a
  secret value into the script, the log file, the clipboard, or any other artefact.
  The script never executes the add-secret command itself.

## Remote SSH execution

When diagnostic code must run on a remote host over SSH:

- Write the script file locally (still under `<repo>/diagnostics/`).
- Generate the exact handoff text the operator runs from their workstation:
  - `scp` to copy the script to the remote
  - `ssh` to open an interactive session
  - The command line to execute the script inside that session
- Copy the handoff text to the operator's clipboard (see `## Clipboard handling`
  above), so the operator can paste it directly into a terminal.

## Stop condition

If after 5 unsuccessful attempts the problem is not solved, stop.

- An attempt is one diagnostic-script cycle (generate → operator runs → model reads
  log → model proposes a fix or next attempt).
- Do not iterate further on the same approach.
- Present the operator with the alternatives that remain — different angles, different
  tools, external help.
- Ask the operator how to proceed.
