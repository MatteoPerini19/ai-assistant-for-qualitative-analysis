# AI Qualitative Analysis Blueprint

## Project goal

Build a Python pipeline that helps **quantize qualitative data** by sending writing samples to one or more LLMs, collecting structured ratings and justifications, repeating calls when needed, and merging the resulting outputs back into the original dataset for analysis.

---

## Core idea

The pipeline should:

1. Read a CSV containing writing samples (one per row) and, if present, information about the specific task from which the writing sample comes from (in case the task was not the same for all the writing samples). Note: in some cases, we won't have a writing sample, but the name of a file containing the writing sample and/or an audio file (at last one per row). 
2. Build an LLM prompt from reusable components.
3. Ask the LLM to score one or more qualitative dimensions.
4. Request a structured JSON output with scores and justifications.
5. Save the raw output together with metadata.
6. Optionally repeat identical calls many times to estimate variability.
7. In case of repeat identical calls, compute summary statistics such as means and standard deviations.
8. Merge the outputs with the original CSV dataset into an analysis-ready table.

---

## Data structure

The input dataset should use one row per analyzable participant contribution. In the most common case, that means one writing sample per row, but the same structure can also support transcripts and audio-based submissions by storing either the text directly in the CSV or a reference to an external file. The goal is to preserve a stable row-level unit that can be sent to the LLM, traced back to the original source, and merged cleanly with downstream outputs.

- `row_id`
  - Unique indentified of the row (e.g., row_001).  
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
  - The participant's text to be evaluated. This variable is alternative to `text_file_name`.
- `text_file_name`
  - Name of the text file containing the task-specific participant's written text or transcript. This variable is alternative to `participant_text`.
- `audio_file_name`
  -  Optional. Name of the audio file containing the task-specific participant's voice recording.
- `language`
  - Language of the writing sample (e.g., EN, NL)
- `condition`
  - Optional. Experimental condition (e.g., treatment, control).
- `wave`
  - Optional. Longitudinal wave or time point (e.g., wave_01).


Note: Our software wants to allow for a comparative analysis in which the LLM will directly compare two texts (e.g., the two texts written by the same participant under two different experimental conditions). In this case, we need to create a second version of the CSV file which will be in a *wide* format, presenting on the same row the texts to be compared. In this case, instead of rows such as `participant_text` and `task_id` we will have 
`participant_text_1` and `task_id_1`, and `participant_text_2` and `task_id_2`.

---

## Config file

The project should expose a config file or config object with decisions such as:

- **Run mode?** `run_mode: testing`/`run_mode: main_analysis`.
  - Default: `run_mode: testing`
- **Include task-specific info in the prompt for the LLM?** `yes/no`. Dafault: yes
- **Where is the task info stored?**
  - in a CSV column
  - in a separate file
  Default: in the CSV file. 
- **Is the analysis comparative?** `yes/no`
  - Default: no. 
  - This means that the LLM is not giving an absolute score to a text, but comparing it with another text (how this is asked is still to be decided, but to the least it will involved a choice between who is higher the evaluation dimension)
  - If yes, use an alternative prompt template 
  - Probably we should build a separate script for this 
  - For the comparative analysis, we should recommend the user to have a separate CSV file in a wide format with the texts to compare presented on the same row. 
  - We should write a separate script for transforming the CSV file from long to wide based on the variable names listed in the "Dataset structure" section of this blueprint.
- **Which prompt template file should be used for the current analysis?**
  - Store the exact prompt-template filename in `config.yaml`.
  - Example: `prompt_template_file: prompt_template_main_analysis.txt`
  - If the analysis is comparative, the default template is `prompt_template_comparative_analysis.txt`.
  - If the analysis is not comparative, the default template is `prompt_template_main_analysis.txt`.
  - The Python script should read the exact prompt-template filename from `config.yaml` rather than hard-coding prompt names, because users may work with multiple prompt templates targeting different variables.
- **Which scoring instructions should the LLM use?**
  - e.g., `1-7 scale`, `0-100 scale`, categorical labels, etc. Dafault: 1-10
- **Temperature.**
  Default: fixed low temperature for deductive scoring.
  - Default if `run_mode: testing`: `0.0`
  - Default if `run_mode: main_analysis`: `0.0`
  - Optional fallback if exact zero performs poorly for a given model or provider: `0.1`
  - Recommended main-analysis range for deductive scoring: `0.0` to `0.2`
  - Provider/model exception path: if official documentation recommends against lowering temperature for a model family, use the provider default and record the override in metadata.
  - If a provider/model override requires using a non-low provider default, that run should be treated as a model-specific exception analysis and should not be pooled into the default fixed-low main analysis unless the user explicitly chooses to do so.
- **How many repeated calls should be made per identical prompt?**
  - Default if `run_mode: testing`: 3.
  - Default if `run_mode: main_analysis`: 100.
