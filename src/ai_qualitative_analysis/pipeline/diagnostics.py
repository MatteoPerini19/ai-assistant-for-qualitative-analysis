from __future__ import annotations

import csv
import json
import statistics
from collections import OrderedDict
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from enums import DiagnosticFlag, DiagnosticScope, DiagnosticSeverity, ParseStatus
from schemas import (
    AnalysisConfig,
    CallExecutionRecord,
    DiagnosticRecord,
    DiagnosticsResult,
    RepeatedCallExecutionResult,
)

_DIAGNOSTICS_DIRNAME = "diagnostics"
_SANITY_CHECKS_FILENAME = "sanity_checks.csv"
_SANITY_CHECKS_MANIFEST_FILENAME = "sanity_checks.manifest.json"
# 🟡 ASSUMPTION: High between-replicate variance is flagged when sample standard deviation exceeds
# 25% of the configured score range width, because the blueprint requires a variance diagnostic but
# does not define a first-pass threshold.
_HIGH_VARIANCE_THRESHOLD_FRACTION = 0.25


def build_sanity_check_records(
    config: AnalysisConfig,
    records_source: RepeatedCallExecutionResult | Sequence[CallExecutionRecord],
) -> DiagnosticsResult:
    records = _coerce_records(records_source)
    diagnostics: list[DiagnosticRecord] = []
    diagnostics.extend(_build_call_level_parse_diagnostics(records))

    call_groups = _group_records_by_call_group(records)
    diagnostic_counter = len(diagnostics) + 1
    for group_records in call_groups.values():
        temperature_diagnostic = _build_temperature_drift_diagnostic(group_records, diagnostic_counter)
        if temperature_diagnostic is not None:
            diagnostics.append(temperature_diagnostic)
            diagnostic_counter += 1

        identical_output_diagnostic = _build_identical_output_diagnostic(group_records, diagnostic_counter)
        if identical_output_diagnostic is not None:
            diagnostics.append(identical_output_diagnostic)
            diagnostic_counter += 1

        variance_diagnostics = _build_high_variance_diagnostics(config, group_records, diagnostic_counter)
        diagnostics.extend(variance_diagnostics)
        diagnostic_counter += len(variance_diagnostics)

    return DiagnosticsResult(records=tuple(diagnostics))


def write_sanity_checks_output(
    config: AnalysisConfig,
    records_source: RepeatedCallExecutionResult | Sequence[CallExecutionRecord],
    output_dir: str | Path,
) -> Path:
    output_path = Path(output_dir).expanduser().resolve()
    diagnostics_path = output_path / _DIAGNOSTICS_DIRNAME
    diagnostics_path.mkdir(parents=True, exist_ok=True)

    csv_path = diagnostics_path / _SANITY_CHECKS_FILENAME
    manifest_path = diagnostics_path / _SANITY_CHECKS_MANIFEST_FILENAME
    diagnostics = build_sanity_check_records(config, records_source)
    column_order = _build_sanity_checks_column_order()

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=column_order, extrasaction="ignore")
        writer.writeheader()
        for row in (_diagnostic_to_row(record) for record in diagnostics.records):
            writer.writerow(row)

    _write_manifest(manifest_path, csv_path, diagnostics)
    return csv_path


def _coerce_records(
    records_source: RepeatedCallExecutionResult | Sequence[CallExecutionRecord],
) -> tuple[CallExecutionRecord, ...]:
    if isinstance(records_source, RepeatedCallExecutionResult):
        return records_source.records
    return tuple(records_source)


