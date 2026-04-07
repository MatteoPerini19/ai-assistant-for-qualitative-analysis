from __future__ import annotations

import csv
from pathlib import Path

import yaml

from ai_qualitative_analysis.pipeline.run import main
from schemas import ProviderResponse, ProviderResponseMetadata


def test_pipeline_entrypoint_smoke_runs_fixture_config_end_to_end(
    sample_config_path: Path,
    tmp_path: Path,
    capsys,
) -> None:
    # Reuse the shared first-pass fixture config so the smoke test exercises the same deterministic
    # mock-backed path users will run first from the repo entry point.
    output_dir = tmp_path / "outputs"

    exit_code = main([str(sample_config_path), "--output-dir", str(output_dir)])

    assert exit_code == 0
    assert (output_dir / "output_ds_inclusive_long.csv").exists()
    assert (output_dir / "output_ds_summaried_wide.csv").exists()
    assert (output_dir / "diagnostics" / "sanity_checks.csv").exists()

    inclusive_rows = _read_csv_rows(output_dir / "output_ds_inclusive_long.csv")
    wide_rows = _read_csv_rows(output_dir / "output_ds_summaried_wide.csv")
    assert len(inclusive_rows) == 9
    assert len(wide_rows) == 3
    assert {row["model_provider"] for row in inclusive_rows} == {"mock"}
    assert {row["parse_status"] for row in inclusive_rows} == {"valid"}
    assert {row["prompt_id"] for row in inclusive_rows} == {"main_analysis"}
    assert {row["prompt_version"] for row in inclusive_rows} == {"v1"}
    assert {row["schema_name"] for row in inclusive_rows} == {"main_analysis_v1"}
    assert {row["schema_version"] for row in inclusive_rows} == {"1.0"}

    stdout = capsys.readouterr().out
    assert "output_ds_inclusive_long.csv" in stdout
    assert "output_ds_summaried_wide.csv" in stdout


def test_pipeline_entrypoint_uses_openai_provider_selected_from_config_without_network(
    sample_config_path: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    # Use the real CLI path here, but swap in a fake OpenAI provider so provider selection
    # is exercised without any live network dependency.
    config_path = _write_openai_config(sample_config_path, tmp_path)
    output_dir = tmp_path / "outputs_openai"

    class FakeOpenAIProvider:
        provider_name = "openai"

        def generate(self, request):
            return ProviderResponse(
                raw_output_text=(
                    '{"item_1_score": 5, "item_1_justification": "Clear evidence.", '
                    '"item_2_score": 4, "item_2_justification": "Consistent tone."}'
                ),
                metadata=ProviderResponseMetadata(
                    model_provider="openai",
                    model_name=request.model_name,
                    method_name=request.method_name,
                    prompt_template_file=request.prompt_template_file,
                    prompt_id=request.prompt_id,
                    prompt_version=request.prompt_version,
                    schema_name=request.schema_name,
                    schema_version=request.schema_version,
                    requested_temperature=request.requested_temperature,
                    effective_temperature=request.effective_temperature,
                    thinking_budget=request.thinking_budget,
                    seed=request.seed,
                ),
            )

    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setattr(
        "ai_qualitative_analysis.pipeline.run._build_openai_provider_from_environment",
        lambda config: FakeOpenAIProvider(),
    )

    exit_code = main([str(config_path), "--output-dir", str(output_dir)])

    assert exit_code == 0
    inclusive_rows = _read_csv_rows(output_dir / "output_ds_inclusive_long.csv")
    assert inclusive_rows
    assert {row["model_provider"] for row in inclusive_rows} == {"openai"}
    assert {row["model_name"] for row in inclusive_rows} == {"gpt-5-nano"}


def test_pipeline_entrypoint_fails_clearly_when_openai_api_key_is_missing(
    sample_config_path: Path,
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    # This covers the user-facing failure path where config selects a live provider but the
    # required credential is missing from the environment.
    config_path = _write_openai_config(sample_config_path, tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    try:
        main([str(config_path), "--output-dir", str(tmp_path / "outputs_missing_key")])
    except SystemExit as exc:
        assert exc.code == 1
    else:
        raise AssertionError("Expected the CLI to exit when OPENAI_API_KEY is missing")

    stderr = capsys.readouterr().err
    assert "OPENAI_API_KEY" in stderr
    assert "model_provider='openai'" in stderr


def _read_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_openai_config(source_config_path: Path, tmp_path: Path) -> Path:
    payload = yaml.safe_load(source_config_path.read_text(encoding="utf-8"))
    source_root = source_config_path.parent
    payload["input_data"]["dataset_file"] = str((source_root / payload["input_data"]["dataset_file"]).resolve())
    payload["prompt_template_file"] = str((source_root / payload["prompt_template_file"]).resolve())
    payload["analysis_instructions_file"] = str((source_root / payload["analysis_instructions_file"]).resolve())
    payload["model_set"] = "openai_smoke_set"
    payload["model_sets"]["openai_smoke_set"] = [
        {
            "model_provider": "openai",
            "model_name": "gpt-5-nano",
            "method_name": "main_analysis",
        }
    ]

    config_path = tmp_path / "openai_config.yaml"
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return config_path
