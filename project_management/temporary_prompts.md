dataset_mappings:
  dataset-awe_and_delpth-field_study.csv:
    row_id: create_ex_novo
    participant_id: pp_code
    task_id: shared_task_id_to_define
    task_label: NA
    task_info: to_add
    task_full_text: to_add
    participant_text:
      source_columns:
        - RT_text1
        - RT_text2
      reshape: wide_to_long
    topic:
      source_columns:
        - Topic_1
        - Topic_2
      prompt_use: include_as_row_level_context
    text_file_name: NA
    audio_file_name: NA
    language: NA
    condition:
      source_columns:
        - Initial_location
        - Location2
      reconstruction: ground_floor_or_top_floor
    wave: NA
    compare_with_row_id: create_after_long_reshape

  dataset-Awe_Depth_VR.csv:
    row_id: unique_ID
    participant_id: pp_code
    task_id: prompt_code
    task_label: NA
    task_info: NA
    task_full_text: NA
    participant_text: RT_text_1
    text_file_name: NA
    audio_file_name: NA
    language: NA
    condition: Condition
    wave: NA


codex_prompts:
  dataset-awe_and_delpth-field_study.csv: |
    Create a long-format version of `data/datasets/dataset-awe_and_delpth-field_study.csv`.

    Requirements:
    - Ignore rows where `pp_code` is blank.
    - Split each original wide row into two long rows:
      - row 1 uses `RT_text1`, `Topic_1`, and `Initial_location`
      - row 2 uses `RT_text2`, `Topic_2`, and `Location2`
    - Create a new unique `row_id` ex novo for every long row.
    - Create `compare_with_row_id` so each long row points to the paired row created from the same original wide row.
    - Set `participant_id = pp_code`.
    - Set `participant_text` from the relevant `RT_text*` column.
    - Preserve the self-chosen reflection topic from `Topic_1` / `Topic_2` in a `topic` column, because it should be included in the prompt as row-level context.
    - Reconstruct `condition` from `Initial_location` / `Location2`. Inspect whether codes `1` and `2` correspond to `ground floor` and `top floor`. If that exact mapping cannot be verified from the local project files, keep the original code available and document the ambiguity instead of inventing a mapping.
    - The task is the same for everybody in this dataset.
    - Use `task_id` only if it can be filled from explicit local project context. Leave `task_label`, `task_info`, and `task_full_text` as `NA` unless explicit local project context is available.
    - Set unsupported fields to `NA`:
      - `text_file_name`
      - `audio_file_name`
      - `language`
      - `wave`
    - Save the reshaped dataset as a new CSV next to the source file.
    - Briefly report the exact output path, the created columns, and any unresolved ambiguity after the transformation.
