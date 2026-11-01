import asyncio

from benchmark.case_files import OUTPUTS_DIR, Case, inferred_test_path, load_cases
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
    asyncio.run(infer_and_save_test_for_each_case(load_cases()))


if __name__ == "__main__":
    main()
