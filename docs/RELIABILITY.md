# Reliability under load: spike, crash, failures and capacity

**Question:** when many calls run at once and things break, is every requested call accounted for, never lost, stuck or counted twice, and how much can the system take?

**Short answer:** in 4 sessions and 32 real voice calls, every call finished and was recorded once. A worker killed mid-call lost nothing (its 4 calls were recovered in about a minute), 30% injected failures were all retried, and a start too big for the queue was refused whole. Measured capacity: **4 calls at once** on this laptop, which is limited by memory before the account's limit of about 10.

## How it stays reliable

| Mechanism | What it guarantees |
|---|---|
| Every requested call is one row in the queue | Totals always add up; a retry is the next attempt on the same row, so it's never counted twice |
| Admission: a start that doesn't fit the queue is refused whole, and recorded | No unbounded backlog; refused work is counted, not dropped |
| Workers claim a call with a 60 s lease, renewed every 10 s | A dead worker's calls aren't stuck: once the lease expires, any other worker's reaper requeues them |
| Up to 3 attempts per call; each attempt has its own room and evidence | Failed or interrupted attempts are retried; an earlier failure stays in the history |
| A hard deadline around every attempt | A hung call can't stay "Running" forever |
| A global cap on calls running at once | Stays within the account's connection limits |

## Results

Setup: one laptop (MacBook Air, 8 GB), LiveKit Ship plan, one pair of agent servers, two workers, a cap of 4 calls at once.

| Session | What we did | Outcome |
|---|---|---|
| 1. Spike and crash | Asked for 12 calls with the queue limit at 10, then 10. Killed worker A (`kill -9`) while it held 4 calls | The 12 were **refused whole** (recorded as 1 refused start); the 10 were queued. Worker A died at 18:50:58; its leases expired and worker B's reaper marked the 4 calls **Interrupted** and requeued them at 18:52:01 (63 s later). Worker B ran them as attempt 2. **10 of 10 Done** in 5 m 37 s |
| 2. Injected failures | 10 calls with 30% of attempts made to fail before placing the call | **3 failures absorbed**: one call failed twice and passed on attempt 3. **10 of 10 Done** in 3 m 07 s |
| 3. Capacity, cap 2 | 6 calls, at most 2 at once | Done in **227 s** |
| 4. Capacity, cap 4 | 6 calls, at most 4 at once | Done in **127 s**; a call takes about 66 s either way |

**Across all 32 calls:** 32 Done, 0 lost, 0 left Running, 0 counted twice. Every Done call has a session report and a recording (the smallest is 375 KB), and **no LiveKit room was left open**. The agents logged no rate-limit (429) errors.

## Limits

| Limit | Measured or known |
|---|---|
| **Laptop memory: the first limit** | At 4 calls at once, 7.5 GB of 8 GB was in use with 105 MB free. Each call runs two agents in their own processes. We didn't go past 4 |
| Account (Ship plan) | 20 concurrent inference connections per model, and each call needs 2 (one per agent), so about **10 calls at once** at most |
| Recovery time | A dead worker's calls wait up to 60 s (the lease) plus up to 15 s (the reaper's interval). Meanwhile they still count against the cap |
| Queue | One SQLite file on one machine; workers and the website must share it |
| Fault controls | Killing a worker from the website only works for workers on the same machine, and only when the website runs with `SIMS_FAULT_INJECTION=1` |

**Bugs this run found and we fixed:**
1. With several processes on one SQLite file, a write could fail at once with "database is locked". Transactions now take the write lock up front and wait.
2. A worker died on that one error. A worker now survives any error in its loop.
3. The Kill button compared hostnames, which macOS reports differently to different processes. It now checks the process is a `sims worker`.

## Reproduce it

```
uv run sims agents                                # terminal 1: agent servers
uv run sims worker                                # terminals 2 and 3: two workers
SIMS_FAULT_INJECTION=1 uv run sims web            # terminal 4: website with fault controls
SIMS_MAX_QUEUED_RUNS=10 uv run sims load <swarm-id> --count 12   # refused whole
SIMS_MAX_QUEUED_RUNS=10 uv run sims load <swarm-id> --count 10   # queued
```
Then on **Dashboard → System health**: watch the queue and the load chart; press **Kill** on the worker holding calls; set **Inject failures** to 30%. The counts always add up to the calls requested.