- **When multiple calls are launched, will the temperature stay always the same or change?** 
  Default: it should stay the same within the main analysis. Repeated calls for the same `row_id × model × prompt_version × method` combination should use the same low temperature. Optional temperature variation should be implemented only as a separate robustness module and should not be pooled into the primary score by default.
- **Which LLMs should be used?**
  -  In the config file there will be dictionaries of LLMs that can be customized (see section below). 
  - Default if `run_mode: testing`: cheap_set.
  - Default if `run_mode: main_analysis`: top_non_reasoning_set.
- **How many justifications should be saved in the final dataset, in case we are averaging across many different calls?**
  - Default if `run_mode: testing`: 3.
  - Default if `run_mode: main_analysis`: 100.
- **Should all raw outputs be saved?** `yes/no`. Default: yes. 
- **In case thinking models are used, what is the thinking budget?** 🔴 TO BE DECIDED 🔴
- **Should the output from the LLM be treated as metric data, ordinal data, or categorical data?**
  - If metric, the aggregation implies calculating the mean and the standard deviation, for example: `{"mean_item_1": 4.82, "standard_deviation_item_1": 0.71, "n_successful_parses_item_1": 100}`
  - If ordinal, compute the median plys dispersion (IQR/MAD), for example: `{"median_item_1": 5, "iqr_item_1": 1, "mad_item_1": 0.5, "n_successful_parses_item_1": 100}`
  - If categrorial, the aggregation implies reporting the most frequent response plus all the options with the corrisponding percentage occurrance, for example: `{"most_frequent_category_item_1": "category_1", "categories_frequencies_item_1": {"category_1": 0.75, "category_2": 0.25}, "n_successful_parses_item_1": 100}`
  - Note: we also have to save all the metadata specified in the `### Metadata to store` subsection under `## What to do with the JSON outputs`.
  - Note: `item_1` refers to the fact the LLM might be asked to score the texts on multiple variables at the same time. 
  - Default: metric. 


### LLM dictionaries

The model lists below are examples of candidate LLM groups that can be stored in `config.yaml`. They were drafted in March 2026, so they should be treated as a starting point rather than a permanent recommendation.

#### 1. Low-cost testing set

Use this set to check whether the script works end to end before running the full analysis. The goal here is low cost and fast turnaround, not maximum performance.

Recommended thinking setting:

- `thinking_budget: 0`

Suggested models by provider:

- `openai`: `gpt-4.1-nano`, `gpt-5-nano`, `gpt-4.1-mini`
- `gemini`: `gemini/gemini-2.5-flash-lite`
- `anthropic`: `anthropic/claude-haiku-4-5`
- `mistral`: `mistral/ministral-3b-2512`, `mistral/ministral-8b-2512`, `mistral/mistral-small-2506`
- `deepseek`: `together_ai/deepseek-ai/DeepSeek-V3.1`
- `qwen`: `together_ai/Qwen/Qwen3.5-9B`
- `meta_llama`: `together_ai/meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8`
- `minimax`: `together_ai/MiniMaxAI/MiniMax-M2.5`
- `kimi`: `together_ai/moonshotai/Kimi-K2.5`

#### 2. Strong non-reasoning set

Use this set for the main analysis when you want strong models but do not want to activate explicit reasoning or high-thinking modes.

Recommended thinking setting:

- `thinking_budget: 0`

Suggested models by provider:

- `openai`: `gpt-4.1`, `gpt-4.1-mini`
- `gemini`: `gemini/gemini-3-flash-preview`, `gemini/gemini-2.5-flash`
- `anthropic`: `anthropic/claude-sonnet-4-6`
- `mistral`: `mistral/mistral-large-2512`, `mistral/mistral-medium-2508`, `mistral/mistral-small-2506`
- `deepseek`: `together_ai/deepseek-ai/DeepSeek-V3.1`
- `qwen`: `together_ai/Qwen/Qwen3.5-397B-A17B`, `together_ai/Qwen/Qwen3-Next-80B-A3B-Instruct`, `together_ai/Qwen/Qwen3-235B-A22B-Instruct-2507-tput`
- `meta_llama`: `together_ai/meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8`, `together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo`
- `minimax`: `together_ai/MiniMaxAI/MiniMax-M2.5`
- `kimi`: `together_ai/moonshotai/Kimi-K2.5`

#### 3. Reasoning set

Use this set when the study explicitly wants models with stronger reasoning behavior, while still avoiding the most expensive extreme settings.

Recommended thinking setting:

- `thinking_budget: > 0`
- exact value: 🔴 TO BE DECIDED 🔴

Suggested models by provider:

