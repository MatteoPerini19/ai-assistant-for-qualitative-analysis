from __future__ import annotations

from ai_qualitative_analysis.pipeline import build_call_execution_record, parse_provider_output
from ai_qualitative_analysis.prompts import render_effective_prompt
from enums import MockScenario, ParseStatus
from providers.mock import MockProvider
from schemas import ProviderRequest


def test_parse_provider_output_classifies_valid_output(
    sample_config,
    sample_normalized_row,
) -> None:
    response = MockProvider(scenario=MockScenario.VALID).generate(
        _build_request(sample_config, sample_normalized_row)
    )

    validation = parse_provider_output(response, sample_config.analysis_schema)

    assert validation.parse_status is ParseStatus.VALID
    assert validation.parsed_output is not None
    assert validation.validation_error is None


def test_parse_provider_output_rejects_malformed_json(
    sample_config,
    sample_normalized_row,
) -> None:
    response = MockProvider(scenario=MockScenario.INVALID_JSON).generate(
        _build_request(sample_config, sample_normalized_row)
    )

    validation = parse_provider_output(response, sample_config.analysis_schema)

    assert validation.parse_status is ParseStatus.INVALID_JSON
    assert validation.parsed_output is None
    assert validation.validation_error is not None


def test_parse_provider_output_rejects_missing_required_fields(
    sample_config,
    sample_normalized_row,
) -> None:
    response = MockProvider(scenario=MockScenario.MISSING_FIELD).generate(
        _build_request(sample_config, sample_normalized_row)
    )

    validation = parse_provider_output(response, sample_config.analysis_schema)

    assert validation.parse_status is ParseStatus.MISSING_FIELD
    assert validation.validation_error is not None


def test_parse_provider_output_rejects_schema_mismatches(
    sample_config,
    sample_normalized_row,
) -> None:
    response = MockProvider(scenario=MockScenario.SCHEMA_MISMATCH).generate(
        _build_request(sample_config, sample_normalized_row)
    )

    validation = parse_provider_output(response, sample_config.analysis_schema)

    assert validation.parse_status is ParseStatus.SCHEMA_MISMATCH
    assert validation.validation_error is not None


def test_parse_provider_output_rejects_out_of_range_scores(
    sample_config,
    sample_normalized_row,
) -> None:
    response = MockProvider(scenario=MockScenario.OUT_OF_RANGE_SCORE).generate(
        _build_request(sample_config, sample_normalized_row)
    )

    validation = parse_provider_output(response, sample_config.analysis_schema)

    assert validation.parse_status is ParseStatus.OUT_OF_RANGE_SCORE
    assert "outside the allowed range" in (validation.validation_error or "")


def test_parse_provider_output_rejects_empty_justifications(
    sample_config,
    sample_normalized_row,
) -> None:
    response = MockProvider(scenario=MockScenario.EMPTY_JUSTIFICATION).generate(
        _build_request(sample_config, sample_normalized_row)
    )

    validation = parse_provider_output(response, sample_config.analysis_schema)

    assert validation.parse_status is ParseStatus.EMPTY_JUSTIFICATION
    assert "must not be empty" in (validation.validation_error or "")


def test_build_call_execution_record_preserves_raw_json_output_by_default(
    sample_config,
    sample_normalized_row,
) -> None:
    effective_prompt = render_effective_prompt(sample_config, sample_normalized_row)
    response = MockProvider(scenario=MockScenario.VALID).generate(
        _build_request(sample_config, sample_normalized_row)
    )

    record = build_call_execution_record(
        run_id="run_000001",
        row=sample_normalized_row,
        replicate_id=1,
        effective_prompt=effective_prompt,
        output_schema=sample_config.analysis_schema,
        provider_response=response,
        retain_raw_json_output=True,
    )

    assert record.parse_status is ParseStatus.VALID
    assert record.raw_json_output == response.raw_output_text
    assert record.validation_error is None
    assert record.parsed_output is not None
    assert record.prompt_id == sample_config.prompt_id
    assert record.prompt_version == sample_config.prompt_version
    assert record.schema_name == sample_config.analysis_schema.schema_name
    assert record.schema_version == sample_config.analysis_schema.schema_version


def test_build_call_execution_record_can_drop_raw_json_output_when_disabled(
    sample_config,
    sample_normalized_row,
) -> None:
    effective_prompt = render_effective_prompt(sample_config, sample_normalized_row)
    response = MockProvider(scenario=MockScenario.VALID).generate(
        _build_request(sample_config, sample_normalized_row)
    )

    record = build_call_execution_record(
        run_id="run_000001",
        row=sample_normalized_row,
        replicate_id=1,
        effective_prompt=effective_prompt,
        output_schema=sample_config.analysis_schema,
        provider_response=response,
        retain_raw_json_output=False,
    )

    assert record.raw_json_output is None


def _build_request(sample_config, sample_normalized_row) -> ProviderRequest:
    return ProviderRequest(
        model_provider="mock",
        model_name="mock-model",
        method_name="main_analysis",
        prompt_template_file=sample_config.prompt_template_file.name,
        prompt_id=sample_config.prompt_id,
        prompt_version=sample_config.prompt_version,
        schema_name=sample_config.analysis_schema.schema_name,
        schema_version=sample_config.analysis_schema.schema_version,
        effective_prompt=render_effective_prompt(sample_config, sample_normalized_row),
        output_schema=sample_config.analysis_schema,
        requested_temperature=sample_config.repeated_calls.temperature,
        effective_temperature=sample_config.repeated_calls.temperature,
        seed=123,
    )
