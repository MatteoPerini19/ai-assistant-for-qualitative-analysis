# AI Qualitative Analysis Blueprint

## Project goal

Build a Python pipeline that helps **quantize qualitative data** by sending writing samples to one or more LLMs, collecting structured ratings and justifications, repeating calls when needed, and merging the resulting outputs back into the original dataset for analysis.

---

## Core idea

The pipeline should:

1. Read a CSV containing participant-level writing samples and task information.
2. Build an LLM prompt from reusable components.
3. Ask the LLM to score one or more qualitative dimensions.
4. Request a structured JSON output with scores and justifications.
5. Save the raw output together with metadata.
6. Optionally repeat identical calls many times to estimate variability.
7. Compute summary statistics such as means and standard deviations.
8. Merge the outputs into an analysis-ready table.

---

## Recommended input data structure

The original sketch uses a very simple structure with:

- `pid`
- task-specific information
- `writing sample`

That is workable, but too bare-bones for a real project. Human beings love making future selves suffer, so here is a more useful CSV design.

### Recommended CSV columns

- `participant_id`
  - Unique participant identifier.
- `sample_id`
  - Unique identifier for the specific text sample.
- `task_id`
  - Short identifier for the task or prompt version.
- `task_label`
  - Human-readable name such as `prompt_1` or `gratitude_task_v2`.
- `task_info`
  - Short task-specific description to insert into the LLM prompt.
- `task_full_text`
  - Full wording of the participant task, if available.
- `writing_sample`
  - The participant's text to be evaluated.
- `comparison_sample_id`
  - Optional. Used only for comparative tasks.
- `comparison_sample_text`
  - Optional. The reference text for comparative evaluation.
- `language`
  - Language of the writing sample.
- `condition`
  - Experimental condition, if relevant.
- `wave`
  - Optional longitudinal wave or time point.
- `notes`
  - Optional free-text notes.

### Minimal example CSV

```csv
participant_id,sample_id,task_id,task_label,task_info,task_full_text,writing_sample,comparison_sample_id,comparison_sample_text,language,condition,wave,notes
P001,S001,T01,prompt_1,"Write about a meaningful life event","Please describe a life event that still feels meaningful to you today.","When I moved away from home, I realized how much of my identity had depended on familiar people and places...",,,English,meaning,1,
P002,S002,T01,prompt_1,"Write about a meaningful life event","Please describe a life event that still feels meaningful to you today.","I used to think success meant getting approval, but after failing an important exam I started rethinking what mattered to me...",,,English,meaning,1,
P003,S003,T02,comparison_prompt,"Compare current reflection to previous reflection","Read the participant's current text in relation to the previous one and judge whether it is deeper, more self-reflective, and more emotionally nuanced.","I now feel less angry about what happened and more curious about why it affected me so much.",S003_PRE,"At the time I was mostly frustrated and thought the whole thing was unfair.",English,comparison,2,"Has paired baseline sample"
```

### Why this is better than the original toy version

It preserves:

- the participant identity,
- the exact sample being rated,
- the task metadata,
- optional comparative information,
- language and condition information,
- and enough structure to merge outputs later without ritual sacrifice.

---

## Configuration options

The project should expose a config file or config object with decisions such as:

- **Include task-specific info in the prompt?** `yes/no`
- **Where is the task info stored?**
  - in a CSV column
  - in a separate file
  - in a lookup table
- **Is the task comparative?**
  - if yes, use an alternative prompt template
- **Which scoring instructions should be used?**
  - e.g., `1-7 scale`, `0-100 scale`, categorical labels, etc.
- **How many repeated calls should be made per identical prompt?**
  - e.g., `N = 100`
- **Which LLMs should be used?**
- **Which temperatures should be used?**
- **How many justifications should be saved in the final dataset?**
- **Should all raw outputs be saved?** `yes/no`
- **Should outputs be saved in long format, wide format, or both?**

---

## Prompt composition

A general LLM prompt should be built from modular components.

### Base prompt structure

1. **General instructions**
2. **Task-specific information**
3. **Writing sample**
4. **Optional comparison sample**
5. **Output-format instructions**

