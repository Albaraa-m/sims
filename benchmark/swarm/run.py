"""Generates a swarm for v2 from the restaurant's rules, then checks it against the
answer key: which rules it covers, and which planted bugs its tests catch.

Starts its own agent servers. Run it with SIMS_AGENT_NAME_SUFFIX set (see README), so
the website's agent servers, which may predate the planted bugs, never take its calls.
"""

import asyncio
import json
from pathlib import Path

from pydantic import BaseModel

import swarms.models  # noqa: F401  (registers the swarm tables)
from agents.dispatch import AGENT_NAME_SUFFIX
from agents.servers import running_agent_servers
from benchmark.in_memory_database import use_in_memory_database
from benchmark.swarm.answer_key import ANSWER_KEY, AnswerKeyRule
from benchmark.swarm.score import is_bug_caught
from cli import wait_for_runs_to_settle
from core import llm
from evaluations.crud import latest_evaluation_of_simulation
from evaluations.judge import JUDGE_MODEL
from regression_tests.crud import (
    create_test_from_spec,
    save_transcript_as_source_conversation,
)
from simulations.crud import get_simulation
from simulations.models import SimulationStatus
from simulations.queue import RunRequest, admit_runs
from swarms.models import Scenario
from swarms.propose import find_policies_of_agent_version, propose_swarm

RESULTS_PATH = Path(__file__).parent / "results.json"

MATCHING_PROMPT = """\
Below are the rules a restaurant's voice agent must follow, and the tests a generator
wrote for that agent. For each rule, give the number of the test that checks it: its
policy under test and expected outcome are about that rule, so an agent breaking the
rule would fail it. Give null when no test checks the rule.

Reply with JSON only, matching this schema:
{schema}

# Rules

{rules}

# Tests

{tests}
"""


class RuleMatch(BaseModel):
    rule_number: int
    test_number: int | None


class RuleMatches(BaseModel):
    matches: list[RuleMatch]


async def generate_swarm_for_v2() -> list[Scenario]:
    policies = await find_policies_of_agent_version("v2")
    proposal = await propose_swarm("v2", policies)
    return proposal.scenarios


async def match_answer_key_rules_to_tests(
    scenarios: list[Scenario],
) -> list[Scenario | None]:
    """The test covering each answer-key rule, in answer-key order."""
    prompt = MATCHING_PROMPT.format(
        schema=json.dumps(RuleMatches.model_json_schema()),
        rules="\n".join(
            f"{number}. {key.rule}" for number, key in enumerate(ANSWER_KEY, 1)
        ),
        tests="\n".join(
            f"{number}. {scenario.name}: {scenario.spec.policy_under_test} "
            f"Expected: {scenario.spec.expected_outcome}"
            for number, scenario in enumerate(scenarios, 1)
        ),
    )
    reply = await llm.generate_structured(prompt, RuleMatches, JUDGE_MODEL)
    test_number_by_rule = {
        match.rule_number: match.test_number for match in reply.matches
    }
    return [
        scenarios[test_number - 1]
        if (test_number := test_number_by_rule.get(rule_number))
        and 1 <= test_number <= len(scenarios)
        else None
        for rule_number in range(1, len(ANSWER_KEY) + 1)
    ]


def queue_bugged_and_v2_runs_of_test(
    scenario: Scenario, bugged_version: str
) -> list[str]:
    """One run each: a benchmark run, not a release gate (see README limits)."""
    source = save_transcript_as_source_conversation("swarm benchmark")
    test = create_test_from_spec(source, scenario.name, scenario.spec)
    requests = [RunRequest(bugged_version, test.id), RunRequest("v2", test.id)]
    return [simulation.id for simulation in admit_runs(requests)]


def outcome_of_simulation(simulation_id: str) -> dict:
    simulation = get_simulation(simulation_id)
    if simulation.status == SimulationStatus.FAILED:
        return {
            "simulation_id": simulation_id,
            "outcome": "execution_failed",
            "reason": simulation.error,
        }
    evaluation = latest_evaluation_of_simulation(simulation_id)
    return {
        "simulation_id": simulation_id,
        "outcome": evaluation.outcome.value if evaluation else "not_graded",
        "reason": evaluation.reason if evaluation else None,
    }


def result_of_rule(
    key: AnswerKeyRule, scenario: Scenario | None, runs: list[str]
) -> dict:
    if scenario is None:
        return {
            "rule": key.rule,
            "bugged_version": key.bugged_version,
            "test": None,
            "bugged_agent_run": None,
            "v2_run": None,
            "caught": False,
        }
    bugged, v2 = (outcome_of_simulation(run) for run in runs)
    return {
        "rule": key.rule,
        "bugged_version": key.bugged_version,
        "test": scenario.model_dump(),
        "bugged_agent_run": bugged,
        "v2_run": v2,
        "caught": is_bug_caught(bugged["outcome"], v2["outcome"]),
    }


async def run_benchmark() -> dict:
    scenarios = await generate_swarm_for_v2()
    covering_tests = await match_answer_key_rules_to_tests(scenarios)
    runs_by_rule = [
        queue_bugged_and_v2_runs_of_test(scenario, key.bugged_version)
        if scenario
        else []
        for key, scenario in zip(ANSWER_KEY, covering_tests, strict=True)
    ]
    await wait_for_runs_to_settle(
        [run for runs in runs_by_rule for run in runs], with_worker=True
    )
    rules = [
        result_of_rule(key, scenario, runs)
        for key, scenario, runs in zip(
            ANSWER_KEY, covering_tests, runs_by_rule, strict=True
        )
    ]
    return {
        "covered": sum(rule["test"] is not None for rule in rules),
        "caught": sum(rule["caught"] for rule in rules),
        "rules_in_answer_key": len(ANSWER_KEY),
        "generated_tests": [scenario.model_dump() for scenario in scenarios],
        "rules": rules,
    }


def print_summary(results: dict) -> None:
    total = results["rules_in_answer_key"]
    print(f"\ncovers {results['covered']} of {total} rules")
    print(f"catches {results['caught']} of {total} planted bugs")
    for rule in results["rules"]:
        mark = "caught" if rule["caught"] else "missed"
        if rule["test"] is None:
            print(f"  {mark}  {rule['rule']}  no test")
            continue
        bugged, v2 = rule["bugged_agent_run"]["outcome"], rule["v2_run"]["outcome"]
        print(f"  {mark}  {rule['rule']}  bugged {bugged}  v2 {v2}")


def main() -> None:
    if not AGENT_NAME_SUFFIX:
        raise SystemExit(
            "set SIMS_AGENT_NAME_SUFFIX, e.g. SIMS_AGENT_NAME_SUFFIX=-bench"
        )
    use_in_memory_database()
    with running_agent_servers():
        results = asyncio.run(run_benchmark())
    RESULTS_PATH.write_text(json.dumps(results, indent=2) + "\n")
    print_summary(results)


if __name__ == "__main__":
    main()
