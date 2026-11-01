from simulations.models import Simulation
from simulations.transcript import spoken_lines


def test_spoken_lines_keep_only_agent_and_caller_messages():
    simulation = Simulation(
        agent_version="v1",
        report={
            "chat_history": {
                "items": [
                    {"type": "message", "role": "system", "content": ["rules"]},
                    {"type": "message", "role": "assistant", "content": ["Hi!"]},
                    {"type": "function_call", "name": "create_booking"},
                    {"type": "message", "role": "user", "content": ["Table for 4"]},
                ]
            }
        },
    )

    assert spoken_lines(simulation) == ["Agent: Hi!", "Caller: Table for 4"]


def test_simulation_without_report_has_no_lines():
    assert spoken_lines(Simulation(agent_version="v1")) == []
