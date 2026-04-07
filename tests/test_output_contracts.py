from __future__ import annotations

from schemas import AnalysisOutputSchema, AnalysisSchemaItem

from ai_qualitative_analysis.output_contracts import (
    build_analysis_output_contract,
    build_output_json_schema,
)


def test_output_contract_generation_for_one_item_schema() -> None:
    output_schema = AnalysisOutputSchema(
        schema_name="single_item_analysis",
        schema_version="1.0",
        items=(
            AnalysisSchemaItem(
                item_id="clarity",
                score_key="clarity_score",
                justification_key="clarity_justification",
                min_score=1,
                max_score=5,
            ),
        ),
    )

    contract = build_analysis_output_contract(output_schema)

    assert contract.score_keys == ("clarity_score",)
    assert contract.justification_keys == ("clarity_justification",)
    assert contract.required_keys == ("clarity_score", "clarity_justification")
    assert contract.items[0].item_id == "clarity"
    assert contract.items[0].score_range.minimum == 1
    assert contract.items[0].score_range.maximum == 5


def test_output_contract_generation_for_multi_item_schema(sample_config) -> None:
    contract = build_analysis_output_contract(sample_config.analysis_schema)

    assert tuple(item.item_id for item in contract.items) == ("item_1", "item_2")
    assert contract.score_keys == ("item_1_score", "item_2_score")
    assert contract.justification_keys == ("item_1_justification", "item_2_justification")
    assert contract.required_keys == (
        "item_1_score",
        "item_1_justification",
        "item_2_score",
        "item_2_justification",
    )


def test_output_contract_json_schema_has_required_keys_and_score_range_metadata(sample_config) -> None:
    json_schema = build_output_json_schema(sample_config.analysis_schema)

    assert json_schema["required"] == [
        "item_1_score",
        "item_1_justification",
        "item_2_score",
        "item_2_justification",
    ]
    assert json_schema["properties"]["item_1_score"]["type"] == "integer"
    assert json_schema["properties"]["item_1_score"]["minimum"] == 1
    assert json_schema["properties"]["item_1_score"]["maximum"] == 7
    assert json_schema["properties"]["item_1_justification"]["type"] == "string"
    assert json_schema["properties"]["item_1_justification"]["minLength"] == 1
