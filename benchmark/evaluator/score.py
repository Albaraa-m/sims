import json
from collections import Counter

from benchmark.evaluator.case_files import RESULTS_PATH

OUTCOMES = ["pass", "fail", "inconclusive", "execution_failed"]


def percent(part: int, whole: int) -> str:
    return f"{part}/{whole} ({100 * part / whole:.0f}%)" if whole else "n/a"


def precision_and_recall_by_outcome(results: list[dict]) -> str:
    """Precision: of the calls graded X, how many really were X.
    Recall: of the calls that really were X, how many were graded X."""
    pairs = [
        (result["label"]["outcome"], grading["outcome"])
        for result in results
        for grading in result["gradings"]
    ]
    lines = ["| Verdict | Precision | Recall |", "|---|---|---|"]
    for outcome in OUTCOMES:
        graded = [expected for expected, got in pairs if got == outcome]
        actual = [got for expected, got in pairs if expected == outcome]
        lines.append(
            f"| {outcome} | {percent(graded.count(outcome), len(graded))} "
            f"| {percent(actual.count(outcome), len(actual))} |"
        )
    return "\n".join(lines)


def score_results(results: list[dict]) -> dict[str, str]:
    gradings = [
        (result["label"], grading)
        for result in results
        for grading in result["gradings"]
    ]
    # Evidence only means something for pass or fail verdicts that have key turns.
    cited_verdicts = [
        (label, g)
        for label, g in gradings
        if g["outcome"] in ("pass", "fail") and label["key_turns"]
    ]
    return {
        "Accuracy": percent(
            sum(label["outcome"] == g["outcome"] for label, g in gradings),
            len(gradings),
        ),
        "Evidence hit rate": percent(
            sum(
                bool(set(label["key_turns"]) & set(g["cited_turns"]))
                for label, g in cited_verdicts
            ),
            len(cited_verdicts),
        ),
        "Consistency": percent(
            sum(len({g["outcome"] for g in r["gradings"]}) == 1 for r in results),
            len(results),
        ),
    }


def confusion_matrix(results: list[dict]) -> str:
    counts = Counter(
        (result["label"]["outcome"], grading["outcome"])
        for result in results
        for grading in result["gradings"]
    )
    lines = [
        "| Expected ↓ / Got → | " + " | ".join(OUTCOMES) + " |",
        "|---" * (len(OUTCOMES) + 1) + "|",
    ]
    for expected in OUTCOMES:
        cells = [str(counts[(expected, got)]) for got in OUTCOMES]
        lines.append(f"| {expected} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_scores(results: list[dict]) -> None:
    for metric, value in score_results(results).items():
        print(f"{metric}: {value}")
    print()
    print(precision_and_recall_by_outcome(results))
    print()
    print(confusion_matrix(results))
    print()
    for result in results:
        got = [grading["outcome"] for grading in result["gradings"]]
        mark = "✓" if all(g == result["label"]["outcome"] for g in got) else "✗"
        print(f"{mark} {result['case']}: {got}")


def main() -> None:
    write_scores(json.loads(RESULTS_PATH.read_text()))


if __name__ == "__main__":
    main()
