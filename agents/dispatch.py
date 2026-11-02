import os

# A benchmark sets this to register its own agent servers under other names, so the
# website's running servers, which may run older code, never take its calls.
AGENT_NAME_SUFFIX = os.getenv("SIMS_AGENT_NAME_SUFFIX", "")

BOOKING_AGENT = "booking-agent" + AGENT_NAME_SUFFIX
CALLER_AGENT = "caller-agent" + AGENT_NAME_SUFFIX
