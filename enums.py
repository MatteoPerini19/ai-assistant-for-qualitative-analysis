from __future__ import annotations

from enum import StrEnum


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
