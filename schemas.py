from __future__ import annotations

import json
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, ValidationError, create_model, model_validator
from pydantic.types import StrictFloat, StrictInt, StrictStr
from pydantic_core import PydanticCustomError

from enums import ParseStatus


class ScoreRange(BaseModel):
    minimum: float
    maximum: float

    @model_validator(mode="after")
    def validate_bounds(self) -> "ScoreRange":
        if self.minimum > self.maximum:
            raise ValueError("ScoreRange.minimum must be less than or equal to ScoreRange.maximum")
        return self


class OutputFieldSpec(BaseModel):
    score_key: str
    justification_key: str
    score_range: ScoreRange | None = None


class AnalysisOutputSchema(BaseModel):
    schema_name: str
    schema_version: str
    fields: tuple[OutputFieldSpec, ...]
    allow_additional_keys: bool = True

    @model_validator(mode="after")
    def validate_fields(self) -> "AnalysisOutputSchema":
        if not self.fields:
            raise ValueError("AnalysisOutputSchema.fields must contain at least one output field")
        return self


class ProviderRequest(BaseModel):
    model_provider: str
    model_name: str
    method_name: str
    prompt_template_file: str
    prompt_version: str
    effective_prompt: str
    output_schema: AnalysisOutputSchema
    task_type: str | None = None
    requested_temperature: float | None = None
    effective_temperature: float | None = None
    thinking_budget: str | None = None
    seed: int | None = None


class ProviderResponseMetadata(BaseModel):
    model_provider: str
    model_name: str
    server_side_version: str | None = None
    method_name: str
    prompt_template_file: str
    prompt_version: str
    task_type: str | None = None
    requested_temperature: float | None = None
    effective_temperature: float | None = None
    thinking_budget: str | None = None
    seed: int | None = None


class ProviderResponse(BaseModel):
    raw_output_text: str | None = None
    parsed_output: dict[str, Any] | None = None
    parse_status: ParseStatus
    validation_error: str | None = None
    error_message: str | None = None
    metadata: ProviderResponseMetadata


class ParsedOutputValidation(BaseModel):
    parse_status: ParseStatus
    parsed_output: dict[str, Any] | None = None
    validation_error: str | None = None


class _DynamicOutputPayload(BaseModel):
    model_config = ConfigDict(extra="allow")
    schema_spec: ClassVar[AnalysisOutputSchema]

    @model_validator(mode="after")
    def validate_domain_rules(self) -> "_DynamicOutputPayload":
        for field_spec in self.schema_spec.fields:
            score = getattr(self, field_spec.score_key)
            if field_spec.score_range is not None:
                minimum = field_spec.score_range.minimum
                maximum = field_spec.score_range.maximum
                if score < minimum or score > maximum:
                    raise PydanticCustomError(
                        "out_of_range_score",
                        f"{field_spec.score_key}={score} is outside the allowed range [{minimum}, {maximum}]",
                    )

            justification = getattr(self, field_spec.justification_key)
            # 🟡 ASSUMPTION: Whitespace-only justifications count as empty because the blueprint
            # requires justifications but does not define whether blank whitespace is acceptable.
            if not justification.strip():
                raise PydanticCustomError(
                    "empty_justification",
                    f"{field_spec.justification_key} must not be empty",
                )
        return self


def build_output_payload_model(schema: AnalysisOutputSchema) -> type[BaseModel]:
    extra_mode = "allow" if schema.allow_additional_keys else "forbid"
    field_definitions: dict[str, tuple[Any, Any]] = {}
    for field_spec in schema.fields:
        field_definitions[field_spec.score_key] = (StrictInt | StrictFloat, ...)
        field_definitions[field_spec.justification_key] = (StrictStr, ...)

    model = create_model(
        f"{schema.schema_name}_{schema.schema_version}_Payload",
        __base__=_DynamicOutputPayload,
        __config__=ConfigDict(extra=extra_mode),
        **field_definitions,
    )
    model.schema_spec = schema
    return model


def validate_raw_output(
    raw_output_text: str | None,
    output_schema: AnalysisOutputSchema,
) -> ParsedOutputValidation:
    if raw_output_text is None:
        return ParsedOutputValidation(
            parse_status=ParseStatus.PROVIDER_ERROR,
            validation_error="Provider returned no raw output text",
        )

    try:
        payload = json.loads(raw_output_text)
    except json.JSONDecodeError as exc:
        return ParsedOutputValidation(
            parse_status=ParseStatus.INVALID_JSON,
            validation_error=str(exc),
        )

    if not isinstance(payload, dict):
        return ParsedOutputValidation(
            parse_status=ParseStatus.SCHEMA_MISMATCH,
            validation_error="Expected a JSON object at the top level",
        )

    payload_model = build_output_payload_model(output_schema)
    try:
        validated = payload_model.model_validate(payload)
    except ValidationError as exc:
        return ParsedOutputValidation(
            parse_status=_map_validation_error_to_status(exc),
            validation_error=str(exc),
        )

    return ParsedOutputValidation(
        parse_status=ParseStatus.VALID,
        parsed_output=validated.model_dump(mode="python"),
    )


def _map_validation_error_to_status(exc: ValidationError) -> ParseStatus:
    error_types = {error["type"] for error in exc.errors()}
    if "missing" in error_types:
        return ParseStatus.MISSING_FIELD
    if "out_of_range_score" in error_types:
        return ParseStatus.OUT_OF_RANGE_SCORE
    if "empty_justification" in error_types:
        return ParseStatus.EMPTY_JUSTIFICATION
    return ParseStatus.SCHEMA_MISMATCH
