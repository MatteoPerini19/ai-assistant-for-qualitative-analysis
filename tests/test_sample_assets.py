from __future__ import annotations

from pathlib import Path


def test_sample_assets_load_as_a_first_pass_project(
    sample_config_path: Path,
    sample_dataset_path: Path,
    sample_prompt_template_path: Path,
    sample_analysis_instructions_path: Path,
    sample_config,
) -> None:
    assert sample_config_path.name == "config.yaml"
    assert sample_config.input_data.dataset_file == sample_dataset_path.resolve()
    assert sample_config.prompt_template_file == sample_prompt_template_path.resolve()
    assert sample_config.prompt_id == "main_analysis"
    assert sample_config.prompt_version == "v1"
    assert sample_config.analysis_instructions_file == sample_analysis_instructions_path.resolve()
    assert sample_config.model_set == "cheap_set"
    assert len(sample_config.selected_models) == 1
    assert sample_config.selected_models[0].model_name == "mock-first-pass"
    assert sample_config.input_data.column_mapping.participant_text == "essay_text"
    assert sample_config.repeated_calls.count == 3
    assert tuple(item.item_id for item in sample_config.analysis_schema.items) == ("item_1", "item_2")


def test_sample_fixtures_expose_small_text_only_inputs(
    sample_input_rows,
    sample_input_columns,
    sample_prompt_template_text: str,
    sample_analysis_instructions_text: str,
) -> None:
    # 🟡 ASSUMPTION: Three rows are enough to support later parser, aggregation, and diagnostic
    # tests while keeping the shared sample assets easy to inspect and maintain.
    assert len(sample_input_rows) == 3

    # 🟡 ASSUMPTION: The shared sample CSV uses user-facing source column names instead of canonical
    # names so future normalization tests can exercise column_mapping with realistic inputs.
    assert "essay_text" in sample_input_columns
    assert "participant_text" not in sample_input_columns
    assert "audio_file_name" not in sample_input_columns
    assert "text_file_name" not in sample_input_columns
    assert all("_1" not in column and "_2" not in column for column in sample_input_columns)
    assert all(row["essay_text"] for row in sample_input_rows)
    assert "{{ analysis_instructions }}" in sample_prompt_template_text
    assert "non-comparative qualitative analysis" in sample_prompt_template_text
    assert "Return a JSON object" in sample_prompt_template_text
    assert "Evaluate the response on two configured dimensions." in sample_analysis_instructions_text
