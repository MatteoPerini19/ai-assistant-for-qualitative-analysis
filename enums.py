from __future__ import annotations

from enum import StrEnum


class RunMode(StrEnum):
    TESTING = "testing"
    MAIN_ANALYSIS = "main_analysis"


class OutputDataType(StrEnum):
    METRIC = "metric"
    ORDINAL = "ordinal"
    CATEGORICAL = "categorical"


class ScoreType(StrEnum):
    INTEGER = "integer"
    CATEGORICAL = "categorical"


class ParseStatus(StrEnum):
    VALID = "valid"
    INVALID_JSON = "invalid_json"
    MISSING_FIELD = "missing_field"
    SCHEMA_MISMATCH = "schema_mismatch"
    OUT_OF_RANGE_SCORE = "out_of_range_score"
    EMPTY_JUSTIFICATION = "empty_justification"
    PROVIDER_ERROR = "provider_error"


class MockScenario(StrEnum):
    VALID = "valid"
    INVALID_JSON = "invalid_json"
    MISSING_FIELD = "missing_field"
    SCHEMA_MISMATCH = "schema_mismatch"
    OUT_OF_RANGE_SCORE = "out_of_range_score"
    EMPTY_JUSTIFICATION = "empty_justification"
    PROVIDER_ERROR = "provider_error"


class DiagnosticScope(StrEnum):
    CALL = "call"
    CALL_GROUP = "call_group"


class DiagnosticSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class DiagnosticFlag(StrEnum):
    INVALID_JSON = "invalid_json"
    SCHEMA_MISMATCH = "schema_mismatch"
    MISSING_FIELD = "missing_field"
    OUT_OF_RANGE_SCORE = "out_of_range_score"
    EMPTY_JUSTIFICATION = "empty_justification"
    TEMPERATURE_DRIFT = "temperature_drift"
    IDENTICAL_OUTPUTS = "identical_outputs"
    HIGH_BETWEEN_REPLICATE_VARIANCE = "high_between_replicate_variance"
