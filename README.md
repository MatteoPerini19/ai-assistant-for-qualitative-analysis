# AI Assistant for Qualitative Analysis

This repository contains the first-pass implementation of a qualitative-analysis pipeline that:

- normalizes a user CSV into canonical internal fields
- renders prompts from a template plus a user-authored analysis instructions file and row-level task/text fields
- executes repeated provider calls
- validates structured JSON outputs against a config-driven schema
- writes an inclusive long output, a summarized wide output, and diagnostics

The current default workflow is mock-provider based so the full pipeline can be tested end to end without API keys or network calls.

## Quick Start

If you want to run a first analysis quickly, change these files and nothing else:

1. Put your CSV file in the repo.
   Recommended location: [data/qualitative_data/](data/qualitative_data)
   You can place it elsewhere, but then `input_data.dataset_file` in `config.yaml` must point to that exact path.
2. Edit [config.yaml](config.yaml).
   Change `input_data.dataset_file` to your CSV path.
   Change `input_data.column_mapping` so the canonical fields map to your dataset's exact column names.
   If useful, first fill in the helper worksheet at [data/datasets/dataset_config.yaml](data/datasets/dataset_config.yaml), then copy the final mapping into `config.yaml`.
   For the fastest supported path, keep `comparative_analysis: false` and make sure the normalized data will contain `row_id` and `participant_text`.
   The field-by-field explanation now lives in the `Config Reference` section below.
3. Edit [prompts/analysis_instructions_main_analysis.txt](prompts/analysis_instructions_main_analysis.txt).
   Put the substantive scoring instructions there: what the model should evaluate, how to interpret each item, and how justifications should be written.
4. Edit [prompts/prompt_template_main_analysis.txt](prompts/prompt_template_main_analysis.txt).
   Keep the prompt structure, but adapt the wording around task context and participant text as needed.
   Make sure the prompt clearly tells the model to return exactly the JSON keys defined in `analysis_schema.items` in `config.yaml`.
5. Run a mock smoke test first.

```bash
venv/bin/python run_pipeline.py config.yaml --output-dir ./outputs_smoke
```

6. If the smoke run looks correct, switch to a real provider if wanted.
   Set `model_set` in `config.yaml` to a live set such as `openai_smoke_set`.
   Export the required API key, for example:

```bash
export OPENAI_API_KEY="your-openai-api-key"
venv/bin/python run_pipeline.py config.yaml --output-dir ./outputs_real
```

Files you will usually change first:

- [config.yaml](config.yaml)
- [prompts/analysis_instructions_main_analysis.txt](prompts/analysis_instructions_main_analysis.txt)
- [prompts/prompt_template_main_analysis.txt](prompts/prompt_template_main_analysis.txt)

Minimum dataset requirement for the quick path:

- one row per analyzable text
- a column that can map to `row_id`
- a column that can map to `participant_text`

Outputs will be written under the chosen output directory, including:

- `output_ds_inclusive_long.csv`
- `output_ds_summaried_wide.csv`
- `diagnostics/sanity_checks.csv`

The rest of this README explains the config fields, prompt files, provider setup, outputs, and limitations in more detail.

## Current first-pass scope

Implemented in the current scope:

- `comparative_analysis: true` is accepted in `config.yaml`
- text-only input using `participant_text`
- one explicit YAML `analysis_schema.items` format
- `metric` and `ordinal` summarized outputs for numeric item schemas
- config-driven model-set selection through the main entry point for the locally wired adapters (`mock`, `openai`)

Explicitly deferred in the current scope:

- full comparative runtime branching
- audio-based input
- external text-file lookup via `text_file_name`
- categorical output treatment
- fuzzy column auto-detection

The starter config and fixture config still default to the mock provider so the full pipeline can be tested end to end without API keys or network calls.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

This installs the package plus the current first-pass dependencies, including `pydantic`, `PyYAML`, `polars`, `pytest`, and `litellm`.

## Configuring `config.yaml`

The repository now includes a runnable root example at [config.yaml](config.yaml). It is intentionally lightly commented and points at the simulated dataset plus the starter prompt files under [prompts/](prompts).

The fixture config at [tests/fixtures/first_pass_project/config.yaml](tests/fixtures/first_pass_project/config.yaml) remains the smallest deterministic example used in automated tests.

Implemented config fields:

```yaml
run_mode: testing
include_task_info: true
input_data:
  dataset_file: data/participant_text_samples.csv
  column_mapping:
    row_id: source_row_id
    participant_id: subject_code
    task_id: prompt_code
    task_label: prompt_label
    task_info: prompt_short_description
    task_full_text: prompt_full_text
    participant_text: essay_text
    language: lang
    condition: experimental_condition
    wave: timepoint
prompt_template_file: prompts/prompt_template_main_analysis.txt
prompt_id: main_analysis
prompt_version: "v1"
analysis_instructions_file: prompts/analysis_instructions_main_analysis.txt
model_set: cheap_set
model_sets:
  cheap_set:
    - model_provider: mock
      model_name: mock-first-pass
      method_name: main_analysis
  openai_smoke_set:
    - model_provider: openai
      model_name: gpt-5-nano
      method_name: main_analysis
repeated_calls:
  count: 3
  temperature: 0.0
merge_output: false
retain_raw_json_output: true
output_data_type: metric
analysis_schema:
  schema_name: main_analysis_v1
  schema_version: "1.0"
  items:
    - item_id: item_1
      score_key: item_1_score
      justification_key: item_1_justification
      score_type: integer
      min_score: 1
      max_score: 7
    - item_id: item_2
      score_key: item_2_score
      justification_key: item_2_justification
      score_type: integer
      min_score: 1
      max_score: 7
```

## Config Reference

All relative paths in `config.yaml` are resolved relative to the directory that contains the config file.

### Runtime fields

- `run_mode`: Use `testing` for small smoke runs and `main_analysis` for larger runs. If `repeated_calls.count` is omitted, the defaults are `3` for `testing` and `100` for `main_analysis`. If `repeated_calls.temperature` is omitted, the default is `0.0`.
- `comparative_analysis`: This flag is accepted by config validation, but the full comparative runtime path is still deferred in the current first pass.
- `include_task_info`: Controls whether available row-level task fields such as `task_label`, `task_info`, and `task_full_text` are inserted into the prompt.

### Input dataset

- `input_data.dataset_file`: Path to the CSV file you want to analyze.
- `input_data.column_mapping`: Maps canonical internal names to the exact column names in your dataset.
- Required normalized fields in the current first-pass text-only path: `row_id` and `participant_text`.
- Optional canonical fields in the current scope: `participant_id`, `task_id`, `task_label`, `task_info`, `task_full_text`, `language`, `condition`, `wave`.
- Keep `column_mapping` minimal. If your source CSV already uses a canonical name, you can usually leave that mapping out.
- Unsupported mapping targets in the current scope: `text_file_name`, `audio_file_name`, and comparative `_1` / `_2` variants.

### Prompt files and prompt identity

- `prompt_template_file`: Plain-text template used to build the final prompt.
- `analysis_instructions_file`: Plain-text file containing the substantive explanation of what the model should evaluate and how it should justify scores.
- `prompt_id`: Stable prompt-family identifier for metadata.
- `prompt_version`: Version for the wording or assembly of the prompt.
- Keep `prompt_version` separate from `analysis_schema.schema_version`. The first identifies the prompt sent to the model; the second identifies the JSON contract used to validate the response.

### Model selection

- `model_set`: Chooses one named entry from `model_sets`.
- `model_sets`: Declares the provider/model/method combinations available to the run.
- The current entry point wires provider adapters for `mock` and `openai`.
- `openai` runs require `OPENAI_API_KEY` in the environment.
- The default starter workflow uses the local `mock` adapter so you can test the pipeline without network calls.

### Repeated calls and output controls

- `repeated_calls.count`: Number of repeated calls per identical prompt/model combination.
- `repeated_calls.temperature`: Fixed temperature used across repeats within a call group. The validator currently allows values from `0.0` to `2.0`.
- `merge_output`: If `true`, append the original dataset columns back onto the generated long and wide outputs using `row_id`.
- `retain_raw_json_output`: If `true`, keep the provider's verbatim JSON response in the inclusive long output.
- `output_data_type`: Summary treatment for repeated numeric outputs. The current implementation supports `metric` and `ordinal`. `categorical` is still deferred.

### Analysis schema

- `analysis_schema.schema_name`: Human-readable name for the scoring design.
- `analysis_schema.schema_version`: Version label for the machine-readable output contract.
- `analysis_schema.items`: Source of truth for the expected JSON keys returned by the model.
- Each item must define exactly one `score_key` and one `justification_key`.
- The current first pass supports integer-style numeric scores with per-item `min_score` and `max_score` validation.
- Put user-facing scoring instructions in `analysis_instructions_file`, not in `analysis_schema.items`.
- If you rename keys in `analysis_schema.items`, update your prompt instructions so the model returns exactly those keys.

## Dataset Mapping Helper

[data/datasets/dataset_config.yaml](data/datasets/dataset_config.yaml) is a worksheet, not a second runtime config file.

Use it when:

- you want to draft the mapping from your study dataset into the pipeline's canonical names
- you want a short, editable record of the dataset path and candidate column mappings before changing the main config

How to use it:

