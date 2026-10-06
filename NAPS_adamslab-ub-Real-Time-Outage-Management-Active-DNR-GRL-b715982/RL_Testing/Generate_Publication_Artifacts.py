"""
Generate paper-ready tables and figures from FDIA experiment CSV files.

Inputs are the raw CSVs produced by:
    Run_FDIA_PhysicalImpact.py
    Run_RL_FDIA_Resilience.py

Outputs are compact tables, plots, and a short markdown summary under
RL_Testing/paper_results/publication_artifacts by default.
"""

import argparse
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "paper_results"
SYSTEMS = ["13bus", "34bus", "123bus"]


def parse_args():
    parser = argparse.ArgumentParser(description="Generate FDIA publication tables and figures")
    parser.add_argument("--results-dir", default=str(RESULTS_DIR))
    parser.add_argument("--output-dir", default=str(RESULTS_DIR / "publication_artifacts"))
    return parser.parse_args()


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fieldnames):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def as_float(row, key, default=0.0):
    try:
        value = row.get(key, "")
        if value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(row, key, default=0):
    try:
        value = row.get(key, "")
        if value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def fmt(value, digits=6):
    if value == "":
        return ""
    if isinstance(value, str):
        return value
    if not math.isfinite(float(value)):
        return ""
    return f"{float(value):.{digits}f}"


def clean_metric(row, metric, delta):
    return as_float(row, metric) - as_float(row, delta)


def physical_rows(results_dir):
    rows = []
    for system in SYSTEMS:
        rows.extend(read_csv(results_dir / f"fdia_physical_impact_{system}.csv"))
        rows.extend(read_csv(results_dir / f"fdia_physical_impact_{system}_search.csv"))
    return rows


def resilience_rows(results_dir):
    rows = []
    for system in SYSTEMS:
        rows.extend(read_csv(results_dir / f"rl_fdia_resilience_{system}.csv"))
    return rows


def dynamic_rows(results_dir):
    rows = []
    paths = []
    for pattern in [
        "fdia_dynamic_impact_*bus*.csv",
        "rl_fdia_resilience_dynamic_*bus*.csv",
    ]:
        paths.extend(sorted(results_dir.glob(pattern)))

    seen = set()
    for path in paths:
        if "reprocheck" in path.name:
            continue
        if path in seen:
            continue
        seen.add(path)
        rows.extend(read_csv(path))
    return rows


def make_physical_table(rows):
    table = []
    for row in rows:
        clean_energy_ratio = clean_metric(row, "energy_ratio", "energy_ratio_delta_vs_clean")
        clean_energy_kw = clean_metric(row, "energy_kw", "energy_kw_delta_vs_clean")
        clean_reward = clean_metric(row, "reward", "reward_delta_vs_clean")
        clean_voltage = clean_metric(row, "voltage_violation", "voltage_violation_delta_vs_clean")
        table.append(
            {
                "system": row.get("system", ""),
                "scenario": row.get("scenario", ""),
                "attack": row.get("attack", ""),
                "clean_energy_ratio": fmt(clean_energy_ratio),
                "attacked_energy_ratio": fmt(as_float(row, "energy_ratio")),
                "energy_ratio_delta": fmt(as_float(row, "energy_ratio_delta_vs_clean")),
                "clean_energy_kw": fmt(clean_energy_kw),
                "attacked_energy_kw": fmt(as_float(row, "energy_kw")),
                "energy_kw_delta": fmt(as_float(row, "energy_kw_delta_vs_clean")),
                "clean_reward": fmt(clean_reward),
                "attacked_reward": fmt(as_float(row, "reward")),
                "reward_delta": fmt(as_float(row, "reward_delta_vs_clean")),
                "clean_voltage_violation": fmt(clean_voltage),
                "attacked_voltage_violation": fmt(as_float(row, "voltage_violation")),
                "voltage_violation_delta": fmt(as_float(row, "voltage_violation_delta_vs_clean")),
                "loads_served": as_int(row, "loads_served"),
                "loads_served_delta": as_int(row, "loads_served_delta_vs_clean"),
                "action_changed": as_int(row, "action_changed"),
                "switch_changes": as_int(row, "switch_changes_vs_clean"),
                "load_changes": as_int(row, "load_changes_vs_clean"),
                "physical_impact_score": fmt(as_float(row, "physical_impact_score")),
                "bdd_detected": as_int(row, "bdd_detected"),
                "bdd_score": fmt(as_float(row, "bdd_score")),
                "bdd_detected_channels": row.get("bdd_detected_channels", ""),
            }
        )
    return table