- `openai`: `gpt-5.1`, `gpt-5`, `gpt-5-mini`
- `gemini`: `gemini/gemini-3.1-pro-preview`, `gemini/gemini-2.5-pro`, `gemini/gemini-2.5-flash`
- `anthropic`: `anthropic/claude-sonnet-4-6`
- `mistral`: `mistral/magistral-medium-2509`, `mistral/magistral-small-2509`
- `deepseek`: `together_ai/deepseek-ai/DeepSeek-R1`, `together_ai/deepseek-ai/DeepSeek-V3.1`
- `qwen`: `together_ai/Qwen/Qwen3.5-397B-A17B`, `together_ai/Qwen/Qwen3-235B-A22B-Instruct-2507-tput`
- `meta_llama`: `together_ai/meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8`, `together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo`
- `minimax`: `together_ai/MiniMaxAI/MiniMax-M2.5`
- `kimi`: `together_ai/moonshotai/Kimi-K2.5`

## Low-temperature implementation strategy

Because this project is designed mainly for deductive-style scoring, the later scripts should implement temperature as a fixed, low, auditable parameter rather than as a default source of intentional variation.

### Suggested config fields

```yaml
temperature_policy: fixed_low
temperature_default: 0.0
temperature_fallback: 0.1
temperature_max_main_analysis: 0.2
vary_temperature_in_main_analysis: false
temperature_robustness_grid: [0.0, 0.1, 0.2]
prompt_template_file: prompt_template_main_analysis.txt
model_temperature_overrides:
  gemini/gemini-3-flash-preview: null
```

Here, `null` means "use the provider default and record that override in metadata."

If a model-specific override requires the provider default rather than a low temperature, that run should be treated as a model-exception analysis and should not be pooled into the default fixed-low main analysis unless the user explicitly requests it.

### Implementation rules

1. `call_llm.py` should read the temperature policy from `config.yaml`, apply any model-specific override, leave other sampling parameters at provider defaults unless they are being explicitly tested, and save both `requested_temperature` and `effective_temperature`.
2. Main-analysis replicates should repeat the same prompt at the same low temperature. If a provider/model exception requires a non-low provider default, that exception run should still keep a fixed `effective_temperature` within each replicate set, be clearly labeled in metadata, and be written to separate outputs or otherwise excluded from the default fixed-low pooled analysis. If a temperature sweep is run, it should be executed in a separate robustness mode and written to separate files rather than merged into the primary results.
3. `parse_outputs.py` should prefer schema-constrained structured outputs whenever the provider supports them, validate each output against the expected schema, store validation errors verbatim, and fall back to post hoc JSON validation only when necessary.
4. `aggregate_outputs.py` should compute the primary summary statistics only within the fixed low-temperature runs. Alternative-temperature summaries should be labeled as robustness outputs rather than treated as the default score.
5. `sanity_checks.py` should flag malformed JSON, missing fields, out-of-range scores, temperature drift within a call group, unexpectedly identical outputs, and unusually high between-replicate variance even under low temperature.
6. If thinking models are used, the thinking budget should remain fixed within each replicate set and be saved as metadata.


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

Note: we want to allow, as an optiona configuration, to have a more "minimal" CSV file, which does not contain the entire texts and information, but point at other files containing the entire texts and information. The options are:
- The CSV file does not contain the entire texts from participants to be analysed, but the `participant_text` column just contain, in each cell, the precise name of the text files (one per text to be analysed), which we will store here: data/qualitative_data/text_files.
- The CSV does not contain the information on each task of the study (the columns `task_info` and `task_full_text` will be absent or empty), so the Python script, when composing the prompt, needs to get the value from the `task_id` variable and retrive all the task-specific information to be included in the prompt for the LLM stored here: `prompts/task_descriptions.yaml`. The user has to customize this. 

Note: When writing the README.md file, we have to remind the user that he has not only to update config file with his preferences, but also the files in the prompts/ folder. 



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

If the task is comparative, the prompt should explicitly include the reference text to compare against. The prompt should also include information about the task desciption specific to the reference text, exactly as it does for the main text. 

### Comparative prompt logic

- Insert the focal writing sample.
- Insert the comparison sample.
- Specify the comparison criterion.
  - e.g., deeper, clearer, more self-reflective, more emotionally nuanced.
- Specify the output requried.
  - e.g., forced choice, relative score, etc 

This should use a dedicated prompt template. 

---

## Expected LLM output

The intended output format is JSON.

Whenever the provider supports schema-constrained structured outputs, the pipeline should use them instead of relying only on prompt instructions. This should reduce malformed responses and make parsing more reliable. If a provider does not support schema-constrained outputs, the fallback should be to request JSON in the prompt and then validate it after generation.

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

Before an output is treated as successfully parsed, the pipeline should validate that it is valid JSON and that it contains the expected keys required by the schema for that analysis. Validation should distinguish at least `valid`, `invalid_json`, `schema_mismatch`, and `missing_field` outcomes rather than collapsing all failures into a single parse flag.

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

