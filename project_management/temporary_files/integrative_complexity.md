## Information needed for instructions refinement
- Confirm transcript schema. Minimum required columns: `conversation_id`, `dyad_id`, `participant_id`, `topic_id`, `condition`, `turn_index`, `speaker_id`, `text`.
MY ANSWER -> we will decide later when we collect the data.
- Confirm transcript granularity: already split by turns vs full conversation text. 
MY ANSWER -> ...🔴
- Confirm whether we have ICA reference examples with human-assigned scores (`gold_score` 1-7).
MY ANSWER -> ...🔴
- Confirm legal/compliance status for using and storing handbook-derived ICA reference material and excerpts.
MY ANSWER -> yes it is legal, don't worry about this. 



## Confirmed constraints from user
- Transcripts are multilingual.
- Script testing will start with this model set:
```python
cheap_set = {
    "openai": [
        "gpt-4.1-nano",
        "gpt-5-nano",
    ],
    "gemini": [
        "gemini/gemini-2.5-flash-lite",
    ],
    "anthropic": [
        "anthropic/claude-haiku-4-5",
    ],
    "mistral": [
        "mistral/mistral-small-2506+1",
    ],
    "together": [
        "together_ai/Qwen/Qwen3.5-9B",
        "together_ai/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        "together_ai/MiniMaxAI/MiniMax-M2.5",
    ],
}
```
- Additional models may be added later.
- Input/reference files will be stored in the `data/` folder.
- This script must NOT run statistical analyses (no mixed-effects or other inferential modeling). It only produces integrative complexity outputs for later analysis elsewhere.
- Methodological choices are made before coding, frozen in the final version of this markdown file, and then used as the coding prompt.

## Scope locked to preregistration
- Apply Integrative Complexity Analysis (ICA; Smith et al., 1992) to conversation thoughts.
- Score each thought on a 1-7 scale based on differentiation/integration structure.
- Implement two preregistered model variants:
1. Variant A: follow Smith-style ICA guidelines.
2. Variant B: use ICA reference material without pre-given method instructions.
- Produce thought-level and aggregated ICA outputs.
- Export analysis-ready ICA datasets only. Do not fit any statistical models in this script.

## Data folder naming and structure (recommended)
- `data/ic_conversations.parquet`
- `data/ic_ica_examples.parquet`
- `data/ic_model_sets.json`
- `data/ic_readme.md`
- Recommended columns for `data/ic_conversations.parquet`:
`conversation_id`, `dyad_id`, `participant_id`, `topic_id`, `condition`, `turn_index`, `speaker_id`, `text`, `language_code` (if available).
- Recommended columns for `data/ic_ica_examples.parquet`:
`example_id`, `text`, `gold_score` (if available), `source`, `language_code`.
- `data/ic_model_sets.json` should contain named sets (`cheap_set`, later `main_set`, etc.).

## Decision blocks (delete options you do not want)
- Decision policy:
Select all options in this section before prompting the coding agent. Any decision not explicitly selected here must be treated as out of scope.

- Data file naming convention:
🟢 OPTION 1 - Use the recommended canonical names in this file (`data/ic_conversations.parquet`, `data/ic_ica_examples.parquet`, `data/ic_model_sets.json`, `data/ic_readme.md`).
🔵 OPTION 2 - Use custom names/paths; define them explicitly in this section before coding.
EXPLANATION - This decides whether the code can assume a fixed project layout or must be parameterized for custom paths. Choose OPTION 1 if you want less implementation ambiguity and simpler maintenance; choose OPTION 2 only if you already know the project must follow a different naming convention.
MY ANSWER: I'm indifferent at this point. 

- Input format:
🟢 OPTION 1 - Turn table (`csv`/`parquet`): one row per speaker turn with metadata.
🔵 OPTION 2 - Full transcript blobs: parser extracts speaker turns from tagged transcript text.
EXPLANATION - This determines whether the script starts from already structured turn-level data or must first parse transcripts. Choose OPTION 1 if your transcripts can be exported as clean turn rows; choose OPTION 2 only if your source data naturally exists as raw speaker-tagged transcript text.
MY ANSWER: 
The conversations will be stored as individual files:
We will have three audio file per conversation, one for each of the two participants' microphones and one for the entire reconstructed conversation. The audio files for individual participants will be in the data/audio/individuals/ folder, while the reconstructed conversation audio file will be in the data/audio/full_conversations/ folder.
We will also have three text files, one for each of the two participants's parts of the conversation and one for the entire reconstructed conversation. 
The text files for individual participants will be in the data/transcripts/individual_transcripts/ folder, while the transcript for the reconstructed conversation will be in the data/transcripts/full_transcripts/ folder.
In the main dataset (a .csv file) there will be specific variables indicated the name of the audio and text files associated with a specific observation (e.g., participant 1, condition 1). This dataset will be in the data/ folder.


