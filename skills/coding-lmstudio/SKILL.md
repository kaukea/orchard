---
name: coding-lmstudio
description: "Use for any module that talks to a local LLM hosted in LM Studio. Encodes the rules: native /api/v1/* surface only, discovery prefers Staff Picks → catalog → Hugging Face with MLX over GGUF, load your own model instance with a unique identifier, session caching for conversations only, user-approved side-by-side benchmarks, and the two narrow lms CLI exceptions (server start, deletion)."
categories: [development/lmstudio]
metadata:
  tags: [lmstudio, lm-studio, local-llm, native-api, model-loading, benchmarking, mlx, gguf]
  share: github
---

# Coding modules that use LM Studio

Rules for any module whose runtime depends on a local LLM hosted in LM Studio.

## Checklist

- [ ] API changelog fetched before starting work
- [ ] LM Studio HTTP server reachable; started via `lms server start` if not
- [ ] Server URL sourced from configuration, not hardcoded
- [ ] Only the native `/api/v1/*` surface used (SDKs allowed as long as they call native)
- [ ] Auth token handling matches the user's server configuration
- [ ] Models discovered live (Staff Picks → catalog → Hugging Face); MLX preferred
- [ ] Candidate selection confirmed with the user before download
- [ ] Module loads its own model instance with a unique identifier
- [ ] Module unloads only what it loaded
- [ ] Benchmark organisation and iteration count agreed with the user; findings shown before cleanup
- [ ] Cleanup of unselected candidates done via `lms` only after user approval
- [ ] MCP installs into LM Studio confirmed with the user first

## Pre-work

Fetch the API changelog at <https://lmstudio.ai/docs/developer/api-changelog> before any LM Studio work. LM Studio evolves quickly — concurrency dial defaults, MLX backend behaviour, vision-model concurrency, and native endpoints all shift between releases. The skill encodes what was true at writing; the changelog is the live source of truth.

If the LM Studio HTTP server is not running, start it with `lms server start`. This is one of two allowed uses of the `lms` CLI. No user confirmation required.

## Server location

The default LM Studio HTTP server URL is `http://localhost:1234`. Do not hardcode host or port in the module — read both from configuration (environment variable or config file), with the default as fallback. LM Studio's server settings allow either to change.

The same base URL serves both native (`/api/v1/*`) and OpenAI-compatible paths. Only native paths are in scope.

## API surface

Use only the native `/api/v1/*` endpoints.

Off-limits:

- OpenAI-compatible `/v1/*`
- Anthropic-compatible `/v1/messages`
- The deprecated `v0` REST API

The native TypeScript (`@lmstudio/sdk`) and Python (`lmstudio`) SDKs are allowed, provided they call the native APIs.

Embeddings are an unresolved gap: it is not currently confirmed whether the native chat endpoint can return text embeddings. Before falling back to OpenAI-compatible `/v1/embeddings`, the module must test the native path. Opening the OpenAI-compatible surface requires explicit user approval.

## Authentication

The native API supports authentication (added in LM Studio 0.4.0 — check the changelog for the current shape).

- When authentication is enabled, the user provides the token to the module via configuration
- The module holds the token in memory for the duration of the session; never persisted to disk
- Whether authentication is on or off must be configurable, not assumed

## Model discovery

Prefer, in order:

1. LM Studio Staff Picks
2. Other entries in LM Studio's catalog
3. Hugging Face

For Hugging Face, use the live search API — `https://huggingface.co/api/models?search=<term>&filter=mlx&sort=trending&limit=<n>` — and not training-cutoff memory of which models exist.

Prefer MLX builds over GGUF. If no MLX build of a target model exists, look for a conversion (e.g. by the `mlx-community` organisation on Hugging Face).

When picking a model for a specific problem, check benchmark performance on relevant evaluation suites before downloading anything.

## Model download

Downloads are the module's responsibility. Never claim inability to download a model.

`POST /api/v1/models/download` with:

```json
{ "model": "<id-or-url>" }
```

The `model` field accepts both LM Studio catalog identifiers (e.g. `openai/gpt-oss-20b`) and exact Hugging Face URLs (e.g. `https://huggingface.co/lmstudio-community/gpt-oss-20b-GGUF`).

An optional `quantization` parameter (e.g. `Q4_K_M`) is honoured only on Hugging Face URLs, not on catalog identifiers.

The response includes a `job_id`. Poll `GET /api/v1/models/download/status` with that `job_id` until status reaches `completed` or `already_downloaded`. Statuses are `downloading | paused | completed | failed | already_downloaded`. `failed` is a real outcome — handle it explicitly.

## Loading and unload discipline

Load your **own instance** of the model with a unique identifier, every time. LM Studio supports loading the same model multiple times under different identifiers. An already-loaded instance may be serving another consumer — reusing it is wrong, and modules have repeatedly gotten this wrong.

`POST /api/v1/models/load` carries the load parameters (context length and others). Set them deliberately; do not accept silent defaults.

After triggering load, poll `GET /api/v1/models` until your identifier appears in the loaded list, then send the first request.

`POST /api/v1/models/unload` targets your own identifier only. Never unload anything else, under any circumstance, even if it appears idle.

## Benchmarking and cleanup

When selecting a model for a problem:

1. From discovery (above), present the candidate set to the user. Ask which ones to download for the benchmark.
2. Download the user-selected subset using the download rules.
3. Plan the benchmark with the user before running it: organisation (representative inputs, what is being measured — accuracy, speed, others) and iteration count if applicable.
4. Run the benchmark.
5. Stop and show findings to the user.
6. Ask whether to persist per-run and aggregated results to a markdown file.
7. After a winner is chosen, ask whether to delete the unselected candidates.

Deletion uses `lms` — the second and only other allowed use of the CLI. Never touch the filesystem directly.

Only delete models the module downloaded in this work. Pre-existing models on disk are out of bounds.

## Inference patterns

The native chat endpoint supports stateful (session-cached) mode, backed by the server's KV cache. Use it for multi-turn conversations: the module does not resend history each turn.

Use one-shot mode (no session cache) when the module fires a single prompt, takes the result, and moves on.

Concurrency: LM Studio's current default is 4 parallel reasoning branches per loaded model (the "concurrent thinking" dial in the UI). Tune up or down based on the host's specifications — sometimes 4 is too high, sometimes much higher works. The changelog covers drift in this default between releases.

Vision models accept image input via content arrays on the chat endpoint. Concurrency support varies by backend (MLX vs GGUF) and version — defer specifics to the changelog.

## MCP

If the LM Studio session would benefit from an MCP tool — the local agent running inside LM Studio consuming it — ask the user before installing it.

The install targets LM Studio's own MCP configuration, not Claude Code's `.mcp.json`.

Never install silently.

## Stop

Stop when the module integrates with LM Studio's native API per these rules, the chosen model has won a side-by-side benchmark on the actual problem, the user's cleanup and persistence questions are answered, and the agreed test has passed.

## References

Verified upstream sources, current at writing. Re-fetch when these claims need updating.

- API changelog: <https://lmstudio.ai/docs/developer/api-changelog>
- Native REST endpoints: <https://lmstudio.ai/docs/app/api/endpoints/rest>
- Native download endpoint: <https://lmstudio.ai/docs/developer/rest/download>
- CLI: <https://lmstudio.ai/docs/cli>
- TypeScript SDK: <https://lmstudio.ai/docs/typescript>
- Python SDK: <https://lmstudio.ai/docs/python>
- Hugging Face Hub API: <https://huggingface.co/docs/hub/api>
