from __future__ import annotations

from collections.abc import Mapping, Sequence

from providers.base import AnalysisProvider
from schemas import (
    AnalysisConfig,
    CallExecutionRecord,
    NormalizedInputDataset,
    ProviderRequest,
    RepeatedCallExecutionResult,
    SelectedModelSpec,
)

from ai_qualitative_analysis.pipeline.parsing import build_call_execution_record
from ai_qualitative_analysis.prompts import render_effective_prompt


def execute_repeated_calls(
    config: AnalysisConfig,
    dataset: NormalizedInputDataset,
    providers_by_name: Mapping[str, AnalysisProvider],
    selected_models: Sequence[SelectedModelSpec] | None = None,
) -> RepeatedCallExecutionResult:
    records: list[CallExecutionRecord] = []
    prompt_identity = config.prompt_identity
    schema_identity = config.schema_identity
    configured_models = tuple(selected_models or config.selected_models)
    run_counter = 1

    for row in dataset.rows:
        effective_prompt = render_effective_prompt(config, row)
        for selected_model in configured_models:
            provider = _get_provider(selected_model.model_provider, providers_by_name)
            for replicate_id in range(1, config.repeated_calls.count + 1):
                request = ProviderRequest(
                    model_provider=selected_model.model_provider,
                    model_name=selected_model.model_name,
                    method_name=selected_model.method_name,
                    prompt_template_file=prompt_identity.prompt_template_file,
                    prompt_id=prompt_identity.prompt_id,
                    prompt_version=prompt_identity.prompt_version,
                    schema_name=schema_identity.schema_name,
                    schema_version=schema_identity.schema_version,
                    effective_prompt=effective_prompt,
                    output_schema=config.analysis_schema,
                    task_type=selected_model.task_type,
                    requested_temperature=config.repeated_calls.temperature,
                    effective_temperature=config.repeated_calls.temperature,
                    thinking_budget=selected_model.thinking_budget,
                    seed=selected_model.seed,
                )
                response = provider.generate(request)
                records.append(
                    build_call_execution_record(
                        run_id=_build_run_id(run_counter),
                        row=row,
                        replicate_id=replicate_id,
                        effective_prompt=effective_prompt,
                        output_schema=config.analysis_schema,
                        provider_response=response,
                        retain_raw_json_output=config.retain_raw_json_output,
                    )
                )
                run_counter += 1

    return RepeatedCallExecutionResult(records=tuple(records))


def _get_provider(
    provider_name: str,
    providers_by_name: Mapping[str, AnalysisProvider],
) -> AnalysisProvider:
    provider = providers_by_name.get(provider_name)
    if provider is None:
        raise ValueError(f"No provider instance was supplied for model_provider={provider_name!r}")
    return provider


def _build_run_id(run_counter: int) -> str:
    return f"run_{run_counter:06d}"
