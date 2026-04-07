## General coding rules
- Treat `project_management/BLUEPRINT.md` as the objective source of product requirements.
- When a future-looking section of `BLUEPRINT.md` conflicts with `Current implementation scope`, follow the simplified current scope and explicitly defer the conflicting feature.
- Prefer Python for implementation when it is a natural fit for the task.
- Prefer Polars for new tabular data-processing code, especially transformation, aggregation, and larger-data workflows.
- Prefer the Polars lazy API when it is a natural fit for the workflow.
- Use pandas when interoperability with external libraries or APIs requires it.
- Avoid unnecessary back-and-forth conversion between pandas and Polars within the same pipeline.
- Use YAML (`.yaml`) for config files.
- Read runtime behavior from config files or typed settings objects rather than hard-coding model names, prompt-template filenames, thresholds, or analysis modes.

## Current implementation scope
- `comparative_analysis: true` may appear in `config.yaml` without config-level rejection.
- First pass scope is text-only input from `participant_text` only.
- Audio handling is deferred until a later scope expansion.
- The full comparative runtime branch is still a later scope expansion.
- Live provider calls are deferred while the repository is still establishing its first-pass package and validation skeleton.
- Use one explicit `analysis_schema` structure in `config.yaml` as the source of truth for expected scored items and output fields.
- Keep the repository structure ready for package code and thin future wrappers, but do not silently implement deferred features.

## LLM integration rules
- When integrating LLM APIs from Python, use LiteLLM unless a requirement explicitly justifies a direct provider SDK instead.
- When saving outputs from many LLM calls, persist enough metadata to reproduce or audit external calls and persisted outputs, including versioned inputs, effective parameters, timestamps, and validation outcomes.

## Data-contract rules
- Use Pydantic for runtime validation at all external or persisted boundaries.
- Place Pydantic models in a `schemas.py` file unless there is a clear project-structure reason to split them further.
- Do not hand-roll ad hoc dict validation when a Pydantic model is appropriate.
- Do not introduce new magic-string statuses when an enum already exists.
- For projects with many sets of allowed values, define and centralize them in an `enums.py` file.
- Keep one output schema per analysis/prompt version rather than one monolithic global output schema.

## Assumption rules
- If a requirement is underspecified, surface the assumption explicitly in code comments, tests, and task summaries rather than silently turning it into a settled rule.
- Mark ordinary underspecified assumptions with:
  `# 🟡 ASSUMPTION: ...`
- Mark high-risk assumptions, or assumptions made during coding that have major downstream consequences, with:
  `# 🔴 HIGH-RISK ASSUMPTION: ...`
- For every `🔴` assumption, explain the assumption itself, the main plausible alternatives, and why the chosen path was taken.
- Mention every `🟡` and `🔴` assumption in the final task summary.
- Do not silently convert assumptions into settled requirements.

## Testing rules
- When behavior is added or changed, create or update pytest tests when sensible.
- Put tests in `tests/` using standard `test_*.py` naming.
- In test files, include short comments explaining why representative examples were chosen when the choice is not obvious.
