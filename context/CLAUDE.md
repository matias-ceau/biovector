# CLAUDE.md — Biovector Project Instructions

## Project Overview

Biovector is a personal strength training tracker. The user logs sets (exercise, weight, reps) and the system computes standardised volume, intensity, and progression metrics using biomechanical coefficients. All derived metrics are computed on-the-fly from minimal stored data.

## Repository Structure

```
biovector/
├── data/
│   ├── user/                  # Personal workout data (JSON)
│   │   ├── sets.json          # Core: timestamp, exercise, weight, reps
│   │   ├── sessions.json      # Auto-generated session groupings
│   │   └── bodyweight.json    # Bodyweight timeline
│   └── reference/             # Exercise definitions + program templates
│       ├── exercises.json     # 163 exercises with biomechanical coefficients
│       └── programs/          # YAML program templates
├── src/biovector/             # Core Python library
├── bridge/                    # MCP server for LLM integration
├── context/                   # LLM-targeted documentation
├── docs/                      # Human documentation + analysis
├── reports/                   # Generated charts and summaries
├── tests/                     # Pytest test suite
├── AGENT.md                   # Agent rules for session logging
└── strength-states.json       # Current training state + next session
```

## Key Files

- `src/biovector/core.py` — Main `Biovector` class: lazy-loaded data, queries, metric computation
- `src/biovector/workout.py` — Legacy `Exercise`/`Workout` classes (pandas-based, pre-reorganisation)
- `src/biovector/stats.py` — Statistical functions (1RM history, frequency, weekly volume)
- `src/biovector/display.py` — Text formatting for session and exercise summaries
- `bridge/mcp_server.py` — MCP server entry point (tool + resource registration)
- `bridge/tools.py` — Tool implementations called by MCP
- `AGENT.md` — **Read this first when logging a session** — defines the data format and workflow
- `strength-states.json` — Current training state: next session label, per-exercise state/load

## How to Use

### As an MCP Server
```json
{
  "mcpServers": {
    "biovector": {
      "command": "python",
      "args": ["-m", "bridge.mcp_server"],
      "cwd": "/path/to/biovector"
    }
  }
}
```

### Programmatically
```python
from biovector.core import Biovector

bv = Biovector()
bv.add_set("Squat", 100, 5, session_name="A1")
history = bv.exercise_1rm_history("Squat")
metrics = bv.compute_set_metrics(bv.sets[-1])
```

## When Helping the User

1. **Logging workouts**: Read `AGENT.md` for the full workflow. Use `add_set` tool. Always confirm exercise name exists with `list_exercises` if unsure.
2. **Reviewing progress**: Use `get_strength_overview` for a quick snapshot, `get_1rm_progression` for detailed tracking per exercise.
3. **Programming advice**: Reference `data/reference/exercises.json` for available exercises and their biomechanical properties.
4. **Metrics questions**: See `docs/metrics.md` for the mathematical foundations — Epley formula, standardised volume (ψ), hard-set function (h), volume index.
5. **Session logging**: After logging, always update `strength-states.json` and run `git add -A && git commit && git push`.

## Conventions

- Weights are always in **kg**
- Timestamps are Unix timestamps (seconds since epoch)
- Exercise names use title case: "Squat", "Deadlift", "Bench Press"
- Session names follow a pattern: "A1", "B1", "C1", "A2", etc. (from `strength-states.json`)
- All derived metrics (1RM, load, intensity, h, phi) are **not stored** — computed from core fields
- The `data/user/sets.json` file stores only: `timestamp`, `exercise_name`, `weight`, `reps`, and optionally `session_name`, `notes`
