from __future__ import annotations

from pathlib import Path

from schemas import NormalizedInputRow

from ai_qualitative_analysis.prompts import (
    load_analysis_instructions,
    load_prompt_template,
    render_effective_prompt,
)


def test_prompt_rendering_succeeds_with_task_fields_present(
    sample_config,
    sample_normalized_row,
    sample_analysis_instructions_text: str,
) -> None:
    rendered_prompt = render_effective_prompt(sample_config, sample_normalized_row)

    assert "Analysis instructions:" in rendered_prompt
    assert sample_analysis_instructions_text in rendered_prompt
    assert "Task label:" in rendered_prompt
    assert "Personal challenge reflection" in rendered_prompt
    assert "Participants reflected on a recent personal challenge." in rendered_prompt
    assert "Describe a recent personal challenge and explain how you responded to it." in rendered_prompt
    assert sample_normalized_row.participant_text in rendered_prompt


def test_prompt_rendering_succeeds_when_task_info_is_intentionally_omitted(
    sample_config,
) -> None:
    # 🟡 ASSUMPTION: The shared first-pass template keeps optional task sections in simple
    # heading-plus-placeholder blocks, which allows the renderer to drop those sections entirely.
    row_without_task_context = NormalizedInputRow(
        row_id="row_omitted",
        participant_text="I focused on one step at a time and asked for feedback.",
    )
    config_without_task_info = sample_config.model_copy(update={"include_task_info": False})

    rendered_prompt = render_effective_prompt(config_without_task_info, row_without_task_context)

    assert "Task label:" not in rendered_prompt
    assert "Task information:" not in rendered_prompt
    assert "Full task wording:" not in rendered_prompt
    assert row_without_task_context.participant_text in rendered_prompt


def test_prompt_loader_reads_exact_analysis_instructions_file_from_config_fixture(
    sample_analysis_instructions_path: Path,
) -> None:
    loaded_instructions = load_analysis_instructions(sample_analysis_instructions_path)

    assert "Evaluate the response on two configured dimensions." in loaded_instructions
    assert "item_1_score" in loaded_instructions


def test_prompt_rendering_fails_clearly_for_missing_prompt_template_file(
    sample_config,
    tmp_path: Path,
    sample_normalized_row,
) -> None:
    missing_template = tmp_path / "prompts" / "missing_prompt.txt"
    broken_config = sample_config.model_copy(update={"prompt_template_file": missing_template})

    try:
        render_effective_prompt(broken_config, sample_normalized_row)
    except FileNotFoundError as exc:
        assert str(missing_template) in str(exc)
    else:
        raise AssertionError("Expected FileNotFoundError for a missing prompt template file")


def test_prompt_loader_reads_exact_template_file_from_config_fixture(sample_prompt_template_path: Path) -> None:
    loaded_template = load_prompt_template(sample_prompt_template_path)

    assert "{{ analysis_instructions }}" in loaded_template
    assert "{{ participant_text }}" in loaded_template
    assert "Return a JSON object" in loaded_template
