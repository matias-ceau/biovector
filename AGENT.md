# Biovector — Logging Sessions

This doc is for any agent (Diane, Claude Code, Jean-Luc, etc.) that logs training data to this repo.

## The one rule

**Every write to this repo must be followed by `git add -A && git commit -m "log <session> <date>" && git push`. No exceptions. Never skip the sync.**

## Files to write

| File | Purpose |
|---|---|
| `src/biovector/data/sets.csv` | Per-set data (append rows) |
| `src/biovector/data/workouts.csv` | Per-workout summaries (append row) |
| `strength-states.json` | Updated next session + loads + states |

## Minimal workflow for logging a session

```
1. Determine next session label (e.g. B1, C1, A2) from strength-states.json "next_session"
2. Determine workout number: max(existing Number in sets.csv) + 1
3. Determine timestamp: datetime(year, month, day, hour, minute).timestamp()
4. For each set, compute fields (see formula sheet below) and append to sets.csv
5. Sum hardsets (h), Load, and phi across all sets → append one row to workouts.csv
6. Update strength-states.json:
     - Set "updated" to today's date
     - Set "next_session" to the following session label
     - Update load/state for each exercise that changed
7. git add -A && git commit -m "log <session> <date>" && git push
```

## Formulas

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
| Military Press | T21.0 | — | — |

Body weight (`BW`) — use current value from `weight.csv` or approximate to 85 kg if unknown.

Computed per set:

```
load     = round((Delta × weight + BW × kappa) × reps)
pred1RM  = round(epley(weight, reps))
pred1RL  = round(epley(weight × reps / reps, reps))   # same as pred1RM for r=1
Int      = pred1RL / est1RL   (1.0 if no est1RL)
h        = round(logistic(Int), 2)
phi      = round(load × h)
```

## sets.csv row format

```
Timestamp, Time, Number, Workout Name, Program, ID, Exercise Name, Weight, Reps,
User Weight, Pred1RL, 1RL, Pred1RM, 1RM, Int, h, Load, phi, Notes
```

## workouts.csv row format

```
Number, Timestamp, Date, Hardsets, Load, Hardload
```

Sum `h` (not `phi`) for Hardsets. Sum `Load` and `phi` for Load and Hardload.

## strength-states.json schema

```json
{
  "updated": "<YYYY-MM-DD>",
  "next_session": "<A1|B1|C1|A2|B2|C2|...>",
  "FS":  { "state": "<S0|S0p|D0|P0|P0p>", "load": <kg> },
  "SQ":  { "state": "<S0|S0p|D0|P0|P0p>", "load": <kg> },
  "BP":  { "state": "<S0|S0p|D0|P0|P0p>", "load": <kg> },
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
- `D0` — deload
- `P0` — power base
- `P0p` — power progressed

## What "logged" looks like

When a session is correctly logged:
- sets.csv has N new rows (one per set)
- workouts.csv has 1 new row
- strength-states.json has updated `next_session`, `updated`, and changed exercise states/loads
- git push is confirmed

If you are unsure about any value, leave `est1RM` and `est1RL` as `0` — this is what Matias does and the system handles it.

## Development workflow

When developing on biovector itself:

```bash
# Install in editable mode
uv tool install -e .

# Run commands with correct data path
BIOVECTOR_DATA_DIR=$PWD/src/biovector/data biovector viz
BIOVECTOR_DATA_DIR=$PWD/src/biovector/data biovector update
```

Or add to your shell profile:
```bash
export BIOVECTOR_DATA_DIR=$HOME/ghq/github.com/matias-ceau/biovector/src/biovector/data
```
