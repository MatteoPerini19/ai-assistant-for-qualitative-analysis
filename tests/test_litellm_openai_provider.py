from __future__ import annotations

from types import SimpleNamespace

from ai_qualitative_analysis.pipeline import parse_provider_output
from enums import ParseStatus
from providers.litellm_openai import LiteLLMOpenAIProvider
from schemas import AnalysisOutputSchema, OutputFieldSpec, ProviderRequest, ScoreRange


def build_request(*, model_name: str = "gpt-5-nano", thinking_budget: str | None = "none") -> ProviderRequest:
    return ProviderRequest(
        model_provider="openai",
        model_name=model_name,
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
        thinking_budget=thinking_budget,
        seed=123,
    )


def test_litellm_openai_provider_maps_request_to_completion_and_returns_metadata() -> None:
    captured_kwargs: dict[str, object] = {}

    def fake_completion(**kwargs):
        captured_kwargs.update(kwargs)
        return SimpleNamespace(
            model="gpt-5-nano-2026-02-01",
            system_fingerprint="fp_test_123",
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=(
                            '{"item_1_score": 5, "item_1_justification": "Clear evidence.", '
                            '"item_2_score": 4, "item_2_justification": "Consistent tone."}'
                        )
                    )
                )
            ],
        )

    provider = LiteLLMOpenAIProvider(
        completion_callable=fake_completion,
        supports_response_schema_callable=lambda **_: True,
        supported_openai_params_callable=lambda **_: ("response_format", "seed", "temperature", "reasoning_effort"),
    )

    response = provider.generate(build_request())

    assert captured_kwargs["model"] == "openai/gpt-5-nano"
    assert captured_kwargs["messages"] == [
        {"role": "user", "content": "Score this writing sample and return JSON."}
    ]
    assert captured_kwargs["temperature"] == 0.0
    assert captured_kwargs["seed"] == 123
    assert captured_kwargs["reasoning_effort"] == "none"
    response_format = captured_kwargs["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "main_analysis_v1"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"]["required"] == [
        "item_1_score",
        "item_1_justification",
        "item_2_score",
        "item_2_justification",
    ]
    assert response_format["json_schema"]["schema"]["additionalProperties"] is False
    assert response_format["json_schema"]["schema"]["properties"]["item_1_score"]["minimum"] == 1
    assert response_format["json_schema"]["schema"]["properties"]["item_2_score"]["maximum"] == 7
    assert response.raw_output_text is not None
    assert response.metadata.model_provider == "openai"
    assert response.metadata.model_name == "gpt-5-nano-2026-02-01"
    assert response.metadata.server_side_version == "fp_test_123"
    assert parse_provider_output(response, build_request().output_schema).parse_status is ParseStatus.VALID


def test_litellm_openai_provider_returns_provider_error_when_schema_support_is_unavailable() -> None:
    called = False

    def fake_completion(**kwargs):
        nonlocal called
        called = True
        return kwargs

    provider = LiteLLMOpenAIProvider(
        completion_callable=fake_completion,
        supports_response_schema_callable=lambda **_: False,
        supported_openai_params_callable=lambda **_: (),
    )

    response = provider.generate(build_request())

    assert called is False
    assert response.parse_status is ParseStatus.PROVIDER_ERROR
    assert "response_format=json_schema support" in (response.error_message or "")


def test_litellm_openai_provider_returns_provider_error_on_completion_exception() -> None:
    provider = LiteLLMOpenAIProvider(
        completion_callable=lambda **_: (_ for _ in ()).throw(RuntimeError("boom")),
        supports_response_schema_callable=lambda **_: True,
        supported_openai_params_callable=lambda **_: (),
    )

    response = provider.generate(build_request())

    assert response.raw_output_text is None
    assert response.parse_status is ParseStatus.PROVIDER_ERROR
    assert response.error_message == "RuntimeError: boom"
    assert response.metadata.model_name == "gpt-5-nano"
    assert response.metadata.server_side_version is None


def test_litellm_openai_provider_leaves_unavailable_metadata_unset() -> None:
    provider = LiteLLMOpenAIProvider(
        completion_callable=lambda **_: {
            "choices": [
                {
                    "message": {
                        "content": {
                            "item_1_score": 4,
                            "item_1_justification": "Adequate evidence.",
                            "item_2_score": 3,
                            "item_2_justification": "Some support.",
                        }
                    }
                }
            ]
        },
        supports_response_schema_callable=lambda **_: True,
        supported_openai_params_callable=lambda **_: ("response_format", "seed", "temperature"),
    )

    response = provider.generate(build_request(model_name="openai/gpt-5-nano", thinking_budget="none"))

    assert response.metadata.model_name == "openai/gpt-5-nano"
    assert response.metadata.server_side_version is None
    assert response.raw_output_text == (
        '{"item_1_justification": "Adequate evidence.", "item_1_score": 4, '
        '"item_2_justification": "Some support.", "item_2_score": 3}'
    )
    assert parse_provider_output(response, build_request().output_schema).parse_status is ParseStatus.VALID


def test_litellm_openai_provider_does_not_send_reasoning_effort_when_model_does_not_report_support() -> None:
    captured_kwargs: dict[str, object] = {}

    def fake_completion(**kwargs):
        captured_kwargs.update(kwargs)
        return {
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"item_1_score": 5, "item_1_justification": "Clear evidence.", '
                            '"item_2_score": 4, "item_2_justification": "Consistent tone."}'
                        )
                    }
                }
            ],
        }

    provider = LiteLLMOpenAIProvider(
        completion_callable=fake_completion,
        supports_response_schema_callable=lambda **_: True,
        supported_openai_params_callable=lambda **_: ("response_format", "seed", "temperature"),
    )

    response = provider.generate(build_request(model_name="gpt-4o-mini", thinking_budget="none"))

    assert "reasoning_effort" not in captured_kwargs
    assert response.parse_status is None
    assert parse_provider_output(response, build_request(model_name="gpt-4o-mini").output_schema).parse_status is ParseStatus.VALID
