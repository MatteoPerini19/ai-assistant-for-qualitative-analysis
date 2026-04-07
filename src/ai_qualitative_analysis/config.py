from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from schemas import AnalysisConfig


def load_config(config_file: str | Path) -> AnalysisConfig:
    config_path = Path(config_file).expanduser()
    if not config_path.exists():
        raise FileNotFoundError(f"Config file does not exist: {config_path}")
    if not config_path.is_file():
        raise FileNotFoundError(f"Config path is not a file: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)

    if payload is None:
        raise ValueError(f"Config file is empty: {config_path}")
    if not isinstance(payload, dict):
        raise ValueError("config.yaml must contain a top-level mapping")

    resolved_payload = _resolve_relative_paths(payload, config_path.parent.resolve())
    return AnalysisConfig.model_validate(resolved_payload)


def _resolve_relative_paths(payload: dict[str, Any], config_dir: Path) -> dict[str, Any]:
    resolved_payload = dict(payload)

    input_data = resolved_payload.get("input_data")
    if isinstance(input_data, dict) and "dataset_file" in input_data:
        resolved_input_data = dict(input_data)
        resolved_input_data["dataset_file"] = _resolve_path_value(input_data["dataset_file"], config_dir)
        resolved_payload["input_data"] = resolved_input_data

    if "prompt_template_file" in resolved_payload:
        resolved_payload["prompt_template_file"] = _resolve_path_value(
            resolved_payload["prompt_template_file"],
            config_dir,
        )

    if "analysis_instructions_file" in resolved_payload:
        resolved_payload["analysis_instructions_file"] = _resolve_path_value(
            resolved_payload["analysis_instructions_file"],
            config_dir,
        )

    return resolved_payload


def _resolve_path_value(raw_value: Any, config_dir: Path) -> Any:
    if not isinstance(raw_value, (str, Path)):
        return raw_value

    path_value = Path(raw_value).expanduser()
    # 🟡 ASSUMPTION: Relative paths inside config.yaml are resolved relative to the config file's
    # directory, because the blueprint requires configurable paths but does not define a cwd rule.
    if not path_value.is_absolute():
        return (config_dir / path_value).resolve()
    return path_value.resolve()
