from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from ai_qualitative_analysis.config import load_config
from enums import OutputDataType, RunMode


def test_load_config_validates_first_pass_contract_and_resolves_relative_paths(tmp_path: Path) -> None:
    # Use relative paths here because path resolution against config.yaml is a common failure mode.
    payload = build_base_config_payload(tmp_path)
    config_path = write_config_file(tmp_path, payload)

    config = load_config(config_path)

    assert config.run_mode is RunMode.TESTING
    assert config.input_data.dataset_file == (tmp_path / "data" / "input.csv").resolve()
    assert config.input_data.column_mapping.row_id == "source_row_id"
    assert config.input_data.column_mapping.participant_text == "essay_text"
    assert config.prompt_template_file == (tmp_path / "prompts" / "prompt_template_main_analysis.txt").resolve()
    assert config.prompt_id == "main_analysis"
    assert config.prompt_version == "v1"
    assert config.prompt_version != config.analysis_schema.schema_version
    assert config.analysis_instructions_file == (
        tmp_path / "prompts" / "analysis_instructions_main_analysis.txt"
    ).resolve()
    assert config.model_set == "cheap_set"
    assert len(config.selected_models) == 1
    assert config.selected_models[0].model_provider == "mock"
    assert config.selected_models[0].model_name == "mock-first-pass"
    assert config.repeated_calls.count == 3
    assert config.repeated_calls.temperature == 0.0
    assert config.merge_output is False
    assert config.retain_raw_json_output is True
    assert config.output_data_type is OutputDataType.METRIC
    assert len(config.analysis_schema.items) == 2
    assert config.analysis_schema.items[0].score_key == "item_1_score"
    assert config.analysis_schema.items[0].justification_key == "item_1_justification"
    assert tuple(field.score_key for field in config.analysis_schema.fields) == (
        "item_1_score",
        "item_2_score",
    )


def test_load_config_applies_run_mode_defaults_when_repeated_calls_are_omitted(tmp_path: Path) -> None:
    payload = build_base_config_payload(tmp_path)
    payload["run_mode"] = "main_analysis"
    payload["model_set"] = "frontier_main_analysis_set"
    payload["model_sets"]["frontier_main_analysis_set"] = payload["model_sets"]["cheap_set"]
    payload.pop("repeated_calls")
    config_path = write_config_file(tmp_path, payload)

    config = load_config(config_path)

    assert config.run_mode is RunMode.MAIN_ANALYSIS
    assert config.repeated_calls.count == 100
    assert config.repeated_calls.temperature == 0.0
    assert config.merge_output is False


def test_load_config_applies_default_testing_model_set_when_explicit_model_set_is_omitted(tmp_path: Path) -> None:
    payload = build_base_config_payload(tmp_path)
    payload.pop("model_set")
    config_path = write_config_file(tmp_path, payload)

    config = load_config(config_path)

    assert config.model_set == "cheap_set"
    assert config.selected_models[0].model_name == "mock-first-pass"


def test_load_config_allows_comparative_analysis_true_in_config(tmp_path: Path) -> None:
    # Comparative branching is implemented separately; this test only protects config acceptance.
    payload = build_base_config_payload(tmp_path)
    payload["comparative_analysis"] = True
    config_path = write_config_file(tmp_path, payload)

    config = load_config(config_path)

    assert config.comparative_analysis is True


def test_load_config_rejects_categorical_output_type_in_current_scope(tmp_path: Path) -> None:
    payload = build_base_config_payload(tmp_path)
    payload["output_data_type"] = "categorical"
    config_path = write_config_file(tmp_path, payload)

    with pytest.raises(ValidationError, match="categorical"):
        load_config(config_path)


def test_load_config_rejects_duplicate_score_keys(tmp_path: Path) -> None:
    # Duplicate score keys would make analysis_schema.items ambiguous as the JSON contract source of truth.
    payload = build_base_config_payload(tmp_path)
    payload["analysis_schema"]["items"][1]["score_key"] = payload["analysis_schema"]["items"][0]["score_key"]
    config_path = write_config_file(tmp_path, payload)

    with pytest.raises(ValidationError, match="Duplicate analysis_schema.items score_key"):
        load_config(config_path)


def test_load_config_rejects_invalid_score_ranges(tmp_path: Path) -> None:
    payload = build_base_config_payload(tmp_path)
    payload["analysis_schema"]["items"][0]["min_score"] = 7
    payload["analysis_schema"]["items"][0]["max_score"] = 1
    config_path = write_config_file(tmp_path, payload)

    with pytest.raises(ValidationError, match="minimum must be less than or equal to ScoreRange.maximum"):
        load_config(config_path)


def test_load_config_rejects_deferred_text_file_mapping(tmp_path: Path) -> None:
    payload = build_base_config_payload(tmp_path)
    payload["input_data"]["column_mapping"]["text_file_name"] = "essay_file"
    config_path = write_config_file(tmp_path, payload)

    with pytest.raises(ValidationError, match="participant_text"):
        load_config(config_path)


def test_load_config_rejects_missing_analysis_instructions_file(tmp_path: Path) -> None:
    payload = build_base_config_payload(tmp_path)
    payload["analysis_instructions_file"] = "prompts/missing_analysis_instructions.txt"
    config_path = write_config_file(tmp_path, payload)

    with pytest.raises(ValidationError, match="analysis instructions file does not exist"):
        load_config(config_path)


def test_load_config_rejects_unknown_selected_model_set(tmp_path: Path) -> None:
    payload = build_base_config_payload(tmp_path)
    payload["model_set"] = "unknown_set"
    config_path = write_config_file(tmp_path, payload)

    with pytest.raises(ValidationError, match="was not found in model_sets"):
        load_config(config_path)


def build_base_config_payload(tmp_path: Path) -> dict[str, Any]:
    dataset_file = tmp_path / "data" / "input.csv"
    dataset_file.parent.mkdir(parents=True, exist_ok=True)
    dataset_file.write_text("row_id,essay_text\nrow_001,Example text\n", encoding="utf-8")

    prompt_file = tmp_path / "prompts" / "prompt_template_main_analysis.txt"
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text("Score the participant text and return JSON.", encoding="utf-8")
    instructions_file = tmp_path / "prompts" / "analysis_instructions_main_analysis.txt"
    instructions_file.write_text(
        "Score item_1 and item_2 and return exactly the configured JSON keys.",
        encoding="utf-8",
    )

    return {
        "run_mode": "testing",
        "input_data": {
            "dataset_file": "data/input.csv",
            "column_mapping": {
                "row_id": "source_row_id",
                "participant_text": "essay_text",
                "task_info": "prompt_short_description",
            },
        },
        "prompt_template_file": "prompts/prompt_template_main_analysis.txt",
        "prompt_id": "main_analysis",
        "prompt_version": "v1",
        "analysis_instructions_file": "prompts/analysis_instructions_main_analysis.txt",
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


def write_config_file(tmp_path: Path, payload: dict[str, Any]) -> Path:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return config_path
