from __future__ import annotations

import csv
import json
import math
import re
import statistics
from collections import OrderedDict
from pathlib import Path
from typing import Any

from ai_qualitative_analysis.pipeline.merging import merge_output_rows_with_original_dataset
from enums import OutputDataType, ParseStatus
from schemas import AnalysisConfig, CallExecutionRecord, RepeatedCallExecutionResult

_SUMMARIZED_WIDE_FILENAME = "output_ds_summaried_wide.csv"
_SUMMARIZED_WIDE_MANIFEST_FILENAME = "output_ds_summaried_wide.manifest.json"
_REPRESENTATIVE_JUSTIFICATION_COUNT = 3


def aggregate_summarized_wide_rows(
    config: AnalysisConfig,
    execution_result: RepeatedCallExecutionResult,
) -> tuple[list[str], list[dict[str, Any]]]:
    if config.output_data_type is OutputDataType.CATEGORICAL:
        raise NotImplementedError(
            "output_data_type='categorical' is not supported in the current implementation scope"
        )

    row_groups = _group_records_by_row_id(execution_result.records)
    column_order = ["row_id", "participant_id", "task_id"]
    summarized_rows: list[dict[str, Any]] = []

    for row_records in row_groups.values():
        row_summary = _build_base_row_summary(row_records)
        for group_records in _group_records_by_call_group(row_records).values():
            first_record = group_records[0]
            group_suffix = _build_group_suffix(first_record)
            valid_records = [
                record
                for record in group_records
                if record.parse_status is ParseStatus.VALID and record.parsed_output is not None
            ]
            row_summary[f"n_successful_parses{group_suffix}"] = len(valid_records)
            row_summary[f"n_parse_failures{group_suffix}"] = len(group_records) - len(valid_records)
            _append_column(column_order, f"n_successful_parses{group_suffix}")
            _append_column(column_order, f"n_parse_failures{group_suffix}")

            for item in config.analysis_schema.items:
                item_summary = _summarize_item(
                    config.output_data_type,
                    valid_records,
                    item.score_key,
                    item.justification_key,
                    group_suffix,
                )
                row_summary.update(item_summary)
                for column_name in item_summary:
                    _append_column(column_order, column_name)

        summarized_rows.append(row_summary)

    return column_order, summarized_rows


def write_summarized_wide_output(
    config: AnalysisConfig,
    execution_result: RepeatedCallExecutionResult,
    output_dir: str | Path,
) -> Path:
    output_path = Path(output_dir).expanduser().resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    csv_path = output_path / _SUMMARIZED_WIDE_FILENAME
    manifest_path = output_path / _SUMMARIZED_WIDE_MANIFEST_FILENAME
    column_order, rows = aggregate_summarized_wide_rows(config, execution_result)
    column_order, rows = merge_output_rows_with_original_dataset(config, rows, column_order)

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=column_order, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    _write_manifest(
        manifest_path,
        csv_path,
        column_order,
        rows,
        config.output_data_type,
        config.merge_output,
    )
    return csv_path


def _group_records_by_row_id(
    records: tuple[CallExecutionRecord, ...],
) -> "OrderedDict[str, list[CallExecutionRecord]]":
    grouped_records: "OrderedDict[str, list[CallExecutionRecord]]" = OrderedDict()
    for record in records:
        grouped_records.setdefault(record.row_id, []).append(record)
    return grouped_records


def _group_records_by_call_group(
    records: list[CallExecutionRecord],
) -> "OrderedDict[tuple[str, str, str, str, str, str, str, str, str], list[CallExecutionRecord]]":
    grouped_records: "OrderedDict[tuple[str, str, str, str, str, str, str, str, str], list[CallExecutionRecord]]" = OrderedDict()
    for record in records:
        grouped_records.setdefault(record.call_group_key, []).append(record)
    return grouped_records


def _build_base_row_summary(records: list[CallExecutionRecord]) -> dict[str, Any]:
    first_record = records[0]
    participant_ids = {record.participant_id for record in records}
    task_ids = {record.task_id for record in records}

    if len(participant_ids) > 1:
        raise ValueError(f"row_id={first_record.row_id!r} has inconsistent participant_id values")
    if len(task_ids) > 1:
        raise ValueError(f"row_id={first_record.row_id!r} has inconsistent task_id values")

    return {
        "row_id": first_record.row_id,
        "participant_id": first_record.participant_id,
        "task_id": first_record.task_id,
    }


def _build_group_suffix(record: CallExecutionRecord) -> str:
    return (
        f"__provider_{_sanitize_token(record.model_provider)}"
        f"__model_{_sanitize_token(record.model_name)}"
        f"__method_{_sanitize_token(record.method_name)}"
        f"__template_{_sanitize_token(record.prompt_template_file)}"
        f"__prompt_id_{_sanitize_token(record.prompt_id)}"
        f"__prompt_version_{_sanitize_token(record.prompt_version)}"
        f"__schema_name_{_sanitize_token(record.schema_name)}"
        f"__schema_version_{_sanitize_token(record.schema_version)}"
    )