1. Set `dataset.dataset_file` to the study CSV you want to map.
2. Fill `dataset.column_mapping` with the source column names used by your dataset.
3. Copy the final `dataset_file` and `column_mapping` values into `config.yaml`.

In the current first-pass runtime:

- the real runtime reads dataset settings from `config.yaml`, not from `dataset_config.yaml`
- the fastest supported path is one row per analyzable text with columns that normalize to `row_id` and `participant_text`
- file-based inputs through `text_file_name` or `audio_file_name` are still deferred

## Using ChatGPT To Adapt `config.yaml` To Your Dataset

If your study dataset uses different column names from the pipeline's canonical names, you can use ChatGPT to draft the dataset-specific part of `config.yaml`.

Recommended workflow:

1. Start from the current root [config.yaml](config.yaml).
2. Give ChatGPT:
   - the current `config.yaml`
   - your dataset file, or at minimum the exact column names plus a few representative rows
3. Ask it to update only the dataset-alignment parts unless a broader change is clearly required.
4. Review the returned YAML before running the pipeline.

In the current first-pass implementation, ChatGPT should normally only need to adjust:

- `input_data.dataset_file`
- `input_data.column_mapping`

It should usually leave these parts alone unless you explicitly ask otherwise:

- `analysis_schema`
- `model_set` / `model_sets`
- `prompt_template_file`
- `analysis_instructions_file`
- `prompt_id` / `prompt_version`
- repeated-call, output, and merge settings

Important rules for this workflow:

- Keep `column_mapping` minimal. If your CSV already uses a canonical name such as `row_id` or `participant_text`, it usually does not need to be mapped.
- Do not let ChatGPT invent unsupported fields or silent workarounds.
- If your dataset depends on audio inputs, comparative analysis, or external text-file lookup, the assistant should say the dataset is out of scope for the current implementation rather than pretending the config already supports it.
- `analysis_schema.items` is the machine-readable output contract. It should not be rewritten just because the dataset column names differ.

Recommended prompt for ChatGPT:

```text
You are helping me adapt an existing `config.yaml` file so it matches my study dataset exactly.

I will give you:
1. the current `config.yaml`
2. the dataset I want to analyze

Your job:
- inspect the dataset carefully
- update the config so the dataset-related parts match the dataset exactly
- preserve unrelated settings unless a change is clearly necessary for compatibility
- keep the output aligned with the current project scope and do not silently broaden the scope

Current supported scope:
- `comparative_analysis: true` may appear in config without config-level rejection
- text-only input from `participant_text`
- no audio-based input
- no external text-file lookup
- no fuzzy column auto-detection

Canonical internal fields the pipeline may use:
- required: `row_id`, `participant_text`
- optional: `participant_id`, `task_id`, `task_label`, `task_info`, `task_full_text`, `language`, `condition`, `wave`

What to do:
1. Update `input_data.dataset_file` to the correct dataset path if available.
2. Update `input_data.column_mapping` so it maps canonical names to the dataset's exact column names.
3. Keep `column_mapping` minimal.
4. Leave optional fields unmapped if they are absent.
5. Do not change `analysis_schema.items`.
6. Do not change model settings or prompt identity unless I explicitly ask.
7. If the dataset requires unsupported features, say so clearly instead of inventing support.

Return:
1. a short compatibility assessment
2. the full updated `config.yaml`
3. a short list of changed fields
4. a short list of ambiguities or unsupported parts
```

Best practice:

- paste the full YAML, not only fragments
- give ChatGPT a few real rows, not just headers
- check the returned `column_mapping` manually before running the pipeline
- keep a copy of the previous config so changes are easy to compare

## Prompt templates

The pipeline reads the exact prompt template file path from `config.yaml`.

Current behavior:

- the template file is loaded as plain text
- the optional `analysis_instructions_file` is loaded as a plain text fragment and inserted into the prompt context as `{{ analysis_instructions }}`
- row-level `task_label`, `task_info`, `task_full_text`, and `participant_text` are rendered into the template
- omitted optional task fields are removed from the rendered prompt when the template follows the current heading-plus-placeholder pattern

Important:

- Update the files under [prompts/](prompts) before using them in your own config.
- Put the user-authored definition of the scored dimensions in [prompts/analysis_instructions_main_analysis.txt](prompts/analysis_instructions_main_analysis.txt) or another file referenced by `analysis_instructions_file`, and make sure the required JSON keys in that file match `analysis_schema.items` in `config.yaml`.
- [prompts/prompt_template_comparative_analysis.txt](prompts/prompt_template_comparative_analysis.txt) is still an empty deferred placeholder.
- The fixture prompt used in tests lives at [tests/fixtures/first_pass_project/prompts/prompt_template_main_analysis.txt](tests/fixtures/first_pass_project/prompts/prompt_template_main_analysis.txt) and is a good starting reference for the supported first-pass format.
- The fixture analysis-instructions file lives at [tests/fixtures/first_pass_project/prompts/analysis_instructions_main_analysis.txt](tests/fixtures/first_pass_project/prompts/analysis_instructions_main_analysis.txt).

