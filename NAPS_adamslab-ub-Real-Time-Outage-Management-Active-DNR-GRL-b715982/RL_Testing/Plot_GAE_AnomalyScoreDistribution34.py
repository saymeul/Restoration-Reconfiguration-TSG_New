"""Plot GAE anomaly score distributions for IEEE 34-bus FDIA detection."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


METHOD_LABELS = {"GRL": "GCAPS/GRL", "MLP": "MLP", "BPSO": "BPSO"}
METHOD_COLORS = {"GRL": "#1f77b4", "MLP": "#2ca02c", "BPSO": "#d62728"}


def parse_args():
    parser = argparse.ArgumentParser(description="Plot GAE anomaly-score distribution for IEEE 34-bus.")
    parser.add_argument(
        "--input",
        default="paper_results/naps_34bus/topology_status_gae_detection_expanded/expanded_gae_detection_cases_34bus.csv",
    )
    parser.add_argument(
        "--output-dir",
        default="paper_results/naps_34bus/topology_status_gae_detection_expanded",
    )
    return parser.parse_args()


def resolve_path(path):
    candidate = Path(path)
    if candidate.exists() or candidate.is_absolute():
        return candidate
    base = Path(__file__).resolve().parent
    return base / candidate


def read_rows(path):
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def finite_scores(rows):
    scores = []
    for row in rows:
        try:
            value = float(row["gae_score"])
        except (KeyError, TypeError, ValueError):
            continue
        if np.isfinite(value):
            scores.append(value)
    return np.asarray(scores, dtype=float)


def summary_rows(rows):
    output = []
    for method in ("GRL", "MLP", "BPSO"):
        for expected_attack, label in ((0, "Clean"), (1, "FDIA")):
            items = [
                row
                for row in rows
                if row.get("target_method") == method and int(float(row.get("expected_attack", 0))) == expected_attack
            ]
            scores = finite_scores(items)
            detected = sum(int(float(row.get("gae_detected", 0))) for row in items)
            threshold = np.mean([float(row["gae_threshold"]) for row in items]) if items else 0.0
            output.append(
                {
                    "method": method,
                    "paper_method_label": METHOD_LABELS[method],
                    "class": label,
                    "samples": int(scores.size),
                    "detected_count": int(detected),
                    "detected_rate": float(detected / len(items)) if items else 0.0,
                    "threshold": float(threshold),
                    "mean_score": float(np.mean(scores)) if scores.size else 0.0,
                    "std_score": float(np.std(scores)) if scores.size else 0.0,
                    "min_score": float(np.min(scores)) if scores.size else 0.0,
                    "q25_score": float(np.quantile(scores, 0.25)) if scores.size else 0.0,
                    "median_score": float(np.quantile(scores, 0.50)) if scores.size else 0.0,
                    "q75_score": float(np.quantile(scores, 0.75)) if scores.size else 0.0,
                    "max_score": float(np.max(scores)) if scores.size else 0.0,
                }
            )
    return output


def write_csv(path, rows):
    if not rows:
        return
    with Path(path).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_distribution(rows, output_path):
    threshold_values = [float(row["gae_threshold"]) for row in rows if row.get("gae_threshold")]
    threshold = float(np.mean(threshold_values)) if threshold_values else 0.0
    fig, axes = plt.subplots(1, 3, figsize=(12.8, 3.8), sharey=True)
    bins = np.linspace(0.0, max(5.0, max(float(row["gae_score"]) for row in rows) * 1.05), 34)

    for axis, method in zip(axes, ("GRL", "MLP", "BPSO")):
        clean = finite_scores(
            [row for row in rows if row.get("target_method") == method and int(float(row["expected_attack"])) == 0]
        )
        attacked = finite_scores(
            [row for row in rows if row.get("target_method") == method and int(float(row["expected_attack"])) == 1]
        )
        color = METHOD_COLORS[method]
        axis.hist(clean, bins=bins, color="#8f8f8f", alpha=0.58, density=True, label="Clean")
        axis.hist(attacked, bins=bins, color=color, alpha=0.52, density=True, label="FDIA")
        axis.axvline(threshold, color="black", linestyle="--", linewidth=1.35, label="GAE threshold")
        axis.set_title(METHOD_LABELS[method], fontweight="bold", color=color)
        axis.set_xlabel("GAE anomaly score")
        axis.grid(True, linestyle="--", linewidth=0.5, alpha=0.32)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        if method == "GRL":
            axis.set_ylabel("Density")
            axis.legend(frameon=True, fontsize=8, loc="upper right")

    fig.suptitle("GAE Anomaly Score Distribution for Topology/Status FDIA Detection", fontweight="bold", y=1.03)
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_box(rows, output_path):
    fig, axis = plt.subplots(figsize=(8.5, 4.4))
    positions = []
    data = []
    labels = []
    colors = []
    for index, method in enumerate(("GRL", "MLP", "BPSO")):
        clean = finite_scores(
            [row for row in rows if row.get("target_method") == method and int(float(row["expected_attack"])) == 0]
        )
        attacked = finite_scores(
            [row for row in rows if row.get("target_method") == method and int(float(row["expected_attack"])) == 1]
        )
        positions.extend([index * 3.0 + 1.0, index * 3.0 + 2.0])
        data.extend([clean, attacked])
        labels.extend([METHOD_LABELS[method] + "\nClean", METHOD_LABELS[method] + "\nFDIA"])
        colors.extend(["#bdbdbd", METHOD_COLORS[method]])
    box = axis.boxplot(data, positions=positions, widths=0.62, patch_artist=True, showfliers=True)
    for patch, color in zip(box["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.72)
    threshold_values = [float(row["gae_threshold"]) for row in rows if row.get("gae_threshold")]
    threshold = float(np.mean(threshold_values)) if threshold_values else 0.0
    axis.axhline(threshold, color="black", linestyle="--", linewidth=1.35, label="GAE threshold")
    axis.set_xticks(positions)
    axis.set_xticklabels(labels)
    axis.set_ylabel("GAE anomaly score")
    axis.set_title("Clean vs FDIA GAE Anomaly Scores", fontweight="bold")
    axis.grid(True, axis="y", linestyle="--", linewidth=0.5, alpha=0.35)
    axis.legend(frameon=True, fontsize=9, loc="upper left")
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main():
    args = parse_args()
    input_path = resolve_path(args.input)
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = read_rows(input_path)
    summary = summary_rows(rows)
    summary_path = output_dir / "table_gae_anomaly_score_summary_34bus.csv"
    distribution_path = output_dir / "fig_gae_anomaly_score_distribution_34bus.png"
    box_path = output_dir / "fig_gae_anomaly_score_boxplot_34bus.png"
    write_csv(summary_path, summary)
    plot_distribution(rows, distribution_path)
    plot_box(rows, box_path)
    print("wrote {}".format(summary_path))
    print("wrote {}".format(distribution_path))
    print("wrote {}".format(box_path))


if __name__ == "__main__":
    main()