def grouped_by_case(rows):
    grouped = defaultdict(dict)
    for row in rows:
        key = (row.get("system", ""), row.get("scenario", ""), row.get("attack", ""))
        grouped[key][row.get("mode", "")] = row
    return grouped


def unique_time_rows(rows):
    by_step = {}
    for row in rows:
        step = as_int(row, "time_step")
        if step not in by_step:
            by_step[step] = row
    return [by_step[step] for step in sorted(by_step)]


def valid_dynamic_row(row):
    impact = as_float(row, "physical_impact_score", math.nan)
    energy_ratio = as_float(row, "energy_ratio", math.nan)
    convergence = as_float(row, "convergence_violation", 0.0)
    return (
        math.isfinite(impact)
        and math.isfinite(energy_ratio)
        and impact <= 5.0
        and abs(energy_ratio) <= 2.0
        and convergence <= 0.0
    )


def make_resilience_table(rows):
    table = []
    grouped = grouped_by_case(rows)
    for (system, scenario, attack), modes in sorted(grouped.items()):
        attacked = modes.get("attacked_unmitigated")
        mitigated = modes.get("rl_detector_mitigated")
        screened = modes.get("rl_detector_fdia_aware_screened")
        if not attacked:
            continue

        clean_energy = clean_metric(attacked, "energy_ratio", "energy_ratio_delta_vs_clean")
        clean_reward = clean_metric(attacked, "reward", "reward_delta_vs_clean")
        attacked_energy = as_float(attacked, "energy_ratio")
        mitigated_energy = as_float(mitigated, "energy_ratio") if mitigated else ""
        screened_energy = as_float(screened, "energy_ratio") if screened else ""
        attacked_impact = as_float(attacked, "physical_impact_score")
        mitigated_impact = as_float(mitigated, "physical_impact_score") if mitigated else ""
        screened_impact = as_float(screened, "physical_impact_score") if screened else ""

        denom = clean_energy - attacked_energy
        if abs(denom) > 1.0e-12 and mitigated:
            energy_recovery = (mitigated_energy - attacked_energy) / denom
        else:
            energy_recovery = ""

        if attacked_impact > 1.0e-12 and mitigated:
            impact_reduction = (attacked_impact - mitigated_impact) / attacked_impact
        else:
            impact_reduction = ""

        table.append(
            {
                "system": system,
                "scenario": scenario,
                "attack": attack,
                "clean_energy_ratio": fmt(clean_energy),
                "attacked_energy_ratio": fmt(attacked_energy),
                "mitigated_energy_ratio": fmt(mitigated_energy),
                "screened_energy_ratio": fmt(screened_energy),
                "clean_reward": fmt(clean_reward),
                "attacked_reward": fmt(as_float(attacked, "reward")),
                "mitigated_reward": fmt(as_float(mitigated, "reward") if mitigated else ""),
                "screened_reward": fmt(as_float(screened, "reward") if screened else ""),
                "attacked_impact_score": fmt(attacked_impact),
                "mitigated_impact_score": fmt(mitigated_impact),
                "screened_impact_score": fmt(screened_impact),
                "energy_recovery_fraction": fmt(energy_recovery),
                "impact_reduction_fraction": fmt(impact_reduction),
                "attacked_action_changed": as_int(attacked, "action_changed"),
                "rl_detector_attack": mitigated.get("rl_detector_attack", "") if mitigated else "",
                "mitigation_applied": as_int(mitigated, "mitigation_applied") if mitigated else "",
                "screened_selected_candidate": screened.get("selected_candidate", "") if screened else "",
            }
        )
    return table


def make_detector_tables(rows):
    mitigated_rows = [row for row in rows if row.get("mode") == "rl_detector_mitigated"]
    confusion_counts = Counter()
    attack_counts = Counter()
    attack_correct = Counter()
    system_counts = Counter()
    system_correct = Counter()

    for row in mitigated_rows:
        system = row.get("system", "")
        expected = row.get("attack", "")
        predicted = row.get("rl_detector_attack", "")
        confusion_counts[(system, expected, predicted)] += 1
        attack_counts[(system, expected)] += 1
        system_counts[system] += 1
        if expected == predicted:
            attack_correct[(system, expected)] += 1
            system_correct[system] += 1

    confusion = [
        {
            "system": system,
            "expected_attack": expected,
            "predicted_attack": predicted,
            "count": count,
        }
        for (system, expected, predicted), count in sorted(confusion_counts.items())
    ]

    by_attack = []
    for (system, attack), count in sorted(attack_counts.items()):
        correct = attack_correct[(system, attack)]
        by_attack.append(
            {
                "system": system,
                "attack": attack,
                "samples": count,
                "correct": correct,
                "accuracy": fmt(correct / count if count else 0.0),
            }
        )

    by_system = []
    for system, count in sorted(system_counts.items()):
        correct = system_correct[system]
        by_system.append(
            {
                "system": system,
                "samples": count,
                "correct": correct,
                "accuracy": fmt(correct / count if count else 0.0),
            }
        )
    return confusion, by_attack, by_system


