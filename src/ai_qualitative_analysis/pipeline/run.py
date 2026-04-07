from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from ai_qualitative_analysis.config import load_config
from ai_qualitative_analysis.io import load_normalized_input_dataset
from ai_qualitative_analysis.pipeline.aggregation import write_summarized_wide_output
from ai_qualitative_analysis.pipeline.diagnostics import write_sanity_checks_output
from ai_qualitative_analysis.pipeline.execute import execute_repeated_calls
from ai_qualitative_analysis.pipeline.output_writers import write_inclusive_long_output
from enums import MockScenario
from providers import (
    AnalysisProvider,
    LiteLLMOpenAIProvider,
    LiteLLMOpenAIProviderSettings,
    MockProvider,
)
from schemas import AnalysisConfig, NormalizedInputDataset, RepeatedCallExecutionResult


@dataclass(frozen=True)
class PipelineRunArtifacts:
    config: AnalysisConfig
    dataset: NormalizedInputDataset
    execution_result: RepeatedCallExecutionResult
    output_dir: Path
    inclusive_long_csv: Path
    summarized_wide_csv: Path
    diagnostics_csv: Path


def run_pipeline_from_config_file(
    config_file: str | Path,
    *,
    output_dir: str | Path | None = None,
    mock_scenario: MockScenario = MockScenario.VALID,
) -> PipelineRunArtifacts:
    config_path = Path(config_file).expanduser().resolve()
    config = load_config(config_path)
    resolved_output_dir = _resolve_output_dir(config_path, output_dir)
    return run_pipeline(
        config,
        output_dir=resolved_output_dir,
        mock_scenario=mock_scenario,
    )


def run_pipeline(
    config: AnalysisConfig,
    *,
    output_dir: str | Path,
    mock_scenario: MockScenario = MockScenario.VALID,
) -> PipelineRunArtifacts:
    dataset = load_normalized_input_dataset(config)
    execution_result = execute_repeated_calls(
        config,
        dataset,
        providers_by_name=_build_providers_by_name(config, mock_scenario),
    )

    resolved_output_dir = Path(output_dir).expanduser().resolve()
    inclusive_long_csv = write_inclusive_long_output(config, execution_result, resolved_output_dir)
    summarized_wide_csv = write_summarized_wide_output(config, execution_result, resolved_output_dir)
    diagnostics_csv = write_sanity_checks_output(config, execution_result, resolved_output_dir)
    return PipelineRunArtifacts(
        config=config,
        dataset=dataset,
        execution_result=execution_result,
        output_dir=resolved_output_dir,
        inclusive_long_csv=inclusive_long_csv,
        summarized_wide_csv=summarized_wide_csv,
        diagnostics_csv=diagnostics_csv,
    )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the first-pass qualitative-analysis pipeline from config.yaml.",
    )
    parser.add_argument(
        "config_file",
        help="Path to the YAML config file that defines the first-pass analysis.",
    )
    parser.add_argument(
        "--output-dir",
        help="Optional output directory. Defaults to an outputs/ folder next to the config file.",
    )
    parser.add_argument(
        "--mock-scenario",
        choices=[scenario.value for scenario in MockScenario],
        default=MockScenario.VALID.value,
        help="Deterministic mock-provider scenario to run when the selected model_set includes `mock`.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    try:
        artifacts = run_pipeline_from_config_file(
            args.config_file,
            output_dir=args.output_dir,
            mock_scenario=MockScenario(args.mock_scenario),
        )
    except (FileNotFoundError, NotImplementedError, ValueError) as exc:
        parser.exit(status=1, message=f"Error: {exc}\n")
    print(f"Output directory: {artifacts.output_dir}")
    print(f"Inclusive long CSV: {artifacts.inclusive_long_csv}")
    print(f"Summarized wide CSV: {artifacts.summarized_wide_csv}")
    print(f"Diagnostics CSV: {artifacts.diagnostics_csv}")
    return 0


def _build_providers_by_name(
    config: AnalysisConfig,
    mock_scenario: MockScenario,
) -> dict[str, AnalysisProvider]:
    providers_by_name: dict[str, AnalysisProvider] = {}
    for provider_name in {selected_model.model_provider for selected_model in config.selected_models}:
        if provider_name == "mock":
            providers_by_name[provider_name] = MockProvider(scenario=mock_scenario)
            continue

        if provider_name == "openai":
            providers_by_name[provider_name] = _build_openai_provider_from_environment(config)
            continue

        raise NotImplementedError(
            f"model_provider={provider_name!r} is not wired into the first-pass CLI yet"
        )

    return providers_by_name


def _build_openai_provider_from_environment(config: AnalysisConfig) -> AnalysisProvider:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key is None or not api_key.strip():
        raise ValueError(
            "Selected model_set requires model_provider='openai', but OPENAI_API_KEY is not set. "
            f"Set OPENAI_API_KEY before running, or switch model_set={config.model_set!r} to a mock-backed set."
        )

    return LiteLLMOpenAIProvider(
        settings=LiteLLMOpenAIProviderSettings(
            api_key=api_key,
        )
    )


def _resolve_output_dir(config_path: Path, output_dir: str | Path | None) -> Path:
    if output_dir is not None:
        return Path(output_dir).expanduser().resolve()

    # 🟡 ASSUMPTION: The entry point writes to outputs/ next to the selected config file by
    # default, because the blueprint shows a top-level outputs/ directory but does not define
    # whether path resolution should be based on cwd or config location.
    return (config_path.parent / "outputs").resolve()
