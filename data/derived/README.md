# Derived Data

Pre-computed metrics and aggregates generated from raw training sets. This directory is a **cache layer** — every file here can be deleted and regenerated from [`data/user/sets.json`](../user/sets.json).

The pipeline processes ~11,500 raw sets (2018–2026) through five passes: basic enrichment, smoothed 1RM estimation, intensity/hardness scoring, session aggregation, and per-exercise timeseries extraction.

For the full architecture and design rationale, see [DESIGN.md](DESIGN.md).

---

## How to Run

```bash
BIOVECTOR_DATA_DIR=$PWD/data python -m biovector.derived -v
```

| Option | Description |
|--------|-------------|
| `--data-dir PATH` | Override the data directory (default: auto-detected from package location) |
| `-v` / `--verbose` | Print detailed progress for each pipeline pass |

The `BIOVECTOR_DATA_DIR` environment variable is the standard way to point biovector at your data directory. If set, it takes precedence over the default path. The `--data-dir` flag overrides both.

Typical output:

```
Biovector Derived Data Pipeline v1.0.0
Data directory: /path/to/data

Pipeline complete: 11527 sets, 624 sessions, 154 exercise timeseries
Output: /path/to/data/derived
```

---

## Output Files

### `enriched_sets.json`

Every raw set with all derived metrics attached. This is the primary output — all other files are derived from it.

**Structure**: `{ "version": "1.0.0", "generated_at": "...", "sets": [...] }`