def make_dynamic_table(rows):
    grouped = defaultdict(lambda: defaultdict(list))
    for row in rows:
        key = (row.get("system", ""), row.get("scenario", ""), row.get("attack", ""))
        grouped[key][row.get("mode", "")].append(row)

    table = []
    for (system, scenario, attack), modes in sorted(grouped.items()):
        attacked_rows_all = unique_time_rows(modes.get("attacked_unmitigated_dynamic", []))
        mitigated_rows_all = unique_time_rows(modes.get("rl_detector_mitigated_dynamic", []))
        attacked_rows = [row for row in attacked_rows_all if valid_dynamic_row(row)]
        mitigated_rows = [row for row in mitigated_rows_all if valid_dynamic_row(row)]
        if not attacked_rows:
            continue

        max_attack_impact = max(as_float(row, "physical_impact_score") for row in attacked_rows)
        mean_attack_impact = sum(as_float(row, "physical_impact_score") for row in attacked_rows) / len(attacked_rows)
        max_mitigated_impact = (
            max(as_float(row, "physical_impact_score") for row in mitigated_rows) if mitigated_rows else ""
        )
        mean_mitigated_impact = (
            sum(as_float(row, "physical_impact_score") for row in mitigated_rows) / len(mitigated_rows)
            if mitigated_rows
            else ""
        )
        min_attack_energy = min(as_float(row, "energy_ratio") for row in attacked_rows)
        min_mitigated_energy = (
            min(as_float(row, "energy_ratio") for row in mitigated_rows) if mitigated_rows else ""
        )
        table.append(
            {
                "system": system,
                "scenario": scenario,
                "attack": attack,
                "time_steps": len(attacked_rows),
                "excluded_time_steps": len(attacked_rows_all) - len(attacked_rows),
                "max_attacked_impact": fmt(max_attack_impact),
                "mean_attacked_impact": fmt(mean_attack_impact),
                "max_mitigated_impact": fmt(max_mitigated_impact),
                "mean_mitigated_impact": fmt(mean_mitigated_impact),
                "min_attacked_energy_ratio": fmt(min_attack_energy),
                "min_mitigated_energy_ratio": fmt(min_mitigated_energy),
            }
        )
    return table


def plot_physical_impact(table, output_dir):
    ranked = sorted(table, key=lambda row: float(row["physical_impact_score"] or 0.0), reverse=True)
    ranked = ranked[:20]
    labels = [f"{row['system']} {row['scenario']}\n{row['attack']}" for row in ranked]
    values = [float(row["physical_impact_score"] or 0.0) for row in ranked]
    colors = ["#b84a62" if value > 0 else "#9aa3ad" for value in values]

    fig, ax = plt.subplots(figsize=(12, 5.8))
    ax.bar(range(len(values)), values, color=colors)
    ax.set_ylabel("Physical impact score")
    ax.set_title("FDIA-Induced Physical Degradation Before Mitigation")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_physical_impact_scores.png", dpi=220)
    plt.close(fig)


def plot_recovery(table, output_dir):
    harmful = [row for row in table if float(row["attacked_impact_score"] or 0.0) > 1.0e-9]
    harmful = sorted(harmful, key=lambda row: float(row["attacked_impact_score"]), reverse=True)
    if not harmful:
        return

    labels = [f"{row['system']} {row['scenario']}\n{row['attack']}" for row in harmful]
    clean = [float(row["clean_energy_ratio"]) for row in harmful]
    attacked = [float(row["attacked_energy_ratio"]) for row in harmful]
    mitigated = [float(row["mitigated_energy_ratio"]) for row in harmful]
    x = list(range(len(harmful)))
    width = 0.24

    fig, ax = plt.subplots(figsize=(10.5, 5.8))
    ax.bar([i - width for i in x], clean, width=width, label="Clean", color="#4c78a8")
    ax.bar(x, attacked, width=width, label="Attacked", color="#c44e52")
    ax.bar([i + width for i in x], mitigated, width=width, label="RL detector + mitigation", color="#55a868")
    ax.set_ylabel("Energy supplied ratio")
    ax.set_title("Recovery of Physical Restoration Performance")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.set_ylim(0, max(clean + attacked + mitigated) * 1.15)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_energy_recovery.png", dpi=220)
    plt.close(fig)


