from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any

def _ensure_src_on_path() -> None:
    src_dir = Path(__file__).resolve().parents[1] / "src"
    src_path = str(src_dir)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


_ensure_src_on_path()

import pytest

from ai_qualitative_analysis.config import load_config
from ai_qualitative_analysis.io import load_normalized_input_dataset
from schemas import AnalysisConfig


@pytest.fixture(scope="session")
def sample_project_dir() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / "first_pass_project"


@pytest.fixture(scope="session")
def sample_config_path(sample_project_dir: Path) -> Path:
    return sample_project_dir / "config.yaml"


@pytest.fixture(scope="session")
def sample_dataset_path(sample_project_dir: Path) -> Path:
    return sample_project_dir / "data" / "participant_text_samples.csv"


@pytest.fixture(scope="session")
def sample_prompt_template_path(sample_project_dir: Path) -> Path:
    return sample_project_dir / "prompts" / "prompt_template_main_analysis.txt"


@pytest.fixture(scope="session")
def sample_analysis_instructions_path(sample_project_dir: Path) -> Path:
    return sample_project_dir / "prompts" / "analysis_instructions_main_analysis.txt"


@pytest.fixture
def sample_config(sample_config_path: Path) -> AnalysisConfig:
    return load_config(sample_config_path)


@pytest.fixture
def sample_input_rows(sample_dataset_path: Path) -> list[dict[str, Any]]:
    with sample_dataset_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@pytest.fixture
def sample_input_columns(sample_input_rows: list[dict[str, Any]]) -> list[str]:
    if not sample_input_rows:
        return []
    return list(sample_input_rows[0].keys())


@pytest.fixture
def sample_prompt_template_text(sample_prompt_template_path: Path) -> str:
    return sample_prompt_template_path.read_text(encoding="utf-8")


@pytest.fixture
def sample_analysis_instructions_text(sample_analysis_instructions_path: Path) -> str:
    return sample_analysis_instructions_path.read_text(encoding="utf-8")


@pytest.fixture
def sample_normalized_dataset(sample_config: AnalysisConfig):
    return load_normalized_input_dataset(sample_config)


@pytest.fixture
def sample_normalized_row(sample_normalized_dataset):
    return sample_normalized_dataset.rows[0]
