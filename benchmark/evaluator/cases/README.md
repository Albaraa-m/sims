# Evaluator benchmark cases

Each case is what `evaluate_simulation` reads, plus the right answer, written before grading.

| File | Holds |
|---|---|
| `report.json` | The session report's `chat_history`; absent when the fault is a missing report |
| `run.json` | The test spec (from `../specs/`), agent version, status, error, whether a recording exists, and `judge_fails` to fake a broken judge |
| `label.json` | Expected outcome, the key turns that prove it, and why |

| Cases | Source | Expected |
|---|---|---|
| 01–06 | Real voice runs copied from `sims.db` | v1 fails confirmation; both versions refer large parties |
| 07–12 | Real calls edited by hand into subtle passes and failures | Fail, except 10: a different policy's mistake must not fail this one |
| 13–15 | Hand-written off-script callers | Inconclusive: the situation never came up |
| 16–20 | Injected execution faults | Execution failure; inconclusive when the judge breaks |
