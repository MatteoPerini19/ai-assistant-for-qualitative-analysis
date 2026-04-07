from __future__ import annotations

import csv
import json
from pathlib import Path

from ai_qualitative_analysis.pipeline import build_sanity_check_records, write_sanity_checks_output
from enums import DiagnosticFlag, ParseStatus
from schemas import CallExecutionRecord


def test_build_sanity_check_records_flags_call_level_parse_failures(sample_config, sample_normalized_row) -> None:
    records = [
        _build_record(
            sample_normalized_row,
            run_id="run_000001",
            replicate_id=1,
            parse_status=ParseStatus.INVALID_JSON,
            validation_error="Malformed JSON payload",
        ),
        _build_record(
            sample_normalized_row,
            run_id="run_000002",
            replicate_id=2,
            parse_status=ParseStatus.SCHEMA_MISMATCH,
            validation_error="Expected integer score",
        ),
        _build_record(
            sample_normalized_row,
            run_id="run_000003",
            replicate_id=3,
            parse_status=ParseStatus.MISSING_FIELD,
            validation_error="Missing item_1_justification",
        ),
        _build_record(
            sample_normalized_row,
            run_id="run_000004",
            replicate_id=4,
            parse_status=ParseStatus.OUT_OF_RANGE_SCORE,
            validation_error="item_1_score=10 is outside range",
        ),
        _build_record(
            sample_normalized_row,
            run_id="run_000005",
            replicate_id=5,
            parse_status=ParseStatus.EMPTY_JUSTIFICATION,
            validation_error="item_1_justification must not be empty",
        ),
    ]

    diagnostics = build_sanity_check_records(sample_config, records)
    flag_codes = {record.flag_code for record in diagnostics.records}

    assert DiagnosticFlag.INVALID_JSON in flag_codes
    assert DiagnosticFlag.SCHEMA_MISMATCH in flag_codes
    assert DiagnosticFlag.MISSING_FIELD in flag_codes
    assert DiagnosticFlag.OUT_OF_RANGE_SCORE in flag_codes
    assert DiagnosticFlag.EMPTY_JUSTIFICATION in flag_codes


def test_build_sanity_check_records_flags_temperature_drift(sample_config, sample_normalized_row) -> None:
    records = [
        _build_record(sample_normalized_row, run_id="run_000001", replicate_id=1, requested_temperature=0.0),
        _build_record(sample_normalized_row, run_id="run_000002", replicate_id=2, requested_temperature=0.2),
    ]

    diagnostics = build_sanity_check_records(sample_config, records)

    assert any(record.flag_code is DiagnosticFlag.TEMPERATURE_DRIFT for record in diagnostics.records)


def test_build_sanity_check_records_flags_identical_outputs(sample_config, sample_normalized_row) -> None:
    parsed_output = {
        "item_1_score": 4,
        "item_1_justification": "Same output",
        "item_2_score": 2,
        "item_2_justification": "Same second item",
    }
    records = [
        _build_record(
            sample_normalized_row,
            run_id="run_000001",
            replicate_id=1,
            parsed_output=parsed_output,
        ),
        _build_record(
            sample_normalized_row,
            run_id="run_000002",
            replicate_id=2,
            parsed_output=parsed_output,
        ),
    ]

    diagnostics = build_sanity_check_records(sample_config, records)

    assert any(record.flag_code is DiagnosticFlag.IDENTICAL_OUTPUTS for record in diagnostics.records)


def test_build_sanity_check_records_flags_high_between_replicate_variance(
    sample_config,
    sample_normalized_row,
) -> None:
    records = [
        _build_record(
            sample_normalized_row,
            run_id="run_000001",
            replicate_id=1,
            parsed_output=_parsed_output(score=1, justification="low"),
        ),
        _build_record(
            sample_normalized_row,
            run_id="run_000002",
            replicate_id=2,
            parsed_output=_parsed_output(score=4, justification="mid"),
        ),
        _build_record(
            sample_normalized_row,
            run_id="run_000003",
            replicate_id=3,
            parsed_output=_parsed_output(score=7, justification="high"),
        ),
    ]

    diagnostics = build_sanity_check_records(sample_config, records)

    assert any(
        record.flag_code is DiagnosticFlag.HIGH_BETWEEN_REPLICATE_VARIANCE and record.score_key == "item_1_score"
        for record in diagnostics.records
    )


def test_write_sanity_checks_output_writes_csv_under_diagnostics(
    sample_config,
    sample_normalized_row,
    tmp_path: Path,
) -> None:
    records = [
        _build_record(
            sample_normalized_row,
            run_id="run_000001",
            replicate_id=1,
            parse_status=ParseStatus.INVALID_JSON,
            validation_error="Malformed JSON payload",
        ),
        _build_record(
            sample_normalized_row,
            run_id="run_000002",
            replicate_id=2,
            parsed_output=_parsed_output(score=4, justification="Same output"),
        ),
        _build_record(
            sample_normalized_row,
            run_id="run_000003",
            replicate_id=3,
            parsed_output=_parsed_output(score=4, justification="Same output"),
        ),
    ]

    csv_path = write_sanity_checks_output(sample_config, records, tmp_path / "outputs")

    assert csv_path.exists()
    assert csv_path.parent.name == "diagnostics"
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        columns = list(reader.fieldnames or [])

    assert rows
    assert "flag_code" in columns
    assert "message" in columns

    manifest_path = csv_path.with_name("sanity_checks.manifest.json")
    assert manifest_path.exists()
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_payload["csv_file"] == "sanity_checks.csv"
    assert manifest_payload["row_count"] == len(rows)


def _build_record(
    sample_normalized_row,
    *,
    run_id: str,
    replicate_id: int,
    parse_status: ParseStatus = ParseStatus.VALID,
    validation_error: str | None = None,
    requested_temperature: float = 0.0,
    effective_temperature: float = 0.0,
    parsed_output: dict[str, object] | None = None,
) -> CallExecutionRecord:
    if parse_status is ParseStatus.VALID:
        record_parsed_output = parsed_output or _parsed_output(score=4, justification="fallback")
    else:
        record_parsed_output = None
    return CallExecutionRecord(
        run_id=run_id,
        row_id=sample_normalized_row.row_id,
        participant_id=sample_normalized_row.participant_id,
        task_id=sample_normalized_row.task_id,
        model_provider="mock",
        model_name="mock-model-a",
        method_name="main_analysis",
        requested_temperature=requested_temperature,
        effective_temperature=effective_temperature,
        prompt_template_file="prompt_template_main_analysis.txt",
        prompt_id="main_analysis",
        prompt_version="v1",
        schema_name="main_analysis_v1",
        schema_version="1.0",
        replicate_id=replicate_id,
        effective_prompt="Prompt text",
        raw_json_output="{}",
        parsed_output=record_parsed_output,
        parse_status=parse_status,
        validation_error=validation_error,
    )


def _parsed_output(*, score: int, justification: str) -> dict[str, object]:
    return {
        "item_1_score": score,
        "item_1_justification": justification,
        "item_2_score": 2,
        "item_2_justification": "stable item 2",
    }
