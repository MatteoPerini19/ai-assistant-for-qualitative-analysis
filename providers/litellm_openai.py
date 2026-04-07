from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from ai_qualitative_analysis.output_contracts import build_analysis_output_contract
from enums import ParseStatus
from providers.base import AnalysisProvider
from schemas import ProviderRequest, ProviderResponse, ProviderResponseMetadata


@dataclass(frozen=True)
class LiteLLMOpenAIProviderSettings:
    api_key: str | None = None
    base_url: str | None = None
    api_version: str | None = None
    timeout: float | None = None
    extra_headers: Mapping[str, str] | None = None


class LiteLLMOpenAIProvider(AnalysisProvider):
    provider_name = "openai"

    def __init__(
        self,
        *,
        settings: LiteLLMOpenAIProviderSettings | None = None,
        completion_callable: Callable[..., Any] | None = None,
        supports_response_schema_callable: Callable[..., bool] | None = None,
        supported_openai_params_callable: Callable[..., Sequence[str]] | None = None,
    ) -> None:
        self.settings = settings or LiteLLMOpenAIProviderSettings()
        self._completion_callable = completion_callable
        self._supports_response_schema_callable = supports_response_schema_callable
        self._supported_openai_params_callable = supported_openai_params_callable

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        if request.model_provider != self.provider_name:
            raise ValueError(
                f"{self.__class__.__name__} only supports model_provider='openai', "
                f"got {request.model_provider!r}"
            )

        metadata = ProviderResponseMetadata(
            model_provider=self.provider_name,
            model_name=request.model_name,
            method_name=request.method_name,
            prompt_template_file=request.prompt_template_file,
            prompt_id=request.prompt_id,
            prompt_version=request.prompt_version,
            schema_name=request.schema_name,
            schema_version=request.schema_version,
            task_type=request.task_type,
            requested_temperature=request.requested_temperature,
            effective_temperature=request.effective_temperature,
            thinking_budget=request.thinking_budget,
            seed=request.seed,
        )
        model_name = _normalize_openai_model_name(request.model_name)

        if not self._supports_response_schema(request.model_name):
            return ProviderResponse(
                raw_output_text=None,
                parse_status=ParseStatus.PROVIDER_ERROR,
                error_message=(
                    "LiteLLM/OpenAI structured outputs require response_format=json_schema support; "
                    f"model {model_name!r} did not report that capability"
                ),
                metadata=metadata,
            )

        try:
            response = self._completion()(**self._build_completion_kwargs(request, model_name))
        except Exception as exc:
            return ProviderResponse(
                raw_output_text=None,
                parse_status=ParseStatus.PROVIDER_ERROR,
                error_message=f"{type(exc).__name__}: {exc}",
                metadata=metadata,
            )

        raw_output_text = _coerce_raw_output_text(_extract_message_content(response))
        response_model_name = _get_value(response, "model", request.model_name)
        server_side_version = _get_value(response, "system_fingerprint")
        # 🟡 ASSUMPTION: OpenAI's response `system_fingerprint` is stored in the existing
        # `server_side_version` metadata field because the first-pass persisted contract has no
        # separate provider-build field and silently dropping it would lose audit context.
        response_metadata = metadata.model_copy(
            update={
                "model_name": response_model_name,
                "server_side_version": server_side_version,
            }
        )

        if raw_output_text is None:
            return ProviderResponse(
                raw_output_text=None,
                parse_status=ParseStatus.PROVIDER_ERROR,
                error_message="LiteLLM/OpenAI response did not include message.content",
                metadata=response_metadata,
            )

        return ProviderResponse(
            raw_output_text=raw_output_text,
            metadata=response_metadata,
        )

    def _build_completion_kwargs(self, request: ProviderRequest, model_name: str) -> dict[str, Any]:
        completion_kwargs: dict[str, Any] = {
            "model": model_name,
            "messages": [{"role": "user", "content": request.effective_prompt}],
            "response_format": _build_response_format(request),
        }
        if request.effective_temperature is not None:
            completion_kwargs["temperature"] = request.effective_temperature
        if request.seed is not None:
            completion_kwargs["seed"] = request.seed

        supported_params = set(self._supported_openai_params(request.model_name))
        # 🟡 ASSUMPTION: The first real provider adapter uses LiteLLM's chat-completions path and
        # only forwards `thinking_budget` when LiteLLM reports `reasoning_effort` support for the
        # chosen OpenAI model, because the broader blueprint reasoning-budget configuration is
        # deferred and this keeps the first-pass adapter explicit rather than pretending support.
        if request.thinking_budget is not None and "reasoning_effort" in supported_params:
            completion_kwargs["reasoning_effort"] = request.thinking_budget

        if self.settings.api_key is not None:
            completion_kwargs["api_key"] = self.settings.api_key
        if self.settings.base_url is not None:
            completion_kwargs["base_url"] = self.settings.base_url
        if self.settings.api_version is not None:
            completion_kwargs["api_version"] = self.settings.api_version
        if self.settings.timeout is not None:
            completion_kwargs["timeout"] = self.settings.timeout
        if self.settings.extra_headers is not None:
            completion_kwargs["extra_headers"] = dict(self.settings.extra_headers)
        return completion_kwargs

    def _completion(self) -> Callable[..., Any]:
        if self._completion_callable is not None:
            return self._completion_callable

        from litellm import completion

        return completion

    def _supports_response_schema(self, model_name: str) -> bool:
        if self._supports_response_schema_callable is not None:
            return self._supports_response_schema_callable(
                model=_strip_provider_prefix(model_name),
                custom_llm_provider=self.provider_name,
            )

        from litellm import supports_response_schema

        return supports_response_schema(
            model=_strip_provider_prefix(model_name),
            custom_llm_provider=self.provider_name,
        )

    def _supported_openai_params(self, model_name: str) -> Sequence[str]:
        if self._supported_openai_params_callable is not None:
            return self._supported_openai_params_callable(
                model=_strip_provider_prefix(model_name),
                custom_llm_provider=self.provider_name,
            )

        from litellm import get_supported_openai_params

        return get_supported_openai_params(
            model=_strip_provider_prefix(model_name),
            custom_llm_provider=self.provider_name,
        )


