import json
from pathlib import Path
from typing import NamedTuple

EVALUATOR_BENCHMARK_DIR = Path(__file__).parent
CASES_DIR = EVALUATOR_BENCHMARK_DIR / "cases"
SPECS_DIR = EVALUATOR_BENCHMARK_DIR / "specs"
RESULTS_PATH = EVALUATOR_BENCHMARK_DIR / "results.json"


class EvaluatorCase(NamedTuple):
    name: str
    spec: dict
    run: dict
    report: dict | None  # None for the "no report saved" fault
    label: dict


def load_evaluator_cases() -> list[EvaluatorCase]:
    cases = []
    for case_dir in sorted(path for path in CASES_DIR.iterdir() if path.is_dir()):
        run = json.loads((case_dir / "run.json").read_text())
        report_path = case_dir / "report.json"
        cases.append(
            EvaluatorCase(
                name=case_dir.name,
                spec=json.loads((SPECS_DIR / f"{run['spec']}.json").read_text()),
                run=run,
                report=json.loads(report_path.read_text())
                if report_path.exists()
                else None,
                label=json.loads((case_dir / "label.json").read_text()),
            )
        )
    return cases
