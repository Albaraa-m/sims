import json

from benchmark.case_files import REPORT_PATH, RESULTS_PATH, Case, load_cases
from benchmark.score import CLEAN_CRITERION, CRITERIA, JUDGE_MODEL
from regression_tests.convert import CONVERSION_MODEL

HAND_WRITTEN_MARKER = (
    "<!-- Written by hand below; kept when the report is regenerated. -->"
)


def mark(passed: bool) -> str:
    return "✅" if passed else "❌"


def hand_written_section() -> str:
    if not REPORT_PATH.exists():
        return f"{HAND_WRITTEN_MARKER}\n"
    report = REPORT_PATH.read_text()
    return report[report.index(HAND_WRITTEN_MARKER) :]


def render_report(cases: list[Case], results: dict[str, dict[str, dict]]) -> str:
    failure_cases = [case for case in cases if not case.expected.get("is_clean")]
    clean_cases = [case for case in cases if case.expected.get("is_clean")]

    lines = [
        "# Benchmark: conversion fidelity",
        "",
        (
            f"Converter `{CONVERSION_MODEL}`, judge `{JUDGE_MODEL}`. "
            "Facts and the clean control are checked in code; the other criteria by the judge."
        ),
        "",
        "## Failure cases",
        "",
        "| Case | " + " | ".join(CRITERIA) + " |",
        "|---|" + "---|" * len(CRITERIA),
    ]
    for case in failure_cases:
        marks = [
            mark(results[case.name][criterion]["passed"]) for criterion in CRITERIA
        ]
        lines.append(f"| {case.name} | " + " | ".join(marks) + " |")
    passes_per_criterion = [
        sum(results[case.name][criterion]["passed"] for case in failure_cases)
        for criterion in CRITERIA
    ]
    lines.append(
        "| **Passed** | "
        + " | ".join(
            f"{passes}/{len(failure_cases)}" for passes in passes_per_criterion
        )
        + " |"
    )
    total_passes = sum(passes_per_criterion)
    total_checks = len(failure_cases) * len(CRITERIA)
    lines += [
        "",
        (
            f"**Overall: {total_passes}/{total_checks} checks "
            f"({total_passes / total_checks:.0%}).**"
        ),
        "",
        "## Clean control",
        "",
        "| Case | No test created |",
        "|---|---|",
    ]
    for case in clean_cases:
        judgement = results[case.name][CLEAN_CRITERION]
        lines.append(
            f"| {case.name} | {mark(judgement['passed'])} {judgement['why']} |"
        )
    lines += ["", "## Why each check failed", ""]
    for case in failure_cases:
        for criterion in CRITERIA:
            judgement = results[case.name][criterion]
            if not judgement["passed"]:
                lines.append(f"- **{case.name} / {criterion}**: {judgement['why']}")
    return "\n".join(lines) + "\n\n" + hand_written_section()


def write_report(cases: list[Case]) -> None:
    results = json.loads(RESULTS_PATH.read_text())
    REPORT_PATH.write_text(render_report(cases, results))


def main() -> None:
    write_report(load_cases())


if __name__ == "__main__":
    main()
