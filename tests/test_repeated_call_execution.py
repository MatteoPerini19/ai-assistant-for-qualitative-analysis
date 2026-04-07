from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import yaml

from ai_qualitative_analysis.config import load_config
from ai_qualitative_analysis.io import load_normalized_input_dataset
from ai_qualitative_analysis.pipeline import execute_repeated_calls
from enums import ParseStatus
from providers.mock import MockProvider
from schemas import SelectedModelSpec


def test_execute_repeated_calls_uses_testing_mode_default_repeat_count(
    tmp_path: Path,
    sample_dataset_path: Path,
    sample_prompt_template_path: Path,
) -> None:
    config = load_config(
        _write_execution_config(
            tmp_path,
            dataset_file=sample_dataset_path,
            prompt_template_file=sample_prompt_template_path,
            include_repeated_calls=False,
        )
    )
    dataset = load_normalized_input_dataset(config)

    result = execute_repeated_calls(
        config,
        dataset,
        providers_by_name={"mock": MockProvider()},
    )

    assert config.repeated_calls.count == 3
    assert len(result.records) == len(dataset.rows) * 3
    assert {record.replicate_id for record in result.records} == {1, 2, 3}


def test_execute_repeated_calls_keeps_temperature_stable_within_call_group(
    sample_config,
    sample_normalized_dataset,
) -> None:
    result = execute_repeated_calls(
        sample_config,
        sample_normalized_dataset,
        providers_by_name={"mock": MockProvider()},
    )

    grouped_records = defaultdict(list)
    for record in result.records:
        grouped_records[record.call_group_key].append(record)

    for records in grouped_records.values():
        assert {record.requested_temperature for record in records} == {0.0}
        assert {record.effective_temperature for record in records} == {0.0}
        assert len({record.effective_prompt for record in records}) == 1


def test_execute_repeated_calls_generates_unique_run_ids(
    sample_config,
    sample_normalized_dataset,
) -> None:
    dual_model_config = sample_config.model_copy(
        update={
            "model_set": "dual_mock_set",
            "model_sets": {
                **sample_config.model_sets,
                "dual_mock_set": _build_selected_models(),
            },
        }
    )
    result = execute_repeated_calls(
        dual_model_config,
        sample_normalized_dataset,
        providers_by_name={"mock": MockProvider()},
    )

    run_ids = [record.run_id for record in result.records]
    assert len(run_ids) == len(set(run_ids))


def test_execute_repeated_calls_returns_expected_record_count_and_metadata(
    sample_config,
    sample_normalized_dataset,
) -> None:
    # Use two selected models here so the engine has to expand rows x models x replicates.
    dual_model_config = sample_config.model_copy(
        update={
            "model_set": "dual_mock_set",
            "model_sets": {
                **sample_config.model_sets,
                "dual_mock_set": _build_selected_models(),
            },
        }
    )
    result = execute_repeated_calls(
        dual_model_config,
        sample_normalized_dataset,
        providers_by_name={"mock": MockProvider()},
    )

    expected_count = (
        len(sample_normalized_dataset.rows)
        * len(dual_model_config.selected_models)
        * dual_model_config.repeated_calls.count
    )
    assert len(result.records) == expected_count

    first_record = result.records[0]
    assert first_record.run_id == "run_000001"
    assert first_record.prompt_template_file == dual_model_config.prompt_template_file.name
    assert first_record.prompt_id == dual_model_config.prompt_id
    assert first_record.prompt_version == dual_model_config.prompt_version
    assert first_record.schema_name == dual_model_config.analysis_schema.schema_name
    assert first_record.schema_version == dual_model_config.analysis_schema.schema_version
    assert first_record.parse_status is ParseStatus.VALID
    assert first_record.effective_prompt == result.records[1].effective_prompt
    assert sample_normalized_dataset.rows[0].participant_text in first_record.effective_prompt


def _build_selected_models() -> tuple[SelectedModelSpec, ...]:
    return (
        SelectedModelSpec(
            model_provider="mock",
            model_name="mock-model-a",
            method_name="main_analysis",
        ),
        SelectedModelSpec(
            model_provider="mock",
            model_name="mock-model-b",
            method_name="main_analysis",
        ),
    )


def _write_execution_config(
    tmp_path: Path,
    *,
    dataset_file: Path,
    prompt_template_file: Path,
    include_repeated_calls: bool,
) -> Path:
    payload: dict[str, object] = {
        "run_mode": "testing",
        "input_data": {
            "dataset_file": str(dataset_file),
            "column_mapping": {
                "row_id": "source_row_id",
                "participant_id": "subject_code",
                "task_id": "prompt_code",
                "task_label": "prompt_label",
                "task_info": "prompt_short_description",
                "task_full_text": "prompt_full_text",
                "participant_text": "essay_text",
                "language": "lang",
                "condition": "experimental_condition",
                "wave": "timepoint",
            },
        },
        "prompt_template_file": str(prompt_template_file),
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
        "merge_output": False,
        "output_data_type": "metric",
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
    if include_repeated_calls:
        payload["repeated_calls"] = {"count": 3, "temperature": 0.0}

    config_path = tmp_path / "execution_config.yaml"
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return config_path