- Language metadata handling:
🟢 OPTION 1 - Require `language_code` in input tables.
🔵 OPTION 2 - Allow missing `language_code`; auto-detect and write `detected_language_code`.
EXPLANATION - This controls whether language is a required input responsibility or an inference step inside the pipeline. Choose OPTION 1 if you want higher control and fewer hidden preprocessing choices; choose OPTION 2 if language labels are unavailable or unreliable in the raw data.
🔴 LEFT FOR LATER 

- Thought segmentation strategy:
🟢 OPTION 1 - Rule-based: one turn = one thought unless explicit split markers are detected.
🔵 OPTION 2 - LLM-assisted: split turns into one-or-more thoughts when multiple ideas appear.
EXPLANATION - This is one of the main methodological choices because it defines the unit being scored. Choose OPTION 1 if you want maximal reproducibility and simpler auditing; choose OPTION 2 if you expect many multi-idea turns and accept more model dependence in segmentation.
🟣 WAITING  

- Thought segmentation quality control:
🟢 OPTION 1 - Automatic only: no manual checks beyond diagnostics.
🔵 OPTION 2 - Hybrid QA: manual review of random stratified sample before final scoring.
EXPLANATION - This decides whether segmentation is trusted purely through automated checks or also through human spot-checking. Choose OPTION 1 if you want a fully automated pipeline; choose OPTION 2 if segmentation validity is important enough to justify a small manual review burden.
MY CHOICE – I trust the LLMs. I just want some random samples of the outputs to be put into a "manual check" file for looking at how the work is done in case I want. 

- Multilingual handling:
🟢 OPTION 1 - Native-language scoring (recommended): score each thought in its original language.
🔵 OPTION 2 - Translate-to-English scoring: translate each thought before ICA scoring.
EXPLANATION - This determines whether ICA is applied directly to the original text or to a translated version. Choose OPTION 1 if you want to preserve original wording and avoid translation artifacts; choose OPTION 2 only if you believe English scoring will be more stable across models than multilingual direct scoring.
MY CHOICE - We keep native language, no translation. 

- Participant vs conversation scoring target:
🟢 OPTION 1 - Conversation pooled score only.
🔵 OPTION 2 - Both pooled and participant-specific scores.
EXPLANATION - This controls the granularity of the exported outputs. Choose OPTION 1 if downstream analyses only need conversation-level IC; choose OPTION 2 if you want flexibility to compare individual speakers as well as pooled conversations later.
MY CHOICE - The LLM will receive the transcript only from one participant part of conversation, and it will segment it in multiple chuncks.  

- Variant B implementation:
🟢 OPTION 1 - Few-shot example conditioning without rubric text (no provider fine-tuning).
🔵 OPTION 2 - Fine-tune where available, fallback to few-shot for unsupported providers.
EXPLANATION - This determines how far Variant B departs from prompt-only adaptation. Choose OPTION 1 if you want a portable, provider-agnostic implementation based on reference examples; choose OPTION 2 only if you are willing to manage provider-specific fine-tuning workflows and unequal support across models.
🔴 LEFT FOR LATER 

- Model set selection policy:
🟢 OPTION 1 - Use `cheap_set` as default for runs unless explicitly overridden in CLI.
🔵 OPTION 2 - Require explicit `--model-set-name` in each run; no default.
EXPLANATION - This determines whether the script has a standard default model bundle. Choose OPTION 1 if `cheap_set` is your practical default for testing and iteration; choose OPTION 2 if you want every run to make model choice explicit and avoid accidental defaults.
🔴 LEFT FOR LATER 


- Prompt response contract:
🟢 OPTION 1 - Strict JSON output: `score`, `confidence`, `diff_evidence`, `integration_evidence`.
🔵 OPTION 2 - Numeric-only output: single integer 1-7.
EXPLANATION - This determines how much structured information each model call must return. Choose OPTION 1 if you want auditability, debugging support, and richer QA; choose OPTION 2 if you want the simplest and cheapest possible response format.
🔴 LEFT FOR LATER 

- Scoring stability:
🟢 OPTION 1 - Single deterministic pass (`temperature=0`).
🔵 OPTION 2 - Multi-pass consensus (3-5 passes) with median and variability.
EXPLANATION - This controls whether each score is treated as a single deterministic judgment or a small distribution. Choose OPTION 1 for lower cost and simpler outputs; choose OPTION 2 if you want an explicit measure of scoring instability across repeated calls.
MY ANSWER: I will conduct multiple calls for each llm and the do the average. I want these calls to have different levels of temperature to campture more variation. 

