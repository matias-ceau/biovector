# CLAUDE.md — Biovector Project Instructions

## Project Overview

Biovector is a personal strength training tracker. The user logs sets (exercise, weight, reps) and the system computes standardised volume, intensity, and progression metrics using biomechanical coefficients.

## Repository Structure

```
biovector/
├── data/user/          # User workout data (JSON)
├── data/reference/     # Exercise definitions and programs
├── src/biovector/      # Core Python library
├── bridge/             # MCP server for LLM integration
├── context/            # LLM-targeted documentation
└── docs/               # Human documentation
```

## Key Files

- `src/biovector/core.py` — Main `Biovector` class: data loading, queries, metric calculation
- `src/biovector/workout.py` — `ExerciseInfo` and `WorkoutSession` classes
- `src/biovector/stats.py` — Statistical functions (1RM history, frequency, weekly volume)
- `src/biovector/display.py` — Text formatting for summaries
- `bridge/mcp_server.py` — MCP server entry point
- `bridge/tools.py` — Tool implementations called by MCP

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
bv.add_set("Squat", 100, 5)
history = bv.exercise_1rm_history("Squat")
```

## When Helping the User

1. **Logging workouts**: Use `add_set` tool. Always confirm exercise name exists with `list_exercises` if unsure.
2. **Reviewing progress**: Use `get_strength_overview` for a quick snapshot, `get_1rm_progression` for detailed tracking.
3. **Programming advice**: Reference `data/reference/exercises.json` for available exercises and their biomechanical properties.
4. **Metrics questions**: See `docs/metrics.md` for the mathematical foundations — Epley formula, standardised volume (ψ), hard-set function (h), volume index.

## Conventions

- Weights are always in **kg**
- Timestamps are Unix timestamps (seconds since epoch)
- Exercise names use title case: "Squat", "Deadlift", "Bench Press"
- Session names can be freeform: "Push Day", "5/3/1 Week 3", etc.
