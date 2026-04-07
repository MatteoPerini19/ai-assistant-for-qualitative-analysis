from __future__ import annotations

import re
from pathlib import Path

from schemas import AnalysisConfig, NormalizedInputRow

_PLACEHOLDER_RE = re.compile(r"\{\{\s*(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")
_OPTIONAL_SECTION_FIELDS = ("task_label", "task_info", "task_full_text", "analysis_instructions")


def load_prompt_template(template_file: str | Path) -> str:
    template_path = Path(template_file).expanduser()
    if not template_path.exists():
        raise FileNotFoundError(f"Prompt template file does not exist: {template_path}")
    if not template_path.is_file():
        raise FileNotFoundError(f"Prompt template path is not a file: {template_path}")
    return template_path.read_text(encoding="utf-8")


def load_analysis_instructions(instructions_file: str | Path | None) -> str:
    if instructions_file is None:
        return ""

    instructions_path = Path(instructions_file).expanduser()
    if not instructions_path.exists():
        raise FileNotFoundError(f"Analysis instructions file does not exist: {instructions_path}")
    if not instructions_path.is_file():
        raise FileNotFoundError(f"Analysis instructions path is not a file: {instructions_path}")
    return instructions_path.read_text(encoding="utf-8").strip()


def build_prompt_context(
    config: AnalysisConfig,
    row: NormalizedInputRow,
    *,
    analysis_instructions_text: str = "",
) -> dict[str, str]:
    row_payload = row.model_dump(mode="python")
    context = {
        field_name: "" if value is None else str(value)
        for field_name, value in row_payload.items()
    }
    context["analysis_instructions"] = analysis_instructions_text

    if not config.include_task_info:
        for field_name in _OPTIONAL_SECTION_FIELDS:
            if field_name != "analysis_instructions":
                context[field_name] = ""

    return context


def render_prompt_template(template_text: str, context: dict[str, str]) -> str:
    rendered_template = template_text
    for field_name in _OPTIONAL_SECTION_FIELDS:
        if not context.get(field_name, ""):
            rendered_template = _remove_optional_section(rendered_template, field_name)

    def replace_placeholder(match: re.Match[str]) -> str:
        placeholder_name = match.group("name")
        if placeholder_name not in context:
            raise ValueError(f"Prompt template contains unsupported placeholder: {placeholder_name}")
        return context[placeholder_name]

    rendered_prompt = _PLACEHOLDER_RE.sub(replace_placeholder, rendered_template)
    rendered_prompt = re.sub(r"\n{3,}", "\n\n", rendered_prompt)
    return rendered_prompt.strip()


def render_effective_prompt(config: AnalysisConfig, row: NormalizedInputRow) -> str:
    template_text = load_prompt_template(config.prompt_template_file)
    analysis_instructions_text = load_analysis_instructions(config.analysis_instructions_file)
    context = build_prompt_context(
        config,
        row,
        analysis_instructions_text=analysis_instructions_text,
    )
    return render_prompt_template(template_text, context)


def _remove_optional_section(template_text: str, field_name: str) -> str:
    # 🟡 ASSUMPTION: First-pass prompt templates express optional task sections as a heading line
    # immediately followed by the matching placeholder line, so omitted task fields can remove the
    # whole section cleanly without introducing template-specific branching logic.
    section_pattern = re.compile(
        rf"(?m)^[^\n]*\n[ \t]*\{{\{{\s*{re.escape(field_name)}\s*\}}\}}[ \t]*(?:\n[ \t]*){{1,2}}"
    )
    template_without_section = section_pattern.sub("", template_text)
    placeholder_only_pattern = re.compile(
        rf"(?m)^[ \t]*\{{\{{\s*{re.escape(field_name)}\s*\}}\}}[ \t]*\n?"
    )
    return placeholder_only_pattern.sub("", template_without_section)
