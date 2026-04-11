# Biovector — Agent Rules for Session Logging

This doc is for any agent (Diane, Claude Code, Jean-Luc, etc.) that logs training data to this repo.

## The one rule

**Every write to this repo must be followed by `git add -A && git commit -m "log <session> <date>" && git push`. No exceptions. Never skip the sync.**

## Files to write

| File | Purpose |
|---|---|
| `data/user/sets.json` | Per-set data (append to `"sets"` array) |
| `strength-states.json` | Updated next session + loads + states |

## Data format

Each set appended to `data/user/sets.json` has this structure:

```json
{
  "timestamp": 1712500000,
  "exercise_name": "Squat",
  "weight": 100.0,
  "reps": 5,
  "session_name": "A1",
  "notes": ""
}
```

Only `timestamp`, `exercise_name`, `weight`, and `reps` are required. All derived metrics (1RM, load, intensity, h, phi) are computed on-the-fly by the library — **do not store them**.

## Minimal workflow for logging a session

```
1. Read strength-states.json → "next_session" (e.g. B1, C1, A2)
2. Determine timestamp: datetime(year, month, day, hour, minute).timestamp()
3. For each set performed, append a record to data/user/sets.json "sets" array
4. Update strength-states.json:
     - Set "updated" to today's date (YYYY-MM-DD)
     - Set "next_session" to the following session label
     - Update load/state for each exercise that changed
5. git add -A && git commit -m "log <session> <date>" && git push
```

## Formulas

These are used for computing derived metrics (not stored, but useful for analysis and logging context):

```python
import math

def logistic(x):
    return 1.05 / (1 + math.e**(-40*(x - 0.75)))

def epley(w, r):
    return w * (1 + r/30)
```

Per-exercise parameters (Delta, kappa = rho × theta):

| Exercise | ID | Delta | kappa |
|---|---|---|---|
| Squat | S00 | 0.65 | 0.65 |
| Front Squat | S10 | 0.7 | 0.7 |
| Bench Press | P01.00 | 0.5 | 0.0 |
| Deadlift | H00.0 | 0.6 | 0.36 |
| Power Clean | T20.1 | 1.6 | 0.36 |
| Military Press | P10.0 | 0.7 | — |

Body weight (`BW`) — use current value from `data/user/bodyweight.json` or approximate to 85 kg if unknown.

Computed per set (for reference/analysis — not stored):

```
load     = round((Delta × weight + BW × kappa) × reps)
pred1RM  = round(epley(weight, reps))
pred1RL  = round(epley(load / reps, reps))
Int      = pred1RL / est1RL   (1.0 if no est1RL)
h        = round(logistic(Int), 2)
phi      = round(load × h)
```

## strength-states.json schema

```json
{
  "updated": "<YYYY-MM-DD>",
  "next_session": "<A1|B1|C1|A2|B2|C2|...>",
  "FS":  { "state": "<S0|S0p|S2|D0|P0|P0p>", "load": <kg> },
  "SQ":  { "state": "<S0|S0p|S2|D0|P0|P0p>", "load": <kg> },
  "BP":  { "state": "<S0|S0p|S2|D0|P0|P0p>", "load": <kg> },
  "DL":  { "state": "D0", "load": <kg> },
  "MP":  { "state": "<S0|S0p|D0>", "load": <kg> },
  "PC":  { "state": "<P0|P0p|...>", "load": <kg> },
  "chins_target": <n>,
  "dips_target": <n>
}
```

State codes:
- `S0` — base strength
- `S0p` — strength progressed (advanced reps or load)
- `S2` — strength phase 2
- `D0` — deload
- `P0` — power base
- `P0p` — power progressed

## What "logged" looks like

When a session is correctly logged:
- `data/user/sets.json` has N new entries in its `"sets"` array (one per set)
- `strength-states.json` has updated `next_session`, `updated`, and any changed exercise states/loads
- `git push` is confirmed

If you are unsure about any value, leave `est1RM` and `est1RL` as `0` — this is what Matias does and the system handles it.

## Development workflow

When developing on biovector itself:

```bash
# Install in editable mode
uv tool install -e .

# Run tests
python -m pytest tests/

# Run commands with correct data path
BIOVECTOR_DATA_DIR=$PWD/data biovector viz
BIOVECTOR_DATA_DIR=$PWD/data biovector update
```

Or add to your shell profile:
```bash
export BIOVECTOR_DATA_DIR=$HOME/ghq/github.com/matias-ceau/biovector/data
```
