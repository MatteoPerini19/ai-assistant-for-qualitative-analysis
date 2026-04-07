from __future__ import annotations

import csv
from pathlib import Path

import pytest

from ai_qualitative_analysis.pipeline import write_summarized_wide_output
from enums import OutputDataType, ParseStatus
from schemas import CallExecutionRecord, RepeatedCallExecutionResult


def test_write_summarized_wide_output_creates_metric_summary_with_expected_columns(
    sample_config,
    sample_normalized_row,
    tmp_path: Path,
) -> None:
    execution_result = _build_execution_result(
        sample_normalized_row,
        item_1_scores=[1, 4, 7],
        item_1_justifications=["low", "mid", "high"],
    )

    csv_path = write_summarized_wide_output(sample_config, execution_result, tmp_path / "outputs")

    assert csv_path.exists()
    rows = _read_csv_rows(csv_path)
    assert len(rows) == 1

    row = rows[0]
    suffix = _group_suffix()
    assert row["row_id"] == sample_normalized_row.row_id
    assert row["participant_id"] == sample_normalized_row.participant_id
    assert row["task_id"] == sample_normalized_row.task_id
    assert float(row[f"item_1_score_mean{suffix}"]) == 4.0
    assert float(row[f"item_1_score_sd{suffix}"]) == 3.0
    assert float(row[f"item_1_score_min{suffix}"]) == 1.0
    assert float(row[f"item_1_score_max{suffix}"]) == 7.0
    assert row[f"n_successful_parses{suffix}"] == "3"
    assert row[f"n_parse_failures{suffix}"] == "0"


def test_write_summarized_wide_output_supports_ordinal_statistics(
    sample_config,
    sample_normalized_row,
    tmp_path: Path,
) -> None:
    ordinal_config = sample_config.model_copy(update={"output_data_type": OutputDataType.ORDINAL})
    execution_result = _build_execution_result(
        sample_normalized_row,
        item_1_scores=[1, 3, 5, 7, 9],
        item_1_justifications=["s1", "s3", "s5", "s7", "s9"],
    )

    csv_path = write_summarized_wide_output(ordinal_config, execution_result, tmp_path / "outputs")
    row = _read_csv_rows(csv_path)[0]
    suffix = _group_suffix()

    assert float(row[f"item_1_score_median{suffix}"]) == 5.0
    assert float(row[f"item_1_score_iqr{suffix}"]) == 4.0
    assert float(row[f"item_1_score_mad{suffix}"]) == 2.0


def test_write_summarized_wide_output_selects_representative_justifications_nearest_target(
    sample_config,
    sample_normalized_row,
    tmp_path: Path,
) -> None:
    execution_result = _build_execution_result(
        sample_normalized_row,
        item_1_scores=[1, 4, 7],
        item_1_justifications=["low", "mid", "high"],
    )

    csv_path = write_summarized_wide_output(sample_config, execution_result, tmp_path / "outputs")
    row = _read_csv_rows(csv_path)[0]
    suffix = _group_suffix()

    assert row[f"item_1_justification_representative_1{suffix}"] == "mid"
    assert row[f"item_1_justification_representative_2{suffix}"] == "low"
    assert row[f"item_1_justification_representative_3{suffix}"] == "high"


def test_write_summarized_wide_output_rejects_categorical_mode(
    sample_config,
    sample_normalized_row,
    tmp_path: Path,
) -> None:
    categorical_config = sample_config.model_copy(update={"output_data_type": OutputDataType.CATEGORICAL})
    execution_result = _build_execution_result(
        sample_normalized_row,
        item_1_scores=[1, 4, 7],
        item_1_justifications=["low", "mid", "high"],
    )

    with pytest.raises(NotImplementedError, match="categorical"):
        write_summarized_wide_output(categorical_config, execution_result, tmp_path / "outputs")


def _build_execution_result(
    sample_normalized_row,
    *,
    item_1_scores: list[int],
    item_1_justifications: list[str],
) -> RepeatedCallExecutionResult:
    records = []
    for replicate_id, (score, justification) in enumerate(
        zip(item_1_scores, item_1_justifications, strict=True),
        start=1,
    ):
        records.append(
            CallExecutionRecord(
                run_id=f"run_{replicate_id:06d}",
                row_id=sample_normalized_row.row_id,
                participant_id=sample_normalized_row.participant_id,
                task_id=sample_normalized_row.task_id,
                model_provider="mock",
                model_name="mock-model-a",
                method_name="main_analysis",
                requested_temperature=0.0,
                effective_temperature=0.0,
                prompt_template_file="prompt_template_main_analysis.txt",
                prompt_id="main_analysis",
                prompt_version="v1",
                schema_name="main_analysis_v1",
                schema_version="1.0",
                replicate_id=replicate_id,
                effective_prompt="Prompt text",
                raw_json_output="{}",
                parsed_output={
                    "item_1_score": score,
                    "item_1_justification": justification,
                    "item_2_score": 2,
                    "item_2_justification": f"item2-{replicate_id}",
                },
                parse_status=ParseStatus.VALID,
            )
        )

    return RepeatedCallExecutionResult(records=tuple(records))


def _group_suffix() -> str:
    return (
        "__provider_mock"
        "__model_mock_model_a"
        "__method_main_analysis"
        "__template_prompt_template_main_analysis_txt"
        "__prompt_id_main_analysis"
        "__prompt_version_v1"
        "__schema_name_main_analysis_v1"
        "__schema_version_1_0"
    )


def _read_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
