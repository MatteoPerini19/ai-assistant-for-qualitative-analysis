
# Implementation Progress

This file tracks build progress for the task pipeline defined in `CODING_AGENT_TASK_PIPELINE.md`.

## Status legend

- ⬜ Not started
- 🟡 In progress
- 🟠 Awaiting manual review
- ✅ Done and reviewed
- ⛔ Blocked
- ❄️ Deferred until after the first implementation pass

## Current focus

- Active task: Manual review and first-pass stabilization
- Next task: Choose whether to expand one deferred block (`B1`–`B5`) or tighten the first live-provider workflow beyond the current `mock` / `openai` entry-point support
- Current branch: `main`
- Last updated: 2026-03-15
- Notes: Tasks 00-15 are implemented and exercised with local tests; manual review is still pending. The `provider_error` behavior is now a formal design decision rather than an open `🔴` assumption. All current `🟡` flags are consolidated below.

## Master tracker

| ID | Task | Depends on | Status | Agent run / branch | Manual review | Notes |
|---|---|---|---|---|---|---|
| 00 | Repo guardrails and skeleton | — | 🟠 | `main` | pending | Initial repo skeleton, tooling config, root README, and scope-aligned guardrails landed. |
| 01 | Typed contracts and config loading | 00 | 🟠 | `main` | pending | Pydantic config/contracts implemented with first-pass scope checks and YAML loading. |
| 02 | Fixtures and sample assets | 01 | 🟠 | `main` | pending | Deterministic sample config, CSV, prompt template, and pytest fixtures added. |
| 03 | Dataset ingest and normalization | 01, 02 | 🟠 | `main` | pending | CSV ingest, explicit column mapping, normalization, and first-pass input rejection paths implemented. |
| 04 | Prompt rendering | 03 | 🟠 | `main` | pending | Template loading and effective prompt rendering implemented for text-only non-comparative rows. |
| 05 | Analysis-schema driven output contract | 01 | 🟠 | `main` | pending | Provider-agnostic output contract and JSON Schema generation implemented from `analysis_schema.items`. |
| 06 | Provider interface and mock provider | 05 | 🟠 | `main` | pending | Shared provider `Protocol`, deterministic `MockProvider`, and scenario coverage are in place. |
| 07 | Repeated-call execution engine | 04, 06 | 🟠 | `main` | pending | Repeated prompt execution via provider abstraction landed with fixed call-group invariants and call metadata capture. |
| 08 | Parsing and long-record assembly | 05, 07 | 🟠 | `main` | pending | Raw provider outputs are parsed, validated, classified, and assembled into call-level records for inclusive-long persistence. |
| 09 | Inclusive long output writer | 08 | 🟠 | `main` | pending | `output_ds_inclusive_long.csv` plus debugging manifests are written with stable column order and raw JSON retention control. |
| 10 | Aggregation and summarized wide writer | 09 | 🟠 | `main` | pending | `output_ds_summaried_wide.csv` is produced for numeric first-pass schemas with representative justifications and explicit wide columns. |
| 11 | Sanity checks and diagnostics | 09, 10 | 🟠 | `main` | pending | Diagnostics CSV output covers parse failures, temperature drift, identical outputs, and high between-replicate variance. |
| 12 | Optional merge with original dataset | 03, 09, 10 | 🟠 | `main` | pending | Merge-by-`row_id` support is implemented for both long and wide outputs behind the config flag. |
| 13 | CLI / pipeline orchestration | 11, 12 | 🟠 | `main` | pending | One config-driven entry point runs config load through output writing end to end and selects providers/models from `config.yaml`. |
| 14 | First real provider adapter | 13 | 🟠 | `main` | pending | A LiteLLM-backed OpenAI adapter is available behind the provider interface with offline tests and a clear missing-`OPENAI_API_KEY` CLI failure path. |
| 15 | README and final project docs | 13, 14 | 🟠 | `main` | pending | User-facing docs now cover setup, config, prompts, outputs, tests, limitations, and the mock-backed smoke path. |
| B1 | External text-file loading and task-description lookup | 13 | ❄️ |  |  |  |
| B2 | Comparative-task branch and long-to-wide helper | 13 | ❄️ |  |  |  |
| B3 | Audio / transcript path | 13 | ❄️ |  |  |  |
| B4 | Explicit categorical schema format | 10 | ❄️ |  |  |  |
| B5 | Additional provider adapters and benchmark harness | 14 | ❄️ |  |  |  |

