from __future__ import annotations

import csv
from collections import OrderedDict
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from schemas import AnalysisConfig


def merge_output_rows_with_original_dataset(
    config: AnalysisConfig,
    output_rows: Sequence[dict[str, Any]],
    column_order: list[str],
) -> tuple[list[str], list[dict[str, Any]]]:
    if not config.merge_output:
        return column_order, list(output_rows)

    original_columns, rows_by_row_id = _load_original_rows_by_row_id(config)
    # 🟡 ASSUMPTION: Original dataset columns that would collide with existing output columns are
    # omitted from the merged append step, because the output already carries the canonical value
    # and silently overwriting it would risk distorting rows.
    merge_columns = [column for column in original_columns if column not in column_order]

    merged_rows: list[dict[str, Any]] = []
    for output_row in output_rows:
        row_id = str(output_row["row_id"])
        original_row = rows_by_row_id.get(row_id)
        if original_row is None:
            raise ValueError(f"Could not merge outputs: row_id={row_id!r} was not found in the original dataset")

        merged_row = dict(output_row)
        for column_name in merge_columns:
            merged_row[column_name] = original_row.get(column_name)
        merged_rows.append(merged_row)

    return [*column_order, *merge_columns], merged_rows


def _load_original_rows_by_row_id(
    config: AnalysisConfig,
) -> tuple[tuple[str, ...], "OrderedDict[str, dict[str, str]]"]:
    dataset_path = Path(config.input_data.dataset_file)
    with dataset_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Input CSV must include a header row: {dataset_path}")
        original_columns = tuple(reader.fieldnames)
        row_id_source_column = _resolve_row_id_source_column(config, original_columns)
        rows_by_row_id: "OrderedDict[str, dict[str, str]]" = OrderedDict()

        for line_number, row in enumerate(reader, start=2):
            row_id = (row.get(row_id_source_column) or "").strip()
            if not row_id:
                raise ValueError(
                    "Could not merge outputs: the original dataset contains a blank row_id value "
                    f"in source column {row_id_source_column!r} at line {line_number}"
                )
            if row_id in rows_by_row_id:
                raise ValueError(
                    "Could not merge outputs without duplicating rows because the original dataset "
                    f"contains duplicate row_id values: {row_id!r}"
                )
            rows_by_row_id[row_id] = row

    return original_columns, rows_by_row_id


def _resolve_row_id_source_column(config: AnalysisConfig, original_columns: tuple[str, ...]) -> str:
    configured_row_id_source = config.input_data.column_mapping.row_id
    if configured_row_id_source is not None:
        return configured_row_id_source
    if "row_id" in original_columns:
        return "row_id"
    raise ValueError("Could not merge outputs because input_data.column_mapping.row_id is not available")
