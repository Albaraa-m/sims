from datetime import time

import pytest

from agents.booking.planted_bugs import PlantedBug, store_for_agent_version


def test_a_bug_the_tool_enforces_loosens_the_tool_too():
    store_for_agent_version("v2-bug-large-parties").book("Omar", time(19), 12)

    with pytest.raises(ValueError):
        store_for_agent_version("v2").book("Omar", time(19), 12)


def test_a_bug_whose_v2_text_is_gone_fails_loudly():
    bug = PlantedBug("v2-bug-missing", (("text v2 no longer has", "bugged"),))

    with pytest.raises(ValueError):
        bug.apply_to_instructions("v2 instructions")
