from core.db import get_row, save
from simulations.models import Simulation


def create_simulation(agent_version: str) -> Simulation:
    return save(Simulation(agent_version=agent_version))


def get_simulation(simulation_id: str) -> Simulation:
    return get_row(Simulation, simulation_id)


def update_simulation(simulation_id: str, **changes) -> Simulation:
    simulation = get_row(Simulation, simulation_id)
    for field, value in changes.items():
        setattr(simulation, field, value)
    return save(simulation)
