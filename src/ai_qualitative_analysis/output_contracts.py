from __future__ import annotations

from typing import Any

from enums import ScoreType
from schemas import (
    AnalysisOutputContract,
    AnalysisOutputContractItem,
    AnalysisOutputSchema,
)


def build_analysis_output_contract(
    output_schema: AnalysisOutputSchema,
    *,
    include_json_schema: bool = True,
) -> AnalysisOutputContract:
    contract_items = tuple(
        AnalysisOutputContractItem(
            item_id=item.item_id,
            score_key=item.score_key,
            justification_key=item.justification_key,
            score_type=item.score_type,
            score_range=item.score_range,
        )
        for item in output_schema.items
    )

    score_keys = tuple(item.score_key for item in contract_items)
    justification_keys = tuple(item.justification_key for item in contract_items)
    required_keys = tuple(
        key
        for item in contract_items
        for key in (item.score_key, item.justification_key)
    )

    return AnalysisOutputContract(
        schema_name=output_schema.schema_name,
        schema_version=output_schema.schema_version,
        items=contract_items,
        score_keys=score_keys,
        justification_keys=justification_keys,
        required_keys=required_keys,
        json_schema=build_output_json_schema(output_schema) if include_json_schema else None,
    )


def build_output_json_schema(output_schema: AnalysisOutputSchema) -> dict[str, Any]:
    properties: dict[str, dict[str, Any]] = {}
    required_keys: list[str] = []

    for item in output_schema.items:
        if item.score_type is not ScoreType.INTEGER:
            raise ValueError(
                "Only score_type='integer' is supported in the current implementation scope; "
                "categorical item scoring is deferred."
            )

        properties[item.score_key] = {
            "type": "integer",
            "minimum": item.min_score,
            "maximum": item.max_score,
            "description": f"Numeric score for {item.item_id}",
        }
        properties[item.justification_key] = {
            "type": "string",
            "minLength": 1,
            "description": f"Justification text for {item.item_id}",
        }
        required_keys.extend((item.score_key, item.justification_key))

    return {
        "title": f"{output_schema.schema_name}_{output_schema.schema_version}_output",
        "type": "object",
        "properties": properties,
        "required": required_keys,
        "additionalProperties": output_schema.allow_additional_keys,
    }