def _build_response_format(request: ProviderRequest) -> dict[str, Any]:
    output_contract = build_analysis_output_contract(request.output_schema)
    if output_contract.json_schema is None:
        raise ValueError("The output contract did not include a JSON Schema")

    response_schema = dict(output_contract.json_schema)
    response_schema["additionalProperties"] = False

    return {
        "type": "json_schema",
        "json_schema": {
            "name": _sanitize_schema_name(
                f"{request.output_schema.schema_name}_{request.output_schema.schema_version}"
            ),
            "schema": response_schema,
            "strict": True,
        },
    }


def _normalize_openai_model_name(model_name: str) -> str:
    model_name = model_name.strip()
    if model_name.startswith("openai/"):
        return model_name
    return f"openai/{model_name}"


def _strip_provider_prefix(model_name: str) -> str:
    if model_name.startswith("openai/"):
        return model_name.split("/", 1)[1]
    return model_name


def _sanitize_schema_name(raw_name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", raw_name.strip()).strip("_") or "analysis_output"


def _extract_message_content(response: Any) -> Any:
    choices = _get_value(response, "choices", [])
    if not choices:
        return None

    first_choice = choices[0]
    message = _get_value(first_choice, "message")
    if message is None:
        return None

    return _get_value(message, "content")


def _coerce_raw_output_text(raw_content: Any) -> str | None:
    if raw_content is None:
        return None
    if isinstance(raw_content, str):
        return raw_content
    if isinstance(raw_content, (dict, list)):
        return json.dumps(raw_content, sort_keys=True)
    return str(raw_content)


def _get_value(payload: Any, key: str, default: Any = None) -> Any:
    if isinstance(payload, Mapping):
        return payload.get(key, default)
    return getattr(payload, key, default)
