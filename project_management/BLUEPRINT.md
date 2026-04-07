# AI Qualitative Analysis Blueprint

## Current implementation scope

For the first implementation pass, this project should build a simplified version of the pipeline before adding the broader features described later in this blueprint.

### Simplified constraints for now

- `comparative_analysis: true` may appear in `config.yaml` without config-level rejection.
- The full comparative runtime branch is still a separate implementation path and may remain incomplete while other first-pass pieces are being established.
- Only **text-only inputs** are in scope.
  - The first implementation should analyze text provided in `participant_text`.
  - Audio inputs are out of scope for now.
- Only **one explicit item/schema config format** is in scope.
  - The first implementation should use a single YAML structure for defining the expected scored items and their output contract.

### Initial item/schema config format

The first implementation should support one explicit schema definition format in `config.yaml` such as:

```yaml
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

Rules for this initial format:

- `analysis_schema.items` is the single source of truth for the expected JSON output fields.
- Each item must define exactly one score field and one justification field.
- The parser should validate that all required keys exist and that scores fall within the configured range for that item.
- The substantive user-authored description of what the LLM should evaluate should live in a separate prompt-instructions text file rather than inside `config.yaml`; the config-side schema is the machine-readable output contract.
- If a future analysis needs a different output shape, that should be added later as a new explicit schema format rather than silently overloading this first one.

The wider blueprint below can still describe future features, but when implementation decisions conflict with future scope, the simplified constraints above should govern the initial build.

---

## Project goal

Build a Python pipeline that helps **quantize qualitative data** by sending writing samples to one or more LLMs, collecting structured ratings and justifications, repeating calls when needed, and exporting two main output datasets: one **inclusive long** dataset with every individual LLM call and one **summarized wide** dataset with summary statistics computed across repeated calls. Depending on the config file, these output datasets can also be automatically merged with the user's original dataset for analysis.

---

## Core idea

The pipeline should:

1. Read a CSV containing writing samples (one per row) and, if present, information about the specific task from which the writing sample comes (in case the task was not the same for all the writing samples). Note: in some cases, we will not have a writing sample, but the name of a file containing the writing sample and/or an audio file (at least one per row).
2. Build an LLM prompt from reusable components.
   - In the preferred first-pass structure, the reusable components include:
     - a prompt template file,
     - a user-authored analysis-instructions text file,
     - row-level task/text fields from the dataset.
3. Ask the LLM to score one or more qualitative dimensions.
4. Request a structured JSON output with scores and justifications.
5. Save each LLM call together with metadata, and optionally retain the verbatim raw JSON output.
6. Optionally repeat identical calls many times to estimate variability.
7. In case of repeat identical calls, compute summary statistics according to the config choice for `metric/ordinal/categorical` data.
8. Save an inclusive long output dataset with one row per LLM call and one unique `run_id` per row.
9. Save a summarized wide output dataset with one row per original `row_id` and summary columns derived from the repeated calls.
10. Depending on the config file, optionally merge both output datasets with the original CSV dataset into analysis-ready tables.

---

## Data structure

The input dataset should use one row per analyzable participant contribution. In the most common case, that means one writing sample per row, but the same structure can also support transcripts and audio-based submissions by storing either the text directly in the CSV or a reference to an external file. The goal is to preserve a stable row-level unit that can be sent to the LLM, traced back to the original source, and merged cleanly with downstream outputs.

The variable names listed below should be treated as the **canonical internal names** used by the pipeline after input normalization. The user's original dataset does not need to use these exact column names, as long as the config file maps the user's names onto these canonical names.

- `row_id`
  - Unique identifier of the row of the original table (e.g., row_001). Each row_id corresponds to a different text to be analysed.
- `participant_id`
  - Unique participant identifier (e.g., pp_001).
- `task_id`
  - Short identifier for the task or prompt version (e.g., task_01).
- `task_label`
  - Human-readable name (e.g., "Reflection about personal challenges.")
- `task_info`
  - Short task-specific description to insert into the LLM prompt. (e.g., "For this task, participants were asked to...")
- `task_full_text`
  - Full wording of the participant task. (e.g., "For this task, you should reflect about...")
- `participant_text`
  - The participant's text to be evaluated. This variable is an alternative to `text_file_name`.
- `text_file_name`
  - Name of the text file containing the task-specific participant's written text or transcript. This variable is an alternative to `participant_text`.
- `audio_file_name`
  - Optional. Name of the audio file containing the task-specific participant's voice recording.
- `language`
  - Language of the writing sample (e.g., EN, NL)
- `condition`
  - Optional. Experimental condition (e.g., treatment, control).
- `wave`
  - Optional. Longitudinal wave or time point (e.g., wave_01).


Note: Our software wants to allow for a comparative analysis in which the LLM will directly compare two texts (e.g., the two texts written by the same participant under two different experimental conditions). In this case, we need to create a second version of the CSV file which will be in a *wide* format, presenting on the same row the texts to be compared. In this case, instead of columns such as `participant_text` and `task_id`, we will have
`participant_text_1` and `task_id_1`, and `participant_text_2` and `task_id_2`.

---

## Dataset naming and column mapping strategy

The pipeline should allow the user to work with dataset filenames and column names that differ from the examples used in this blueprint.

### Best current hypothesis

The best implementation strategy is to introduce a **normalization layer at ingest time**:

1. The user specifies the input dataset filename/path in `config.yaml`.
2. The user specifies a mapping from the user's original column names to the pipeline's canonical internal names.
3. The pipeline loads the original dataset, renames the mapped columns into the canonical internal names, validates the normalized result, and then runs the rest of the pipeline only on the canonical names.

This means the downstream scripts should always refer to canonical names such as `row_id`, `participant_text`, `task_id`, `task_info`, and `task_full_text`, even if the original dataset used different names such as `id`, `essay_text`, `prompt_code`, or `condition_a_text`.

### Why this is the best current hypothesis

- It keeps the downstream code simple and stable, because only the ingest step needs to know about user-specific naming.
- It makes validation much easier, because Pydantic models can validate one canonical internal schema rather than many user-specific variants.
- It supports both the dataset filename and the variable names being customized without duplicating logic throughout the pipeline.
- It reduces the risk of brittle heuristics. The pipeline should not guess column mappings with fuzzy matching when an explicit mapping can be provided in config.

### Recommended config shape

```yaml
input_data:
  dataset_file: data/qualitative_data/my_real_dataset.csv
  column_mapping:
    row_id: my_row_identifier
    participant_id: subject_code
    task_id: prompt_code
    task_label: prompt_label
    task_info: prompt_short_description
    task_full_text: prompt_full_text
    participant_text: essay_text
    text_file_name: transcript_filename
    audio_file_name: audio_filename
    language: lang
    condition: experimental_condition
    wave: timepoint