#### Enriched set record schema

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | float | Original unix timestamp |
| `exercise_name` | string | Exercise name as recorded |
| `weight` | float | Weight in kg |
| `reps` | int | Repetitions performed |
| `session_name` | string | Session label (e.g. `"A1"`) |
| `notes` | string | Free text notes |
| `date` | string | ISO date derived from timestamp |
| `exercise_id` | string \| null | ID from exercises.json (e.g. `"S00"`) |
| `exercise_tier` | string | `major` / `secondary` / `accessory` / `bodyweight` / `other` |
| `has_params` | bool | Whether Δ/κ parameters exist for this exercise |
| `bw_at_time` | float | Interpolated bodyweight at timestamp (kg) |
| `delta` (Δ) | float \| null | Distance coefficient |
| `kappa` (κ) | float \| null | Body coefficient (ρ × θ) |
| `load` | float | Biovector standardized load (see [Metric Glossary](#metric-glossary)) |
| `pred_1rm` | float | Predicted 1RM via Epley formula |
| `pred_1rl` | float | Predicted 1RM in load units |
| `smoothed_1rm` | float \| null | EWRM-smoothed strength estimate |
| `smoothed_1rl` | float \| null | EWRM-smoothed strength estimate in load units |
| `smoothed_confidence` | string \| null | `"low"` (< 3 sessions) or `"high"` (≥ 3 sessions) |
| `intensity` | float \| null | Relative intensity: `pred_1rl / smoothed_1rl` |
| `h` | float \| null | Hardness (logistic transform of intensity, 0–1.05) |
| `phi` (Φ) | float \| null | Hard load: `load × h` |
| `is_hard_set` | bool | `true` when `h ≥ 0.5` |
| `session_id` | string \| null | Matched session ID from sessions.json |

#### Example record

```json
{
  "timestamp": 1518444054,
  "exercise_name": "Squat",
  "weight": 100.0,
  "reps": 7,
  "session_name": "1RM",
  "notes": "",
  "date": "2018-02-12",
  "exercise_id": "S00",
  "exercise_tier": "major",
  "has_params": true,
  "bw_at_time": 93.1,
  "delta": 0.65,
  "kappa": 0.65,
  "load": 878.6,
  "pred_1rm": 123.3,
  "pred_1rl": 154.8,
  "smoothed_1rm": 123.3,
  "smoothed_1rl": 154.8,
  "smoothed_confidence": "low",
  "intensity": 1.0,
  "h": 1.05,
  "phi": 922.5,
  "is_hard_set": true,
  "session_id": "session_20180212_150054"
}
```

---

### `sessions_enriched.json`

Per-session aggregates with exercise breakdowns, session totals, and intensity distribution.

**Structure**: `{ "version": "1.0.0", "generated_at": "...", "sessions": [...] }`

#### Session record schema

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Session ID (e.g. `"session_20180212_150054"`) |
| `name` | string | Session label |
| `date` | string | ISO date |
| `start_timestamp` | float | Session start (unix) |
| `end_timestamp` | float | Session end (unix) |
| `duration_minutes` | int | Duration in minutes |
| `bw_at_time` | float | Bodyweight at session start (kg) |
| `total_sets` | int | Total sets in session |
| `exercise_count` | int | Distinct exercises performed |
| `exercises_performed` | string[] | List of exercise names |
| `per_exercise` | object | Per-exercise breakdown (see below) |
| `totals` | object | Session-level totals (see below) |
| `intensity_distribution` | object | Set counts by effort category |

**`per_exercise`** — keyed by exercise name:

| Field | Type | Description |
|-------|------|-------------|
| `sets` | int | Number of sets |
| `total_reps` | int | Sum of reps |
| `total_load` | float | Sum of per-set load (Ψ) |
| `total_phi` | float | Sum of per-set phi (Φ) |
| `best_pred_1rm` | float | Max predicted 1RM in session |
| `hard_sets` | float | Sum of h values (fractional hard set count) |
| `avg_intensity` | float \| null | Mean intensity across sets |

**`totals`**:

| Field | Type | Description |
|-------|------|-------------|
| `total_load` | float | Ψ — sum of all set loads |
| `total_hard_load` | float | Φ — sum of all phi |
| `total_hard_sets` | float | N — sum of all h |
| `total_hard_sets_major` | float | N for major/secondary exercises only |
| `volume_index` | float | `Ψ × BW^(-2/3)` — bodyweight-normalized volume |
| `hard_volume_index` | float | `Φ × BW^(-2/3)` — bodyweight-normalized hard load |

**`intensity_distribution`**:

| Category | h range | Meaning |
|----------|---------|---------|
| `warmup_sets` | h < 0.1 | Warm-up / trivial |
| `moderate_sets` | 0.1 ≤ h < 0.5 | Moderate effort |
| `hard_sets` | 0.5 ≤ h < 1.02 | Hard working sets |
| `near_max_sets` | h ≥ 1.02 | Near-maximal effort |

#### Example record (abbreviated)

```json
{
  "id": "session_20180212_150054",
  "name": "1RM",
  "date": "2018-02-12",
  "start_timestamp": 1518444054,
  "end_timestamp": 1518444174,
  "duration_minutes": 2,
  "bw_at_time": 93.1,
  "total_sets": 3,
  "exercise_count": 3,
  "exercises_performed": ["Squat", "Deadlift", "Bench Press"],
  "per_exercise": {
    "Squat": {
      "sets": 1, "total_reps": 7, "total_load": 878.6,
      "total_phi": 922.5, "best_pred_1rm": 123.3,
      "hard_sets": 1.1, "avg_intensity": 1.0
    }
  },
  "totals": {
    "total_load": 1942.6,
    "total_hard_load": 2039.8,
    "total_hard_sets": 3.2,
    "total_hard_sets_major": 3.2,
    "volume_index": 94.6,
    "hard_volume_index": 99.3
  },
  "intensity_distribution": {
    "warmup_sets": 0, "moderate_sets": 0,
    "hard_sets": 0, "near_max_sets": 3
  }
}
```

---

### `exercise_classification.json`

Tier assignments for every exercise found in the raw data.

**Structure**: `{ "version": "1.0.0", "generated_at": "...", "classifications": {...} }`

#### Classification record schema

| Field | Type | Description |
|-------|------|-------------|
| `id` | string \| null | Exercise ID from exercises.json |
| `tier` | string | `major` / `secondary` / `accessory` / `bodyweight` / `other` |
| `has_params` | bool | Whether Δ/κ parameters exist |
| `total_sets_in_data` | int | Total sets recorded for this exercise |
| `total_sessions` | int | Distinct sessions containing this exercise |

#### Example

```json
{
  "Squat": {
    "id": "S00",
    "tier": "major",
    "has_params": true,
    "total_sets_in_data": 772,
    "total_sessions": 142
  },
  "Deadlift": {
    "id": "H00.0",
    "tier": "major",
    "has_params": true,
    "total_sets_in_data": 630,
    "total_sessions": 114
  }
}
```

---

### `exercises/<id>_<name>.json`

One file per exercise (with ≥ 5 sets) containing session-level timeseries. File naming: `{exercise_id}_{snake_case_name}.json` (e.g. `S00_squat.json`, `H00.0_deadlift.json`).

#### Exercise timeseries schema

**Top-level metadata**:

| Field | Type | Description |
|-------|------|-------------|
| `exercise_name` | string | Exercise name |
| `exercise_id` | string \| null | Exercise ID |
| `exercise_tier` | string | Tier classification |
| `has_params` | bool | Whether Δ/κ parameters exist |
| `total_sets` | int | Total sets across all sessions |
| `total_sessions` | int | Number of sessions in timeseries |
| `date_range` | object | `{ "first": "YYYY-MM-DD", "last": "YYYY-MM-DD" }` |
| `current_smoothed_1rm` | float | Latest smoothed 1RM estimate |
| `current_smoothed_1rl` | float | Latest smoothed 1RL estimate |
| `all_time_best_pred_1rm` | float | Highest raw predicted 1RM ever |
| `session_series` | array | Per-session snapshots (see below) |

**`session_series` entry**:

| Field | Type | Description |
|-------|------|-------------|
| `date` | string | ISO date |
| `session_id` | string | Session ID |
| `sets` | int | Sets of this exercise in session |
| `best_weight` | float | Heaviest weight used |
| `best_reps_at_best_weight` | int | Reps at that weight |
| `best_pred_1rm` | float | Highest predicted 1RM in session |
| `smoothed_1rm` | float | Smoothed 1RM after this session |
| `smoothed_1rl` | float | Smoothed 1RL after this session |
| `total_load` | float | Sum of load for this exercise |
| `total_phi` | float | Sum of phi for this exercise |
| `hard_sets` | float | Sum of h values |
| `avg_intensity` | float \| null | Mean intensity |

#### Example (Squat header + first entry)

```json
{
  "exercise_name": "Squat",
  "exercise_id": "S00",
  "exercise_tier": "major",
  "has_params": true,
  "total_sets": 772,
  "total_sessions": 145,
  "date_range": { "first": "2018-02-12", "last": "2026-04-07" },
  "current_smoothed_1rm": 120.0,
  "current_smoothed_1rl": 155.2,
  "all_time_best_pred_1rm": 162.1,
  "session_series": [
    {
      "date": "2018-02-12",
      "session_id": "session_20180212_150054",
      "sets": 1,
      "best_weight": 100.0,
      "best_reps_at_best_weight": 7,
      "best_pred_1rm": 123.3,
      "smoothed_1rm": 123.3,
      "smoothed_1rl": 154.8,
      "total_load": 878.6,
      "total_phi": 922.5,
      "hard_sets": 1.1,
      "avg_intensity": 1.0
    }
  ]
}
```

---

### `metadata.json`

Pipeline run information. Used to check whether derived data is current.

```json
{
  "generated_at": "2026-04-11T17:25:13Z",
  "pipeline_version": "1.0.0",
  "total_sets_processed": 11527,
  "total_sessions": 624,
  "total_exercises": 191,
  "exercises_with_timeseries": 154,
  "last_raw_set_timestamp": 1775601908,
  "smoothing_half_life_weeks": 52,
  "smoothing_floor_ratio": 0.75,
  "min_sessions_for_confidence": 3
}
```

---

## Key Algorithms

### Smoothed 1RM — Exponentially Weighted Running Maximum (EWRM) with Decay-to-Floor

**Problem**: Using a simple all-time max predicted 1RM as the strength baseline has three issues:

1. **Light sessions don't mean you got weaker.** A 100kg×5 set (pred_1rm = 117) after a 140kg×3 set (pred_1rm = 154) shouldn't reset the baseline to 117.
2. **Old PRs should eventually decay.** A PR from 2 years ago shouldn't keep intensity artificially low forever.
3. **New exercises have no history.** The first session needs a usable baseline immediately.

**How it works**: For each exercise, sets are processed chronologically. The algorithm uses a **decay-to-floor** model — strength estimates decay toward a floor (75% of the PR) rather than toward zero, reflecting the physiological reality that trained strength persists for years:

For each historical set at time `t_i` with `pred_1rm_i`:
```
age = current_time - t_i
decay = 2^(-(age) / half_life)
effective_1rm = pred_1rm_i × (floor_ratio + (1 - floor_ratio) × decay)
smoothed_1rm = max over all historical sets of effective_1rm
```

Key parameters:
- **Half-life**: 52 weeks (1 year) — after 1 year without training, the decaying portion halves
- **Floor ratio**: 0.75 — strength never estimated below 75% of a historical PR

This means the smoothed 1RM:
- **Rises instantly** when you set a new PR
- **Decays gradually** toward 75% of the PR (not toward zero)
- **Never drops from a single light session** — only from the passage of time
- **Never drops below 75% of any historical PR** — the floor reflects retained strength

**Decay examples** (starting from a 154 kg PR):

| Time since PR | Decay factor | Effective % | Smoothed 1RM |
|---------------|-------------|-------------|-------------|
| 0 weeks | 1.000 | 100.0% | 154.0 kg |
| 13 weeks (3mo) | 0.842 | 96.1% | 147.9 kg |
| 26 weeks (6mo) | 0.707 | 92.7% | 142.7 kg |
| 52 weeks (1yr) | 0.500 | 87.5% | 134.8 kg |
| 104 weeks (2yr) | 0.250 | 81.3% | 125.1 kg |
| 156 weeks (3yr) | 0.125 | 78.1% | 120.3 kg |
| ∞ | 0.000 | 75.0% | 115.5 kg |

**Confidence levels**:

| Level | Condition | Meaning |
|-------|-----------|---------|
| `null` | No valid sets | Impossible in practice |
| `"low"` | < 3 sessions | Baseline is thin — metrics are computed but not yet reliable |
| `"high"` | ≥ 3 sessions | Stable baseline for intensity calculations |

**Accessories and bodyweight exercises**: The algorithm is self-referential — each exercise is compared only against its own history. For exercises where near-max testing never happens (e.g. Kroc Rows), the smoothed 1RM still reflects the running max Epley estimate, and intensity is meaningful relative to that exercise's own range.

Implementation: [`DerivedDataPipeline.pass2_smoothed_1rm()`](../../src/biovector/derived.py:383)

---

## Exercise Tiers

All exercises are classified into five tiers, evaluated in priority order:

| Tier | Description | Examples | Count |
|------|-------------|----------|-------|
| **major** | The 6 programmed barbell lifts + Chin Up + Dips. Tracked in `strength-states.json` with specific Δ/κ parameters. | Squat, Bench Press, Deadlift, Front Squat, Military Press, Power Clean, Chin Up, Dips | 8 |
| **secondary** | Other barbell/kettlebell compound movements defined in `exercises.json`. | Bent Over Row, Romanian Deadlift, Push Press, Close Grip Bench Press | ~30 |
| **accessory** | Dumbbell, cable, machine, and isolation work. | Kroc Row, Lateral Raise, Tricep Pushdown, Ab Wheel | ~50 |
| **bodyweight** | Exercises typed as `"Bodyweight"` in exercises.json. | Push Up, Bodyweight Squat, Australian Pull Up | ~15 |
| **other** | Exercises not found in exercises.json (imports, typos, etc.). No Δ/κ parameters — `load` falls back to `weight × reps`. | varies | varies |

The 8 major exercises:

| Exercise | ID | Abbreviation |
|----------|----|-------------|
| Squat | S00 | SQ |
| Front Squat | S10 | FS |
| Bench Press | P01.00 | BP |
| Deadlift | H00.0 | DL |
| Military Press | P10.0 | MP |
| Power Clean | T20.1 | PC |
| Chin Up | T00 | CU |
| Dips | P20 | DP |

Classification logic: [`DerivedDataPipeline.classify_exercises()`](../../src/biovector/derived.py:215)

---

## Metric Glossary

| Metric | Symbol | Formula | Description |
|--------|--------|---------|-------------|
| load | Ψ | `(Δ × w + BW × κ) × reps` | Biovector standardized load — accounts for exercise biomechanics and bodyweight contribution. Falls back to `w × reps` when no parameters exist. |
| pred_1rm | — | `w × (1 + r/30)` | Predicted 1RM via Epley formula |
| pred_1rl | — | `epley(load/reps, reps)` | Predicted 1RM in load units. `0` if no Δ/κ parameters. |
| smoothed_1rm | — | EWRM algorithm | Smoothed current strength estimate (52-week half-life, 75% floor decay-to-floor model) |
| smoothed_1rl | — | EWRM algorithm | Smoothed strength in load units (same decay-to-floor model) |
| intensity | I | `pred_1rl / smoothed_1rl` | Relative intensity (0–1+). Values > 1.0 indicate a new PR. |
| h (hardness) | h | `1.05 / (1 + e^(-40(I − 0.75)))` | Logistic transform of intensity. Range 0–1.05. Saturates near 1.05 for maximal efforts. |
| phi | Φ | `load × h` | Hard load — effective volume weighted by effort. Low for warm-ups, high for hard sets. |
| is_hard_set | — | `h ≥ 0.5` | Boolean flag: whether this set counts as a "hard" working set |
| volume_index | — | `Ψ × BW^(-2/3)` | Session total load normalized by bodyweight |
| hard_volume_index | — | `Φ × BW^(-2/3)` | Session hard load normalized by bodyweight |

---

## Regeneration

All files in `data/derived/` are **cache artifacts**. They can be safely deleted and regenerated at any time:

```bash
rm -rf data/derived/exercises/ data/derived/*.json
BIOVECTOR_DATA_DIR=$PWD/data python -m biovector.derived -v
```

The source of truth is always [`data/user/sets.json`](../user/sets.json). The pipeline performs a full rebuild every run (no incremental mode) because the smoothed 1RM algorithm is path-dependent — changing any historical set affects all subsequent calculations. With ~11,500 sets, a full rebuild takes under 2 seconds.

These files should be `.gitignore`'d — they contain no information that cannot be recomputed from raw data.