def _build_call_level_parse_diagnostics(
    records_source: Sequence[CallExecutionRecord],
) -> list[DiagnosticRecord]:
    parse_status_to_flag = {
        ParseStatus.INVALID_JSON: DiagnosticFlag.INVALID_JSON,
        ParseStatus.SCHEMA_MISMATCH: DiagnosticFlag.SCHEMA_MISMATCH,
        ParseStatus.MISSING_FIELD: DiagnosticFlag.MISSING_FIELD,
        ParseStatus.OUT_OF_RANGE_SCORE: DiagnosticFlag.OUT_OF_RANGE_SCORE,
        ParseStatus.EMPTY_JUSTIFICATION: DiagnosticFlag.EMPTY_JUSTIFICATION,
    }

    diagnostics: list[DiagnosticRecord] = []
    diagnostic_count = 0
    for record in records_source:
        flag_code = parse_status_to_flag.get(record.parse_status)
        if flag_code is None:
            continue

        diagnostic_count += 1
        diagnostics.append(
            DiagnosticRecord(
                diagnostic_id=f"diag_{diagnostic_count:06d}",
                diagnostic_scope=DiagnosticScope.CALL,
                severity=DiagnosticSeverity.ERROR,
                flag_code=flag_code,
                row_id=record.row_id,
                run_id=record.run_id,
                model_provider=record.model_provider,
                model_name=record.model_name,
                method_name=record.method_name,
                prompt_template_file=record.prompt_template_file,
                prompt_id=record.prompt_id,
                prompt_version=record.prompt_version,
                schema_name=record.schema_name,
                schema_version=record.schema_version,
                replicate_id=record.replicate_id,
                observed_value=record.parse_status.value,
                threshold_value=ParseStatus.VALID.value,
                parse_status=record.parse_status,
                message=record.validation_error or f"Call failed validation with parse_status={record.parse_status.value}",
            )
        )

    return diagnostics


def _build_temperature_drift_diagnostic(
    group_records: list[CallExecutionRecord],
    diagnostic_index: int,
) -> DiagnosticRecord | None:
    requested_temperatures = _sorted_unique_strings(record.requested_temperature for record in group_records)
    effective_temperatures = _sorted_unique_strings(record.effective_temperature for record in group_records)
    if len(requested_temperatures) <= 1 and len(effective_temperatures) <= 1:
        return None

    first_record = group_records[0]
    observed_value = json.dumps(
        {
            "requested_temperature_values": requested_temperatures,
            "effective_temperature_values": effective_temperatures,
        },
        sort_keys=True,
    )
    return DiagnosticRecord(
        diagnostic_id=f"diag_{diagnostic_index:06d}",
        diagnostic_scope=DiagnosticScope.CALL_GROUP,
        severity=DiagnosticSeverity.ERROR,
        flag_code=DiagnosticFlag.TEMPERATURE_DRIFT,
        row_id=first_record.row_id,
        model_provider=first_record.model_provider,
        model_name=first_record.model_name,
        method_name=first_record.method_name,
        prompt_template_file=first_record.prompt_template_file,
        prompt_id=first_record.prompt_id,
        prompt_version=first_record.prompt_version,
        schema_name=first_record.schema_name,
        schema_version=first_record.schema_version,
        observed_value=observed_value,
        threshold_value="exactly one requested temperature and one effective temperature per call group",
        message="Temperature drift detected within a supposed fixed-temperature call group",
    )


def _build_identical_output_diagnostic(
    group_records: list[CallExecutionRecord],
    diagnostic_index: int,
) -> DiagnosticRecord | None:
    valid_records = [
        record for record in group_records if record.parse_status is ParseStatus.VALID and record.parsed_output is not None
    ]
    if len(valid_records) < 2:
        return None

    # 🟡 ASSUMPTION: "Unexpectedly identical outputs" means every valid parsed output in a call
    # group is identical after canonical JSON serialization, because the blueprint names this
    # diagnostic but does not define a softer similarity threshold.
    output_signatures = {
        json.dumps(record.parsed_output, sort_keys=True, separators=(",", ":"))
        for record in valid_records
        if record.parsed_output is not None
    }
    if len(output_signatures) != 1:
        return None

    first_record = valid_records[0]
    return DiagnosticRecord(
        diagnostic_id=f"diag_{diagnostic_index:06d}",
        diagnostic_scope=DiagnosticScope.CALL_GROUP,
        severity=DiagnosticSeverity.WARNING,
        flag_code=DiagnosticFlag.IDENTICAL_OUTPUTS,
        row_id=first_record.row_id,
        model_provider=first_record.model_provider,
        model_name=first_record.model_name,
        method_name=first_record.method_name,
        prompt_template_file=first_record.prompt_template_file,
        prompt_id=first_record.prompt_id,
        prompt_version=first_record.prompt_version,
        schema_name=first_record.schema_name,
        schema_version=first_record.schema_version,
        observed_value=str(len(valid_records)),
        threshold_value="more than one distinct valid parsed output within a call group",
        message="All valid parsed outputs in this call group are identical",
    )


