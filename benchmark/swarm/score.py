def is_bug_caught(bugged_agent_outcome: str, v2_outcome: str) -> bool:
    """Caught only when the rule's test fails the bugged agent and passes clean v2,
    so a test that always fails catches nothing."""
    return bugged_agent_outcome == "fail" and v2_outcome == "pass"
