# biovector

Workout tracking and biomechanical metrics library with MCP bridge for LLM integration.

Biovector stores minimal core data (timestamp, exercise, weight, reps) and derives all training metrics — 1RM estimates, standardised volume, intensity, and hard-set counts — on-the-fly using biomechanical coefficients.

## Architecture

```
biovector/
├── data/
│   ├── user/                  # Personal workout data (JSON)
│   │   ├── sets.json          # Core: timestamp, exercise, weight, reps
│   │   ├── sessions.json      # Auto-generated session groupings
│   │   └── bodyweight.json    # Bodyweight timeline
│   └── reference/             # Exercise definitions + program templates
│       ├── exercises.json     # 163 exercises with biomechanical coefficients
│       └── programs/          # YAML program templates (531, monolith)
├── src/biovector/             # Core Python library
│   ├── __init__.py            # Public API exports
│   ├── core.py                # Biovector class, metric functions
│   ├── workout.py             # Exercise + Workout classes (legacy)
│   ├── stats.py               # Statistical queries
│   └── display.py             # Text formatting
├── bridge/                    # MCP server for LLM agents
│   ├── __init__.py
│   ├── mcp_server.py          # Server entry point + tool/resource registration
│   └── tools.py               # Tool implementations
├── context/                   # LLM-targeted documentation
│   ├── AGENTS.md              # General agent context
│   ├── CLAUDE.md              # Claude-specific instructions
│   └── exercises_context.md   # Full exercise reference table
├── docs/                      # Human documentation
│   ├── metrics.md             # Mathematical foundations
│   └── analysis/              # Analysis outputs and feedback
├── reports/                   # Generated charts and summary reports
├── tests/                     # Pytest test suite
├── AGENT.md                   # Agent rules for session logging
├── strength-states.json       # Current training state + next session
└── pyproject.toml             # Package metadata (hatchling build)
```

## Installation

Requires Python ≥ 3.12.

```bash
# Clone the repository
git clone https://github.com/matias-ceau/biovector.git
cd biovector

# Install in editable mode (with uv)
uv tool install -e .

# Or with pip
pip install -e .
```

## Data Model

Core set data stores only essential fields — all derived metrics are computed on-the-fly:

| Stored | Derived |
|--------|---------|
| `timestamp` | 1RM — Epley formula |
| `exercise_name` | Load (ψ) — standardised volume |
| `weight` | Intensity — predicted vs. best 1RL |
| `reps` | Hard Set (h) — logistic weighting |
| `session_name?` | Volume (Φ) — hard-set weighted load |
| `notes?` | |

See [docs/metrics.md](docs/metrics.md) for the full mathematical foundations.

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

# Log a set
bv.add_set("Squat", 120, 5, session_name="Heavy Day")

# Query 1RM progression
history = bv.exercise_1rm_history("Squat")

# Compute all derived metrics for a set
metrics = bv.compute_set_metrics(bv.sets[-1])

# Look up exercises by name, short code, or ID
bv.get_exercise("sq")       # by short code
bv.get_exercise("S00")      # by ID
bv.get_exercise("Squat")    # by name

# List exercises with filtering
bv.list_exercises(category="Barbell")
bv.list_exercises(search="press")
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `add_set` | Log a new exercise set (name, weight, reps) |
| `get_workout_history` | Retrieve sets by exercise/date range |
| `get_exercise_stats` | Statistics and progression for an exercise |
| `get_1rm_progression` | Track estimated 1RM over time |
| `get_recent_sessions` | List recent workout sessions |
| `get_session_detail` | Detailed breakdown of a specific session |
| `list_exercises` | Search/filter the exercise database |
| `get_weekly_summary` | Weekly training volume summary |
| `get_strength_overview` | Best recent 1RM per exercise |

### MCP Resources

| Resource URI | Description |
|--------------|-------------|
| `biovector://exercises` | All exercise definitions with coefficients |
| `biovector://sessions/recent` | Last 10 workout sessions |

## Development

```bash
# Install in editable mode
uv tool install -e .

# Run tests
python -m pytest tests/

# Run with local data path
BIOVECTOR_DATA_DIR=$PWD/data biovector viz
```

## License

GPL-3.0 — see [LICENSE](LICENSE) for details.