def _build_high_variance_diagnostics(
    config: AnalysisConfig,
    group_records: list[CallExecutionRecord],
    diagnostic_start_index: int,
) -> list[DiagnosticRecord]:
    diagnostics: list[DiagnosticRecord] = []
    valid_records = [
        record for record in group_records if record.parse_status is ParseStatus.VALID and record.parsed_output is not None
    ]
    if len(valid_records) < 2:
        return diagnostics

    for item_offset, item in enumerate(config.analysis_schema.items):
        scores = [
            float(record.parsed_output[item.score_key])
            for record in valid_records
            if record.parsed_output is not None
        ]
        if len(scores) < 2:
            continue

        score_range_width = item.max_score - item.min_score
        variance_threshold = score_range_width * _HIGH_VARIANCE_THRESHOLD_FRACTION
        sample_standard_deviation = statistics.stdev(scores)
        if sample_standard_deviation <= variance_threshold:
            continue

        first_record = valid_records[0]
        diagnostics.append(
            DiagnosticRecord(
                diagnostic_id=f"diag_{diagnostic_start_index + item_offset:06d}",
                diagnostic_scope=DiagnosticScope.CALL_GROUP,
                severity=DiagnosticSeverity.WARNING,
                flag_code=DiagnosticFlag.HIGH_BETWEEN_REPLICATE_VARIANCE,
                row_id=first_record.row_id,
                model_provider=first_record.model_provider,
                model_name=first_record.model_name,
                method_name=first_record.method_name,
                prompt_template_file=first_record.prompt_template_file,
                prompt_id=first_record.prompt_id,
                prompt_version=first_record.prompt_version,
                schema_name=first_record.schema_name,
                schema_version=first_record.schema_version,
                item_id=item.item_id,
                score_key=item.score_key,
                observed_value=f"{sample_standard_deviation:.6f}",
                threshold_value=f"{variance_threshold:.6f}",
                message=(
                    f"Between-replicate variance is high for {item.score_key}: "
                    f"sd={sample_standard_deviation:.6f}"
                ),
            )
        )

    return diagnostics


def _group_records_by_call_group(
    records_source: Sequence[CallExecutionRecord],
) -> "OrderedDict[tuple[str, str, str, str, str, str, str, str, str], list[CallExecutionRecord]]":
    grouped_records: "OrderedDict[tuple[str, str, str, str, str, str, str, str, str], list[CallExecutionRecord]]" = OrderedDict()
    for record in records_source:
        grouped_records.setdefault(record.call_group_key, []).append(record)
    return grouped_records


def _sorted_unique_strings(values: Sequence[Any]) -> list[str]:
    return sorted({repr(value) for value in values})


def _build_sanity_checks_column_order() -> list[str]:
    return [
        "diagnostic_id",
        "diagnostic_scope",
        "severity",
        "flag_code",
        "row_id",
        "run_id",
        "model_provider",
        "model_name",
        "method_name",
        "prompt_template_file",
        "prompt_id",
        "prompt_version",
        "schema_name",
        "schema_version",
        "replicate_id",
        "item_id",
        "score_key",
        "observed_value",
        "threshold_value",
        "parse_status",
        "message",
    ]


def _diagnostic_to_row(record: DiagnosticRecord) -> dict[str, Any]:
    return {
        "diagnostic_id": record.diagnostic_id,
        "diagnostic_scope": record.diagnostic_scope.value,
        "severity": record.severity.value,
        "flag_code": record.flag_code.value,
        "row_id": record.row_id,
        "run_id": record.run_id,
        "model_provider": record.model_provider,
        "model_name": record.model_name,
        "method_name": record.method_name,
        "prompt_template_file": record.prompt_template_file,
        "prompt_id": record.prompt_id,
        "prompt_version": record.prompt_version,
        "schema_name": record.schema_name,
        "schema_version": record.schema_version,
        "replicate_id": record.replicate_id,
        "item_id": record.item_id,
        "score_key": record.score_key,
        "observed_value": record.observed_value,
        "threshold_value": record.threshold_value,
        "parse_status": None if record.parse_status is None else record.parse_status.value,
        "message": record.message,
    }


def _write_manifest(
    manifest_path: Path,
    csv_path: Path,
    diagnostics: DiagnosticsResult,
) -> None:
    flag_counts: dict[str, int] = {}
    for record in diagnostics.records:
        flag_counts[record.flag_code.value] = flag_counts.get(record.flag_code.value, 0) + 1

    manifest_payload = {
        "csv_file": csv_path.name,
        "row_count": len(diagnostics.records),
        "flag_counts": flag_counts,
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True), encoding="utf-8")