```

In the config file, especially in this section, it is important to explain to the user what each entry means, to guide them in making the right choice without doubt.



### Implementation rules

- `dataset_file` should point to the user-selected input dataset file. The filename should not be hard-coded anywhere else in the pipeline.
- `column_mapping` should map canonical internal names to the column names present in the user's original dataset.
- Only columns that are actually present and needed for a given analysis must be mapped. Optional canonical fields may be omitted.
- If a canonical internal name already exists in the original dataset, the user may map it to itself or the pipeline may accept the exact-match name directly.
- After renaming, the pipeline should validate the normalized dataset against the internal schema and fail clearly if required canonical fields are still missing.
- For comparative analyses, the same strategy should be used, but with canonical names such as `participant_text_1`, `task_id_1`, `participant_text_2`, and `task_id_2`.
- The pipeline should not rely on fuzzy auto-detection of column names as a primary strategy. If any auto-detection is added later, it should be conservative, transparent, and overrideable by explicit config.

### Assisted config-alignment workflow

When helping a user adapt `config.yaml` to a new study dataset, it is acceptable to use an external LLM such as ChatGPT as a drafting assistant, as long as the workflow stays explicit and auditable.

Recommended workflow:

1. Provide the current `config.yaml`.
2. Provide the target dataset or, at minimum, its exact column names and a few representative rows.
3. Ask the assistant to update only the dataset-specific parts of the config unless a broader change is explicitly requested.

Rules for this assisted workflow:

- The assistant should preserve unrelated settings whenever possible.
- The assistant should update `input_data.dataset_file` and `input_data.column_mapping` to match the user's dataset exactly.
- The assistant may also point out when optional fields such as `task_label`, `task_info`, `task_full_text`, `language`, `condition`, or `wave` are unavailable and therefore should remain unmapped.
- The assistant should not invent fuzzy column matches and should not guess silently when multiple plausible mappings exist.
- If the dataset appears to require an unsupported path in the current implementation scope, such as audio-based input, comparative analysis, or external text-file lookup, the assistant should say so explicitly rather than pretending the current config already supports it.
- The assistant should keep the machine-readable `analysis_schema` stable unless the user explicitly asks to change the output contract.

Recommended response shape for this workflow:

1. A short compatibility assessment.
2. The full updated `config.yaml`.
3. A short list of changed fields.
4. A short list of ambiguities, unsupported inputs, or follow-up confirmations still needed.

---

## Config file

The project should expose a config file or config object with decisions such as:

- **Run mode?** `run_mode: testing`/`run_mode: main_analysis`.
  - Default: `run_mode: testing`
- **Include task-specific info in the prompt for the LLM?** `yes/no`. Default: yes
- **Where is the task info stored?**
  - in a CSV column
  - in a separate file
  Default: in the CSV file. 
- **Which dataset file should be used as input, and how should its columns be mapped to the pipeline's canonical internal names?**
  - Store the dataset filename/path and the column mapping in `config.yaml`.
  - The pipeline should normalize user-specific column names into canonical internal names at ingest time and then use only the canonical names downstream.
- **Is the analysis comparative?** `yes/no`
  - Default: no. 
  - This means that the LLM is not giving an absolute score to a text, but comparing it with another text (how this is asked is still to be decided, but at minimum it will involve choosing which text is higher on the evaluation dimension).
  - If yes, use an alternative prompt template.
  - We will probably build a separate script for this.
  - For the comparative analysis, we should recommend the user to have a separate CSV file in a wide format with the texts to compare presented on the same row. 
  - We should write a separate script for transforming the CSV file from long to wide based on the variable names listed in the "Dataset structure" section of this blueprint.
- **Which prompt template file should be used for the current analysis?**
  - Store the exact prompt-template filename in `config.yaml`.
  - Example: `prompt_template_file: prompt_template_main_analysis.txt`
  - If the analysis is comparative, the default template is `prompt_template_comparative_analysis.txt`.
  - If the analysis is not comparative, the default template is `prompt_template_main_analysis.txt`.
  - The Python script should read the exact prompt-template filename from `config.yaml` rather than hard-coding prompt names, because users may work with multiple prompt templates targeting different variables.
- **Which user-authored analysis instructions should be inserted into the prompt?**
  - Store the exact analysis-instructions filename in `config.yaml`.
  - Example: `analysis_instructions_file: prompts/analysis_instructions_main_analysis.txt`
  - This text file should contain the substantive description of what the LLM should score, how each dimension should be interpreted, and how justifications should be written.
  - This keeps `config.yaml` focused on runtime settings and the machine-readable output contract.
- **Which scoring instructions should the LLM use?**
  - Put the user-facing scoring instructions in the analysis-instructions text file rather than in `config.yaml`.
  - `config.yaml` should still define the machine-readable score range and JSON keys through `analysis_schema.items`.
  - e.g., the text file can say `Use a 1-7 scale`, while `analysis_schema.items` defines `min_score: 1` and `max_score: 7`.
- **Temperature.**
  Default: fixed low temperature for deductive scoring.
  - Default if `run_mode: testing`: `0.0`
  - Default if `run_mode: main_analysis`: `0.0`
- **How many repeated calls should be made per identical prompt?**
  - Default if `run_mode: testing`: 3.
  - Default if `run_mode: main_analysis`: 100.
- **When multiple calls are launched, will the temperature stay always the same or change?** 
  Default: it should stay the same within the analysis. Repeated calls for the same `row_id × model × prompt_version × method` combination should use the same fixed low temperature.
- **Which LLMs should be used?**
  - In the config file there will be named dictionaries of LLMs that can be customized (see section below).
  - Default if `run_mode: testing`: cheap_set.
  - Default if `run_mode: main_analysis`: frontier_main_analysis_set.
- **How many representative justifications should be saved in `output_ds_summaried_wide.csv`, in case we are averaging across many different calls?**
  - Default if `run_mode: testing`: 3.
  - Default if `run_mode: main_analysis`: 3.
  - Rationale: `output_ds_summaried_wide.csv` is meant to stay presentation-friendly, while `output_ds_inclusive_long.csv` already retains the full set of individual call-level outputs.
- **Should the verbatim raw JSON outputs be retained inside `output_ds_inclusive_long.csv`?** `yes/no`. Default: yes.
  - Note: the inclusive long dataset should still contain one row per LLM call either way; this option only controls whether the verbatim raw JSON strings are retained as a column.
- **If the selected models expose reasoning controls, what is the default reasoning budget?**
  - Default: `reasoning_budget: none`
  - Interpretation for the default main analysis: use `none` when the provider allows disabling explicit reasoning, otherwise use `low` or the mildest equivalent exposed by that model family.
  - If a provider exposes reasoning as a separate model choice rather than an in-model budget, treat the model ID itself as the fixed reasoning configuration.
  - Save the effective provider-specific reasoning configuration in metadata and keep it fixed within each replicate set.
  - Do not use `xhigh`, `max`, `deep think`, `Speciale`, or analogous long-think modes by default.
  - Provider-specific examples:
    - OpenAI GPT-5.x: `reasoning.effort: none` for the default structured-scoring pass; test `low` only in a separate benchmark pass.
    - Gemini 3 Pro Preview: `thinkingLevel: low`
    - Anthropic Claude: leave extended thinking off for the default pass; if a benchmark pass enables it, keep `thinking.budget_tokens` modest and fixed.
    - DeepSeek: select `deepseek-chat` for the standard pass or `deepseek-reasoner` for an explicit reasoning benchmark; do not mix them within one replicate group.
- **Should the script automatically merge the output datasets with the user's original dataset?** `yes/no`
  - Default: no.
  - If yes, the script should still write the same two output files, `output_ds_inclusive_long.csv` and `output_ds_summaried_wide.csv`, but these files should also include the columns from the user's original dataset.
- **Should the output from the LLM be treated as metric data, ordinal data, or categorical data?** `metric/ordinal/categorical`
  - Default: metric. 
  - If metric, the aggregation implies calculating the mean and the standard deviation, for example: `{"mean_item_1": 4.82, "standard_deviation_item_1": 0.71, "n_successful_parses_item_1": 100}`
  - If ordinal, compute the median plus dispersion (IQR/MAD), for example: `{"median_item_1": 5, "iqr_item_1": 1, "mad_item_1": 0.5, "n_successful_parses_item_1": 100}`
  - If categorical, the aggregation implies reporting the most frequent response plus all the options with the corresponding percentage occurrence, for example: `{"most_frequent_category_item_1": "category_1", "categories_frequencies_item_1": {"category_1": 0.75, "category_2": 0.25}, "n_successful_parses_item_1": 100}`
  - Note: we also have to save all the metadata specified in the `### Metadata to store` subsection under `## What to do with the JSON outputs`.
  - Note: `item_1` refers to the fact the LLM might be asked to score the texts on multiple variables at the same time. 
  - Note: the conceptual meaning of `item_1`, `item_2`, etc. should be explained in the analysis-instructions text file, not in the runtime comments of `config.yaml`.
  - Note for the user: in case they want the LLMs to use different types of data for the same analysis (e.g., one ordinal item and one categorical item), we recommend running the analysis multiple times with different configurations.


