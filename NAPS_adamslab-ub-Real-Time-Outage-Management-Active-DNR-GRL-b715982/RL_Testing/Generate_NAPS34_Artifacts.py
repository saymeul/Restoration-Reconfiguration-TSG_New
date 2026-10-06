"""
Generate NAPS 2026 IEEE 34-bus FDIA paper artifacts.

This script is intentionally separate from the multi-feeder publication
artifact generator. It reads the focused 34-bus search, resilience, dynamic,
and robustness CSVs and writes a compact NAPS-ready summary under
RL_Testing/paper_results/naps_34bus/naps_artifacts.
"""

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_RESULTS_DIR = BASE_DIR / "paper_results" / "naps_34bus"


def parse_args():
    parser = argparse.ArgumentParser(description="Generate NAPS 34-bus FDIA artifacts")
    parser.add_argument("--results-dir", default=str(DEFAULT_RESULTS_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_RESULTS_DIR / "naps_artifacts"))
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
            writer.writerow({field: row.get(field, "") for field in fieldnames})


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
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return ""
    return f"{number:.{digits}f}"


def clean_metric(row, metric, delta):
    return as_float(row, metric) - as_float(row, delta)


def clean_convergence(row):
    return clean_metric(row, "convergence_violation", "convergence_delta_vs_clean")


def paper_valid_row(row):
    impact = as_float(row, "physical_impact_score", math.nan)
    energy_ratio = as_float(row, "energy_ratio", math.nan)
    convergence = as_float(row, "convergence_violation", 0.0)
    clean_conv = clean_convergence(row)
    return (
        math.isfinite(impact)
        and 0.0 <= impact <= 5.0
        and math.isfinite(energy_ratio)
        and abs(energy_ratio) <= 2.0
        and convergence <= 0.0
        and clean_conv <= 0.0
    )


def group_by_case(rows):
    grouped = defaultdict(dict)
    for row in rows:
        key = (row.get("system", ""), row.get("scenario", ""), row.get("attack", ""))
        grouped[key][row.get("mode", "")] = row
    return grouped


def valid_dynamic_row(row):
    return paper_valid_row(row)


def unique_time_rows(rows):
    by_step = {}
    for row in rows:
        by_step[as_int(row, "time_step")] = row
    return [by_step[step] for step in sorted(by_step)]


def physical_table(rows):
    table = []
    valid_rows = [row for row in rows if paper_valid_row(row)]
    for row in sorted(valid_rows, key=lambda item: as_float(item, "physical_impact_score"), reverse=True):
        table.append(
            {
                "scenario": row.get("scenario", ""),
                "attack": row.get("attack", ""),
                "clean_energy_ratio": fmt(clean_metric(row, "energy_ratio", "energy_ratio_delta_vs_clean")),
                "attacked_energy_ratio": fmt(as_float(row, "energy_ratio")),
                "energy_loss": fmt(max(0.0, -as_float(row, "energy_ratio_delta_vs_clean"))),
                "clean_energy_kw": fmt(clean_metric(row, "energy_kw", "energy_kw_delta_vs_clean")),
                "attacked_energy_kw": fmt(as_float(row, "energy_kw")),
                "energy_kw_loss": fmt(max(0.0, -as_float(row, "energy_kw_delta_vs_clean"))),
                "physical_impact_score": fmt(as_float(row, "physical_impact_score")),
                "voltage_violation_delta": fmt(as_float(row, "voltage_violation_delta_vs_clean")),
                "action_changed": as_int(row, "action_changed"),
                "switch_changes": as_int(row, "switch_changes_vs_clean"),
                "load_changes": as_int(row, "load_changes_vs_clean"),
                "bdd_score": fmt(as_float(row, "bdd_score")),
                "bdd_detected_channels": row.get("bdd_detected_channels", ""),
            }
        )
    return table


