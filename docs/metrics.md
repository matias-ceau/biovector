# Workout Metrics System

Mathematical foundations for the biovector training metrics.

---

## 1. Standardised Volume (Ψ)

Volume ($V$) is traditionally calculated by multiplying the number of sets ($s$) by reps ($r$) and weight ($w$), but this leads to uninformative data for two main reasons:

1. **Non-comparable**: Volume of different exercises cannot be meaningfully compared or summed.
2. **Inflatible**: Volume can be artificially inflated by high-rep, low-intensity sets such as warm-ups.

### Per-set load (ψ)

To address (1), the **load** ($\psi$), which accounts for both the type of exercise (range of motion) and the lifter (bodyweight), is used instead of raw volume:

$$\psi = r(w\Delta + m\kappa)$$

| Symbol | Definition |
|--------|-----------|
| $\Delta$ | Distance traveled by the weight (measured via video/tape) |
| $m$ | Current bodyweight |
| $\kappa = \rho\theta$ | **Body coefficient** — proportion $\rho$ of bodyweight being moved × distance $\theta$ traveled by the body's centre of mass |
| $r$ | Number of reps (or time/distance for some exercises, with coefficients adjusted accordingly) |

### Workout total (Ψ)

The sum over all sets in a workout is the **standardised volume** ($\Psi$), expressed in kg·m:

$$\Psi = \sum_{i = 1}^n{\psi_i} = \sum_{i=1}^n{r_i(w_i\Delta_j + m\kappa_j)}$$

where $\Delta_j$ and $\kappa_j$ are constants for each exercise $j$. The resulting value has a similar order of magnitude to traditional volume for compound exercises.

---

## 2. Number of Hard Sets (N)

To address point (2) — filtering out low-intensity work — a **hard set** metric is defined.

A "hard set" [has been defined](https://www.strongerbyscience.com/the-new-approach-to-training-volume/) as any set performed above 80–85% intensity. Rather than a binary cutoff, a **logistic function** $f$ provides a smooth transition:

$$f(x) = \frac{1.05}{1 + e^{-40(x - 0.75)}}$$

| Intensity | $f(x)$ ≈ | Interpretation |
|-----------|-----------|----------------|
| < 60% | ≈ 0 | Warm-up / easy |
| 75% | ≈ 0.5 | Moderate effort |
| 80–85% | ≈ 1.0 | Hard set |
| > 90% | ≈ 1.05 | Near-maximal |

### Predicted 1RM and 1RL

1RM is estimated using **Epley's formula** (better for higher repetitions):

$$1RM = w\left(1 + \frac{r}{30}\right)$$

Since 1RM can only be calculated for weighted exercises, $\Pi$ — the **predicted 1RL** — uses load-based values instead of raw weight:

$$\Pi = \frac{\psi}{r}\left(1 + \frac{r}{30}\right) = \frac{\psi}{r} + \frac{\psi}{30}$$

### Hard-set count

With $\Pi_{max}$ as the maximum predicted 1RL (over a configurable time period, e.g. rolling 90 days), the intensity-related weight $\epsilon$ of each set is:

$$\epsilon_i = f\!\left(\frac{\Pi_i}{\Pi_{max}}\right)$$

The total hard-set count across $n$ sets in a workout:

$$N = \sum_{i=1}^{n}{\epsilon_i}$$

For hard sets $\epsilon \approx 1$, for moderate sets $\epsilon \approx 0.5$, and for warm-ups $\epsilon \approx 0$.

---

## 3. Hard-Set Volume (Φ)

The per-set load can now be weighted by intensity, producing **meaningful load** $\phi$ that discounts easy sets:

$$\phi_i = \psi_i \cdot \epsilon_i$$

The workout total — **hard-set volume**:

$$\Phi = \sum_{i = 1}^n \phi_i = \sum_{i = 1}^n \psi_i \epsilon_i$$

---

## 4. Volume Index

To account for bodyweight changes or to compare lifters of different sizes, volume is normalised by $m^{2/3}$ following [established allometric scaling laws](https://www.researchgate.net/profile/Guy-Haff/publication/239731099_Quantifying_Workloads_in_Resistance_Training_A_Brief_Review/links/02e7e51ca383fafe13000000/Quantifying-Workloads-in-Resistance-Training-A-Brief-Review.pdf):

$$I_S = \Psi \cdot m^{-2/3} \qquad \text{(standardised volume index)}$$

$$I_H = \Phi \cdot m^{-2/3} \qquad \text{(hard-set volume index)}$$

---

## Summary of Symbols

| Symbol | Name | Scope | Description |
|--------|------|-------|-------------|
| $\psi$ | Load | Per set | Biomechanically standardised load |
| $\Psi$ | Standardised Volume | Per workout | Sum of all set loads |
| $\epsilon$ | Hard-set weight | Per set | Logistic intensity weighting (0–1.05) |
| $N$ | Hard sets | Per workout | Sum of $\epsilon$ values |
| $\phi$ | Meaningful load | Per set | $\psi \cdot \epsilon$ |
| $\Phi$ | Hard-set Volume | Per workout | Sum of meaningful loads |
| $\Pi$ | Predicted 1RL | Per set | Load-based 1RM estimate |
| $\Delta$ | Distance coeff. | Per exercise | Weight travel distance (m) |
| $\kappa$ | Body coeff. | Per exercise | $\rho \cdot \theta$ |
| $I_S$, $I_H$ | Volume indices | Per workout | Bodyweight-normalised volumes |