### LLM dictionaries

The model lists below are examples of candidate LLM groups that can be stored in `config.yaml`. They should be treated as version-pinned defaults, reviewed periodically, and kept separate by purpose: low-cost testing, default frontier analysis, and optional benchmark/robustness passes.

#### 1. Low-cost testing set (`cheap_set`)

Use this set to check whether the script works end to end before running the full analysis. The goal here is low cost and fast turnaround, not maximum performance.

Before using real API-backed models from this set, the initial pipeline wiring should first be checked with a repo-local mock provider so the end-to-end flow can be tested without network calls, API keys, or provider-side variability.

Recommended reasoning setting:

- `reasoning_budget: none`

Suggested models by provider:

- `openai`: `gpt-5-nano`, `gpt-4.1-mini`
- `gemini`: `gemini/gemini-2.5-flash-lite`
- `anthropic`: `anthropic/claude-haiku-4-5`
- `mistral`: `mistral/ministral-8b-2512`, `mistral/mistral-small-2506`
- `deepseek`: `deepseek-chat`
- `qwen`: `together_ai/Qwen/Qwen3.5-9B`

#### 2. Frontier main-analysis set (`frontier_main_analysis_set`)

Use this set for the default main analysis. It should prioritize the most up-to-date frontier models by intelligence rather than keeping older lighter models in the main set just because they are cheaper.

