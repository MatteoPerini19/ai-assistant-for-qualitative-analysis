from __future__ import annotations

from enums import ParseStatus
from schemas import (
    AnalysisOutputSchema,
    CallExecutionRecord,
    NormalizedInputRow,
    ParsedOutputValidation,
    ProviderResponse,
    validate_raw_output,
)


def parse_provider_output(
    response: ProviderResponse,
    output_schema: AnalysisOutputSchema,
) -> ParsedOutputValidation:
    if response.raw_output_text is None or response.parse_status is ParseStatus.PROVIDER_ERROR:
        return ParsedOutputValidation(parse_status=ParseStatus.PROVIDER_ERROR)
    return validate_raw_output(response.raw_output_text, output_schema)


def build_call_execution_record(
    *,
    run_id: str,
    row: NormalizedInputRow,
    replicate_id: int,
    effective_prompt: str,
    output_schema: AnalysisOutputSchema,
    provider_response: ProviderResponse,
    retain_raw_json_output: bool = True,
) -> CallExecutionRecord:
    validation = parse_provider_output(provider_response, output_schema)

    return CallExecutionRecord(
        run_id=run_id,
        row_id=row.row_id,
        participant_id=row.participant_id,
        task_id=row.task_id,
        model_provider=provider_response.metadata.model_provider,
        model_name=provider_response.metadata.model_name,
        method_name=provider_response.metadata.method_name,
        requested_temperature=provider_response.metadata.requested_temperature,
        effective_temperature=provider_response.metadata.effective_temperature,
        prompt_template_file=provider_response.metadata.prompt_template_file,
        prompt_id=provider_response.metadata.prompt_id,
        prompt_version=provider_response.metadata.prompt_version,
        schema_name=provider_response.metadata.schema_name,
        schema_version=provider_response.metadata.schema_version,
        replicate_id=replicate_id,
        effective_prompt=effective_prompt,
        task_type=provider_response.metadata.task_type,
        thinking_budget=provider_response.metadata.thinking_budget,
        seed=provider_response.metadata.seed,
        server_side_version=provider_response.metadata.server_side_version,
        raw_json_output=provider_response.raw_output_text if retain_raw_json_output else None,
        parsed_output=validation.parsed_output,
        parse_status=validation.parse_status,
        validation_error=validation.validation_error,
        error_message=provider_response.error_message,
    )
