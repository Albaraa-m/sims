from simulations.conversation import SpokenLine, conversation_of_simulation
from simulations.models import Simulation, SimulationStatus


def find_execution_failure(simulation: Simulation) -> str | None:
    # TODO: The return values can be constants instead of hardcoded strings
    """Why the call can't be graded, or None when it ran properly."""
    if simulation.status == SimulationStatus.FAILED:
        return f"the call failed: {simulation.error or 'unknown error'}"
    if simulation.status != SimulationStatus.DONE:
        return f"the call hasn't finished; it is {simulation.status}"
    if not simulation.report:
        return "the call has no session report"
    if simulation.recording_path is None:
        return "the call has no recording"
    speakers = {
        turn.speaker
        for turn in conversation_of_simulation(simulation)
        if isinstance(turn, SpokenLine) and turn.text.strip()
    }
    for speaker in ("Agent", "Caller"):
        if speaker not in speakers:
            return f"the {speaker.lower()} never spoke"
    return None