def recovery_table(rows):
    table = []
    for (_system, scenario, attack), modes in sorted(group_by_case(rows).items()):
        attacked = modes.get("attacked_unmitigated")
        mitigated = modes.get("rl_detector_mitigated")
        screened = modes.get("rl_detector_fdia_aware_screened")
        if not attacked or not mitigated:
            continue
        if not paper_valid_row(attacked) or not paper_valid_row(mitigated):
            continue

        clean_energy = clean_metric(attacked, "energy_ratio", "energy_ratio_delta_vs_clean")
        attacked_energy = as_float(attacked, "energy_ratio")
        mitigated_energy = as_float(mitigated, "energy_ratio")
        screened_energy = as_float(screened, "energy_ratio") if screened else ""
        attacked_impact = as_float(attacked, "physical_impact_score")
        mitigated_impact = as_float(mitigated, "physical_impact_score")
        screened_impact = as_float(screened, "physical_impact_score") if screened else ""

        if attacked_impact > 1.0e-12:
            impact_reduction = (attacked_impact - mitigated_impact) / attacked_impact
        else:
            impact_reduction = ""
        denom = clean_energy - attacked_energy
        if abs(denom) > 1.0e-12:
            energy_recovery = (mitigated_energy - attacked_energy) / denom
        else:
            energy_recovery = ""

        table.append(
            {
                "scenario": scenario,
                "attack": attack,
                "clean_energy_ratio": fmt(clean_energy),
                "attacked_energy_ratio": fmt(attacked_energy),
                "mitigated_energy_ratio": fmt(mitigated_energy),
                "screened_energy_ratio": fmt(screened_energy),
                "attacked_impact_score": fmt(attacked_impact),
                "mitigated_impact_score": fmt(mitigated_impact),
                "screened_impact_score": fmt(screened_impact),
                "energy_recovery_fraction": fmt(energy_recovery),
                "impact_reduction_fraction": fmt(impact_reduction),
                "detector_expected": attack,
                "detector_predicted": mitigated.get("rl_detector_attack", ""),
                "detector_correct": int(mitigated.get("rl_detector_attack", "") == attack),
                "mitigation_applied": as_int(mitigated, "mitigation_applied"),
            }
        )

    return sorted(table, key=lambda row: float(row["attacked_impact_score"] or 0.0), reverse=True)


def dynamic_table(rows):
    grouped = defaultdict(lambda: defaultdict(list))
    for row in rows:
        key = (row.get("scenario", ""), row.get("attack", ""))
        grouped[key][row.get("mode", "")].append(row)

    table = []
    for (scenario, attack), modes in sorted(grouped.items()):
        attacked_all = unique_time_rows(modes.get("attacked_unmitigated_dynamic", []))
        mitigated_all = unique_time_rows(modes.get("rl_detector_mitigated_dynamic", []))
        attacked = [row for row in attacked_all if valid_dynamic_row(row)]
        mitigated = [row for row in mitigated_all if valid_dynamic_row(row)]
        if not attacked:
            continue

        max_attacked = max(as_float(row, "physical_impact_score") for row in attacked)
        mean_attacked = sum(as_float(row, "physical_impact_score") for row in attacked) / len(attacked)
        max_mitigated = max(as_float(row, "physical_impact_score") for row in mitigated) if mitigated else ""
        mean_mitigated = (
            sum(as_float(row, "physical_impact_score") for row in mitigated) / len(mitigated)
            if mitigated
            else ""
        )
        table.append(
            {
                "scenario": scenario,
                "attack": attack,
                "time_steps": len(attacked),
                "excluded_time_steps": len(attacked_all) - len(attacked),
                "max_attacked_impact": fmt(max_attacked),
                "mean_attacked_impact": fmt(mean_attacked),
                "max_mitigated_impact": fmt(max_mitigated),
                "mean_mitigated_impact": fmt(mean_mitigated),
                "min_attacked_energy_ratio": fmt(min(as_float(row, "energy_ratio") for row in attacked)),
                "min_mitigated_energy_ratio": fmt(min(as_float(row, "energy_ratio") for row in mitigated) if mitigated else ""),
            }
        )

    return sorted(table, key=lambda row: float(row["max_attacked_impact"] or 0.0), reverse=True)


def plot_recovery(table, output_dir):
    rows = table[:8]
    if not rows:
        return
    labels = [f"{row['scenario']}\n{row['attack']}" for row in rows]
    clean = [float(row["clean_energy_ratio"]) for row in rows]
    attacked = [float(row["attacked_energy_ratio"]) for row in rows]
    mitigated = [float(row["mitigated_energy_ratio"]) for row in rows]
    x = list(range(len(rows)))
    width = 0.24

    fig, ax = plt.subplots(figsize=(11.5, 5.6))
    ax.bar([i - width for i in x], clean, width=width, label="Clean", color="#4c78a8")
    ax.bar(x, attacked, width=width, label="Attacked", color="#c44e52")
    ax.bar([i + width for i in x], mitigated, width=width, label="RL detection + mitigation", color="#55a868")
    ax.set_ylabel("Restored energy ratio")
    ax.set_title("IEEE 34-Bus FDIA Recovery")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=8)
    ax.set_ylim(0.0, max(clean + attacked + mitigated) * 1.12)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_naps34_energy_recovery.png", dpi=220)
    plt.close(fig)


