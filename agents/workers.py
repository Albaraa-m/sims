import os
import signal
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager

from core.config import LOGS_DIR

SERVERS = {"booking": "agents.booking.server", "caller": "agents.caller.server"}
READY_LINE = "registered worker"
STARTUP_TIMEOUT_SECONDS = 60


@contextmanager
def running_workers() -> Iterator[None]:
    """Starts both agent workers, waits until they are registered, and stops them on exit."""
    LOGS_DIR.mkdir(exist_ok=True)
    processes = []
    try:
        for name, module in SERVERS.items():
            log = (LOGS_DIR / f"{name}.log").open("w")
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
    logs = [LOGS_DIR / f"{name}.log" for name in SERVERS]
    while not all(READY_LINE in log.read_text() for log in logs):
        if time.monotonic() > deadline:
            raise TimeoutError(f"agent workers did not register; see {LOGS_DIR}")
        time.sleep(1)