## Review checklist for every completed task

Use this checklist before changing a task from 🟠 to ✅.

- [ ] Diff reviewed manually
- [ ] Tests run locally
- [ ] New or changed tests include rationale comments where needed
- [ ] Any uncertain assumptions are marked with `🟡` or `🔴` in code/tests
- [ ] All `🟡` and `🔴` assumptions from the agent summary are copied into the sections below
- [ ] README / docs updated if the interface changed
- [ ] No unrelated refactor slipped into the task

## Milestone gates

| Milestone | Reached when | Status | Notes |
|---|---|---|---|
| M1 | Tasks 00–01 done | 🟠 | Implemented and tested; awaiting manual review |
| M2 | Tasks 02–06 done | 🟠 | Offline core is testable without network; awaiting manual review |
| M3 | Tasks 07–10 done | 🟠 | Both canonical output datasets exist; awaiting manual review |
| M4 | Tasks 11–13 done | 🟠 | Full config-driven first-pass pipeline runs end to end; awaiting manual review |
| M5 | Task 14 done | 🟠 | First real provider safely integrated with offline tests and CLI wiring; awaiting manual review |
| M6 | Task 15 done | 🟠 | Repo is documented and handoff-ready for first-pass manual review |

## Open 🟡 assumptions

| ID | Raised in task | Description | Status | Resolution / note |
|---|---|---|---|---|
| Y-001 | 01 | Whitespace-only justifications count as empty during output validation. | open | Raised in `schemas.py`; the blueprint requires justifications but does not define whether whitespace-only text is acceptable. |
| Y-002 | 01 | Relative paths in `config.yaml` are resolved relative to the config file directory. | open | Raised in `src/ai_qualitative_analysis/config.py`; the blueprint requires configurable paths but does not define a cwd rule. |
| Y-003 | 02 | Three sample rows are enough for shared parser, aggregation, and diagnostic fixtures. | open | Raised in `tests/test_sample_assets.py`; chosen to keep shared fixtures readable and maintainable. |
| Y-004 | 02 | The shared sample CSV should use user-facing source column names rather than canonical normalized names. | open | Raised in `tests/test_sample_assets.py`; this keeps normalization tests realistic. |
| Y-005 | 03 | Any explicitly mapped source column missing from the CSV is treated as an error, even if the canonical field would otherwise be optional. | open | Raised in `src/ai_qualitative_analysis/io/ingest.py`; this makes misconfigured mappings fail clearly. |
| Y-006 | 04 | First-pass prompt templates express optional task sections as a heading line followed immediately by the matching placeholder line, so omitted task info can remove the whole section. | open | Raised in `src/ai_qualitative_analysis/prompts/render.py` and mirrored in `tests/test_prompt_rendering.py`. |
| Y-008 | 10 | Metric dispersion uses sample standard deviation when at least two valid scores exist, and `0.0` for single-score groups. | open | Raised in `src/ai_qualitative_analysis/pipeline/aggregation.py`; the blueprint requests standard deviation but does not specify sample-vs-population behavior. |
| Y-009 | 10 | Ordinal IQR uses inclusive 25th/75th percentiles with linear interpolation, and MAD is the median absolute deviation from the group median. | open | Raised in `src/ai_qualitative_analysis/pipeline/aggregation.py`; the blueprint names IQR/MAD but does not fix a small-sample convention. |
| Y-010 | 10 | Representative justifications default to three entries, with ties broken by lower `replicate_id` and then lower `run_id`. | open | Raised in `src/ai_qualitative_analysis/pipeline/aggregation.py`; the blueprint treats `3` as the default but the first-pass config does not expose this as a setting yet. |
| Y-011 | 11 | High between-replicate variance is flagged when sample standard deviation exceeds 25% of the configured score-range width. | open | Raised in `src/ai_qualitative_analysis/pipeline/diagnostics.py`; the blueprint requires a variance diagnostic but does not define a first-pass threshold. |
| Y-012 | 11 | “Unexpectedly identical outputs” means every valid parsed output in a call-group is identical after canonical JSON serialization. | open | Raised in `src/ai_qualitative_analysis/pipeline/diagnostics.py`; the blueprint names this diagnostic but does not define a softer similarity threshold. |
| Y-013 | 12 | Original dataset columns that would collide with generated output columns are omitted during merge instead of overwriting generated values. | open | Raised in `src/ai_qualitative_analysis/pipeline/merging.py`; this avoids silently distorting output rows. |
| Y-016 | 13 | The entry point writes to `outputs/` next to the selected config file by default when `--output-dir` is omitted. | open | Raised in `src/ai_qualitative_analysis/pipeline/run.py`; the blueprint shows a top-level outputs directory but does not define whether path resolution is based on cwd or config location. |
| Y-017 | 14 | OpenAI `system_fingerprint` is stored in the existing `server_side_version` metadata field. | open | Raised in `providers/litellm_openai.py`; the first-pass persisted contract has no separate provider-build field and silently dropping it would lose audit context. |
| Y-018 | 14 | The first real provider adapter uses LiteLLM chat completions and only forwards `thinking_budget` when LiteLLM reports `reasoning_effort` support for the chosen model. | open | Raised in `providers/litellm_openai.py`; the broader reasoning-budget configuration remains deferred, so the first-pass adapter stays explicit about what it supports. |