## Running the pipeline

The current entry point is:

```bash
venv/bin/python run_pipeline.py path/to/config.yaml
```

Optional output directory override:

```bash
venv/bin/python run_pipeline.py path/to/config.yaml --output-dir path/to/outputs
```

If the selected config uses a `mock` model set, you can also force a deterministic mock failure mode:

```bash
venv/bin/python run_pipeline.py path/to/config.yaml --mock-scenario valid
```

By default, the entry point:

- loads the config
- loads and normalizes the input CSV
- renders prompts
- resolves the selected `model_set` from config and instantiates the locally wired provider adapters it needs
- writes the output datasets under `outputs/`
- writes diagnostics under `outputs/diagnostics/`

## Default mock-provider workflow

Use the fixture config for a deterministic smoke run:

```bash
venv/bin/python run_pipeline.py \
  tests/fixtures/first_pass_project/config.yaml \
  --output-dir ./tmp_smoke_outputs
```

That path uses:

- the sample CSV fixture in `tests/fixtures/first_pass_project/data/`
- the sample prompt template in `tests/fixtures/first_pass_project/prompts/`
- the selected `cheap_set` entry from the fixture config, which points to the repo-local mock provider

The fixture smoke path does not make live network calls. Live calls only happen if your selected `model_set` uses a live provider adapter such as `openai`.

## Minimal real-provider workflow

The root [config.yaml](config.yaml) includes an example `openai_smoke_set`.

Required environment variable:

- `OPENAI_API_KEY`

Example real-provider run:

1. Set `model_set: openai_smoke_set` in [config.yaml](config.yaml).
2. Export the API key.
3. Run the pipeline:

```bash
export OPENAI_API_KEY="your-openai-api-key"
venv/bin/python run_pipeline.py config.yaml --output-dir ./outputs_openai
```

If `model_set` points to `openai` but `OPENAI_API_KEY` is missing, the CLI exits with a clear error instead of attempting a live call.

## Outputs

The pipeline currently writes these user-facing outputs:

- `output_ds_inclusive_long.csv`
- `output_ds_summaried_wide.csv`

It also writes debugging/inspection artifacts such as manifests and diagnostics under `outputs/`.

### Inclusive long

`output_ds_inclusive_long.csv` keeps one row per LLM call. It includes:

- `run_id`
- row metadata such as `row_id`, `participant_id`, `task_id`
- provider/model/method metadata
- prompt identity metadata: `prompt_template_file`, `prompt_id`, `prompt_version`
- schema identity metadata: `schema_name`, `schema_version`
- prompt metadata and the full `effective_prompt`
- one column per configured score/justification key
- `parse_status`, `validation_error`, and `error_message`
- `raw_json_output` when `retain_raw_json_output: true`

Provider-side failures are also written here as ordinary call rows with `parse_status='provider_error'` and `error_message`, rather than being dropped as exception-only events.

Use this file when you need full auditability or want to inspect individual replicates.

### Summarized wide

`output_ds_summaried_wide.csv` keeps one row per original `row_id`. It summarizes repeated calls using explicit wide-column names.

Current summarized behavior:

- `metric`: mean, sample standard deviation, min, max
- `ordinal`: median, IQR, MAD
- representative justifications closest to the summary target
- parse-success and parse-failure counts per call group

Use this file when you want one summary row per original observation.

### Merge behavior

If `merge_output: true`, both outputs append original dataset columns by `row_id`.

- the inclusive file stays long
- the summarized file stays wide
- duplicate original `row_id` values are rejected instead of being merged silently

## Tests

Run the full test suite:

```bash
venv/bin/python -m pytest
```

Run the entry-point smoke test only:

```bash
venv/bin/python -m pytest tests/test_pipeline_entrypoint.py
```

The smoke test exercises the same mock-backed path used by the default CLI and verifies that:

- the pipeline runs from config load to output writing
- `output_ds_inclusive_long.csv` is created
- `output_ds_summaried_wide.csv` is created
- `outputs/diagnostics/sanity_checks.csv` is created

## First-pass limitations

These are not supported yet and should be treated as deferred features:

- comparative prompt rendering and comparative datasets
- audio inputs and audio-file processing
- text-file loading through `text_file_name`
- categorical output aggregation
- provider adapters beyond the currently wired `mock` and `openai` paths
- fuzzy column mapping or auto-detection

If you want to work beyond the current scope, use the blueprint as the future target, but follow the implemented first-pass behavior described above rather than assuming the wider blueprint already exists in code.
