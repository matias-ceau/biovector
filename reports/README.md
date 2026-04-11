# Biovector Reports

Training reports with charts, exercise tier filtering, and automated generation.

## Quick Start

```bash
# Generate a standard report (main lifts only)
python reports/generate_report.py --type standard -o reports/latest_report.md

# Detailed report (main + supporting exercises)
python reports/generate_report.py --type detailed -o reports/latest_report.md

# Full report with accessories in appendix
python reports/generate_report.py --type full --since 2026-01-01 -o reports/latest_report.md
```

## Files

| File | Purpose |
|------|---------|
| [`REPORT_INSTRUCTIONS.md`](REPORT_INSTRUCTIONS.md) | Full instructions for LLMs generating reports (with or without code) |
| [`exercise_tiers.json`](exercise_tiers.json) | Exercise classification: tier 1 (program lifts), tier 2 (supporting), tier 3 (accessories) |
| [`generate_report.py`](generate_report.py) | CLI script — generates markdown + 5 PNG charts |
| [`latest_report.md`](latest_report.md) | Sample generated report |

## Charts Generated

| Chart | Description |
|-------|-------------|
| `chart_main_lifts.png` | Running best e1RM progression for main lifts |
| `chart_volume.png` | Weekly standardised load with session count overlay |
| `chart_balance.png` | Movement balance donuts (by load and by sets) |
| `chart_sessions.png` | Per-session load breakdown by movement category |
| `chart_bw_exercises.png` | Chin Up / Dips rep totals over time |

## Exercise Tier System

| Tier | Exercises | In Reports? |
|------|-----------|-------------|
| **1** | SQ, FS, BP, DL, MP, PC, Chin Up, Dips | ✅ Always |
| **2** | RDL, Row, Push Press, Pull Up, Snatch, etc. | ✅ Detailed/Full |
| **3** | Grip, Core, Curls, Calf, Neck | ❌ Excluded from aggregations |

> ⚠️ Tier 3 exercises (especially grip work) produce inflated load values and are **never** included in volume totals.
