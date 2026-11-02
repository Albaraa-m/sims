import os
import signal
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from agents.dispatch import AGENT_NAME_SUFFIX
from core.config import LOGS_DIR

SERVERS = {"booking": "agents.booking.server", "caller": "agents.caller.server"}
# LiveKit still logs agent servers under their old name, "worker".
READY_LINE = "registered worker"
STARTUP_TIMEOUT_SECONDS = 60


def log_path_of_server(name: str) -> Path:
    # Named like the servers, so a benchmark's servers don't overwrite the website's logs.
    return LOGS_DIR / f"{name}{AGENT_NAME_SUFFIX}.log"


@contextmanager
def running_agent_servers() -> Iterator[None]:
    """Starts both agent servers, waits until they are registered, and stops them on exit."""
    LOGS_DIR.mkdir(exist_ok=True)
    processes = []
    try:
        for name, module in SERVERS.items():
            log = log_path_of_server(name).open("w")
            # Own process group, so stopping it also stops the dev-mode child processes.
            processes.append(
                subprocess.Popen(
                    [sys.executable, "-m", module, "dev"],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            )
        wait_until_registered()
        yield
    finally:
        for process in processes:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
        for process in processes:
            process.wait()


def wait_until_registered() -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    logs = [log_path_of_server(name) for name in SERVERS]
    while not all(READY_LINE in log.read_text() for log in logs):
        if time.monotonic() > deadline:
            raise TimeoutError(f"agent servers did not register; see {LOGS_DIR}")
        time.sleep(1)
