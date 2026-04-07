from __future__ import annotations

import json
from typing import Any

from enums import MockScenario, ParseStatus
from providers.base import AnalysisProvider
from schemas import (
    OutputFieldSpec,
    ProviderRequest,
    ProviderResponse,
    ProviderResponseMetadata,
)


class MockProvider(AnalysisProvider):
    provider_name = "mock"

    def __init__(
        self,
        scenario: MockScenario = MockScenario.VALID,
        *,
        server_side_version: str = "mock-provider-v1",
    ) -> None:
        self.scenario = MockScenario(scenario)
        self.server_side_version = server_side_version

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        metadata = ProviderResponseMetadata(
            model_provider=self.provider_name,
            model_name=request.model_name,
            server_side_version=self.server_side_version,
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

        if self.scenario == MockScenario.PROVIDER_ERROR:
            # Provider-side failures stay in-band so the inclusive-long dataset can
            # preserve one auditable call-record shape for both success and failure.
            return ProviderResponse(
                raw_output_text=None,
                parse_status=ParseStatus.PROVIDER_ERROR,
                error_message="Mock provider forced provider_error scenario",
                metadata=metadata,
            )

        raw_output_text = self._build_raw_output(request)
        return ProviderResponse(
            raw_output_text=raw_output_text,
            metadata=metadata,
        )

    def _build_raw_output(self, request: ProviderRequest) -> str:
        if self.scenario == MockScenario.INVALID_JSON:
            return '{"item_1_score": 5, "item_1_justification": "Malformed"'

        payload = self._build_valid_payload(request.output_schema.fields)
        first_field = request.output_schema.fields[0]

        if self.scenario == MockScenario.MISSING_FIELD:
            payload.pop(first_field.justification_key, None)
        elif self.scenario == MockScenario.SCHEMA_MISMATCH:
            payload[first_field.score_key] = "not-a-number"
        elif self.scenario == MockScenario.OUT_OF_RANGE_SCORE:
            payload[first_field.score_key] = self._out_of_range_value(first_field)
        elif self.scenario == MockScenario.EMPTY_JUSTIFICATION:
            payload[first_field.justification_key] = ""

        return json.dumps(payload, sort_keys=True)

    def _build_valid_payload(self, fields: tuple[OutputFieldSpec, ...]) -> dict[str, Any]:
        payload: dict[str, Any] = {"other_notes": "Deterministic mock output for initial pipeline testing."}
        for index, field_spec in enumerate(fields, start=1):
            payload[field_spec.score_key] = self._valid_score(field_spec, index)
            payload[field_spec.justification_key] = (
                f"Deterministic justification {index} for {field_spec.score_key}."
            )
        return payload

    def _valid_score(self, field_spec: OutputFieldSpec, index: int) -> int | float:
        if field_spec.score_range is None:
            return index

        minimum = field_spec.score_range.minimum
        maximum = field_spec.score_range.maximum
        candidate = minimum + index - 1
        return candidate if candidate <= maximum else minimum

    def _out_of_range_value(self, field_spec: OutputFieldSpec) -> int | float:
        if field_spec.score_range is None:
            return 10_000
        return field_spec.score_range.maximum + 1
