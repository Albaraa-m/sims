import asyncio
import json

from pydantic import BaseModel

from benchmark.case_files import RESULTS_PATH, Case, load_cases, load_inferred_test
from core import llm
from regression_tests.convert import InferredTest
from regression_tests.models import TestSpec

# A different, stronger model than the converter's, so it doesn't grade its own work.
JUDGE_MODEL = "openai/gpt-5.4"

CRITERIA = ["goal_kept", "facts_kept", "trigger_kept", "policy_right"]
CLEAN_CRITERION = "no_test_for_clean_call"

CALLER_FIELDS = {"goal", "facts", "behavior"}

# Each judge sees only the fields its question is about.
JUDGED_FIELDS = {
    "goal_kept": {"goal"},
    "trigger_kept": CALLER_FIELDS,
    "policy_right": {"policy_under_test"},
}

JUDGE_QUESTIONS = {
    "goal_kept": "Does the spec's goal describe the same thing the caller wanted in "
    "the answer key's goal? Extra detail is fine; a different aim is not.",
    "trigger_kept": "The answer key's trigger is what the caller must do for the "
    "failure to happen. Would a caller who follows only the spec's goal, facts and "
    "behavior do it?",
    "policy_right": "Does the spec's policy_under_test name the same rule as the "
    "answer key's policy?",
}

JUDGE_PROMPT = """\
You grade a regression test that was generated from a failed call with a restaurant
booking agent, against an answer key a human wrote beforehand.

Question: {question}

If you are unsure, answer passed: false. Explain in one or two sentences.
Reply with JSON only, matching this schema:
{schema}

# Answer key

{expected}

# Generated test spec (only the fields this question is about)

{spec}
"""


class Judgement(BaseModel):
    passed: bool
    why: str


def normalized(text: str) -> str:
    return " ".join(text.lower().split())


def check_facts_kept(expected_facts: dict[str, str], spec: TestSpec) -> Judgement:
    """Fact names vary between runs, so each expected value is looked up in the caller fields."""
    caller_text = normalized(" ".join([*spec.facts.values(), spec.goal, spec.behavior]))
    missing = [
        f"{name}={value}"
        for name, value in expected_facts.items()
        if normalized(value) not in caller_text
    ]
    if missing:
        return Judgement(passed=False, why=f"missing: {', '.join(missing)}")
    return Judgement(passed=True, why="every expected fact is in the caller fields")


async def judge_criterion(criterion: str, expected: dict, spec: TestSpec) -> Judgement:
    prompt = JUDGE_PROMPT.format(
        question=JUDGE_QUESTIONS[criterion],
        schema=json.dumps(Judgement.model_json_schema()),
        expected=json.dumps(expected, indent=2),
        spec=spec.model_dump_json(indent=2, include=JUDGED_FIELDS[criterion]),
    )
    return await llm.generate_structured(prompt, Judgement, JUDGE_MODEL)


async def score_case(case: Case, inferred: InferredTest) -> dict[str, Judgement]:
    if case.expected.get("is_clean"):
        passed = inferred.spec is None
        why = "no test was created" if passed else "a test was created for a clean call"
        return {CLEAN_CRITERION: Judgement(passed=passed, why=why)}
    spec = inferred.spec
    if spec is None:
        missed = Judgement(passed=False, why=f"no test created: {inferred.reason}")
        return dict.fromkeys(CRITERIA, missed)
    judged = await asyncio.gather(
        *(
            judge_criterion(criterion, case.expected, spec)
            for criterion in JUDGE_QUESTIONS
        )
    )
    scores = dict(zip(JUDGE_QUESTIONS, judged, strict=True))
    scores["facts_kept"] = check_facts_kept(case.expected["facts"], spec)
    return {criterion: scores[criterion] for criterion in CRITERIA}


async def score_and_save_all_cases(cases: list[Case]) -> None:
    scores = await asyncio.gather(
        *(score_case(case, load_inferred_test(case.name)) for case in cases)
    )
    results = {
        case.name: {criterion: j.model_dump() for criterion, j in case_scores.items()}
        for case, case_scores in zip(cases, scores, strict=True)
    }
    RESULTS_PATH.write_text(json.dumps(results, indent=2) + "\n")


def main() -> None:
    asyncio.run(score_and_save_all_cases(load_cases()))


if __name__ == "__main__":
    main()
