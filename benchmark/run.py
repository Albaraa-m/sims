import asyncio

from benchmark.case_files import OUTPUTS_DIR, Case, inferred_test_path, load_cases
from benchmark.report import write_report
from benchmark.score import score_and_save_all_cases
from regression_tests.convert import infer_test_spec_from_transcript


async def infer_and_save_test_for_each_case(cases: list[Case]) -> None:
    # No reported issue: the converter must find the failure from the transcript alone.
    inferred_tests = await asyncio.gather(
        *(infer_test_spec_from_transcript(case.transcript) for case in cases)
    )
    OUTPUTS_DIR.mkdir(exist_ok=True)
    for case, inferred in zip(cases, inferred_tests, strict=True):
        inferred_test_path(case.name).write_text(
            inferred.model_dump_json(indent=2) + "\n"
        )
        print(f"{case.name}: {'spec' if inferred.spec else 'no spec'}")


def main() -> None:
    """Infers, scores and reports; score.py and report.py also run alone."""
    cases = load_cases()
    asyncio.run(infer_and_save_test_for_each_case(cases))
    asyncio.run(score_and_save_all_cases(cases))
    write_report(cases)


if __name__ == "__main__":
    main()
