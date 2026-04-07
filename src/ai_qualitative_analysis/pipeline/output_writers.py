from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from ai_qualitative_analysis.pipeline.merging import merge_output_rows_with_original_dataset
from schemas import AnalysisConfig, CallExecutionRecord, RepeatedCallExecutionResult

_INCLUSIVE_LONG_FILENAME = "output_ds_inclusive_long.csv"
_INCLUSIVE_LONG_MANIFEST_FILENAME = "output_ds_inclusive_long.manifest.json"


def write_inclusive_long_output(
    config: AnalysisConfig,
    execution_result: RepeatedCallExecutionResult,
    output_dir: str | Path,
) -> Path:
    output_path = Path(output_dir).expanduser().resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    csv_path = output_path / _INCLUSIVE_LONG_FILENAME
    manifest_path = output_path / _INCLUSIVE_LONG_MANIFEST_FILENAME
    column_order = _build_inclusive_long_column_order(config)
    rows = [_record_to_output_row(record, config) for record in execution_result.records]
    column_order, rows = merge_output_rows_with_original_dataset(config, rows, column_order)

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=column_order, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    _write_manifest(
        manifest_path,
        csv_path,
        execution_result,
        column_order,
        config.retain_raw_json_output,
        config.merge_output,
    )
    return csv_path


def _build_inclusive_long_column_order(config: AnalysisConfig) -> list[str]:
    columns = [
        "run_id",
        "row_id",
        "participant_id",
        "task_id",
        "model_provider",
        "model_name",
        "server_side_version",
        "method_name",
        "requested_temperature",
        "effective_temperature",
        "prompt_template_file",
        "prompt_id",
        "prompt_version",
        "schema_name",
        "schema_version",
        "replicate_id",
        "task_type",
        "thinking_budget",
        "seed",
        "effective_prompt",
    ]

    for field_spec in config.analysis_schema.fields:
        columns.extend((field_spec.score_key, field_spec.justification_key))

    if config.retain_raw_json_output:
        columns.append("raw_json_output")

    columns.extend(("parse_status", "validation_error", "error_message"))
    return columns


def _record_to_output_row(record: CallExecutionRecord, config: AnalysisConfig) -> dict[str, Any]:
    parsed_output = record.parsed_output or {}
    row: dict[str, Any] = {
        "run_id": record.run_id,
        "row_id": record.row_id,
        "participant_id": record.participant_id,
        "task_id": record.task_id,
        "model_provider": record.model_provider,
        "model_name": record.model_name,
        "server_side_version": record.server_side_version,
        "method_name": record.method_name,
        "requested_temperature": record.requested_temperature,
        "effective_temperature": record.effective_temperature,
        "prompt_template_file": record.prompt_template_file,
        "prompt_id": record.prompt_id,
        "prompt_version": record.prompt_version,
        "schema_name": record.schema_name,
        "schema_version": record.schema_version,
        "replicate_id": record.replicate_id,
        "task_type": record.task_type,
        "thinking_budget": record.thinking_budget,
        "seed": record.seed,
        "effective_prompt": record.effective_prompt,
        "parse_status": record.parse_status.value,
        "validation_error": record.validation_error,
        "error_message": record.error_message,
    }

    for field_spec in config.analysis_schema.fields:
        row[field_spec.score_key] = parsed_output.get(field_spec.score_key)
        row[field_spec.justification_key] = parsed_output.get(field_spec.justification_key)

    if config.retain_raw_json_output:
        row["raw_json_output"] = record.raw_json_output

    return row


def _write_manifest(
    manifest_path: Path,
    csv_path: Path,
    execution_result: RepeatedCallExecutionResult,
    column_order: list[str],
    retain_raw_json_output: bool,
    merge_output: bool,
) -> None:
    parse_status_counts: dict[str, int] = {}
    for record in execution_result.records:
        status = record.parse_status.value
        parse_status_counts[status] = parse_status_counts.get(status, 0) + 1

    manifest_payload = {
        "csv_file": csv_path.name,
        "row_count": len(execution_result.records),
        "column_order": column_order,
        "retain_raw_json_output": retain_raw_json_output,
        "merge_output": merge_output,
        "parse_status_counts": parse_status_counts,
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True), encoding="utf-8")
