from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from ai_qualitative_analysis.config import load_config
from ai_qualitative_analysis.io import load_normalized_input_dataset


def test_dataset_ingest_supports_exact_match_canonical_columns(tmp_path: Path) -> None:
    dataset_file = tmp_path / "data" / "canonical_input.csv"
    dataset_file.parent.mkdir(parents=True, exist_ok=True)
    dataset_file.write_text(
        (
            "row_id,participant_text,task_info\n"
            "row_001,This response uses canonical column names.,Short task info\n"
        ),
        encoding="utf-8",
    )

    config = load_config(write_config_file(tmp_path, build_base_config_payload(tmp_path, dataset_file)))

    normalized_dataset = load_normalized_input_dataset(config)

    assert normalized_dataset.original_columns == ("row_id", "participant_text", "task_info")
    assert normalized_dataset.normalized_columns == ("row_id", "participant_text", "task_info")
    assert normalized_dataset.rows[0].row_id == "row_001"
    assert normalized_dataset.rows[0].participant_text == "This response uses canonical column names."


def test_dataset_ingest_applies_custom_column_mapping(sample_config) -> None:
    normalized_dataset = load_normalized_input_dataset(sample_config)

    assert normalized_dataset.original_columns[0] == "source_row_id"
    assert "row_id" in normalized_dataset.normalized_columns
    assert normalized_dataset.rows[0].row_id == "row_001"
    assert normalized_dataset.rows[0].participant_id == "pp_001"
    assert normalized_dataset.rows[0].participant_text.startswith("I felt overwhelmed")


def test_dataset_ingest_fails_clearly_when_required_fields_are_missing(tmp_path: Path) -> None:
    dataset_file = tmp_path / "data" / "missing_participant_text.csv"
    dataset_file.parent.mkdir(parents=True, exist_ok=True)
    dataset_file.write_text("row_id,task_info\nrow_001,Short task info\n", encoding="utf-8")

    config = load_config(write_config_file(tmp_path, build_base_config_payload(tmp_path, dataset_file)))

    with pytest.raises(ValueError, match="missing required canonical columns"):
        load_normalized_input_dataset(config)


def test_dataset_ingest_rejects_audio_based_input_paths(tmp_path: Path) -> None:
    dataset_file = tmp_path / "data" / "audio_input.csv"
    dataset_file.parent.mkdir(parents=True, exist_ok=True)
    dataset_file.write_text(
        "row_id,audio_file_name\nrow_001,participant_001.wav\n",
        encoding="utf-8",
    )

    config = load_config(write_config_file(tmp_path, build_base_config_payload(tmp_path, dataset_file)))

    with pytest.raises(NotImplementedError, match="File-based qualitative inputs are not yet supported"):
        load_normalized_input_dataset(config)


def test_dataset_ingest_rejects_comparative_wide_format_input(tmp_path: Path) -> None:
    dataset_file = tmp_path / "data" / "comparative_input.csv"
    dataset_file.parent.mkdir(parents=True, exist_ok=True)
    dataset_file.write_text(
        (
            "row_id,participant_text_1,participant_text_2,task_id_1,task_id_2\n"
            "row_001,First text,Second text,task_a,task_b\n"
        ),
        encoding="utf-8",
    )

    config = load_config(write_config_file(tmp_path, build_base_config_payload(tmp_path, dataset_file)))

    with pytest.raises(NotImplementedError, match="Comparative wide-format input is not yet supported"):
        load_normalized_input_dataset(config)


def build_base_config_payload(tmp_path: Path, dataset_file: Path) -> dict[str, Any]:
    prompt_file = tmp_path / "prompts" / "prompt_template_main_analysis.txt"
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text("Score the participant text and return JSON.", encoding="utf-8")

    return {
        "run_mode": "testing",
        "input_data": {
            "dataset_file": str(dataset_file),
            "column_mapping": {},
        },
        "prompt_template_file": str(prompt_file),
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
        "repeated_calls": {
            "count": 3,
            "temperature": 0.0,
        },
        "merge_output": False,
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
                }
            ],
        },
    }


def write_config_file(tmp_path: Path, payload: dict[str, Any]) -> Path:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return config_path