- Aggregation from thought to conversation:
🟢 OPTION 1 - Unweighted mean.
🔵 OPTION 2 - Token-weighted mean plus dispersion (`sd`, `iqr`, `n_thoughts`).
EXPLANATION - This defines how individual thought scores become conversation-level outputs. Choose OPTION 1 if every thought should count equally; choose OPTION 2 if longer thoughts should contribute more and you want richer summary statistics.
MY ANSWER: great idea!!! I want the weighted mean based on how long that chuck was as compared to the other chuncks. Longer chuncks should weight more. Yet, I don't care about dispersion measures. 

- Logging/privacy:
🟢 OPTION 1 - Store full prompt/response logs for audit.
🔵 OPTION 2 - Store parsed outputs only plus hashed text IDs.
EXPLANATION - This balances reproducibility against privacy and storage sensitivity. Choose OPTION 1 if traceability and debugging are more important; choose OPTION 2 if you want to minimize retained model text and reduce exposure of transcript content.
MY ANSWER: store everything. 

- Output layout:
🟢 OPTION 1 - Long-format output tables only.
🔵 OPTION 2 - Long-format plus convenience wide-format summaries.
EXPLANATION - This determines whether the script exports only analysis-ready canonical tables or also user-friendly summaries. Choose OPTION 1 if you want a leaner, cleaner output surface; choose OPTION 2 if you expect manual inspection or quick spreadsheet-style review of results.
MY ASNWER: long format only. 


## Methodological freeze protocol
- Finalize all methodological choices in this markdown before coding starts.
- Treat the final committed version of this file as the frozen analysis specification.
- Record the specification reference in `run_manifest.json`.
- Any change after freeze must be documented in `deviations_log.md` with rationale and timestamp.

## Reference material handling protocol
- Keep the ICA reference material fixed once this specification is frozen.
- If reference examples are used in prompts for Variant B, document exactly how they are used.
- Do not silently add, remove, or rewrite reference examples after reviewing model outputs.
- Freeze prompt templates before full conversation scoring.

## Script non-goals
- Do not fit mixed-effects models.
- Do not run any inferential statistical testing.
- Do not generate p-values, Bayesian posteriors, or model comparison outputs.

## Proposed code architecture for `integrative_complexity.py`
- `Config` dataclass: paths, selected options, model list, seeds, retries, timeouts.
- `load_env_and_validate_keys()`: validate provider keys from `.env`.
- `load_model_set()`: load named model sets from `data/ic_model_sets.json`.
- `load_conversations()`: ingest transcript data with schema checks.
- `load_ica_material()`: ingest ICA reference examples with schema validation.
- `prepare_multilingual_text()`: language tag normalization and optional translation.
- `segment_thoughts()`: produce one-or-more thought units per turn/transcript.
- `qa_segmentation_sample()`: create QA sample package when hybrid QA is selected.
- `build_prompt_variant_a()` and `build_prompt_variant_b()`: strict prompt templates.
- `score_with_litellm()`: robust wrapper with retry/backoff/parse checks.
- `score_reference_material()`: optionally score ICA reference examples for manual inspection.
- `aggregate_scores()`: build conversation-level and optional participant-level IC outputs.
- `export_ic_outputs()`: write final ICA tables and manifests.
- `write_run_manifest()`: metadata, hashes, lock settings, template versions.
- `main()`: CLI orchestration with step-level commands.

## Detailed implementation plan
## Step 0 - Setup and reproducibility files
- Create `outputs/integrative_complexity/` and standard subfolders.
- Initialize `run_manifest.json` and `deviations_log.md`.
- Validate selected options for internal consistency.
- Store the frozen spec reference in `run_manifest.json`.

## Step 1 - CLI and configuration
- Add CLI arguments:
`--input-conversations`, `--input-ica-material`, `--output-dir`, `--models`, `--model-set-name`, `--variants`, `--segmentation-mode`, `--multilingual-mode`, `--aggregation-mode`, `--n-repeats`, `--resume`, `--dry-run`.
- Fail fast on missing keys for selected providers.
- Apply model set policy according to the selected decision block option.

## Step 2 - Data contracts and schema validation
- Define canonical internal tables:
1. `thoughts_df`: `thought_id`, `conversation_id`, `speaker_id`, `thought_text`, `language_code`, `condition`, `topic_id`, `participant_id`, `dyad_id`, `source_turn_id`.
2. `ica_examples_df`: `example_id`, `text`, `gold_score`, `language_code`, optional auxiliary columns.
3. `scores_df`: `thought_id`, `llm_id`, `variant_id`, `score_int`, `confidence`, `run_id`, `attempt_id`.
4. `conv_scores_df`: `conversation_id`, `llm_id`, `variant_id`, `ic_score`, `ic_sd`, `n_thoughts`.
5. `participant_scores_df` (if selected): `participant_id`, `conversation_id`, `llm_id`, `variant_id`, `ic_score`.
- Halt execution if required columns are missing or duplicate IDs are detected.
- Apply language metadata policy according to the selected decision block option.

