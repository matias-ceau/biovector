# Feedback on Workout Metrics Heuristics

*Analysis of docs/metrics.md methodology*

## Summary

Your metrics system demonstrates sophisticated biomechanical thinking with several innovative elements. The load-based volume calculation and logistic intensity weighting are particularly well-designed.

## Strengths

### 1. Biomechanically-Informed Load Calculation

The use of `ψ = r(wΔ + mκ)` addresses a real problem in training volume tracking:

- **Δ (distance coefficient)** accounts for range of motion differences
- **κ (body coefficient)** incorporates bodyweight contribution
- This makes squat and leg curl volumes actually comparable

The separation of `κ = pδ` into proportion moved and distance traveled shows careful attention to biomechanics.

### 2. Logistic Intensity Function

Your hard set definition using:

```
f(x) = 1.05 / (1 + e^(-40(x - 0.75)))
```

is elegant because:
- Smooth transition avoids arbitrary cutoffs
- 1.05 ceiling allows for PR attempts to count slightly more
- 75% → 0.5 weighting aligns with moderate effort perception

### 3. Metabolic Scaling

Using `m^(-2/3)` for volume indices follows established allometric scaling laws from physiology literature.

## Considerations & Suggestions

### 1. 1RM Formula Selection

**Current**: Epley's formula (`1RM = w(1 + r/30)`)

**Consideration**: Epley works best for high-rep sets (8-12+). Your data shows substantial low-rep work (singles, doubles, triples). Consider:

- **Lombardi**: `1RM = w × r^0.10` (better for low reps)
- **Brzycki**: `1RM = w / (1.0278 - 0.0278r)` (widely validated)
- Or use a blend based on rep range

### 2. Π_max Window Definition

Your Π_max "can be set on a time period" but doesn't specify:

- **30-day window**: Responsive to recent training, volatile
- **90-day window**: Smoother, misses detraining
- **All-time PR**: Stable but doesn't reflect current capacity

**Suggestion**: Define a default (90-day rolling) with option to override.

### 3. Intensity Threshold Calibration

Your logistic function puts 75% at ε ≈ 0.5:

| Intensity | ε |
|-----------|---|
| 75% | 0.5 |
| 80-85% | ~1.0 |
| 90%+ | ~1.05 |

Verify this matches your RPE perception:
- RPE 7 (3 reps in reserve) ≈ 75% for most
- If 75% feels like RPE 6 to you, the threshold may be slightly off

### 4. Missing: Fatigue/Recovery Modeling

Your metrics capture session load well but lack between-session tracking:

**Current**: Per-workout Ψ, Φ, N

**Missing**: 
- Chronic training load (CTL) - 4-week rolling average
- Acute training load (ATL) - 7-day rolling average
- Training stress balance (TSB) - CTL - ATL

**Suggestion**: Add a simple TSB model on top of Φ:
```
CTL_t = 0.9 × CTL_{t-1} + 0.1 × Φ_t
ATL_t = 0.7 × ATL_{t-1} + 0.3 × Φ_t
TSB = CTL - ATL
```

### 5. Decline Detection

Your data shows clear pressing declines (Bench -19%, Military Press -12%). Consider automated alerts when:

- Estimated 1RM drops >10% over 4+ weeks
- Hard set volume (Φ) drops >30% from 4-week average
- Intensity distribution shifts toward <75% consistently

### 6. Exercise-Specific Δ/κ Calibration

Your `data/reference/exercises.json` contains measured values ("measured by hand", "measured with picture"). Consider:

- Documenting your measurement protocol
- Adding uncertainty estimates (Δ ± error)
- Validating a few against motion capture or video analysis

## Minor Issues

1. **Typo in metrics.md**: "adressed" → "addressed" (line 16)
2. **Typo**: "adress" → "address" (line 5)
3. **Pi symbol**: `Π` and `Π_max` are clear, but consider using `Π̂` (predicted) to distinguish from true 1RM

## Overall Assessment

| Aspect | Rating |
|--------|--------|
| Theoretical foundation | Excellent |
| Biomechanical detail | Excellent |
| Practical implementation | Good |
| Fatigue/recovery tracking | Missing |
| Trend detection | Could improve |

Your system is well-suited for:
- Long-term volume tracking
- Exercise load comparison
- Intensity distribution analysis

Consider adding for completeness:
- Recovery/fatigue metrics
- Automated trend alerts
- Confidence intervals on 1RM estimates
