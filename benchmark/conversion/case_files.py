import json
from pathlib import Path
from typing import NamedTuple

from regression_tests.convert import InferredTest

BENCHMARK_DIR = Path(__file__).parent
CASES_DIR = BENCHMARK_DIR / "cases"
OUTPUTS_DIR = BENCHMARK_DIR / "outputs"
RESULTS_PATH = BENCHMARK_DIR / "results.json"
# Results before the last converter change, to show what it changed.
BASELINE_RESULTS_PATH = BENCHMARK_DIR / "results.baseline.json"
REPORT_PATH = BENCHMARK_DIR / "results.md"


class Case(NamedTuple):
    name: str
    transcript: str
    expected: dict


def load_cases() -> list[Case]:
    return [
        Case(
            name=case_dir.name,
            transcript=(case_dir / "transcript.txt").read_text(),
            expected=json.loads((case_dir / "expected.json").read_text()),
        )
        for case_dir in sorted(CASES_DIR.iterdir())
        if case_dir.is_dir()
    ]


def inferred_test_path(case_name: str) -> Path:
    return OUTPUTS_DIR / f"{case_name}.json"


def load_inferred_test(case_name: str) -> InferredTest:
    return InferredTest.model_validate_json(inferred_test_path(case_name).read_text())
