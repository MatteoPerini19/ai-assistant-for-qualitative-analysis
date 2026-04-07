from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import yaml

from ai_qualitative_analysis.config import load_config
from ai_qualitative_analysis.io import load_normalized_input_dataset
from ai_qualitative_analysis.pipeline import (
    execute_repeated_calls,
    write_inclusive_long_output,
    write_summarized_wide_output,
)


def test_merge_disabled_leaves_original_source_columns_out_of_outputs(
    sample_config,
    sample_normalized_dataset,
    tmp_path: Path,
) -> None:
    execution_result = execute_repeated_calls(
        sample_config,
        sample_normalized_dataset,
        providers_by_name={"mock": _build_mock_provider()},
    )

    csv_path = write_inclusive_long_output(sample_config, execution_result, tmp_path / "outputs")
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        columns = list(csv.DictReader(handle).fieldnames or [])

    assert "source_row_id" not in columns
    assert "essay_text" not in columns


def test_merge_enabled_for_long_output_preserves_long_shape_and_appends_original_columns(
    sample_config,
    sample_normalized_dataset,
    tmp_path: Path,
) -> None:
    merged_config = sample_config.model_copy(update={"merge_output": True})
    execution_result = execute_repeated_calls(
        merged_config,
        sample_normalized_dataset,
        providers_by_name={"mock": _build_mock_provider()},
    )

    csv_path = write_inclusive_long_output(merged_config, execution_result, tmp_path / "outputs")
    rows = _read_csv_rows(csv_path)

    assert len(rows) == len(execution_result.records)
    assert "source_row_id" in rows[0]
    assert "essay_text" in rows[0]
    assert rows[0]["source_row_id"] == rows[0]["row_id"]
    assert rows[0]["subject_code"] == rows[0]["participant_id"]


def test_merge_enabled_for_wide_output_preserves_wide_shape_and_appends_original_columns(
    sample_config,
    sample_normalized_dataset,
    tmp_path: Path,
) -> None:
    merged_config = sample_config.model_copy(update={"merge_output": True})
    execution_result = execute_repeated_calls(
        merged_config,
        sample_normalized_dataset,
        providers_by_name={"mock": _build_mock_provider()},
    )

    csv_path = write_summarized_wide_output(merged_config, execution_result, tmp_path / "outputs")
    rows = _read_csv_rows(csv_path)

    assert len(rows) == len(sample_normalized_dataset.rows)
    assert "source_row_id" in rows[0]
    assert "essay_text" in rows[0]
    assert rows[0]["source_row_id"] == rows[0]["row_id"]


def test_merge_uses_row_id_key_and_avoids_accidental_duplication(
    tmp_path: Path,
    sample_prompt_template_path: Path,
) -> None:
    config = _load_merge_test_config(tmp_path, sample_prompt_template_path)
    normalized_dataset = load_normalized_input_dataset(config)
    execution_result = execute_repeated_calls(
        config,
        normalized_dataset,
        providers_by_name={"mock": _build_mock_provider()},
    )

    csv_path = write_summarized_wide_output(config, execution_result, tmp_path / "outputs")
    rows = _read_csv_rows(csv_path)
    rows_by_row_id = {row["row_id"]: row for row in rows}

    assert len(rows) == 2
    assert rows_by_row_id["row_001"]["essay_text"] == "First text for the same participant."
    assert rows_by_row_id["row_002"]["essay_text"] == "Second text for the same participant."

def _build_mock_provider():
    from providers.mock import MockProvider

    return MockProvider()


def _read_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_merge_test_config(tmp_path: Path, sample_prompt_template_path: Path):
    dataset_path = tmp_path / "duplication_case.csv"
    dataset_path.write_text(
        (
            "source_row_id,subject_code,prompt_code,prompt_label,prompt_short_description,"
            "prompt_full_text,essay_text\n"
            "row_001,pp_001,task_shared,Shared task,Short task info,Full task text,"
            "\"First text for the same participant.\"\n"
            "row_002,pp_001,task_shared,Shared task,Short task info,Full task text,"
            "\"Second text for the same participant.\"\n"
        ),
        encoding="utf-8",
    )

    config_payload: dict[str, Any] = {
        "run_mode": "testing",
        "include_task_info": True,
        "input_data": {
            "dataset_file": str(dataset_path),
            "column_mapping": {
                "row_id": "source_row_id",
                "participant_id": "subject_code",
                "task_id": "prompt_code",
                "task_label": "prompt_label",
                "task_info": "prompt_short_description",
                "task_full_text": "prompt_full_text",
                "participant_text": "essay_text",
            },
        },
        "prompt_template_file": str(sample_prompt_template_path),
        "prompt_id": "main_analysis",
        "prompt_version": "v1",
        "model_set": "cheap_set",
        "model_sets": {
            "cheap_set": [
                {
                    "model_provider": "mock",
                    "model_name": "mock-first-pass",
                    "method_name": "main_analysis",
                }
            ]
        },
        "repeated_calls": {"count": 2, "temperature": 0.0},
        "merge_output": True,
        "analysis_schema": {
            "schema_name": "main_analysis_v1",
            "schema_version": "1.0",
            "items": [
                {
                    "item_id": "item_1",
                    "score_key": "item_1_score",
                    "justification_key": "item_1_justification",
                    "score_type": "integer",
                    "min_score": 1,
                    "max_score": 7,
                },
                {
                    "item_id": "item_2",
                    "score_key": "item_2_score",
                    "justification_key": "item_2_justification",
                    "score_type": "integer",
                    "min_score": 1,
                    "max_score": 7,
                },
            ],
        },
    }

    config_path = tmp_path / "merge_config.yaml"
    config_path.write_text(yaml.safe_dump(config_payload, sort_keys=False), encoding="utf-8")
    return load_config(config_path)