Recommended reasoning setting:

- `reasoning_budget: none`
- If a provider does not expose `none`, use `low` or the mildest equivalent and keep it fixed within the replicate set.

Suggested models by provider:

- `openai`: `gpt-5.4`
- `gemini`: `gemini/gemini-3.1-pro-preview`
- `anthropic`: `anthropic/claude-opus-4-6`
- `mistral`: `mistral/mistral-large-2512`
- `deepseek`: `deepseek-chat`, `deepseek-reasoner`
- `qwen`: `together_ai/Qwen/Qwen3.5-397B-A17B`
- `meta_llama`: `together_ai/meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8`
- `minimax`: `together_ai/MiniMaxAI/MiniMax-M2.5`
- `kimi`: `together_ai/moonshotai/Kimi-K2.5`

Notes:

- `gemini/gemini-3.1-pro-preview` is a preview model, so the pipeline should save the exact provider-exposed version metadata for auditability.
- `🔴` Confirm the exact account-exposed alias for `gpt-5.4`, `gemini/gemini-3.1-pro-preview`, and `anthropic/claude-opus-4-6` before freezing `config.yaml`; public provider docs may surface slightly different names than the routed LiteLLM-style IDs used here.
- `🔴` If the deployment must stay Together-routed for DeepSeek, the explicit fallback is `together_ai/deepseek-ai/DeepSeek-V3.1`. Keep that fallback out of the default frontier set because it lags the native DeepSeek V3.2 `deepseek-chat` / `deepseek-reasoner` pair.

