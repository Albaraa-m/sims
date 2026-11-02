from agents.booking.agent import INSTRUCTIONS_BY_VERSION
from benchmark.swarm.answer_key import ANSWER_KEY
from benchmark.swarm.score import is_bug_caught


def test_every_answer_key_rule_has_its_own_bugged_agent():
    bugged_versions = [key.bugged_version for key in ANSWER_KEY]

    assert len(set(bugged_versions)) == len(ANSWER_KEY)
    for version in bugged_versions:
        assert INSTRUCTIONS_BY_VERSION[version] != INSTRUCTIONS_BY_VERSION["v2"]


def test_a_bug_is_caught_when_its_test_fails_the_bug_and_passes_v2():
    assert is_bug_caught("fail", "pass")


def test_a_test_that_also_fails_v2_catches_nothing():
    assert not is_bug_caught("fail", "fail")


def test_an_untested_call_catches_nothing():
    assert not is_bug_caught("inconclusive", "pass")