def plot_dynamic(dynamic_rows, output_dir):
    grouped = defaultdict(lambda: defaultdict(list))
    for row in dynamic_rows:
        key = (row.get("scenario", ""), row.get("attack", ""))
        grouped[key][row.get("mode", "")].append(row)

    best_key = None
    best_impact = -1.0
    for key, modes in grouped.items():
        attacked = [row for row in unique_time_rows(modes.get("attacked_unmitigated_dynamic", [])) if valid_dynamic_row(row)]
        if not attacked:
            continue
        impact = max(as_float(row, "physical_impact_score") for row in attacked)
        if impact > best_impact:
            best_key = key
            best_impact = impact

    if best_key is None:
        return

    modes = grouped[best_key]
    attacked = [row for row in unique_time_rows(modes.get("attacked_unmitigated_dynamic", [])) if valid_dynamic_row(row)]
    mitigated = [row for row in unique_time_rows(modes.get("rl_detector_mitigated_dynamic", [])) if valid_dynamic_row(row)]
    time_steps = [as_int(row, "time_step") for row in attacked]
    attacked_impact = [as_float(row, "physical_impact_score") for row in attacked]
    mitigated_impact = [as_float(row, "physical_impact_score") for row in mitigated]

    fig, ax = plt.subplots(figsize=(9.0, 5.0))
    ax.plot(time_steps, attacked_impact, color="#c44e52", linewidth=2.0, label="Attacked")
    if mitigated_impact:
        ax.plot(time_steps, mitigated_impact, color="#55a868", linewidth=2.0, label="RL detection + mitigation")
    ax.set_xlabel("Time step")
    ax.set_ylabel("Physical impact score")
    ax.set_title(f"IEEE 34-Bus Dynamic FDIA Impact: {best_key[0]} {best_key[1]}")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_naps34_dynamic_impact.png", dpi=220)
    plt.close(fig)