Older strong-but-lighter defaults such as `gpt-4.1`, Gemini Flash variants, `claude-sonnet-4-6`, `mistral-medium-2508`, `together_ai/deepseek-ai/DeepSeek-V3.1`, and older Qwen 3 entries should stay in testing, fallback, or secondary benchmark roles rather than in the default frontier main-analysis set.

#### 3. Optional benchmark / robustness set (`frontier_benchmark_set`)

Use this set only for targeted benchmark or robustness passes. It is not the default for repeated main-analysis scoring.

Recommended reasoning setting:

- `reasoning_budget: low`
- Keep the provider-specific resolved reasoning configuration fixed within each replicate set and save it in metadata.
- Do not use `xhigh`, `max`, `deep think`, `Speciale`, or analogous long-think modes as the default benchmark setting either.

Suggested additions or variants:

- `openai`: the same frontier model with `reasoning.effort: low`
- `gemini`: the same frontier model with `thinkingLevel: low`
- `anthropic`: the same frontier model with extended thinking enabled only if the study explicitly wants that benchmark
- `mistral`: `mistral/magistral-medium-2509`
- `deepseek`: `deepseek-reasoner`
- `zai`: `together_ai/zai-org/GLM-5` only if the routed endpoint is confirmed in the target environment

## Low-temperature implementation strategy

Because this project is designed mainly for deductive-style scoring, the later scripts should implement temperature as a fixed, low, auditable parameter rather than as a default source of intentional variation. The same fixed-configuration principle should apply to reasoning controls when they are used.

### Suggested config fields

```yaml
model_set: frontier_main_analysis_set
temperature_policy: fixed_low
temperature_default: 0.0
reasoning_budget: none
prompt_template_file: prompt_template_main_analysis.txt
```

### Implementation rules

1. `call_llm.py` should read the temperature policy from `config.yaml`, use the fixed low temperature specified there, leave other sampling parameters at provider defaults, and save both `requested_temperature` and `effective_temperature`.
2. Main-analysis replicates should repeat the same prompt at the same fixed low temperature for each replicate set.
3. `parse_outputs.py` should prefer schema-constrained structured outputs whenever the provider supports them, validate each output against the expected schema, store validation errors verbatim, and fall back to post hoc JSON validation only when necessary.
4. `aggregate_outputs.py` should compute the primary summary statistics within the fixed low-temperature runs.
5. `sanity_checks.py` should flag malformed JSON, missing fields, out-of-range scores, temperature drift within a call group, unexpectedly identical outputs, and unusually high between-replicate variance under fixed low temperature.
6. If models expose reasoning controls, the effective reasoning configuration should remain fixed within each replicate set and be saved as metadata.


---

## Prompt composition

A general LLM prompt should be built from modular components.

### Base prompt structure

1. **General instructions**
2. **Task-specific information**
3. **Writing sample**
4. **Optional comparison sample**
5. **Output-format instructions**


### Prompt template logic

```text
[Instructions for the LLM analysis]

[JSON output request format with additional details]

[Task-specific information]

[Writing sample] 

[If comparative task: comparison text with corresponding task-specific information]

```

The different parts of the prompt sent to the LLM have to be merged by a Python script and will have the following origins:
1. The prompts/ folder, containing a file called something like `prompt_template_main_analysis.txt` or `prompt_template_comparative_analysis.txt` (depending on the analysis to be conducted) and will contain a pre-filled text for [Instructions for the LLM analysis] and [JSON output request format with additional details]. The Python script should read the exact prompt-template filename from `config.yaml`, since the user might be working with different prompt templates (for example, different prompts can ask the LLM to identify different variables in the texts).
2. The [Writing sample] section of the prompt will come from the CSV file, variable named `participant_text`. 
3. The [Task-specific information] is a mix of the information in the variable `task_info` and the precise text the participant received, contained in the variable `task_full_text`. 

