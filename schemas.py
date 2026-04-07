from __future__ import annotations

import json
from pathlib import Path
from typing import Any, ClassVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    create_model,
    field_validator,
    model_validator,
)
from pydantic.types import PositiveInt, StrictFloat, StrictInt, StrictStr
from pydantic_core import PydanticCustomError

from enums import (
    DiagnosticFlag,
    DiagnosticScope,
    DiagnosticSeverity,
    OutputDataType,
    ParseStatus,
    RunMode,
    ScoreType,
)


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
    score_type: ScoreType = ScoreType.INTEGER
    score_range: ScoreRange | None = None


class AnalysisSchemaItem(BaseModel):
    item_id: StrictStr
    score_key: StrictStr
    justification_key: StrictStr
    score_type: ScoreType = ScoreType.INTEGER
    min_score: StrictInt
    max_score: StrictInt

    @field_validator("item_id", "score_key", "justification_key")
    @classmethod
    def validate_non_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Analysis schema item strings must not be blank")
        return value

    @model_validator(mode="after")
    def validate_current_scope(self) -> "AnalysisSchemaItem":
        if self.score_type is not ScoreType.INTEGER:
            raise ValueError(
                "Only score_type='integer' is supported in the current implementation scope; "
                "categorical item scoring is deferred."
            )

        if self.score_key == self.justification_key:
            raise ValueError("score_key and justification_key must be distinct within each schema item")

        ScoreRange(minimum=self.min_score, maximum=self.max_score)
        return self

    @property
    def score_range(self) -> ScoreRange:
        return ScoreRange(minimum=self.min_score, maximum=self.max_score)

    def to_output_field_spec(self) -> OutputFieldSpec:
        return OutputFieldSpec(
            score_key=self.score_key,
            justification_key=self.justification_key,
            score_type=self.score_type,
            score_range=self.score_range,
        )


class AnalysisOutputSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_name: str
    schema_version: str
    items: tuple[AnalysisSchemaItem, ...]
    allow_additional_keys: bool = True

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "items" in data or "fields" not in data:
            return data

        legacy_items: list[dict[str, Any]] = []
        for index, raw_field in enumerate(data["fields"], start=1):
            field_spec = raw_field
            if not isinstance(field_spec, OutputFieldSpec):
                field_spec = OutputFieldSpec.model_validate(raw_field)

            if field_spec.score_range is None:
                raise ValueError("Legacy AnalysisOutputSchema.fields input requires score_range for each field")

            minimum = field_spec.score_range.minimum
            maximum = field_spec.score_range.maximum
            if int(minimum) != minimum or int(maximum) != maximum:
                raise ValueError(
                    "Legacy AnalysisOutputSchema.fields input must use integer score ranges "
                    "in the current implementation scope"
                )

            legacy_items.append(
                {
                    "item_id": f"item_{index}",
                    "score_key": field_spec.score_key,
                    "justification_key": field_spec.justification_key,
                    "score_type": field_spec.score_type,
                    "min_score": int(minimum),
                    "max_score": int(maximum),
                }
            )

        normalized = dict(data)
        normalized.pop("fields", None)
        normalized["items"] = legacy_items
        return normalized

    @model_validator(mode="after")
    def validate_items(self) -> "AnalysisOutputSchema":
        if not self.items:
            raise ValueError("AnalysisOutputSchema.items must contain at least one schema item")

        duplicate_item_ids = _find_duplicates(item.item_id for item in self.items)
        if duplicate_item_ids:
            raise ValueError(f"Duplicate analysis_schema.items item_id values are not allowed: {duplicate_item_ids}")

        duplicate_score_keys = _find_duplicates(item.score_key for item in self.items)
        if duplicate_score_keys:
            raise ValueError(
                f"Duplicate analysis_schema.items score_key values are not allowed: {duplicate_score_keys}"
            )

        duplicate_justification_keys = _find_duplicates(item.justification_key for item in self.items)
        if duplicate_justification_keys:
            raise ValueError(
                "Duplicate analysis_schema.items justification_key values are not allowed: "
                f"{duplicate_justification_keys}"
            )

        overlapping_keys = sorted(
            {item.score_key for item in self.items}.intersection(
                {item.justification_key for item in self.items}
            )
        )
        if overlapping_keys:
            raise ValueError(
                "score_key values and justification_key values must be globally distinct across "
                f"analysis_schema.items: {overlapping_keys}"
            )
        return self

    @property
    def fields(self) -> tuple[OutputFieldSpec, ...]:
        return tuple(item.to_output_field_spec() for item in self.items)


class AnalysisOutputContractItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: StrictStr
    score_key: StrictStr
    justification_key: StrictStr
    score_type: ScoreType
    score_range: ScoreRange


class AnalysisOutputContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_name: StrictStr
    schema_version: StrictStr
    items: tuple[AnalysisOutputContractItem, ...]
    score_keys: tuple[str, ...]
    justification_keys: tuple[str, ...]
    required_keys: tuple[str, ...]
    json_schema: dict[str, Any] | None = None


class ColumnMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_id: StrictStr | None = None
    participant_id: StrictStr | None = None
    task_id: StrictStr | None = None
    task_label: StrictStr | None = None
    task_info: StrictStr | None = None
    task_full_text: StrictStr | None = None
    participant_text: StrictStr | None = None
    language: StrictStr | None = None
    condition: StrictStr | None = None
    wave: StrictStr | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_deferred_columns(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        deferred_columns = [key for key in ("text_file_name", "audio_file_name") if key in data]
        comparative_columns = sorted(key for key in data if key.endswith(("_1", "_2")))
        unsupported_columns = deferred_columns + comparative_columns
        if unsupported_columns:
            raise ValueError(
                "The current implementation scope only supports direct text input from "
                "`participant_text`; deferred column mappings are not supported: "
                f"{unsupported_columns}"
            )

        return data

    @model_validator(mode="after")
    def validate_unique_source_columns(self) -> "ColumnMapping":
        source_columns = [value for value in self.model_dump(exclude_none=True).values()]
        duplicate_sources = _find_duplicates(source_columns)
        if duplicate_sources:
            raise ValueError(
                "Each input source column may map to at most one canonical column: "
                f"{duplicate_sources}"
            )
        return self


class InputDataConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_file: Path
    column_mapping: ColumnMapping = Field(default_factory=ColumnMapping)

    @field_validator("dataset_file")
    @classmethod
    def validate_dataset_file(cls, value: Path) -> Path:
        if value.suffix.lower() != ".csv":
            raise ValueError("input_data.dataset_file must point to a CSV file in the current scope")
        if not value.exists():
            raise ValueError(f"Configured dataset file does not exist: {value}")
        if not value.is_file():
            raise ValueError(f"Configured dataset path is not a file: {value}")
        return value


class RepeatedCallSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: PositiveInt | None = None
    temperature: float | None = None

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if value < 0 or value > 2:
            raise ValueError("repeated_calls.temperature must be between 0.0 and 2.0")
        return value


class SelectedModelSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_provider: StrictStr
    model_name: StrictStr
    method_name: StrictStr
    task_type: StrictStr | None = None
    thinking_budget: StrictStr | None = None
    seed: StrictInt | None = None

    @field_validator("model_provider", "model_name", "method_name")
    @classmethod
    def validate_required_strings(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Selected model metadata must not be blank")
        return value


class PromptIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt_template_file: StrictStr
    prompt_id: StrictStr
    prompt_version: StrictStr

    @field_validator("prompt_template_file", "prompt_id", "prompt_version")
    @classmethod
    def validate_non_blank_strings(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Prompt identity strings must not be blank")
        return value


class AnalysisSchemaIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_name: StrictStr
    schema_version: StrictStr

    @field_validator("schema_name", "schema_version")
    @classmethod
    def validate_non_blank_strings(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Schema identity strings must not be blank")
        return value


class AnalysisConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_mode: RunMode = RunMode.TESTING
    comparative_analysis: bool = False
    include_task_info: bool = True
    input_data: InputDataConfig
    prompt_template_file: Path
    prompt_id: StrictStr
    prompt_version: StrictStr
    analysis_instructions_file: Path | None = None
    model_set: StrictStr | None = None
    model_sets: dict[str, tuple[SelectedModelSpec, ...]] = Field(default_factory=dict)
    repeated_calls: RepeatedCallSettings = Field(default_factory=RepeatedCallSettings)
    merge_output: bool = False
    retain_raw_json_output: bool = True
    output_data_type: OutputDataType = OutputDataType.METRIC
    analysis_schema: AnalysisOutputSchema

    @field_validator("prompt_template_file")
    @classmethod
    def validate_prompt_template_file(cls, value: Path) -> Path:
        if not value.exists():
            raise ValueError(f"Configured prompt template file does not exist: {value}")
        if not value.is_file():
            raise ValueError(f"Configured prompt template path is not a file: {value}")
        return value

    @field_validator("analysis_instructions_file")
    @classmethod
    def validate_analysis_instructions_file(cls, value: Path | None) -> Path | None:
        if value is None:
            return value
        if not value.exists():
            raise ValueError(f"Configured analysis instructions file does not exist: {value}")
        if not value.is_file():
            raise ValueError(f"Configured analysis instructions path is not a file: {value}")
        return value

    @field_validator("prompt_id", "prompt_version", "model_set")
    @classmethod
    def validate_optional_identity_strings(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.strip():
            raise ValueError("Prompt and model-set identity strings must not be blank")
        return value

    @model_validator(mode="after")
    def validate_current_scope(self) -> "AnalysisConfig":
        if self.output_data_type is OutputDataType.CATEGORICAL:
            raise ValueError(
                "output_data_type='categorical' is not supported in the current implementation scope; "
                "numeric item schemas only."
            )

        if self.repeated_calls.count is None:
            self.repeated_calls.count = 3 if self.run_mode is RunMode.TESTING else 100

        if self.repeated_calls.temperature is None:
            self.repeated_calls.temperature = 0.0

        if not self.model_sets:
            raise ValueError("model_sets must contain at least one named model set")

        for set_name, selected_models in self.model_sets.items():
            if not set_name.strip():
                raise ValueError("model_sets keys must not be blank")
            if not selected_models:
                raise ValueError(f"model_sets.{set_name} must include at least one model specification")

            duplicate_model_identities = _find_duplicates(
                _selected_model_identity(selected_model) for selected_model in selected_models
            )
            if duplicate_model_identities:
                raise ValueError(
                    f"model_sets.{set_name} contains duplicate model identities: {duplicate_model_identities}"
                )

        if self.model_set is None:
            self.model_set = "cheap_set" if self.run_mode is RunMode.TESTING else "frontier_main_analysis_set"

        if self.model_set not in self.model_sets:
            raise ValueError(
                f"Configured model_set={self.model_set!r} was not found in model_sets; "
                f"available sets: {sorted(self.model_sets)}"
            )

        return self

    @property
    def selected_models(self) -> tuple[SelectedModelSpec, ...]:
        return self.model_sets[self.model_set]

    @property
    def prompt_identity(self) -> PromptIdentity:
        return PromptIdentity(
            prompt_template_file=self.prompt_template_file.name,
            prompt_id=self.prompt_id,
            prompt_version=self.prompt_version,
        )

    @property
    def schema_identity(self) -> AnalysisSchemaIdentity:
        return AnalysisSchemaIdentity(
            schema_name=self.analysis_schema.schema_name,
            schema_version=self.analysis_schema.schema_version,
        )


class NormalizedInputRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_id: StrictStr
    participant_text: StrictStr
    participant_id: StrictStr | None = None
    task_id: StrictStr | None = None
    task_label: StrictStr | None = None
    task_info: StrictStr | None = None
    task_full_text: StrictStr | None = None
    language: StrictStr | None = None
    condition: StrictStr | None = None
    wave: StrictStr | None = None

    @field_validator("row_id", "participant_text")
    @classmethod
    def validate_required_text_fields(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Required normalized input fields must not be blank")
        return value


class NormalizedInputDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_file: Path
    original_columns: tuple[str, ...]
    normalized_columns: tuple[str, ...]
    rows: tuple[NormalizedInputRow, ...]

    @model_validator(mode="after")
    def validate_rows(self) -> "NormalizedInputDataset":
        if not self.rows:
            raise ValueError("Input dataset must contain at least one row")

        duplicate_row_ids = _find_duplicates(row.row_id for row in self.rows)
        if duplicate_row_ids:
            raise ValueError(f"Normalized input dataset contains duplicate row_id values: {duplicate_row_ids}")

        return self


class ProviderRequest(BaseModel):
    model_provider: str
    model_name: str
    method_name: str
    prompt_template_file: str
    prompt_id: str
    prompt_version: str
    schema_name: str
    schema_version: str
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
    prompt_id: str
    prompt_version: str
    schema_name: str
    schema_version: str
    task_type: str | None = None
    requested_temperature: float | None = None
    effective_temperature: float | None = None
    thinking_budget: str | None = None
    seed: int | None = None


class ProviderResponse(BaseModel):
    """Structured provider result for both successful and failed calls."""

    raw_output_text: str | None = None
    parsed_output: dict[str, Any] | None = None
    parse_status: ParseStatus | None = None
    validation_error: str | None = None
    error_message: str | None = None
    metadata: ProviderResponseMetadata

    @model_validator(mode="after")
    def validate_provider_error_contract(self) -> "ProviderResponse":
        if self.parse_status is ParseStatus.PROVIDER_ERROR:
            if self.parsed_output is not None:
                raise ValueError("provider_error responses must not include parsed_output")
            if self.error_message is None or not self.error_message.strip():
                raise ValueError("provider_error responses must include a non-empty error_message")
        return self


class CallExecutionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: StrictStr
    row_id: StrictStr
    participant_id: StrictStr | None = None
    task_id: StrictStr | None = None
    model_provider: StrictStr
    model_name: StrictStr
    method_name: StrictStr
    requested_temperature: float | None = None
    effective_temperature: float | None = None
    prompt_template_file: StrictStr
    prompt_id: StrictStr
    prompt_version: StrictStr
    schema_name: StrictStr
    schema_version: StrictStr
    replicate_id: PositiveInt
    effective_prompt: StrictStr
    task_type: StrictStr | None = None
    thinking_budget: StrictStr | None = None
    seed: StrictInt | None = None
    server_side_version: StrictStr | None = None
    raw_json_output: str | None = None
    parsed_output: dict[str, Any] | None = None
    parse_status: ParseStatus
    validation_error: StrictStr | None = None
    error_message: StrictStr | None = None

    @field_validator(
        "run_id",
        "row_id",
        "model_provider",
        "model_name",
        "method_name",
        "prompt_template_file",
        "prompt_id",
        "prompt_version",
        "schema_name",
        "schema_version",
        "effective_prompt",
    )
    @classmethod
    def validate_non_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Call execution metadata strings must not be blank")
        return value

    @model_validator(mode="after")
    def validate_parse_payload_state(self) -> "CallExecutionRecord":
        if self.parse_status is ParseStatus.VALID and self.parsed_output is None:
            raise ValueError("Valid call execution records must include parsed_output")
        return self

    @property
    def call_group_key(self) -> tuple[str, str, str, str, str, str, str, str, str]:
        return (
            self.row_id,
            self.model_provider,
            self.model_name,
            self.method_name,
            self.prompt_template_file,
            self.prompt_id,
            self.prompt_version,
            self.schema_name,
            self.schema_version,
        )


class RepeatedCallExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    records: tuple[CallExecutionRecord, ...]

    @model_validator(mode="after")
    def validate_execution_invariants(self) -> "RepeatedCallExecutionResult":
        run_ids = [record.run_id for record in self.records]
        duplicate_run_ids = _find_duplicates(run_ids)
        if duplicate_run_ids:
            raise ValueError(f"Repeated-call execution produced duplicate run_id values: {duplicate_run_ids}")

        group_state: dict[tuple[str, str, str, str, str, str, str, str, str], tuple[Any, ...]] = {}
        group_replicates: dict[tuple[str, str, str, str, str, str, str, str, str], set[int]] = {}
        for record in self.records:
            current_state = (
                record.requested_temperature,
                record.effective_temperature,
                record.effective_prompt,
            )
            previous_state = group_state.get(record.call_group_key)
            if previous_state is None:
                group_state[record.call_group_key] = current_state
            elif previous_state != current_state:
                raise ValueError(
                    "Call-group invariants were violated: requested/effective temperature and "
                    "effective_prompt must stay fixed within each row_id × provider × model × "
                    "method × prompt-template × prompt-id × prompt-version × schema-name × "
                    "schema-version group"
                )

            replicate_ids = group_replicates.setdefault(record.call_group_key, set())
            if record.replicate_id in replicate_ids:
                raise ValueError(
                    "Call-group invariants were violated: replicate_id values must be unique "
                    f"within each call group, got duplicate {record.replicate_id}"
                )
            replicate_ids.add(record.replicate_id)

        return self


class DiagnosticRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diagnostic_id: StrictStr
    diagnostic_scope: DiagnosticScope
    severity: DiagnosticSeverity
    flag_code: DiagnosticFlag
    row_id: StrictStr
    run_id: StrictStr | None = None
    model_provider: StrictStr
    model_name: StrictStr
    method_name: StrictStr
    prompt_template_file: StrictStr
    prompt_id: StrictStr
    prompt_version: StrictStr
    schema_name: StrictStr
    schema_version: StrictStr
    replicate_id: PositiveInt | None = None
    item_id: StrictStr | None = None
    score_key: StrictStr | None = None
    observed_value: StrictStr | None = None
    threshold_value: StrictStr | None = None
    parse_status: ParseStatus | None = None
    message: StrictStr

    @field_validator(
        "diagnostic_id",
        "row_id",
        "model_provider",
        "model_name",
        "method_name",
        "prompt_template_file",
        "prompt_id",
        "prompt_version",
        "schema_name",
        "schema_version",
        "message",
    )
    @classmethod
    def validate_required_diagnostic_strings(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Diagnostic record strings must not be blank")
        return value


class DiagnosticsResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    records: tuple[DiagnosticRecord, ...]


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
            if field_spec.score_type is ScoreType.INTEGER:
                if isinstance(score, float) and not score.is_integer():
                    raise PydanticCustomError(
                        "integer_score_required",
                        f"{field_spec.score_key} must be an integer-compatible JSON number",
                    )
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


def _find_duplicates(values: Any) -> list[str]:
    counts: dict[str, int] = {}
    for value in values:
        counts[str(value)] = counts.get(str(value), 0) + 1
    return sorted(value for value, count in counts.items() if count > 1)


def _selected_model_identity(selected_model: SelectedModelSpec) -> str:
    return "::".join(
        [
            selected_model.model_provider,
            selected_model.model_name,
            selected_model.method_name,
            selected_model.task_type or "",
            selected_model.thinking_budget or "",
            "" if selected_model.seed is None else str(selected_model.seed),
        ]
    )