def plot_harmful_rate(rows, output_dir):
    if not rows:
        return
    labels = [row["attack"] for row in rows]
    values = [float(row["harmful_rate"]) for row in rows]
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.bar(labels, values, color="#4c78a8")
    ax.set_ylim(0.0, max(0.2, max(values) * 1.25))
    ax.set_ylabel("Harmful-case rate")
    ax.set_title("IEEE 34-Bus Filtered Robustness: Harmful FDIA Rate")
    ax.grid(axis="y", alpha=0.25)
    for index, value in enumerate(values):
        ax.text(index, value + 0.005, f"{value:.3f}", ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_naps34_harmful_rate.png", dpi=220)
    plt.close(fig)


def markdown_table(lines, rows, fields, headers, limit=None):
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows[:limit]:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")


def write_summary(output_dir, physical, recovery, dynamic, trial_summary, detector_summary, filter_report):
    lines = [
        "# NAPS 2026 IEEE 34-Bus FDIA Artifact Summary",
        "",
        "## Experiment Focus",
        "",
        "This artifact set focuses only on the IEEE 34-bus feeder. FDIA is applied to the cyber observation received by the graph RL restoration controller; the selected action is then evaluated on the true OpenDSS feeder. The main attacks emphasized for the NAPS paper are voltage masking and topology drop because they produced the strongest 34-bus degradation.",
        "",
        "## Strongest One-Step Physical Degradation",
        "",
    ]
    markdown_table(
        lines,
        physical,
        ["scenario", "attack", "clean_energy_ratio", "attacked_energy_ratio", "energy_loss", "physical_impact_score"],
        ["Scenario", "Attack", "Clean Energy", "Attacked Energy", "Energy Loss", "Impact"],
        limit=10,
    )

    lines.extend(["", "## RL Detection and Mitigation Recovery", ""])
    markdown_table(
        lines,
        recovery,
        [
            "scenario",
            "attack",
            "attacked_energy_ratio",
            "mitigated_energy_ratio",
            "impact_reduction_fraction",
            "detector_predicted",
        ],
        ["Scenario", "Attack", "Attacked Energy", "Mitigated Energy", "Impact Reduction", "Detector"],
        limit=10,
    )

    lines.extend(["", "## Dynamic Loadshape Validation", ""])
    markdown_table(
        lines,
        dynamic,
        ["scenario", "attack", "time_steps", "excluded_time_steps", "max_attacked_impact", "max_mitigated_impact"],
        ["Scenario", "Attack", "Steps", "Excluded", "Max Attacked Impact", "Max Mitigated Impact"],
        limit=10,
    )

    lines.extend(["", "## Filtered Robustness Statistics", ""])
    markdown_table(
        lines,
        trial_summary,
        ["attack", "trials", "harmful_cases", "harmful_rate", "harmful_rate_ci_low", "harmful_rate_ci_high", "max_impact"],
        ["Attack", "Trials", "Harmful", "Rate", "CI Low", "CI High", "Max Impact"],
    )

    lines.extend(["", "## RL Detector Summary", ""])
    markdown_table(
        lines,
        detector_summary,
        ["samples", "correct", "accuracy", "accuracy_ci_low", "accuracy_ci_high", "harmful_recovery_samples", "mean_impact_reduction"],
        ["Samples", "Correct", "Accuracy", "CI Low", "CI High", "Harmful Recovery Samples", "Mean Impact Reduction"],
    )

    lines.extend(["", "## Filter Accounting", ""])
    markdown_table(lines, filter_report, ["item", "count", "details"], ["Item", "Count", "Details"])

    lines.extend(
        [
            "",
            "## Paper-Safe Interpretation",
            "",
            "The 34-bus feeder shows attack-dependent vulnerability. Voltage masking produced the strongest paper-valid one-step physical degradation in the focused search, and topology drop also produced harmful cases. The RL detector correctly classified the selected recovery cases, and reference-assisted channel mitigation restored the top one-step cases to the clean physical outcome. Dynamic loadshape replay shows that some high-impact one-step cases do not persist dynamically, while selected voltage-masking and topology-drop cases still show time-varying degradation that is reduced or removed by mitigation.",
            "",
            "The mitigation remains reference/state-estimator-assisted, and the dynamic validation is quasi-static OpenDSS loadshape simulation rather than transient stability analysis.",
        ]
    )

    (output_dir / "naps34_summary.md").write_text("\n".join(lines) + "\n")


def main():
    args = parse_args()
    results_dir = Path(args.results_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    physical_rows = read_csv(results_dir / "fdia_physical_impact_34bus_top.csv")
    recovery_rows = read_csv(results_dir / "rl_fdia_resilience_34bus_top.csv")
    dynamic_rows_raw = read_csv(results_dir / "rl_fdia_resilience_dynamic_34bus_top.csv")
    robustness_dir = results_dir / "robustness_validation"
    trial_summary = read_csv(robustness_dir / "robustness_trial_summary_filtered.csv")
    detector_summary = read_csv(robustness_dir / "robustness_detector_summary_filtered.csv")
    filter_report = read_csv(robustness_dir / "robustness_filter_report.csv")

    physical = physical_table(physical_rows)
    recovery = recovery_table(recovery_rows)
    dynamic = dynamic_table(dynamic_rows_raw)

    write_csv(
        output_dir / "table_naps34_physical_degradation.csv",
        physical,
        [
            "scenario",
            "attack",
            "clean_energy_ratio",
            "attacked_energy_ratio",
            "energy_loss",
            "clean_energy_kw",
            "attacked_energy_kw",
            "energy_kw_loss",
            "physical_impact_score",
            "voltage_violation_delta",
            "action_changed",
            "switch_changes",
            "load_changes",
            "bdd_score",
            "bdd_detected_channels",
        ],
    )
    write_csv(
        output_dir / "table_naps34_recovery.csv",
        recovery,
        [
            "scenario",
            "attack",
            "clean_energy_ratio",
            "attacked_energy_ratio",
            "mitigated_energy_ratio",
            "screened_energy_ratio",
            "attacked_impact_score",
            "mitigated_impact_score",
            "screened_impact_score",
            "energy_recovery_fraction",
            "impact_reduction_fraction",
            "detector_expected",
            "detector_predicted",
            "detector_correct",
            "mitigation_applied",
        ],
    )
    write_csv(
        output_dir / "table_naps34_dynamic.csv",
        dynamic,
        [
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
        ],
    )

    plot_recovery(recovery, output_dir)
    plot_dynamic(dynamic_rows_raw, output_dir)
    plot_harmful_rate(trial_summary, output_dir)
    write_summary(output_dir, physical, recovery, dynamic, trial_summary, detector_summary, filter_report)

    print("Generated NAPS 34-bus artifacts in: {}".format(output_dir))
    print("Physical cases: {}".format(len(physical)))
    print("Recovery cases: {}".format(len(recovery)))
    print("Dynamic cases: {}".format(len(dynamic)))


if __name__ == "__main__":
    main()
