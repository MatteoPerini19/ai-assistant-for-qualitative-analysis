from __future__ import annotations

import socket

import pytest

from ai_qualitative_analysis.pipeline import parse_provider_output
from enums import MockScenario, ParseStatus
from providers.mock import MockProvider
from schemas import AnalysisOutputSchema, OutputFieldSpec, ProviderRequest, ScoreRange, validate_raw_output


def build_request() -> ProviderRequest:
    # Use two score items so the mock covers the flattened multi-item JSON contract from the blueprint.
    return ProviderRequest(
        model_provider="mock",
        model_name="mock-model",
        method_name="main_analysis",
        prompt_template_file="prompt_template_main_analysis.txt",
        prompt_id="main_analysis",
        prompt_version="v1",
        schema_name="main_analysis",
        schema_version="v1",
        effective_prompt="Score this writing sample and return JSON.",
        output_schema=AnalysisOutputSchema(
            schema_name="main_analysis",
            schema_version="v1",
            fields=(
                OutputFieldSpec(
                    score_key="item_1_score",
                    justification_key="item_1_justification",
                    score_range=ScoreRange(minimum=1, maximum=7),
                ),
                OutputFieldSpec(
                    score_key="item_2_score",
                    justification_key="item_2_justification",
                    score_range=ScoreRange(minimum=1, maximum=7),
                ),
            ),
        ),
        requested_temperature=0.0,
        effective_temperature=0.0,
        seed=123,
    )


@pytest.mark.parametrize(
    ("scenario", "expected_status"),
    [
        (MockScenario.VALID, ParseStatus.VALID),
        (MockScenario.INVALID_JSON, ParseStatus.INVALID_JSON),
        (MockScenario.MISSING_FIELD, ParseStatus.MISSING_FIELD),
        (MockScenario.SCHEMA_MISMATCH, ParseStatus.SCHEMA_MISMATCH),
        (MockScenario.OUT_OF_RANGE_SCORE, ParseStatus.OUT_OF_RANGE_SCORE),
        (MockScenario.EMPTY_JUSTIFICATION, ParseStatus.EMPTY_JUSTIFICATION),
        (MockScenario.PROVIDER_ERROR, ParseStatus.PROVIDER_ERROR),
    ],
)
def test_mock_provider_supports_all_required_scenarios(
    scenario: MockScenario,
    expected_status: ParseStatus,
) -> None:
    provider = MockProvider(scenario=scenario)
    response = provider.generate(build_request())

    assert response.metadata.model_provider == "mock"
    assert response.metadata.model_name == "mock-model"
    assert response.metadata.server_side_version == "mock-provider-v1"

    if scenario == MockScenario.PROVIDER_ERROR:
        # Provider failures stay in-band so later pipeline stages can persist failed
        # calls in the inclusive-long file with the same row shape as successful calls.
        assert response.raw_output_text is None
        assert response.parsed_output is None
        assert response.parse_status is ParseStatus.PROVIDER_ERROR
        assert response.error_message == "Mock provider forced provider_error scenario"
        return

    assert response.raw_output_text is not None
    assert response.parse_status is None
    validation = parse_provider_output(response, build_request().output_schema)
    assert validation.parse_status == expected_status


def test_mock_provider_valid_scenario_is_deterministic() -> None:
    provider = MockProvider(scenario=MockScenario.VALID)

    first = provider.generate(build_request())
    second = provider.generate(build_request())

    assert first.model_dump() == second.model_dump()


def test_mock_provider_valid_scenario_avoids_network_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("MockProvider should not attempt any network access")

    monkeypatch.setattr(socket, "create_connection", fail_if_called)

    response = MockProvider(scenario=MockScenario.VALID).generate(build_request())

    assert response.raw_output_text is not None
    assert parse_provider_output(response, build_request().output_schema).parse_status is ParseStatus.VALID


def test_validate_raw_output_rejects_non_object_json() -> None:
    validation = validate_raw_output('["not", "an", "object"]', build_request().output_schema)

    assert validation.parse_status == ParseStatus.SCHEMA_MISMATCH
    assert validation.validation_error == "Expected a JSON object at the top level"