## Step 3 - Multilingual preprocessing and thought segmentation
- Clean transcript artifacts (`[noise]`, timestamps, repeated whitespace).
- Apply multilingual mode (native scoring or translate-first).
- Enforce thought unit target: one participant speaking on one idea.
- Use language-agnostic segmentation logic (avoid English-only assumptions).
- Preserve reversible mappings (`source_char_start`, `source_char_end`) when splitting within turns.
- Export diagnostics:
`thought_segmentation_preview.csv` and `thought_segmentation_qc.csv`.

## Step 4 - Prompt engineering for two prereg variants
- Variant A prompt:
1. Include ICA anchors (1, 3, 5, 7) and transitional levels (2, 4, 6).
2. Instruct model to evaluate thought structure, not argument quality.
- Variant B prompt:
1. Exclude rubric instructions.
2. Use the selected reference-material strategy (few-shot or fine-tuned endpoint).
- In native-language mode, score in original language (no forced translation).
- Apply strict parser with explicit repair policy for malformed outputs.

## Step 5 - LiteLLM inference engine and reliability controls
- Loop over `(llm_id, variant_id, thought_id)` with resume support.
- Add retries, timeout, and output validation.
- Track invalid outputs and recovery outcomes.
- If consensus mode is selected, compute per-thought variability.

## Step 6 - Optional reference-material output export
- If `data/ic_ica_examples.parquet` is available, optionally score the ICA reference examples with each model and variant.
- If `gold_score` is available, export side-by-side human and model scores for descriptive inspection only.
- Export:
`reference_material_scores.csv`.

## Step 7 - Score study conversations
- Score all segmented thoughts with the configured model-variant pairs.
- Validate score range `[1,7]` and coercion rules.
- Write:
`thought_scores_parsed.csv`.
- If enabled, write:
`thought_scores_raw.jsonl`.

## Step 8 - Aggregate ICA outputs
- Build conversation-level and optionally participant-level outputs.
- Include variability fields (`n_thoughts`, `ic_sd`, and optionally `iqr`).
- Keep thought and aggregated tables linkable via IDs.

## Step 9 - Export outputs only (no statistical analysis)
- Export final ICA handoff tables for external statistical scripts:
`ic_thought_scores.csv`, `ic_conversation_scores.csv`, `ic_participant_scores.csv` (optional).
- Export canonical long-format analysis file:
`ic_for_external_stats.csv`.
- Do not run mixed-effects or any inferential model in this script.

## Step 10 - QA and reproducibility artifacts
- Generate QA report with:
1. Distribution summaries by model and variant.
2. Missing/invalid score counts.
3. Segmentation length distributions.
4. Cross-model disagreement summaries.
- Save:
`qa_report.md`.
- Save reproducibility files:
`run_manifest.json`, response cache hashes.

## High-risk failure points and safeguards
- Risk: reference examples are changed or reused inconsistently across variants.
Safeguard: keep the reference material fixed after freeze and document exactly how each variant uses it.
- Risk: thought segmentation drift changes the estimand.
Safeguard: lock segmentation strategy and run sample QA before full scoring.
- Risk: provider output format variability.
Safeguard: strict parser with retry/repair and invalid-rate tracking.
- Risk: cross-model incomparability.
Safeguard: standardized prompt contracts, consistent preprocessing, and locked aggregation.
- Risk: excessive flexibility after seeing results.
Safeguard: frozen markdown specification (version-controlled) plus deviation logging.

## Expected directory structure
- `data/ic_conversations.parquet`
- `data/ic_ica_examples.parquet`
- `data/ic_model_sets.json`
- `data/ic_readme.md`
- `outputs/integrative_complexity/run_manifest.json`
- `outputs/integrative_complexity/deviations_log.md`
- `outputs/integrative_complexity/reference_material_scores.csv`
- `outputs/integrative_complexity/thought_scores_parsed.csv`
- `outputs/integrative_complexity/ic_conversation_scores.csv`
- `outputs/integrative_complexity/ic_for_external_stats.csv`

## Minimum tests before first full run
- Unit checks:
1. Parser accepts only integer scores 1-7.
2. Segmentation returns non-empty thought set with stable IDs.
3. Aggregation returns expected values on toy fixtures.
- Integration checks:
1. Dry run on 5-10 thoughts across at least two models from `cheap_set`.
2. Verify `run_manifest.json` includes the frozen spec reference and resume behavior.
3. Verify export schema and required output files.

## Execution sequence after option selection
1. Finalize options by deleting unwanted branches in this file.
2. Freeze and commit this file as the final analysis specification.
3. Implement `integrative_complexity.py` modules based on this frozen specification.
4. Run dry test and inspect QA outputs.
5. Run full ICA scoring and export final output tables.
