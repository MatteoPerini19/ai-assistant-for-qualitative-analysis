from __future__ import annotations

import csv
from pathlib import Path

from pydantic import ValidationError

from schemas import AnalysisConfig, NormalizedInputDataset, NormalizedInputRow

_SUPPORTED_CANONICAL_COLUMNS = tuple(NormalizedInputRow.model_fields.keys())
_REQUIRED_CANONICAL_COLUMNS = ("row_id", "participant_text")
_UNSUPPORTED_FILE_INPUT_COLUMNS = ("text_file_name", "audio_file_name")
_COMPARATIVE_COLUMN_ROOTS = (
    "participant_text",
    "task_id",
    "task_label",
    "task_info",
    "task_full_text",
    "text_file_name",
    "audio_file_name",
)


def load_normalized_input_dataset(config: AnalysisConfig) -> NormalizedInputDataset:
    dataset_path = config.input_data.dataset_file
    with dataset_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        original_columns = _read_original_columns(reader, dataset_path)
        canonical_to_source = _resolve_canonical_sources(config, original_columns)
        normalized_columns = tuple(canonical_to_source.keys())

        _raise_if_required_columns_missing(normalized_columns, original_columns)

        normalized_rows = tuple(
            _build_normalized_row(row, line_number=index, canonical_to_source=canonical_to_source)
            for index, row in enumerate(reader, start=2)
        )

    return NormalizedInputDataset(
        source_file=dataset_path,
        original_columns=original_columns,
        normalized_columns=normalized_columns,
        rows=normalized_rows,
    )


def _read_original_columns(reader: csv.DictReader[str], dataset_path: Path) -> tuple[str, ...]:
    if reader.fieldnames is None:
        raise ValueError(f"Input CSV must include a header row: {dataset_path}")
    return tuple(reader.fieldnames)


def _resolve_canonical_sources(
    config: AnalysisConfig,
    original_columns: tuple[str, ...],
) -> dict[str, str]:
    configured_mapping = config.input_data.column_mapping.model_dump(exclude_none=True)

    missing_mapped_sources = sorted(
        source_column
        for source_column in configured_mapping.values()
        if source_column not in original_columns
    )
    if missing_mapped_sources:
        # 🟡 ASSUMPTION: Explicitly configured source columns are treated as intentional user input,
        # so any mapped source column missing from the CSV is an error even when the canonical field
        # would otherwise be optional.
        raise ValueError(
            "Configured source columns were not found in the input CSV: "
            f"{missing_mapped_sources}"
        )

    canonical_to_source: dict[str, str] = {}
    for canonical_column in _SUPPORTED_CANONICAL_COLUMNS:
        if canonical_column in configured_mapping:
            canonical_to_source[canonical_column] = configured_mapping[canonical_column]
        elif canonical_column in original_columns:
            canonical_to_source[canonical_column] = canonical_column

    return canonical_to_source


def _raise_if_required_columns_missing(
    normalized_columns: tuple[str, ...],
    original_columns: tuple[str, ...],
) -> None:
    if "participant_text" not in normalized_columns:
        unsupported_columns = _detect_unsupported_file_inputs(original_columns)
        if unsupported_columns:
            raise NotImplementedError(
                "File-based qualitative inputs are not yet supported in the current implementation "
                f"scope. Detected columns: {unsupported_columns}. Use direct `participant_text` input."
            )

        comparative_columns = _detect_comparative_columns(original_columns)
        if comparative_columns:
            raise NotImplementedError(
                "Comparative wide-format input is not yet supported in the current implementation "
                f"scope. Detected columns: {comparative_columns}."
            )

    missing_required_columns = sorted(
        column_name
        for column_name in _REQUIRED_CANONICAL_COLUMNS
        if column_name not in normalized_columns
    )
    if missing_required_columns:
        raise ValueError(
            "Normalized input dataset is missing required canonical columns after applying "
            f"column_mapping: {missing_required_columns}"
        )


def _build_normalized_row(
    raw_row: dict[str, str | None],
    *,
    line_number: int,
    canonical_to_source: dict[str, str],
) -> NormalizedInputRow:
    normalized_payload = {
        canonical_column: raw_row[source_column]
        for canonical_column, source_column in canonical_to_source.items()
    }

    try:
        return NormalizedInputRow.model_validate(normalized_payload)
    except ValidationError as exc:
        raise ValueError(f"Row {line_number} failed normalized input validation: {exc}") from exc


def _detect_unsupported_file_inputs(original_columns: tuple[str, ...]) -> list[str]:
    return sorted(column for column in original_columns if column in _UNSUPPORTED_FILE_INPUT_COLUMNS)


def _detect_comparative_columns(original_columns: tuple[str, ...]) -> list[str]:
    supported_comparative_columns = {
        f"{root}_1" for root in _COMPARATIVE_COLUMN_ROOTS
    }.union({f"{root}_2" for root in _COMPARATIVE_COLUMN_ROOTS})
    return sorted(column for column in original_columns if column in supported_comparative_columns)
