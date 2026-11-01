import asyncio

from benchmark.case_files import Case
from benchmark.score import CLEAN_CRITERION, CRITERIA, check_facts_kept, score_case
from regression_tests.convert import InferredTest


def test_facts_are_found_in_any_caller_field(spec):
    spec = spec.model_copy(update={"facts": {"time": "19:00"}, "goal": "Book for Dana"})

    judgement = check_facts_kept({"name": "dana", "time": "19:00"}, spec)

    assert judgement.passed


def test_missing_fact_fails_and_is_named(spec):
    judgement = check_facts_kept({"party_size": "12"}, spec)

    assert not judgement.passed
    assert "party_size=12" in judgement.why


def test_clean_case_passes_only_without_a_test(spec):
    clean_case = Case(name="clean", transcript="", expected={"is_clean": True})

    without_test = asyncio.run(score_case(clean_case, InferredTest(reason="fine")))
    with_test = asyncio.run(
        score_case(clean_case, InferredTest(reason="x", name="x", spec=spec))
    )

    assert without_test[CLEAN_CRITERION].passed
    assert not with_test[CLEAN_CRITERION].passed


def test_missed_failure_fails_every_criterion():
    failure_case = Case(name="f", transcript="", expected={"facts": {}})

    scores = asyncio.run(score_case(failure_case, InferredTest(reason="looked fine")))

    assert list(scores) == CRITERIA
    assert not any(judgement.passed for judgement in scores.values())