def plot_detector_accuracy(by_system, output_dir):
    if not by_system:
        return
    labels = [row["system"] for row in by_system]
    values = [float(row["accuracy"]) for row in by_system]
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    ax.bar(labels, values, color="#4c78a8")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Accuracy")
    ax.set_title("RL FDIA Detector Accuracy on Tested Cases")
    ax.grid(axis="y", alpha=0.25)
    for idx, value in enumerate(values):
        ax.text(idx, value + 0.02, f"{value:.2f}", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(output_dir / "fig_rl_detector_accuracy.png", dpi=220)
    plt.close(fig)


def plot_dynamic(rows, output_dir):
    grouped = defaultdict(lambda: defaultdict(list))
    for row in rows:
        key = (row.get("system", ""), row.get("scenario", ""), row.get("attack", ""))
        grouped[key][row.get("mode", "")].append(row)

    best_key = None
    best_impact = -1.0
    for key, modes in grouped.items():
        attacked_rows = [row for row in modes.get("attacked_unmitigated_dynamic", []) if valid_dynamic_row(row)]
        if not attacked_rows:
            continue
        impact = max(as_float(row, "physical_impact_score") for row in attacked_rows)
        if impact > best_impact:
            best_impact = impact
            best_key = key

    if best_key is None:
        return

    modes = grouped[best_key]
    attacked = [row for row in unique_time_rows(modes.get("attacked_unmitigated_dynamic", [])) if valid_dynamic_row(row)]
    mitigated = [row for row in unique_time_rows(modes.get("rl_detector_mitigated_dynamic", [])) if valid_dynamic_row(row)]
    if not attacked:
        return

    time_steps = [as_int(row, "time_step") for row in attacked]
    clean_energy = [
        as_float(row, "energy_ratio") - as_float(row, "energy_ratio_delta_vs_clean")
        for row in attacked
    ]
    attacked_energy = [as_float(row, "energy_ratio") for row in attacked]
    mitigated_energy = [as_float(row, "energy_ratio") for row in mitigated] if mitigated else []

    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    ax.plot(time_steps, clean_energy, label="Clean", color="#4c78a8", linewidth=2.0)
    ax.plot(time_steps, attacked_energy, label="Attacked", color="#c44e52", linewidth=2.0)
    if mitigated_energy:
        ax.plot(time_steps, mitigated_energy, label="RL detector + mitigation", color="#55a868", linewidth=2.0)
    ax.set_xlabel("Time step")
    ax.set_ylabel("Energy supplied ratio")
    ax.set_title(f"Dynamic Energy Trajectory: {best_key[0]} {best_key[1]} {best_key[2]}")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_dynamic_energy_trajectory.png", dpi=220)
    plt.close(fig)

    attacked_impact = [as_float(row, "physical_impact_score") for row in attacked]
    mitigated_impact = [as_float(row, "physical_impact_score") for row in mitigated] if mitigated else []
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    ax.plot(time_steps, attacked_impact, label="Attacked", color="#c44e52", linewidth=2.0)
    if mitigated_impact:
        ax.plot(time_steps, mitigated_impact, label="RL detector + mitigation", color="#55a868", linewidth=2.0)
    ax.set_xlabel("Time step")
    ax.set_ylabel("Physical impact score")
    ax.set_title(f"Dynamic Physical Impact: {best_key[0]} {best_key[1]} {best_key[2]}")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_dynamic_impact_trajectory.png", dpi=220)
    plt.close(fig)


def write_markdown_summary(output_dir, physical_table, resilience_table, detector_by_system, dynamic_table):
    harmful = sorted(
        [row for row in resilience_table if float(row["attacked_impact_score"] or 0.0) > 1.0e-9],
        key=lambda row: float(row["attacked_impact_score"]),
        reverse=True,
    )
    top_physical = sorted(
        physical_table,
        key=lambda row: float(row["physical_impact_score"] or 0.0),
        reverse=True,
    )[:5]

    lines = [
        "# FDIA Publication Artifact Summary",
        "",
        "## Strongest Physical Degradation Cases",
        "",
        "| System | Scenario | Attack | Clean Energy | Attacked Energy | Impact |",
        "|---|---|---|---:|---:|---:|",
    ]
    for row in top_physical:
        lines.append(
            "| {system} | {scenario} | {attack} | {clean_energy_ratio} | {attacked_energy_ratio} | {physical_impact_score} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "## Recovery Cases",
            "",
            "| System | Scenario | Attack | Attacked Energy | Mitigated Energy | Impact Reduction | Detector Decision |",
            "|---|---|---|---:|---:|---:|---|",
        ]
    )
    for row in harmful:
        lines.append(
            "| {system} | {scenario} | {attack} | {attacked_energy_ratio} | {mitigated_energy_ratio} | {impact_reduction_fraction} | {rl_detector_attack} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "## RL Detector Accuracy",
            "",
            "| System | Samples | Correct | Accuracy |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in detector_by_system:
        lines.append("| {system} | {samples} | {correct} | {accuracy} |".format(**row))

    if dynamic_table:
        lines.extend(
            [
                "",
                "## Dynamic Summary",
                "",
                "| System | Scenario | Attack | Max Attacked Impact | Max Mitigated Impact |",
                "|---|---|---|---:|---:|",
            ]
        )
        for row in sorted(dynamic_table, key=lambda item: float(item["max_attacked_impact"] or 0.0), reverse=True)[:8]:
            lines.append(
                "| {system} | {scenario} | {attack} | {max_attacked_impact} | {max_mitigated_impact} |".format(
                    **row
                )
            )

    (output_dir / "publication_summary.md").write_text("\n".join(lines) + "\n")


def main():
    args = parse_args()
    results_dir = Path(args.results_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    physical_table = make_physical_table(physical_rows(results_dir))
    resilience_table = make_resilience_table(resilience_rows(results_dir))
    confusion, detector_by_attack, detector_by_system = make_detector_tables(resilience_rows(results_dir))
    dynamic_table = make_dynamic_table(dynamic_rows(results_dir))

    physical_fields = [
        "system",
        "scenario",
        "attack",
        "clean_energy_ratio",
        "attacked_energy_ratio",
        "energy_ratio_delta",
        "clean_energy_kw",
        "attacked_energy_kw",
        "energy_kw_delta",
        "clean_reward",
        "attacked_reward",
        "reward_delta",
        "clean_voltage_violation",
        "attacked_voltage_violation",
        "voltage_violation_delta",
        "loads_served",
        "loads_served_delta",
        "action_changed",
        "switch_changes",
        "load_changes",
        "physical_impact_score",
        "bdd_detected",
        "bdd_score",
        "bdd_detected_channels",
    ]
    resilience_fields = [
        "system",
        "scenario",
        "attack",
        "clean_energy_ratio",
        "attacked_energy_ratio",
        "mitigated_energy_ratio",
        "screened_energy_ratio",
        "clean_reward",
        "attacked_reward",
        "mitigated_reward",
        "screened_reward",
        "attacked_impact_score",
        "mitigated_impact_score",
        "screened_impact_score",
        "energy_recovery_fraction",
        "impact_reduction_fraction",
        "attacked_action_changed",
        "rl_detector_attack",
        "mitigation_applied",
        "screened_selected_candidate",
    ]
    detector_confusion_fields = ["system", "expected_attack", "predicted_attack", "count"]
    detector_attack_fields = ["system", "attack", "samples", "correct", "accuracy"]
    detector_system_fields = ["system", "samples", "correct", "accuracy"]
    dynamic_fields = [
        "system",
        "scenario",
        "attack",
        "time_steps",
        "excluded_time_steps",
        "max_attacked_impact",
        "mean_attacked_impact",
        "max_mitigated_impact",
        "mean_mitigated_impact",
        "min_attacked_energy_ratio",
        "min_mitigated_energy_ratio",
    ]

    write_csv(output_dir / "table_physical_degradation.csv", physical_table, physical_fields)
    write_csv(output_dir / "table_resilience_recovery.csv", resilience_table, resilience_fields)
    write_csv(output_dir / "table_rl_detector_confusion.csv", confusion, detector_confusion_fields)
    write_csv(output_dir / "table_rl_detector_by_attack.csv", detector_by_attack, detector_attack_fields)
    write_csv(output_dir / "table_rl_detector_by_system.csv", detector_by_system, detector_system_fields)
    write_csv(output_dir / "table_dynamic_summary.csv", dynamic_table, dynamic_fields)

    plot_physical_impact(physical_table, output_dir)
    plot_recovery(resilience_table, output_dir)
    plot_detector_accuracy(detector_by_system, output_dir)
    plot_dynamic(dynamic_rows(results_dir), output_dir)
    write_markdown_summary(output_dir, physical_table, resilience_table, detector_by_system, dynamic_table)

    print(f"Generated publication artifacts in: {output_dir}")
    print(f"Physical cases: {len(physical_table)}")
    print(f"Resilience cases: {len(resilience_table)}")
    print(f"Detector systems: {len(detector_by_system)}")
    print(f"Dynamic cases: {len(dynamic_table)}")


if __name__ == "__main__":
    main()
