from __future__ import annotations

import csv
import json
from pathlib import Path

from ai_qualitative_analysis.pipeline import execute_repeated_calls, write_inclusive_long_output
from providers.mock import MockProvider


def test_write_inclusive_long_output_creates_file_and_matches_call_count(
    sample_config,
    sample_normalized_dataset,
    tmp_path: Path,
) -> None:
    execution_result = execute_repeated_calls(
        sample_config,
        sample_normalized_dataset,
        providers_by_name={"mock": MockProvider()},
    )

    csv_path = write_inclusive_long_output(sample_config, execution_result, tmp_path / "outputs")

    assert csv_path.exists()
    rows = _read_csv_rows(csv_path)
    assert len(rows) == len(execution_result.records)

    manifest_path = csv_path.with_name("output_ds_inclusive_long.manifest.json")
    assert manifest_path.exists()
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_payload["row_count"] == len(execution_result.records)
    assert manifest_payload["csv_file"] == "output_ds_inclusive_long.csv"


def test_write_inclusive_long_output_uses_stable_explicit_column_order(
    sample_config,
    sample_normalized_dataset,
    tmp_path: Path,
) -> None:
    execution_result = execute_repeated_calls(
        sample_config,
        sample_normalized_dataset,
        providers_by_name={"mock": MockProvider()},
    )

    csv_path = write_inclusive_long_output(sample_config, execution_result, tmp_path / "outputs")
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        columns = list(csv.DictReader(handle).fieldnames or [])

    assert columns == [
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
        "item_1_score",
        "item_1_justification",
        "item_2_score",
        "item_2_justification",
        "raw_json_output",
        "parse_status",
        "validation_error",
        "error_message",
    ]


def test_write_inclusive_long_output_respects_raw_json_retention_setting(
    sample_config,
    sample_normalized_dataset,
    tmp_path: Path,
) -> None:
    config_without_raw_json = sample_config.model_copy(update={"retain_raw_json_output": False})
    execution_result = execute_repeated_calls(
        config_without_raw_json,
        sample_normalized_dataset,
        providers_by_name={"mock": MockProvider()},
    )

    csv_path = write_inclusive_long_output(config_without_raw_json, execution_result, tmp_path / "outputs")
    rows = _read_csv_rows(csv_path)
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        columns = list(csv.DictReader(handle).fieldnames or [])

    assert "raw_json_output" not in columns
    assert len(rows) == len(execution_result.records)
def _read_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