## Open 🔴 assumptions

None currently open.

## Decision log

| Date | Task | Decision | Reason |
|---|---|---|---|
| 2026-03-15 | 06 | Provider-side failures are represented as structured `provider_error` call records instead of being raised away as exceptions. | Keeps one auditable call-record shape for both success and failure, matching the inclusive-long output design and validation-outcome tracking. |

## Blockers

| Date | Task | Blocker | Owner / next action |
|---|---|---|---|
|  |  |  |  |

## Notes by task

### 00. Repo guardrails and skeleton
- Outcome:
- Files touched:
- Commands run:
- Review notes:

### 01. Typed contracts and config loading
- Outcome:
- Files touched:
- Commands run:
- Review notes:

### 02. Fixtures and sample assets
- Outcome:
- Files touched:
- Commands run:
- Review notes:

### 03. Dataset ingest and normalization
- Outcome:
- Files touched:
- Commands run:
- Review notes:

### 04. Prompt rendering
- Outcome:
- Files touched:
- Commands run:
- Review notes:

### 05. Analysis-schema driven output contract
- Outcome:
- Files touched:
- Commands run:
- Review notes:

### 06. Provider interface and mock provider
- Outcome:
- Files touched:
- Commands run:
- Review notes:

### 07. Repeated-call execution engine
- Outcome:
- Files touched:
- Commands run:
- Review notes:

### 08. Parsing and long-record assembly
- Outcome:
- Files touched:
- Commands run:
- Review notes:

### 09. Inclusive long output writer
- Outcome:
- Files touched:
- Commands run:
- Review notes:

### 10. Aggregation and summarized wide writer
- Outcome:
- Files touched:
- Commands run:
- Review notes:

### 11. Sanity checks and diagnostics
- Outcome:
- Files touched:
- Commands run:
- Review notes:

### 12. Optional merge with original dataset
- Outcome:
- Files touched:
- Commands run:
- Review notes:

### 13. CLI / pipeline orchestration
- Outcome:
- Files touched:
- Commands run:
- Review notes:

### 14. First real provider adapter
- Outcome:
- Files touched:
- Commands run:
- Review notes:

### 15. README and final project docs
- Outcome:
- Files touched:
- Commands run:
- Review notes:
