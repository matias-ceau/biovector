#!/usr/bin/env python3
"""Generate a daily smoothed bodyweight CSV from sparse measurements.

Reads data/user/bodyweight.json (irregular measurements) and produces
data/user/bodyweight_smoothed.csv with one row per day, using a
Gaussian kernel smoother (Nadaraya-Watson estimator).

Usage:
    python scripts/smooth_bodyweight.py [--bandwidth DAYS] [--plot]

Options:
    --bandwidth  Gaussian kernel bandwidth in days (default: 21)
    --plot       Show a matplotlib plot of raw vs smoothed data
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(
    __import__("os").environ.get("BIOVECTOR_DATA_DIR", ROOT / "data")
)
BW_JSON = DATA_DIR / "user" / "bodyweight.json"
OUT_CSV = DATA_DIR / "user" / "bodyweight_smoothed.csv"


# ---------------------------------------------------------------------------
# Gaussian kernel smoother (Nadaraya-Watson)
# ---------------------------------------------------------------------------
def gaussian_kernel(distances: np.ndarray, bandwidth: float) -> np.ndarray:
    """Return Gaussian weights for given distances and bandwidth (σ)."""
    return np.exp(-0.5 * (distances / bandwidth) ** 2)


def smooth_bodyweight(
    dates_raw: np.ndarray,
    weights_raw: np.ndarray,
    dates_out: np.ndarray,
    bandwidth: float = 21.0,
) -> np.ndarray:
    """Nadaraya-Watson kernel regression with Gaussian kernel.

    Parameters
    ----------
    dates_raw : array of float — day offsets of actual measurements
    weights_raw : array of float — measured weights (kg)
    dates_out : array of float — day offsets for output grid
    bandwidth : float — kernel bandwidth in days (σ)

    Returns
    -------
    smoothed : array of float — estimated weight for each output day
    """
    smoothed = np.empty(len(dates_out))
    for i, t in enumerate(dates_out):
        dists = np.abs(dates_raw - t)
        w = gaussian_kernel(dists, bandwidth)
        total_w = w.sum()
        if total_w < 1e-12:
            # Fallback: nearest measurement
            smoothed[i] = weights_raw[np.argmin(dists)]
        else:
            smoothed[i] = np.dot(w, weights_raw) / total_w
    return smoothed


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------
def load_measurements(path: Path) -> tuple[list[date], list[float]]:
    """Load bodyweight.json and return (dates, weights_kg) sorted by date."""
    with open(path) as f:
        data = json.load(f)

    entries = data["measurements"]
    pairs: list[tuple[date, float]] = []
    for e in entries:
        d = date.fromisoformat(e["date"])
        w = float(e["weight_kg"])
        pairs.append((d, w))

    # De-duplicate: if multiple measurements on same day, keep mean
    from collections import defaultdict

    day_vals: dict[date, list[float]] = defaultdict(list)
    for d, w in pairs:
        day_vals[d].append(w)

    dates_sorted = sorted(day_vals.keys())
    weights = [np.mean(day_vals[d]) for d in dates_sorted]
    return dates_sorted, weights


def date_to_offset(dates: list[date], origin: date) -> np.ndarray:
    """Convert dates to float day offsets from origin."""
    return np.array([(d - origin).days for d in dates], dtype=float)


def write_csv(
    path: Path,
    origin: date,
    offsets: np.ndarray,
    smoothed: np.ndarray,
) -> int:
    """Write CSV with columns: date, weight_kg (smoothed, 1 decimal)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "weight_kg"])
        for off, val in zip(offsets, smoothed):
            day = origin + timedelta(days=int(off))
            writer.writerow([day.isoformat(), round(float(val), 1)])
    return len(offsets)


# ---------------------------------------------------------------------------
# Plotting (optional)
# ---------------------------------------------------------------------------
def plot_results(
    dates_raw: list[date],
    weights_raw: list[float],
    origin: date,
    offsets_out: np.ndarray,
    smoothed: np.ndarray,
    bandwidth: float,
) -> None:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    dates_out = [origin + timedelta(days=int(o)) for o in offsets_out]

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.scatter(dates_raw, weights_raw, s=10, alpha=0.5, label="measured", zorder=3)
    ax.plot(dates_out, smoothed, color="crimson", linewidth=1.5,
            label=f"smoothed (σ={bandwidth}d)", zorder=4)
    ax.set_ylabel("Body weight (kg)")
    ax.set_title("Bodyweight — Gaussian kernel smoothing")
    ax.legend()
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=[4, 7, 10]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    plt.show()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate daily smoothed bodyweight CSV."
    )
    parser.add_argument(
        "--bandwidth",
        type=float,
        default=21.0,
        help="Gaussian kernel bandwidth σ in days (default: 21)",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Show matplotlib plot of raw vs smoothed",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help=f"Output CSV path (default: {OUT_CSV})",
    )
    args = parser.parse_args()

    # Load
    dates_raw, weights_raw = load_measurements(BW_JSON)
    print(f"Loaded {len(dates_raw)} measurements "
          f"({dates_raw[0]} → {dates_raw[-1]})")

    origin = dates_raw[0]
    x_raw = date_to_offset(dates_raw, origin)
    w_raw = np.array(weights_raw)

    # Build daily output grid from first to last measurement
    n_days = (dates_raw[-1] - origin).days + 1
    x_out = np.arange(n_days, dtype=float)
    print(f"Generating {n_days} daily estimates (σ = {args.bandwidth} days)…")

    # Smooth
    smoothed = smooth_bodyweight(x_raw, w_raw, x_out, bandwidth=args.bandwidth)

    # Write
    out_path = Path(args.output) if args.output else OUT_CSV
    n_written = write_csv(out_path, origin, x_out, smoothed)
    print(f"Wrote {n_written} rows → {out_path}")

    # Optional plot
    if args.plot:
        plot_results(dates_raw, weights_raw, origin, x_out, smoothed,
                     args.bandwidth)


if __name__ == "__main__":
    main()