Note: we want to allow, as an optional configuration, a more "minimal" CSV file, which does not contain the entire texts and information, but instead points to other files containing the entire texts and information. The options are:
- The CSV file does not contain the entire texts from participants to be analysed, but the `participant_text` column contains, in each cell, the precise name of the text file (one per text to be analysed), which we will store here: `data/qualitative_data/text_files`.
- The CSV does not contain the information on each task of the study (the columns `task_info` and `task_full_text` will be absent or empty), so the Python script, when composing the prompt, needs to get the value from the `task_id` variable and retrieve all the task-specific information to be included in the prompt for the LLM stored here: `prompts/task_descriptions.yaml`. The user has to customize this.

Note: When writing the README.md file, we have to remind the user that they have to update not only the config file with their preferences, but also the files in the `prompts/` folder.



### Important implementation detail

If the CSV stores only a short task label such as `prompt_1`, Python should be able to:

- detect that label,
- look up the full task description,
- and replace the short label with the full wording inside the final prompt.

In this case, the prompt descriptions should be stored in `prompts/task_descriptions.yaml`.

For example:

```yaml
prompt_1:
  task_info: "Participants were asked to reflect on a meaningful life event."
  task_full_text: "Please describe a life event that still feels meaningful to you today."

prompt_2:
  task_info: "Participants were asked to compare their current reflection with an earlier one."
  task_full_text: "Read the current reflection in relation to the earlier reflection and evaluate whether it is deeper, more self-reflective, and more emotionally nuanced."
```

---

## Comparative-task branch

If the task is comparative, the prompt should explicitly include the reference text to compare against. The prompt should also include information about the task description specific to the reference text, exactly as it does for the main text.

### Comparative prompt logic

- Insert the focal writing sample.
- Insert the comparison sample.
- Specify the comparison criterion.
  - e.g., deeper, clearer, more self-reflective, more emotionally nuanced.
- Specify the output required.
  - e.g., forced choice, relative score, etc 

This should use a dedicated prompt template. 

---

## Validation and typed contracts

The pipeline should use Pydantic models as the internal contract layer for:

- config loading and validation
- input-row validation after reading CSV/YAML sources
- provider request/response objects
- parsed LLM outputs
- metadata records written to outputs
- diagnostics and sanity-check records

Each prompt template / prompt version should correspond to an explicit output schema. When a provider supports schema-constrained structured outputs, the pipeline should use the schema associated with that analysis rather than relying only on prompt wording.

The parser should validate raw JSON outputs against the relevant schema and distinguish at least:

- `valid`
- `invalid_json`
- `schema_mismatch`
- `missing_field`

---

## Expected LLM output

The intended output format is JSON.

The JSON should conform to the schema associated with the selected prompt template / prompt version.

### Example JSON schema

```json
{
  "item_1_score": 6,
  "item_1_justification": "The text reflects on the meaning of the experience and links it to a change in self-understanding.",
  "item_2_score": 5,
  "item_2_justification": "The emotional content is present and somewhat differentiated, though not highly elaborate.",
  "item_3_score": 4,
  "item_3_justification": "The writing shows moderate nuance but remains partly descriptive rather than deeply interpretive.",
  "other_notes": "The sample is coherent and clearly written."
}
```

Before an output is treated as successfully parsed, the pipeline should validate that it is valid JSON and that it contains the expected keys required by the schema for that analysis.

### Possible additional fields

Depending on the project, the JSON could also include:

- `language_detected`
- `confidence`
- `flag_for_review`
- `reason_for_flag`
- `comparison_direction`
  - for comparative tasks

---

## What to do with the JSON outputs

Each LLM response should be saved with metadata.
Provider-side call failures should also be preserved as structured call rows once request
metadata is available, rather than being dropped as exception-only events.

### Metadata to store

- `run_id`
  - unique identifier for each individual LLM call row saved in `output_ds_inclusive_long.csv`
- `model_provider`
- `model_name`
- `server_side_version` if exposed by the provider
  - e.g., `model_version`, `system_fingerprint`, backend revision, or any other provider-exposed version field
- `method_name`
- `date`
- `time`
- `requested_temperature`
- `effective_temperature`
- `reasoning_budget` if used
- `reasoning_config`
  - save the effective provider-specific setting or fixed reasoning-model mode, such as `reasoning.effort: none`, `thinkingLevel: low`, or `deepseek-chat`
