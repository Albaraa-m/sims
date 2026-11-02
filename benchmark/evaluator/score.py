import json

from benchmark.evaluator.case_files import RESULTS_PATH


def percent(part: int, whole: int) -> str:
    return f"{part}/{whole} ({100 * part / whole:.0f}%)" if whole else "n/a"


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
    graded_pass = [label for label, g in gradings if g["outcome"] == "pass"]
    return {
        "Pass precision": percent(
            sum(label["outcome"] == "pass" for label in graded_pass), len(graded_pass)
        ),
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


def write_scores(results: list[dict]) -> None:
    for metric, value in score_results(results).items():
        print(f"{metric}: {value}")
    print()
    for result in results:
        got = [grading["outcome"] for grading in result["gradings"]]
        mark = "✓" if all(g == result["label"]["outcome"] for g in got) else "✗"
        print(f"{mark} {result['case']}: {got}")


def main() -> None:
    write_scores(json.loads(RESULTS_PATH.read_text()))


if __name__ == "__main__":
    main()
