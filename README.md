# biovector

Workout tracking and biomechanical metrics library with MCP bridge for LLM integration.

## Architecture

```
biovector/
├── data/
│   ├── user/               # Personal workout data (JSON)
│   │   ├── sets.json       # Core: timestamp, exercise, weight, reps
│   │   ├── sessions.json   # Auto-generated session groupings
│   │   └── bodyweight.json # Bodyweight timeline
│   └── reference/          # Exercise definitions + program templates
│       ├── exercises.json  # 163 exercises with biomechanical coefficients
│       └── programs/       # YAML program templates
├── src/biovector/          # Core Python library
│   ├── core.py             # Biovector class, metric functions
│   ├── workout.py          # ExerciseInfo, WorkoutSession
│   ├── stats.py            # Statistical queries
│   └── display.py          # Text formatting
├── bridge/                 # MCP server for LLM agents
│   ├── mcp_server.py       # Server entry point
│   └── tools.py            # Tool implementations
├── context/                # LLM-targeted documentation
│   ├── AGENTS.md           # General agent context
│   ├── CLAUDE.md           # Claude-specific instructions
│   └── exercises_context.md
└── docs/                   # Human documentation
    └── metrics.md          # Mathematical foundations
```

## Data Model

Core set data stores only essential fields — all derived metrics are computed on-the-fly:

| Stored | Derived |
|--------|---------|
| timestamp | 1RM (Epley) |
| exercise_name | Load (ψ) |
| weight | Intensity |
| reps | Hard Set (h) |
| session_name? | Volume (Φ) |
| notes? | |

## Usage

### As MCP Server

Add to your MCP client config:

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

### Programmatic

```python
from biovector.core import Biovector

bv = Biovector()
bv.add_set("Squat", 120, 5, session_name="Heavy Day")
history = bv.exercise_1rm_history("Squat")
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `add_set` | Log a new exercise set |
| `get_workout_history` | Retrieve sets by exercise/date |
| `get_exercise_stats` | Exercise statistics |
| `get_1rm_progression` | 1RM over time |
| `get_recent_sessions` | Recent workout sessions |
| `list_exercises` | Search exercise database |
| `get_weekly_summary` | Weekly volume trends |
| `get_strength_overview` | Current strength levels |
