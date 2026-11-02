import json

from benchmark.conversion.case_files import (
    BASELINE_RESULTS_PATH,
    REPORT_PATH,
    RESULTS_PATH,
    Case,
    load_cases,
)
from benchmark.conversion.score import CLEAN_CRITERION, CRITERIA, JUDGE_MODEL
from regression_tests.convert import CONVERSION_MODEL

HAND_WRITTEN_MARKER = (
    "<!-- Written by hand below; kept when the report is regenerated. -->"
)


INTRODUCTION = """\
# Benchmark: does a converted test keep the original failure?

A reviewer pastes a failed call with the restaurant booking agent. A model turns it
into a voice test: what the simulated caller wants and does, plus the rule the agent
broke. This benchmark checks whether that test still reproduces the original failure.

**Setup.** 6 call transcripts, each breaking a different agent rule, plus 1 clean
call. For each, an answer key (goal, facts, trigger, rule) was written by hand before
any conversion ran. Each generated test gets 4 pass/fail checks:

| Check | Passes if | Graded by |
|---|---|---|
| Goal | The caller wants the same thing as in the original call | LLM judge |
| Facts | Every key detail (name, time, party size, day) is kept | Code |
| Trigger | The caller still does what made the agent fail (e.g. asks for 22:00) | LLM judge |
| Policy | The test names the rule the agent actually broke | LLM judge |

The clean call passes if no test is created, so the converter can't score by
inventing failures. The judge is a stronger model than the converter, sees only the
fields it grades, and fails when unsure. Run it with `uv run python -m benchmark.conversion.run`.
"""


def mark(passed: bool) -> str:
    return "✅" if passed else "❌"


def hand_written_section() -> str:
    if not REPORT_PATH.exists():
        return f"{HAND_WRITTEN_MARKER}\n"
    report = REPORT_PATH.read_text()
    return report[report.index(HAND_WRITTEN_MARKER) :]


def count_passes(
    cases: list[Case], results: dict[str, dict[str, dict]], criterion: str
) -> int:
    return sum(results[case.name][criterion]["passed"] for case in cases)


CRITERION_LABELS = {
    "goal_kept": "Goal",
    "facts_kept": "Facts",
    "trigger_kept": "Trigger",
    "policy_right": "Policy",
}


def render_report(
    cases: list[Case],
    results: dict[str, dict[str, dict]],
    baseline_results: dict[str, dict[str, dict]] | None,
) -> str:
    failure_cases = [case for case in cases if not case.expected.get("is_clean")]
    clean_cases = [case for case in cases if case.expected.get("is_clean")]
    total_checks = len(failure_cases) * len(CRITERIA)

    def totals_row(label: str, results: dict[str, dict[str, dict]]) -> str:
        passes = [count_passes(failure_cases, results, c) for c in CRITERIA]
        cells = " | ".join(f"{p}/{len(failure_cases)}" for p in passes)
        return f"| {label} | {cells} | **{sum(passes)}/{total_checks}** |"

    labels = [CRITERION_LABELS[criterion] for criterion in CRITERIA]
    lines = [
        "## Results",
        "",
        f"Converter `{CONVERSION_MODEL}`; judge `{JUDGE_MODEL}`.",
        "",
        "| What the agent did wrong | " + " | ".join(labels) + " | Total |",
        "|---|" + "---|" * (len(CRITERIA) + 1),
    ]
    for case in failure_cases:
        case_results = results[case.name]
        marks = [mark(case_results[criterion]["passed"]) for criterion in CRITERIA]
        passes = sum(case_results[criterion]["passed"] for criterion in CRITERIA)
        lines.append(
            f"| {case.expected['failure']} | "
            + " | ".join(marks)
            + f" | {passes}/{len(CRITERIA)} |"
        )
    lines.append(totals_row("**After fixes**", results))
    if baseline_results:
        lines.append(totals_row("*Before fixes*", baseline_results))
    for case in clean_cases:
        judgement = results[case.name][CLEAN_CRITERION]
        lines += [
            "",
            (
                f"**Clean call** ({case.expected['failure'].lower()}): "
                f"{mark(judgement['passed'])} {judgement['why']}."
            ),
        ]
    lines += [
        "",
        (
            "Each judgement's reason: `benchmark/conversion/results.json`; each generated test: "
            "`benchmark/conversion/outputs/`."
        ),
    ]
    return INTRODUCTION + "\n" + "\n".join(lines) + "\n\n" + hand_written_section()


def write_report(cases: list[Case]) -> None:
    results = json.loads(RESULTS_PATH.read_text())
    baseline_results = (
        json.loads(BASELINE_RESULTS_PATH.read_text())
        if BASELINE_RESULTS_PATH.exists()
        else None
    )
    REPORT_PATH.write_text(render_report(cases, results, baseline_results))


def main() -> None:
    write_report(load_cases())


if __name__ == "__main__":
    main()
