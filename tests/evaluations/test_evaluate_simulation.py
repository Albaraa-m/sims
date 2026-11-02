import asyncio
import json

import pytest

from evaluations.crud import list_evaluations_of_simulation
from evaluations.evaluate import evaluate_simulation
from evaluations.models import Outcome
from regression_tests.crud import create_test_from_spec
from simulations.crud import create_simulation, update_simulation
from simulations.models import Simulation, SimulationStatus

REPORT = {
    "chat_history": {
        "items": [
            {"type": "message", "role": "assistant", "content": ["Hello."]},
            {"type": "message", "role": "user", "content": ["Table for 4 at 19:00."]},
            {"type": "message", "role": "assistant", "content": ["Booked."]},
        ]
    }
}


@pytest.fixture
def finished_run(source_conversation, spec) -> Simulation:
    test = create_test_from_spec(source_conversation, "Unconfirmed", spec)
    simulation = create_simulation("v1", test.id)
    return update_simulation(
        simulation.id,
        status=SimulationStatus.DONE,
        report=REPORT,
        recording_path="evidence/x/audio.ogg",
    )


def judge_reply(verdict: str) -> str:
    return json.dumps(
        {
            "reasoning": "worked through",
            "situation_happened": True,
            "verdict": verdict,
            "cited_turns": [2],
            "reason": "booked without reading back",
        }
    )


def evaluate(simulation: Simulation):
    return asyncio.run(evaluate_simulation(simulation.id))


def test_judge_verdict_is_saved_with_its_settings(llm_replies, finished_run):
    llm_replies.append(judge_reply("fail"))

    evaluation = evaluate(finished_run)

    assert evaluation.outcome == Outcome.FAIL
    assert evaluation.cited_turns == [2]
    assert evaluation.judge_model is not None


def test_execution_failure_skips_the_judge(llm_replies):
    simulation = create_simulation("v1")
    update_simulation(simulation.id, status=SimulationStatus.FAILED, error="timeout")

    assert evaluate(simulation).outcome == Outcome.EXECUTION_FAILED
    assert llm_replies == []


def test_failed_judge_is_inconclusive_not_a_pass(llm_replies, finished_run):
    llm_replies.extend(["not json", "still not json"])

    evaluation = evaluate(finished_run)

    assert evaluation.outcome == Outcome.INCONCLUSIVE
    assert evaluation.error


def test_regrading_keeps_the_earlier_evaluation(llm_replies, finished_run):
    llm_replies.extend([judge_reply("fail"), judge_reply("pass")])

    evaluate(finished_run)
    evaluate(finished_run)

    outcomes = [e.outcome for e in list_evaluations_of_simulation(finished_run.id)]
    assert sorted(outcomes) == [Outcome.FAIL, Outcome.PASS]
