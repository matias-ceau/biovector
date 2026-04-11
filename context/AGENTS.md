# Biovector — Agent Context

## What is Biovector?

Biovector is a personal workout tracking system that records exercise sets and computes advanced training metrics. It stores minimal core data (timestamp, exercise, weight, reps) and derives everything else on-the-fly.

## Data Model

### Core Data (stored in `data/user/sets.json`)
Each set record contains only:
- **timestamp** — Unix timestamp of when the set was performed
- **exercise_name** — Full exercise name (e.g. "Squat", "Deadlift")
- **weight** — Weight in kg (0 for bodyweight exercises)
- **reps** — Number of repetitions
- **session_name** — Optional workout session name
- **notes** — Optional notes

### Derived Metrics (computed, not stored)
- **1RM** — Estimated one-rep max using Epley formula: `weight × (1 + reps/30)`
- **Load (ψ)** — Standardised volume: `reps × (weight × Δ + bodyweight × ρ × θ)` where Δ, ρ, θ are exercise-specific coefficients
- **Hard Set (h)** — Logistic function: `1.05 / (1 + e^(-40×(intensity - 0.75)))` — returns ~1 for hard sets, ~0 for easy sets
- **Intensity** — `predicted_1RL / best_1RL` for each exercise

### Exercise Reference Data (`data/reference/exercises.json`)
Each exercise has:
- **id** — Alphanumeric code (e.g. S00 = Squat, H00.0 = Deadlift)
- **name** — Full name
- **short** — Short alias
- **delta** — Distance traveled by the weight (metres)
- **rho** — Proportion of bodyweight engaged
- **theta** — Distance traveled by body's center of mass
- **type** — Equipment type (Barbell, Bodyweight, Dumbell, Kettlebell, etc.)

### Exercise ID Coding System
- **S** = Squat variants
- **H** = Hip hinge (deadlift, RDL, etc.)
- **P** = Push (bench, overhead press, push-up, dips)
- **T** = Pull (chin-up, rows, cleans)
- **C** = Core (abs, back extensions, neck)
- **G** = Grip (carries, wrist work)
- **L** = Legs (isolation: leg curl, calf raise)
- **U** = Upper arms (curls, triceps)
- **X** = Complex/Olympic (snatch, clean & jerk, burpee)

## Available MCP Tools

| Tool | Purpose |
|------|---------|
| `add_set` | Log a new exercise set |
| `get_workout_history` | Retrieve sets, filtered by exercise/date |
| `get_exercise_stats` | Statistics for a specific exercise |
| `get_1rm_progression` | Track 1RM over time |
| `get_recent_sessions` | List recent workout sessions |
| `get_session_detail` | Detailed breakdown of a session |
| `list_exercises` | Search/filter exercise database |
| `get_weekly_summary` | Weekly volume summary |
| `get_strength_overview` | Current strength levels across exercises |

## Common Tasks

### Logging a workout
1. Use `add_set` for each set performed
2. Include `session_name` to group sets into a session
3. The system auto-persists to `data/user/sets.json`

### Reviewing progress  
1. `get_strength_overview` for current maximums
2. `get_1rm_progression` for a specific lift
3. `get_weekly_summary` for volume trends

### Finding exercises
1. `list_exercises` with `search` parameter
2. Or filter by `category` (Barbell, Bodyweight, etc.)