### Template logic

```text
[General instructions]

[Task-specific information]

[Writing sample]

[If comparative task: comparison sample]

[Return output in JSON using the requested schema]
```

### Important implementation detail

If the CSV stores only a short task label such as `prompt_1`, Python should be able to:

- detect that label,
- look up the full task description,
- and replace the short label with the full wording inside the final prompt.

---

## Comparative-task branch

If the task is comparative, the prompt should explicitly include the reference text to compare against.

### Comparative prompt logic

- Insert the focal writing sample.
- Insert the comparison sample.
- Specify the comparison criterion.
  - e.g., deeper, clearer, more self-reflective, more emotionally nuanced.

This should probably use a dedicated prompt template rather than overloading the non-comparative version.

---

## Expected LLM output

The intended output format is JSON.

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

- `model_name`
- `method_name`
- `date`
- `time`
- `temperature`
- `seed` if available
- `prompt_version`
- `task_type`
- `raw_prompt`
- `raw_json_output`
- `parsed_successfully` flag

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
- optionally same temperature.

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

- `participant_id`
- `sample_id`
- `task_id`
- `model_name`
- `method_name`
- `temperature`
- `replicate_id`
- `item_1_score`
- `item_1_justification`
- `item_2_score`
- `item_2_justification`
- `...`
- `raw_json_output`
- `parsed_successfully`

### 2. Aggregated output table

One row per unique sample x method x model combination.

Suggested columns:

- `participant_id`
- `sample_id`
- `task_id`
- `model_name`
- `method_name`
- `temperature`
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

Merge aggregated outputs back into the original participant/sample dataset.

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
- method / prompt version
- temperature
- task type
- item
- participant/sample

A remaining design question is whether temperature should be:

- treated as a meaningful experimental factor,
- or fixed for reproducibility.

---

## Sanity checks

The pipeline should include automatic checks such as:

- Was the JSON parsed successfully?
- Are all expected items present?
- Are scores within range?
- Are justifications non-empty?
- Are repeated calls unexpectedly identical?
- Are some models producing systematically malformed outputs?

---

## Extra ideas for future expansion

Ideas from the sketch:

- temperature variation
- parallel calls
- audit / council approach
- logprobs or entropy measures

### Expanded interpretation

These could become advanced modules such as:

- **temperature robustness module**
- **multi-model ensemble scoring**
- **auditor model that reviews another model's coding**
- **uncertainty diagnostics using token-level metrics**

---

## Suggested project structure

```text
qual_analysis_project/
│
├── data/
│   ├── input/
│   │   └── writing_samples.csv
│   ├── intermediate/
│   │   ├── raw_llm_outputs.csv
│   │   ├── repeated_calls_long.csv
│   │   └── parsed_outputs_long.csv
│   └── output/
│       ├── aggregated_scores.csv
│       └── final_merged_dataset.csv
│
├── prompts/
│   ├── general_instructions.md
│   ├── template_noncomparative.txt
│   └── template_comparative.txt
│
├── config/
│   └── config.yaml
│
├── src/
│   ├── load_data.py
│   ├── build_prompts.py
│   ├── call_llm.py
│   ├── parse_outputs.py
│   ├── aggregate_outputs.py
│   ├── merge_results.py
│   └── sanity_checks.py
│
└── notebooks/
    └── exploratory_checks.ipynb
```

---

## Short conceptual summary

**CSV in -> prompt builder -> JSON scoring + justification -> repeated calls -> summary stats + selected justifications -> merged final analysis table**

---

## Open design questions

1. Should task information live directly in the CSV or in an external prompt library?
2. Should repeated calls vary temperature or keep it fixed?
3. How should representative justifications be selected?
4. Should all models use the same prompt wording, or should prompts be optimized per model?
5. Should the final analysis rely on one preferred model, or compare multiple models systematically?

---

## Practical next step

The next natural step is to turn this blueprint into:

- a `config.yaml` schema,
- a Python package layout,
- and one toy end-to-end script that runs on a miniature dataset.