- `seed` if available
- `prompt_template_file`
  - e.g., `prompt_template_main_analysis.txt` or `prompt_template_comparative_analysis.txt`
- `prompt_version`
- `task_type`
- `effective_prompt`
  - the fully rendered prompt actually sent to the LLM after all template fields, task information, and text content have been inserted
- `raw_json_output`
- `parse_status`
  - recommended values: `valid`, `invalid_json`, `schema_mismatch`, `missing_field`, `provider_error`
- `validation_error`
  - store the validation error message verbatim if validation fails
- `error_message`
  - store the provider-side error message verbatim when a call fails before returning valid JSON

### Then the pipeline should:

1. Save every LLM call in `output_ds_inclusive_long.csv`, with one unique `run_id` per row.
2. If a provider call fails after request metadata is known, save that attempt as a structured row with `parse_status='provider_error'` and the provider error message rather than surfacing it only as an exception.
3. Compute summary statistics across repeated calls according to the config choice for `metric/ordinal/categorical` data.
4. Save those summaries in `output_ds_summaried_wide.csv`.
5. Run sanity checks and write the diagnostic output.
6. It is also acceptable to save additional files in `outputs/` when useful, such as intermediate tables, manifests, logs, or debugging artifacts.
7. The two canonical user-facing output datasets should still be `output_ds_inclusive_long.csv` and `output_ds_summaried_wide.csv`.
8. Depending on the config file, leave the two output datasets as standalone files or merge them with the original CSV dataset before saving them.

---

## Repeated calls

One of the key ideas in your sketch is to treat all identical repeated calls as a clearly defined **call-group** inside `output_ds_inclusive_long.csv`.

Each call-group means:

- same input sample,
- same model,
- same prompt template,
- same method,
- same fixed `requested_temperature` and `effective_temperature` within each call group.

In other words, repeated calls in the default main analysis should keep a fixed low temperature for each `row_id × model × prompt_version × method` combination.

### Purpose

Run repeated calls such as `N = 100` in order to estimate:

- stability of scores,
- variability across generations,
- central tendency,
- representativeness of justifications.

### Summary statistics to compute

For each item and call-group, the exact summary statistics should depend on the config choice for `metric/ordinal/categorical` data:

- If `metric`: mean score, standard deviation, minimum, and maximum.
- If `ordinal`: median, IQR, and MAD.
- If `categorical`: most frequent category and category frequencies/percentages.
- For all data types: number of successful parses and number of flagged outputs.

This call-group logic is what feeds the summarized wide output dataset and can also support later multilevel or reliability-oriented analyses.

---

## Justification handling

The sketch suggests keeping only a limited number of justifications in `output_ds_summaried_wide.csv`.

### Candidate strategy

For each item:

- retain all raw justifications in `output_ds_inclusive_long.csv`,
- compute the relevant summary target across repeated calls,
- keep a small number of representative justifications,
- ideally select justifications attached to outputs close to that summary target.

### Possible rule

Save:

- if `metric`, the 3 justifications whose scores are closest to the mean,
- if `ordinal`, the 3 justifications whose scores are closest to the median,
- if `categorical`, 3 typical justifications from outputs belonging to the modal category,
- or, more generally, the 3 most typical outputs after filtering malformed responses.

This avoids clutter while preserving interpretable examples.

---

## Output datasets

The two required user-facing output datasets are `output_ds_inclusive_long.csv` and `output_ds_summaried_wide.csv`. Beyond those two files, it is acceptable, and even desirable for now, to save additional files in `outputs/` if they help transparency, debugging, robustness checks, or later extensions of the pipeline.

### 1. Inclusive long output dataset

File name: `output_ds_inclusive_long.csv`

This is the most inclusive user-facing output file. It should be in long format, with one row per LLM call. The file should contain a `run_id` column that uniquely identifies each row. There will be multiple rows for the same `row_id` whenever repeated calls are made for the same original text.

Depending on the config choice about automatic merging, this file should either:

- remain a standalone LLM-output file, or
- include the columns from the user's original dataset alongside the LLM-output columns.

Suggested columns:

- `run_id`
- `row_id`
- `participant_id`
- `task_id`
- `model_name`
- `method_name`
- `requested_temperature`
- `effective_temperature`
- `replicate_id`
- `item_1_score`
- `item_1_justification`
- `item_2_score`
- `item_2_justification`
- `...`
- `raw_json_output`
- `parse_status`
- `validation_error`

### 2. Summarized wide output dataset

File name: `output_ds_summaried_wide.csv`

This file is meant for easier presentation and downstream analysis. It should be in wide format, with one row per original `row_id`. Summary columns should be added for each `item × model × method` combination.