def _sanitize_token(value: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    return sanitized.strip("_")


def _summarize_item(
    output_data_type: OutputDataType,
    valid_records: list[CallExecutionRecord],
    score_key: str,
    justification_key: str,
    group_suffix: str,
) -> dict[str, Any]:
    scores = [float(record.parsed_output[score_key]) for record in valid_records if record.parsed_output is not None]

    if not scores:
        return _empty_item_summary(output_data_type, score_key, justification_key, group_suffix)

    if output_data_type is OutputDataType.METRIC:
        summary = _summarize_metric_item(scores, score_key, group_suffix)
        target_score = summary[f"{score_key}_mean{group_suffix}"]
    elif output_data_type is OutputDataType.ORDINAL:
        summary = _summarize_ordinal_item(scores, score_key, group_suffix)
        target_score = summary[f"{score_key}_median{group_suffix}"]
    else:
        raise NotImplementedError(
            "output_data_type='categorical' is not supported in the current implementation scope"
        )

    summary.update(
        _build_representative_justification_summary(
            valid_records,
            score_key,
            justification_key,
            group_suffix,
            target_score,
        )
    )
    return summary


def _summarize_metric_item(scores: list[float], score_key: str, group_suffix: str) -> dict[str, Any]:
    # 🟡 ASSUMPTION: Metric dispersion uses sample standard deviation when at least two valid
    # scores exist, and 0.0 for single-score groups, because the blueprint requests standard
    # deviation but does not specify sample-vs-population behavior.
    standard_deviation = statistics.stdev(scores) if len(scores) > 1 else 0.0
    return {
        f"{score_key}_mean{group_suffix}": statistics.mean(scores),
        f"{score_key}_sd{group_suffix}": standard_deviation,
        f"{score_key}_min{group_suffix}": min(scores),
        f"{score_key}_max{group_suffix}": max(scores),
    }


def _summarize_ordinal_item(scores: list[float], score_key: str, group_suffix: str) -> dict[str, Any]:
    median_score = statistics.median(scores)
    # 🟡 ASSUMPTION: Ordinal IQR uses inclusive 25th/75th percentiles with linear interpolation,
    # and MAD is the median absolute deviation from the group median, because the blueprint names
    # IQR/MAD but does not fix a small-sample convention.
    q1 = _inclusive_percentile(scores, 0.25)
    q3 = _inclusive_percentile(scores, 0.75)
    mad = statistics.median(abs(score - median_score) for score in scores)
    return {
        f"{score_key}_median{group_suffix}": median_score,
        f"{score_key}_iqr{group_suffix}": q3 - q1,
        f"{score_key}_mad{group_suffix}": mad,
    }


def _inclusive_percentile(scores: list[float], percentile: float) -> float:
    ordered_scores = sorted(scores)
    if len(ordered_scores) == 1:
        return ordered_scores[0]

    position = (len(ordered_scores) - 1) * percentile
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return ordered_scores[lower_index]

    weight = position - lower_index
    lower_value = ordered_scores[lower_index]
    upper_value = ordered_scores[upper_index]
    return lower_value + (upper_value - lower_value) * weight


def _build_representative_justification_summary(
    valid_records: list[CallExecutionRecord],
    score_key: str,
    justification_key: str,
    group_suffix: str,
    target_score: float,
) -> dict[str, Any]:
    # 🟡 ASSUMPTION: Representative justifications default to three entries because the blueprint
    # treats 3 as the default but the first-pass config does not yet expose this as a setting.
    # Ties are broken deterministically by lower replicate_id and then lower run_id.
    ranked_justifications = sorted(
        (
            (
                abs(float(record.parsed_output[score_key]) - target_score),
                record.replicate_id,
                record.run_id,
                record.parsed_output[justification_key],
            )
            for record in valid_records
            if record.parsed_output is not None
        ),
    )
    chosen_justifications = [entry[3] for entry in ranked_justifications[:_REPRESENTATIVE_JUSTIFICATION_COUNT]]
    while len(chosen_justifications) < _REPRESENTATIVE_JUSTIFICATION_COUNT:
        chosen_justifications.append(None)

    return {
        f"{justification_key}_representative_{index}{group_suffix}": value
        for index, value in enumerate(chosen_justifications, start=1)
    }


def _empty_item_summary(
    output_data_type: OutputDataType,
    score_key: str,
    justification_key: str,
    group_suffix: str,
) -> dict[str, Any]:
    if output_data_type is OutputDataType.METRIC:
        summary = {
            f"{score_key}_mean{group_suffix}": None,
            f"{score_key}_sd{group_suffix}": None,
            f"{score_key}_min{group_suffix}": None,
            f"{score_key}_max{group_suffix}": None,
        }
    elif output_data_type is OutputDataType.ORDINAL:
        summary = {
            f"{score_key}_median{group_suffix}": None,
            f"{score_key}_iqr{group_suffix}": None,
            f"{score_key}_mad{group_suffix}": None,
        }
    else:
        raise NotImplementedError(
            "output_data_type='categorical' is not supported in the current implementation scope"
        )

    summary.update(
        {
            f"{justification_key}_representative_{index}{group_suffix}": None
            for index in range(1, _REPRESENTATIVE_JUSTIFICATION_COUNT + 1)
        }
    )
    return summary


def _append_column(column_order: list[str], column_name: str) -> None:
    if column_name not in column_order:
        column_order.append(column_name)


def _write_manifest(
    manifest_path: Path,
    csv_path: Path,
    column_order: list[str],
    rows: list[dict[str, Any]],
    output_data_type: OutputDataType,
    merge_output: bool,
) -> None:
    manifest_payload = {
        "csv_file": csv_path.name,
        "row_count": len(rows),
        "column_order": column_order,
        "merge_output": merge_output,
        "output_data_type": output_data_type.value,
        "representative_justification_count": _REPRESENTATIVE_JUSTIFICATION_COUNT,
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True), encoding="utf-8")