### Metadata to store

- `model_provider`
- `model_name`
- `server_side_version` if exposed by the provider
  - e.g., `model_version`, `system_fingerprint`, backend revision, or any other provider-exposed version field
- `method_name`
- `date`
- `time`
- `requested_temperature`
- `effective_temperature`
- `thinking_budget` if used
- `seed` if available
- `prompt_template_file`
  - e.g., `prompt_template_main_analysis.txt` or `prompt_template_comparative_analysis.txt`
- `prompt_version`
- `task_type`
- `effective_prompt`
  - the fully rendered prompt actually sent to the LLM after all template fields, task information, and text content have been inserted
- `raw_json_output`
- `parse_status`
  - recommended values: `valid`, `invalid_json`, `schema_mismatch`, `missing_field`
- `validation_error`
  - store the validation error message verbatim if validation fails

### Then the pipeline should:

1. Save all raw outputs.
2. Create a combined file containing all LLM outputs.
3. Compute summary statistics and sanity checks.
4. Merge results back with the original CSV.

---

## Repeated calls and robustness

One of the key ideas in your sketch is to create an **intermediate file with all identical calls**.

This means:

- same input sample,
- same model,
- same prompt template,
- same method,
- same fixed `requested_temperature` and `effective_temperature` within each call group.

In other words, repeated calls in the default main analysis should keep a fixed low temperature for each `row_id × model × prompt_version × method` combination. If a provider/model exception requires a non-low provider default, that exception run should still keep a fixed `effective_temperature` within its own call group and should not be pooled into the default fixed-low analysis unless the user explicitly chooses to do so. Separate temperature sweeps should belong only to an explicit robustness module and should not be treated as part of the default identical-call group.

### Purpose

Run repeated calls such as `N = 100` in order to estimate:

- stability of scores,
- variability across generations,
- central tendency,
- representativeness of justifications.

### Summary statistics to compute

For each item and call-group:

- mean score
- standard deviation
- minimum and maximum
- number of successful parses
- number of flagged outputs

This intermediate repeated-call file can also support later multilevel or reliability-oriented analyses.

---

## Justification handling

The sketch suggests keeping only a limited number of justifications in the final dataset.

### Candidate strategy

For each item:

- save all raw justifications in a long-format file,
- compute the mean score across repeated calls,
- keep a small number of representative justifications,
- ideally select justifications attached to outputs close to the mean.

### Possible rule

Save:

- the 3 justifications whose scores are closest to the mean,
- or the 3 most typical outputs after filtering malformed responses.

This avoids clutter while preserving interpretable examples.

---

## Output tables

### 1. Raw output table

One row per LLM call.

Suggested columns:

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

### 2. Aggregated output table

One row per unique `row_id × method × model` combination in the default fixed-low main analysis. If separate temperature sweeps or model-exception temperatures are included, aggregate instead by unique `row_id × method × model × effective_temperature` combination.

Suggested columns:

- `row_id`
- `participant_id`
- `task_id`
- `model_name`
- `method_name`
- `effective_temperature`
- `item_1_score_mean`
- `item_1_score_sd`
- `item_1_justification_1`
- `item_1_justification_2`
- `item_1_justification_3`
- `item_2_score_mean`
- `item_2_score_sd`
- `item_2_justification_1`
- `...`

### 3. Final merged analysis table

Merge aggregated outputs back into the original row-level input dataset.

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

That naming scheme is ugly, yes, but usefully ugly. It is explicit and easier to parse programmatically.

---

## Long vs wide format

A note in the sketch suggests that **long format may be preferable** in some places.

That is probably right.

### Recommendation 

Use:

- **long format** for raw outputs and repeated-call data,
- **wide format** for the final merged analysis table.

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

For separate robustness analyses, `temperature_level` may be added as an optional grouping factor. It should not be treated as a default grouping factor in the main analysis, because the main analysis is designed to use a fixed low temperature.
For model-exception analyses, `effective_temperature` should also be retained as an explicit stratification or grouping variable rather than silently pooled with fixed low-temperature runs.

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
│       └── simulated_dataset_qualitative_data.csv
│
├── outputs/
│
├── prompts/
│   ├── prompt_template_main_analysis.txt
│   ├── prompt_template_comparative_analysis.txt
│   └── task_descriptions_template.yaml
│
├── venv/
├── .env
├── .gitignore
├── config.yalm
├── README.md
└── requirements.txt
```

---

## Short conceptual summary
#NOT UPDATED
**CSV in -> prompt builder -> JSON scoring + justification -> repeated calls -> summary stats + selected justifications -> merged final analysis table**


---

## Practical next step

The next natural step is to turn this blueprint into:

- a `config.yaml` schema,
- a Python package layout,
- and one toy end-to-end script that runs on a miniature dataset.
