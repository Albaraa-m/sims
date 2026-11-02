from core.db import save
from evaluations.execution import find_execution_failure
from evaluations.judge import (
    JUDGE_MODEL,
    JUDGE_PROMPT_VERSION,
    ask_judge_for_verdict,
    outcome_from_judge_verdict,
)
from evaluations.models import Evaluation, Outcome
from regression_tests.crud import get_test
from regression_tests.models import TestSpec
from simulations.conversation import conversation_of_simulation
from simulations.crud import get_simulation


async def evaluate_simulation(simulation_id: str) -> Evaluation:
    """Saves a new evaluation each time, so regrading keeps the earlier ones."""
    simulation = get_simulation(simulation_id)
    execution_failure = find_execution_failure(simulation)
    if execution_failure:
        return save(
            Evaluation(
                simulation_id=simulation_id,
                attempt=max(simulation.attempt, 1),
                outcome=Outcome.EXECUTION_FAILED,
                reason=execution_failure.reason,
            )
        )
    if simulation.test_id is None:
        return save(
            Evaluation(
                simulation_id=simulation_id,
                attempt=max(simulation.attempt, 1),
                outcome=Outcome.INCONCLUSIVE,
                reason="the run has no test, so there is no policy to grade",
            )
        )

    spec = TestSpec.model_validate(get_test(simulation.test_id).spec)
    conversation = conversation_of_simulation(simulation)
    try:
        reply = await ask_judge_for_verdict(spec, conversation)
    # A failed judge must never pass a run; anything it raises becomes inconclusive.
    except Exception as error:  # noqa: BLE001
        return save(
            Evaluation(
                simulation_id=simulation_id,
                attempt=max(simulation.attempt, 1),
                outcome=Outcome.INCONCLUSIVE,
                reason="the judge failed",
                error=str(error) or type(error).__name__,
                judge_model=JUDGE_MODEL,
                judge_prompt_version=JUDGE_PROMPT_VERSION,
            )
        )
    graded = outcome_from_judge_verdict(reply, len(conversation))
    return save(
        Evaluation(
            simulation_id=simulation_id,
            attempt=max(simulation.attempt, 1),
            outcome=graded.outcome,
            situation_happened=reply.situation_happened,
            cited_turns=reply.cited_turns,
            reason=graded.reason,
            judge_model=JUDGE_MODEL,
            judge_prompt_version=JUDGE_PROMPT_VERSION,
        )
    )