Depending on the config choice about automatic merging, this file should either:

- remain a standalone summarized file keyed by `row_id`, or
- include the columns from the user's original dataset alongside the summary columns.

The exact summary columns depend on whether the outputs are treated as `metric`, `ordinal`, or `categorical` in the config file. The list below shows examples of possible columns rather than a single mandatory set to include all at once.

Suggested columns:

- `row_id`
- `participant_id`
- `task_id`
- `item_1_score_mean__model_modelA__method_method1`
- `item_1_score_sd__model_modelA__method_method1`
- `item_1_median__model_modelA__method_method1`
- `item_1_iqr__model_modelA__method_method1`
- `item_1_most_frequent_category__model_modelA__method_method1`
- `item_1_categories_frequencies__model_modelA__method_method1`
- `item_1_n_successful_parses__model_modelA__method_method1`
- `item_1_justification_1__model_modelA__method_method1`
- `item_1_justification_2__model_modelA__method_method1`
- `item_1_justification_3__model_modelA__method_method1`
- `...`

---

## Variable naming logic

Your sketch suggests variable names like:

- `item1_score_gemini3_mean_method1`
- `item1_score_gemini3_sd_method1`
- `item1_justification1_gemini3_method1`

A cleaner, machine-friendly naming style would be:

- `item1_score_mean__model_gemini25__method_v1`
- `item1_score_sd__model_gemini25__method_v1`
- `item1_justification_1__model_gemini25__method_v1`

That naming scheme is verbose but usefully explicit. It is easier to parse programmatically.

---

## Long vs. wide format

A note in the sketch suggests that **long format may be preferable** in some places.

That is a reasonable default.

### Recommendation 

Use:

- **long format** for `output_ds_inclusive_long.csv`,
- **wide format** for `output_ds_summaried_wide.csv`.

If the config file requests automatic merging with the original dataset, that merge should not change the basic long/wide structure of the corresponding output file.

This gives you:

- easier aggregation and diagnostics during processing,
- easier modeling and reporting later.

---

## Grouping factors

Important grouping factors in the project include:

- LLM model
- prompting method
- task_id
- participant_id
- row_id (since we are getting multiple LLM output per row of the original CSV file)

Example R script:

```R
library(brms)

fit <- brm(
    DV ~ LLM_score + 
      (1 + LLM_score | row_id) + 
      (1 + LLM_score | participant_id) + 
      (1 + LLM_score | task_id) + 
      (1 + LLM_score | LLM_model) +
      (1 + LLM_score | prompting_method),
    data = ds, 
    family = gaussian(),
    chains = 4,
    cores = 4,
    iter = 4000
)
```

Where DV is a variable of the original dataset that we want to predict (e.g., self-reported reflective depth). 


---

## Sanity checks

The pipeline should include automatic checks such as:

- Was the JSON parsed successfully?
- Are all expected items present?
- Are scores within range?
- Are justifications non-empty?
- Are repeated calls unexpectedly identical?
- Are there cases of temperature drift within a supposedly identical call group?
- Is between-replicate variance unexpectedly high even under low temperature?
- Are some models producing systematically malformed outputs?


---

## Suggested project structure

```text
qual_analysis_project/
│
├── data/
│   └── qualitative_data/
│       ├── audio_files/
│       ├── text_files/
│       ├── qualitative_data_long.csv
│       └── qualitative_data_comparative_wide.csv
│
├── outputs/
│   ├── output_ds_inclusive_long.csv
│   ├── output_ds_summaried_wide.csv
│   ├── diagnostics/
│   │   └── sanity_checks.csv
│   ├── intermediate/
│   │   ├── repeated_call_groups.csv
│   │   └── parsed_outputs_debug.csv
│   └── logs/
│       └── run_manifest.csv
│
├── prompts/
│   ├── prompt_template_main_analysis.txt
│   ├── prompt_template_comparative_analysis.txt
│   └── task_descriptions.yaml
│
├── scripts/
│   ├── build_prompt.py
│   ├── long_to_wide.py
│   ├── call_llm.py
│   ├── parse_outputs.py
│   ├── aggregate_outputs.py
│   └── sanity_checks.py
│
├── .env
├── .gitignore
├── config.yaml
├── README.md
└── pyproject.toml
```

---

## Short conceptual summary
**CSV in -> prompt builder -> repeated LLM calls -> `output_ds_inclusive_long.csv` -> config-dependent summary statistics -> `output_ds_summaried_wide.csv` -> optional merge with the original dataset**
