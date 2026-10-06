"""Build paper-facing IEEE 123 TSG vulnerability artifacts.

This script reads the completed IEEE 123 simulation outputs and creates
paper-ready tables, figures, a concise narrative, an evidence audit, and a
freeze marker. It does not rerun restoration simulations.
"""

import argparse
import csv
import json
import math
import textwrap
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_RESULTS_DIR = BASE_DIR / "paper_results" / "tsg_ieee123"
RESULTS_DIR = DEFAULT_RESULTS_DIR


def choose_existing_dir(results_dir, *names):
    for name in names:
        path = results_dir / name
        if path.exists():
            return path
    return results_dir / names[0]


def is_bpso_results_dir(results_dir):
    return "bpso" in str(results_dir).lower()


def filter_scoped_missing_inputs(missing_inputs, results_dir):
    if not is_bpso_results_dir(results_dir):
        return sorted(set(missing_inputs)), []
    scoped_markers = [
        "/full_criticality_merged/voltage/",
        "/full_criticality_merged/branchflow/",
        "/branchflow_subset_ablation/",
    ]
    retained = []
    scoped_out = []
    for item in sorted(set(missing_inputs)):
        normalized = item.replace("\\", "/")
        if any(marker in normalized for marker in scoped_markers):
            scoped_out.append(item)
        else:
            retained.append(item)
    return retained, scoped_out


def claim_boundary_for(results_dir, row_counts):
    if is_bpso_results_dir(results_dir):
        return (
            "Completed IEEE 123 BPSO p2/i2 evidence only: the 30-case "
            "baseline attack-family study, the 41-target action-mask/status "
            "criticality study, defense-stress summary, and advanced mitigation "
            "ablation are complete. Voltage, branchflow, topology, and energy "
            "false-data channels are not claimed as direct BPSO decision "
            "vulnerabilities because this BPSO objective uses ActionMasking as "
            "the decision-relevant observation constraint."
        )
    if row_counts.get("voltage_single", 0) and row_counts.get("branchflow_single", 0):
        return (
            "Completed IEEE 123 direct controller-observation evidence only; "
            "action-mask, voltage, and branchflow single-observation criticality "
            "are exhaustive over the current target registries."
        )
    return (
        "Completed IEEE 123 direct controller-observation evidence for the "
        "available input studies only; empty or scoped-out observation channels "
        "should not be claimed as exhaustive."
    )


def freeze_status_for(results_dir):
    if is_bpso_results_dir(results_dir):
        return (
            "IEEE 123 BPSO is frozen as a scoped p2/i2 controller-comparison "
            "evidence package: the 30-case baseline, 41 action-mask targets, "
            "defense-stress summary, and advanced mitigation ablation are complete."
        )
    return (
        "IEEE 123 is frozen as the second completed TSG vulnerability-assessment "
        "case study, with post-freeze exhaustive action-mask and branchflow "
        "criticality completed."
    )


def build_inputs(results_dir):
    baseline_dir = choose_existing_dir(
        results_dir,
        "baseline_attack_full_deterministic",
        "baseline_attack_full_deterministic_p2_i2",
    )
    criticality_dir = choose_existing_dir(
        results_dir,
        "full_criticality_merged",
        "full_criticality_merged_partial",
    )
    defense_dir = choose_existing_dir(
        results_dir,
        "defense_stress_summary_exhaustive_criticality",
        "defense_stress_summary",
        "defense_stress_summary_partial",
    )
    advanced_dir = choose_existing_dir(
        results_dir,
        "advanced_mitigation_ablation_exhaustive_criticality",
        "advanced_mitigation_ablation_partial",
    )
    return {
        "baseline_attack_ranking": baseline_dir / "tsg_ieee123_attack_ranking.csv",
        "baseline_cases": baseline_dir / "tsg_ieee123_case_summary.csv",
        "baseline_manifest": baseline_dir / "tsg_ieee123_manifest.json",
        "action_mask_ranking": criticality_dir
    / "action_mask"
    / "tsg_ieee123_action_mask_criticality_ranking.csv",
        "action_mask_manifest": criticality_dir
    / "action_mask"
    / "tsg_ieee123_action_mask_criticality_manifest.json",
        "voltage_single_ranking": criticality_dir
    / "voltage"
    / "tsg_ieee123_measurement_criticality_ranking.csv",
        "voltage_single_manifest": criticality_dir
    / "voltage"
    / "tsg_ieee123_measurement_criticality_manifest.json",
        "branchflow_single_ranking": criticality_dir
    / "branchflow"
    / "tsg_ieee123_measurement_criticality_ranking.csv",
        "branchflow_single_manifest": criticality_dir
    / "branchflow"
    / "tsg_ieee123_measurement_criticality_manifest.json",
        "branchflow_subset_summary": results_dir
    / "branchflow_subset_ablation"
    / "tsg_ieee123_branchflow_subset_ablation_k_summary.csv",
        "branchflow_subset_manifest": results_dir
    / "branchflow_subset_ablation"
    / "tsg_ieee123_branchflow_subset_ablation_manifest.json",
        "defense_stress_group_summary": defense_dir / "tsg_ieee123_defense_stress_group_summary.csv",
        "defense_stress_low_recovery": defense_dir / "tsg_ieee123_defense_stress_low_recovery_cases.csv",
        "defense_stress_manifest": defense_dir / "tsg_ieee123_defense_stress_manifest.json",
        "advanced_mitigation_summary": advanced_dir / "tsg_ieee123_advanced_mitigation_variant_summary.csv",
        "advanced_mitigation_best_by_case": advanced_dir / "tsg_ieee123_advanced_mitigation_best_by_case.csv",
        "advanced_mitigation_manifest": advanced_dir / "tsg_ieee123_advanced_mitigation_manifest.json",
    }


INPUTS = build_inputs(RESULTS_DIR)


def resolve_path(path_text, default):
    if not path_text:
        return default
    path = Path(path_text)
    if path.is_absolute():
        return path
    return (BASE_DIR / path).resolve()


def relative(path):
    try:
        return str(Path(path).resolve().relative_to(BASE_DIR))
    except ValueError:
        return str(path)


def read_csv(path, missing):
    if not path.exists():
        missing.append(relative(path))
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def read_json(path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def safe_float(value, default=0.0):
    if value is None or value == "":
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return number


def safe_int(value, default=0):
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def pct(value):
    return 100.0 * safe_float(value)


def fmt(value):
    if isinstance(value, float):
        return "{:.3f}".format(value)
    if isinstance(value, int):
        return str(value)
    text = "" if value is None else str(value)
    try:
        number = float(text)
    except (TypeError, ValueError):
        return text
    if not math.isfinite(number):
        return text
    if abs(number - round(number)) < 1.0e-9 and abs(number) < 1000000:
        return str(int(round(number)))
    return "{:.3f}".format(number)


def round_row(row, fields):
    rounded = {}
    for field in fields:
        value = row.get(field, "")
        if isinstance(value, float):
            rounded[field] = round(value, 6)
        else:
            rounded[field] = value
    return rounded


def markdown_table(rows, columns, limit=None):
    rows = rows[:limit] if limit is not None else rows
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    lines = [header, sep]
    for row in rows:
        cells = []
        for column in columns:
            cell = fmt(row.get(column, "")).replace("|", "/")
            cells.append(cell)
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_table_bundle(table_dir, name, rows, columns, title, md_limit=20):
    csv_path = table_dir / "{}.csv".format(name)
    md_path = table_dir / "{}.md".format(name)
    clipped_rows = [round_row(row, columns) for row in rows]
    write_csv(csv_path, clipped_rows, columns)
    body = ["# {}".format(title), "", markdown_table(clipped_rows, columns, md_limit), ""]
    if len(clipped_rows) > md_limit:
        body.append("Markdown preview shows first {} of {} rows.".format(md_limit, len(clipped_rows)))
        body.append("")
    write_text(md_path, "\n".join(body))
    return [relative(csv_path), relative(md_path)]


def sort_rows(rows, field, reverse=True):
    return sorted(rows, key=lambda row: safe_float(row.get(field)), reverse=reverse)


def normalize_attack_family(rows):
    out = []
    for row in rows:
        out.append(
            {
                "damage_rank": safe_int(row.get("damage_rank")),
                "attack": row.get("attack", ""),
                "case_count": safe_int(row.get("case_count")),
                "mean_degradation_kwh": safe_float(row.get("mean_physical_degradation_kwh")),
                "total_degradation_kwh": safe_float(row.get("total_physical_degradation_kwh")),
                "max_degradation_kwh": safe_float(row.get("max_physical_degradation_kwh")),
                "damaging_cases": safe_int(row.get("damaging_case_count")),
                "damaging_case_rate_pct": pct(row.get("damaging_case_rate")),
                "detection_rate_pct": pct(row.get("detection_rate")),
                "mitigation_recovery_pct": pct(
                    row.get("mean_mitigation_recovery_of_degradation_ratio_clipped")
                ),
                "mean_accidental_improvement_kwh": safe_float(
                    row.get("mean_accidental_improvement_kwh")
                ),
            }
        )
    return sorted(out, key=lambda row: row["damage_rank"] or 999999)


def normalize_worst_cases(rows, limit=20):
    out = []
    for row in sort_rows(rows, "physical_degradation_kwh")[:limit]:
        out.append(
            {
                "case_id": row.get("case_id", ""),
                "attack": row.get("attack", ""),
                "scenario_seed": safe_int(row.get("scenario_seed")),
                "physical_degradation_kwh": safe_float(row.get("physical_degradation_kwh")),
                "restored_energy_loss_kwh": safe_float(row.get("restored_energy_loss_kwh")),
                "residual_after_mitigation_kwh": safe_float(
                    row.get("residual_degradation_after_mitigation_kwh")
                ),
                "fdia_detected": safe_int(row.get("fdia_detected")),
                "mitigation_recovery_pct": pct(
                    row.get("mitigation_recovery_of_degradation_ratio_clipped")
                ),
                "attacked_action_changed": safe_int(row.get("attacked_action_changed")),
                "switch_changes_vs_clean": safe_int(row.get("attacked_switch_changes_vs_clean")),
                "load_changes_vs_clean": safe_int(row.get("attacked_load_changes_vs_clean")),
            }
        )
    return out


def normalize_action_mask(rows):
    out = []
    for row in rows:
        out.append(
            {
                "target_observation_id": row.get("target_observation_id", ""),
                "component_type": row.get("target_component_type", ""),
                "component_name": row.get("target_component_name", ""),
                "case_count": safe_int(row.get("case_count")),
                "attack_applied_count": safe_int(row.get("attack_applied_count")),
                "mean_degradation_kwh": safe_float(row.get("mean_physical_degradation_kwh")),
                "max_degradation_kwh": safe_float(row.get("max_physical_degradation_kwh")),
                "damaging_cases": safe_int(row.get("damaging_case_count")),
                "detection_rate_pct": pct(row.get("detection_rate")),
                "mitigation_recovery_pct": pct(
                    row.get("mean_mitigation_recovery_of_degradation_ratio_clipped")
                ),
            }
        )
    return sort_rows(out, "mean_degradation_kwh")


def normalize_branchflow_single(rows):
    out = []
    for row in rows:
        out.append(
            {
                "target_observation_id": row.get("target_observation_id", ""),
                "component_name": row.get("target_component_name", ""),
                "measurement_index": safe_int(row.get("target_measurement_index")),
                "case_count": safe_int(row.get("case_count")),
                "attack_applied_count": safe_int(row.get("attack_applied_count")),
                "mean_degradation_kwh": safe_float(row.get("mean_physical_degradation_kwh")),
                "max_degradation_kwh": safe_float(row.get("max_physical_degradation_kwh")),
                "damaging_cases": safe_int(row.get("damaging_case_count")),
                "detection_rate_pct": pct(row.get("detection_rate")),
                "mitigation_recovery_pct": pct(
                    row.get("mean_mitigation_recovery_of_degradation_ratio_clipped")
                ),
            }
        )
    return sort_rows(out, "mean_degradation_kwh")


def subset_sort_key(row):
    label = str(row.get("subset_k", "")).lower()
    if label == "full":
        return 10**9
    return safe_int(label)


def normalize_branchflow_subset(rows):
    out = []
    for row in rows:
        out.append(
            {
                "subset_k": row.get("subset_k", ""),
                "case_count": safe_int(row.get("case_count")),
                "mean_selected_count": safe_float(row.get("mean_selected_count")),
                "total_degradation_kwh": safe_float(row.get("total_physical_degradation_kwh")),
                "mean_degradation_kwh": safe_float(row.get("mean_physical_degradation_kwh")),
                "max_degradation_kwh": safe_float(row.get("max_physical_degradation_kwh")),
                "damaging_cases": safe_int(row.get("damaging_case_count")),
                "total_baseline_reproduction_pct": pct(row.get("total_baseline_reproduction_ratio")),
                "detection_rate_pct": pct(row.get("detection_rate")),
                "mitigation_recovery_pct": pct(
                    row.get("mean_mitigation_recovery_of_degradation_ratio_clipped")
                ),
            }
        )
    return sorted(out, key=subset_sort_key)


def normalize_defense_stress(rows):
    out = []
    for row in rows:
        source_study = row.get("source_study", "")
        if source_study.endswith("_partial"):
            source_study = source_study[: -len("_partial")]
        out.append(
            {
                "source_study": source_study,
                "attack_group": row.get("attack_group", ""),
                "case_count": safe_int(row.get("case_count")),
                "damaging_cases": safe_int(row.get("damaging_case_count")),
                "detection_rate_pct": pct(row.get("detection_rate")),
                "detection_rate_on_damaging_pct": pct(row.get("detection_rate_on_damaging_cases")),
                "bypass_high_impact_count": safe_int(row.get("bypass_high_impact_count")),
                "total_degradation_kwh": safe_float(row.get("total_physical_degradation_kwh")),
                "max_degradation_kwh": safe_float(row.get("max_physical_degradation_kwh")),
                "total_residual_kwh": safe_float(
                    row.get("total_residual_degradation_after_mitigation_kwh")
                ),
                "total_recovery_pct": pct(row.get("total_recovery_ratio_on_positive_degradation")),
                "worst_case_id": row.get("worst_case_id", ""),
                "worst_case_residual_kwh": safe_float(
                    row.get("worst_case_residual_degradation_kwh")
                ),
            }
        )
    return sorted(
        out,
        key=lambda row: (row["total_residual_kwh"], row["total_degradation_kwh"]),
        reverse=True,
    )


def normalize_advanced_mitigation(rows):
    out = []
    for row in rows:
        out.append(
            {
                "variant": row.get("variant", ""),
                "variant_family": row.get("variant_family", ""),
                "case_count": safe_int(row.get("case_count")),
                "total_attacked_degradation_kwh": safe_float(
                    row.get("total_attacked_physical_degradation_kwh")
                ),
                "total_residual_kwh": safe_float(row.get("total_variant_residual_degradation_kwh")),
                "max_residual_kwh": safe_float(row.get("max_variant_residual_degradation_kwh")),
                "total_recovered_kwh": safe_float(row.get("total_variant_degradation_recovered_kwh")),
                "total_recovery_pct": pct(row.get("total_recovery_ratio_clipped")),
                "cases_improved_vs_current": safe_int(row.get("cases_improved_vs_current")),
                "cases_worse_vs_current": safe_int(row.get("cases_worse_vs_current")),
                "total_residual_reduction_vs_current_kwh": safe_float(
                    row.get("total_residual_reduction_vs_current_kwh")
                ),
            }
        )
    return sorted(out, key=lambda row: (row["total_residual_kwh"], -row["total_recovery_pct"]))


def normalize_best_mitigation_cases(rows):
    out = []
    for row in rows:
        out.append(
            {
                "source_case_id": row.get("source_case_id", ""),
                "source_attack_group": row.get("source_attack_group", ""),
                "source_attack": row.get("source_attack", ""),
                "subset_k": row.get("subset_k", ""),
                "scenario_seed": safe_int(row.get("scenario_seed")),
                "best_variant": row.get("best_variant", ""),
                "current_residual_kwh": safe_float(row.get("current_residual_degradation_kwh")),
                "best_residual_kwh": safe_float(row.get("best_residual_degradation_kwh")),
                "residual_reduction_kwh": safe_float(
                    row.get("best_residual_reduction_vs_current_kwh")
                ),
                "best_recovery_pct": pct(row.get("best_recovery_ratio_clipped")),
            }
        )
    return sort_rows(out, "residual_reduction_kwh")


def build_evidence_audit(raw_inputs, missing_inputs):
    roles = {
        "baseline_attack_ranking": "Which attack families are most damaging?",
        "baseline_cases": "Worst individual attack cases and restored-energy loss.",
        "action_mask_ranking": "Critical switch/load status observations completed so far.",
        "voltage_single_ranking": "Critical bus-voltage observations completed so far.",
        "branchflow_single_ranking": "Critical single branchflow observations completed so far.",
        "branchflow_subset_summary": "Coordinated branchflow sensitivity/ablation.",
        "defense_stress_group_summary": "Detection, bypass, residual-risk summary.",
        "defense_stress_low_recovery": "Hard cases for advanced mitigation.",
        "advanced_mitigation_summary": "Advanced mitigation variant comparison.",
        "advanced_mitigation_best_by_case": "Best mitigation strategy per residual case.",
    }
    rows = []
    for name, path in INPUTS.items():
        if path.suffix.lower() == ".csv":
            rows.append(
                {
                    "input_id": name,
                    "path": relative(path),
                    "exists": int(path.exists()),
                    "row_count": len(raw_inputs.get(name, [])),
                    "paper_role": roles.get(name, "Manifest/provenance."),
                    "status_note": "available" if path.exists() else "missing",
                }
            )
        else:
            manifest = read_json(path)
            rows.append(
                {
                    "input_id": name,
                    "path": relative(path),
                    "exists": int(path.exists()),
                    "row_count": 1 if manifest else 0,
                    "paper_role": roles.get(name, "Manifest/provenance."),
                    "status_note": "available" if path.exists() else "missing",
                }
            )
    if missing_inputs:
        rows.append(
            {
                "input_id": "missing_input_count",
                "path": "",
                "exists": 0,
                "row_count": len(missing_inputs),
                "paper_role": "Artifact completeness check.",
                "status_note": "; ".join(sorted(set(missing_inputs))),
            }
        )
    return rows


def import_matplotlib(manifest):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        return plt
    except Exception as exc:
        manifest.setdefault("figure_notes", []).append(
            "Matplotlib unavailable; figures were not generated: {}".format(exc)
        )
        return None


def short_label(text, width=42):
    text = str(text).replace("_", " ")
    return textwrap.shorten(text, width=width, placeholder="...")


def plot_horizontal_bar(plt, rows, label_field, value_field, path, title, xlabel, limit=12):
    selected = sort_rows(rows, value_field)[:limit]
    selected = list(reversed(selected))
    labels = [short_label(row.get(label_field, "")) for row in selected]
    values = [safe_float(row.get(value_field)) for row in selected]
    height = max(4.2, 0.43 * len(selected) + 1.5)
    fig, ax = plt.subplots(figsize=(9.2, height))
    ax.barh(labels, values, color="#2f6f8f")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.grid(axis="x", alpha=0.25)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def plot_branchflow_subset(plt, rows, path):
    labels = [str(row["subset_k"]) for row in rows]
    totals = [row["total_degradation_kwh"] for row in rows]
    reproduction = [row["total_baseline_reproduction_pct"] for row in rows]
    fig, ax1 = plt.subplots(figsize=(8.4, 4.8))
    x_positions = list(range(len(rows)))
    ax1.bar(x_positions, totals, color="#2f6f8f", label="Total degradation")
    ax1.set_ylabel("Total physical degradation (kWh)")
    ax1.set_xticks(x_positions)
    ax1.set_xticklabels(labels)
    ax1.grid(axis="y", alpha=0.25)
    ax2 = ax1.twinx()
    ax2.plot(x_positions, reproduction, color="#c66b3d", marker="o", label="Baseline reproduction")
    ax2.set_ylabel("Baseline reproduction (%)")
    ax1.set_title("IEEE 123 Coordinated Branchflow Top-k Ablation")
    for spine in ("top",):
        ax1.spines[spine].set_visible(False)
        ax2.spines[spine].set_visible(False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def plot_advanced_mitigation(plt, rows, path):
    labels = [short_label(row["variant"], 28) for row in rows]
    residuals = [row["total_residual_kwh"] for row in rows]
    recovered = [row["total_recovered_kwh"] for row in rows]
    x_positions = list(range(len(rows)))
    width = 0.38
    fig, ax = plt.subplots(figsize=(10.0, 5.0))
    ax.bar([x - width / 2 for x in x_positions], residuals, width, color="#c66b3d", label="Residual")
    ax.bar([x + width / 2 for x in x_positions], recovered, width, color="#2f6f8f", label="Recovered")
    ax.set_title("IEEE 123 Advanced Mitigation Ablation")
    ax.set_ylabel("Energy (kWh)")
    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def generate_figures(
    figure_dir,
    manifest,
    attack_rows,
    action_rows,
    voltage_rows,
    branchflow_rows,
    branchflow_subset_rows,
    defense_rows,
    advanced_rows,
):
    plt = import_matplotlib(manifest)
    if plt is None:
        return []
    paths = {
        "attack_family": figure_dir / "fig_01_attack_family_degradation.png",
        "action_mask": figure_dir / "fig_02_action_mask_criticality.png",
        "voltage_single": figure_dir / "fig_03_voltage_single_criticality.png",
        "branchflow_single": figure_dir / "fig_04_branchflow_single_criticality.png",
        "branchflow_subset": figure_dir / "fig_05_branchflow_subset_ablation.png",
        "defense_residual": figure_dir / "fig_06_defense_residual_risk.png",
        "advanced_mitigation": figure_dir / "fig_07_advanced_mitigation_ablation.png",
    }
    created = []
    plot_horizontal_bar(
        plt,
        attack_rows,
        "attack",
        "mean_degradation_kwh",
        paths["attack_family"],
        "IEEE 123 Attack-Family Degradation",
        "Mean physical degradation (kWh)",
        limit=8,
    )
    created.append(paths["attack_family"])
    plot_horizontal_bar(
        plt,
        action_rows,
        "target_observation_id",
        "mean_degradation_kwh",
        paths["action_mask"],
        "IEEE 123 Action-Mask Observation Criticality",
        "Mean physical degradation (kWh)",
        limit=10,
    )
    created.append(paths["action_mask"])
    if voltage_rows:
        plot_horizontal_bar(
            plt,
            voltage_rows,
            "target_observation_id",
            "mean_degradation_kwh",
            paths["voltage_single"],
            "IEEE 123 Voltage Observation Criticality",
            "Mean physical degradation (kWh)",
            limit=10,
        )
        created.append(paths["voltage_single"])
    if branchflow_rows:
        plot_horizontal_bar(
            plt,
            branchflow_rows,
            "target_observation_id",
            "mean_degradation_kwh",
            paths["branchflow_single"],
            "IEEE 123 Branchflow Observation Criticality",
            "Mean physical degradation (kWh)",
            limit=10,
        )
        created.append(paths["branchflow_single"])
    if branchflow_subset_rows:
        plot_branchflow_subset(plt, branchflow_subset_rows, paths["branchflow_subset"])
        created.append(paths["branchflow_subset"])
    if defense_rows:
        plot_horizontal_bar(
            plt,
            defense_rows,
            "attack_group",
            "total_residual_kwh",
            paths["defense_residual"],
            "IEEE 123 Defense Residual Risk",
            "Total residual degradation after mitigation (kWh)",
            limit=12,
        )
        created.append(paths["defense_residual"])
    if advanced_rows:
        plot_advanced_mitigation(plt, advanced_rows, paths["advanced_mitigation"])
        created.append(paths["advanced_mitigation"])
    return [relative(path) for path in created if path.exists()]


def first_row(rows):
    return rows[0] if rows else {}


def build_narrative(
    attack_rows,
    worst_case_rows,
    action_rows,
    voltage_rows,
    branchflow_rows,
    branchflow_subset_rows,
    defense_rows,
    advanced_rows,
    best_case_rows,
    audit_rows,
    missing_inputs,
    claim_boundary,
):
    top_attack = first_row(attack_rows)
    top_case = first_row(worst_case_rows)
    top_action = first_row(action_rows)
    top_voltage = first_row(voltage_rows)
    top_branchflow = first_row(branchflow_rows)
    top_defense = first_row(defense_rows)
    best_mitigation = first_row(best_case_rows)
    current_rows = [row for row in advanced_rows if row["variant"] == "current_one_step_fdia_aware"]
    detector_rows = [row for row in advanced_rows if row["variant"] == "detector_mitigated_only"]
    current = first_row(current_rows)
    detector = first_row(detector_rows)
    defense_total_residual_kwh = sum(row["total_residual_kwh"] for row in defense_rows)
    defense_bypass_count = sum(row["bypass_high_impact_count"] for row in defense_rows)
    completed_studies = ["baseline five attack families"]
    if action_rows:
        completed_studies.append("exhaustive action-mask criticality")
    if voltage_rows:
        completed_studies.append("exhaustive voltage single-observation criticality")
    if branchflow_rows:
        completed_studies.append(
            "exhaustive branchflow single-observation criticality over applicable cases"
        )
    if branchflow_subset_rows:
        completed_studies.append("coordinated branchflow top-k ablation")
    if defense_rows:
        completed_studies.append("defense-stress summarization")
    if advanced_rows:
        completed_studies.append("advanced mitigation ablation")
    lines = [
        "# IEEE 123 TSG Vulnerability Assessment Results Narrative",
        "",
        "Generated: {}".format(datetime.now().isoformat(timespec="seconds")),
        "",
        "## Evidence Boundary",
        "",
        "This IEEE 123 package uses the completed IEEE 123 evidence only. It does not use IEEE 34 results as simulation data, and it does not claim IEEE 8500 behavior.",
        "",
        claim_boundary,
        "",
        "The completed IEEE 123 observation studies include {}.".format(
            ", ".join(completed_studies)
        ),
        "",
        "## Which Attacks Are Most Damaging?",
        "",
    ]
    if top_attack:
        lines.append(
            "`{}` is the most damaging baseline attack family with mean degradation {:.3f} kWh, total degradation {:.3f} kWh, maximum degradation {:.3f} kWh, and {} damaging cases out of {}.".format(
                top_attack["attack"],
                top_attack["mean_degradation_kwh"],
                top_attack["total_degradation_kwh"],
                top_attack["max_degradation_kwh"],
                top_attack["damaging_cases"],
                top_attack["case_count"],
            )
        )
    if top_case:
        lines.append(
            "The largest single baseline case is `{}` under `{}`, with {:.3f} kWh physical degradation.".format(
                top_case["case_id"],
                top_case["attack"],
                top_case["physical_degradation_kwh"],
            )
        )
    lines.extend(["", "## Which Observations Are Most Critical?", ""])
    if top_action:
        lines.append(
            "Among completed action-mask targets, `{}` is the most critical with mean degradation {:.3f} kWh and maximum degradation {:.3f} kWh.".format(
                top_action["target_observation_id"],
                top_action["mean_degradation_kwh"],
                top_action["max_degradation_kwh"],
            )
        )
    if top_voltage:
        lines.append(
            "Among completed voltage targets, `{}` is the most critical with mean degradation {:.3f} kWh and maximum degradation {:.3f} kWh.".format(
                top_voltage["target_observation_id"],
                top_voltage["mean_degradation_kwh"],
                top_voltage["max_degradation_kwh"],
            )
        )
    if top_branchflow:
        lines.append(
            "Among completed branchflow single-observation targets, `{}` is the most critical with mean degradation {:.3f} kWh and maximum degradation {:.3f} kWh.".format(
                top_branchflow["target_observation_id"],
                top_branchflow["mean_degradation_kwh"],
                top_branchflow["max_degradation_kwh"],
            )
        )
    if branchflow_subset_rows:
        lines.append(
            "The coordinated branchflow subset ablation tests whether branchflow vulnerability is driven by groups of observations rather than one individual sensor."
        )
        full_rows = [row for row in branchflow_subset_rows if str(row["subset_k"]).lower() == "full"]
        k10_rows = [row for row in branchflow_subset_rows if str(row["subset_k"]).lower() == "10"]
        k3_rows = [row for row in branchflow_subset_rows if str(row["subset_k"]).lower() == "3"]
        if k3_rows:
            row = k3_rows[0]
            lines.append(
                "At k=3, coordinated branchflow hiding reproduces {:.1f}% of the baseline branchflow degradation.".format(
                    row["total_baseline_reproduction_pct"]
                )
            )
        if k10_rows:
            row = k10_rows[0]
            lines.append(
                "At k=10, coordinated branchflow hiding reproduces {:.1f}% of the baseline branchflow degradation.".format(
                    row["total_baseline_reproduction_pct"]
                )
            )
        if full_rows:
            row = full_rows[0]
            lines.append(
                "The full selected branchflow subset reaches {:.1f}% reproduction with total degradation {:.3f} kWh.".format(
                    row["total_baseline_reproduction_pct"],
                    row["total_degradation_kwh"],
                )
            )
    else:
        lines.append(
            "A coordinated branchflow subset ablation is not available in this artifact package, so coordinated branchflow conclusions should not be claimed from this package alone."
        )
    lines.extend(["", "## How Much Restored Energy Is Lost?", ""])
    lines.append(
        "Use physical degradation in kWh as the primary damage metric. It measures positive restored-energy loss relative to the clean restoration outcome and avoids overstating cases where an attack accidentally improves restoration."
    )
    if top_defense and top_defense["total_residual_kwh"] > 1.0e-9:
        lines.append(
            "The largest residual-risk defense group is `{}` from `{}`, with total degradation {:.3f} kWh and residual degradation {:.3f} kWh after mitigation.".format(
                top_defense["attack_group"],
                top_defense["source_study"],
                top_defense["total_degradation_kwh"],
                top_defense["total_residual_kwh"],
            )
        )
    elif defense_rows:
        lines.append(
            "Across the completed defense-stress groups, mitigation left {:.3f} kWh residual degradation after detected damaging attacks.".format(
                defense_total_residual_kwh
            )
        )
    lines.extend(["", "## Detection and Mitigation", ""])
    if defense_rows:
        if defense_bypass_count == 0 and defense_total_residual_kwh <= 1.0e-9:
            lines.append(
                "The completed IEEE 123 defense-stress evidence found zero high-impact detection bypass cases and zero residual restored-energy degradation after mitigation among the damaging completed cases."
            )
        elif defense_bypass_count == 0:
            lines.append(
                "The completed IEEE 123 defense-stress evidence found zero high-impact detection bypass cases among the damaging completed cases. The remaining weakness is residual mitigation loss after detection."
            )
        else:
            lines.append(
                "The completed IEEE 123 defense-stress evidence found {} high-impact detection bypass cases; those cases should be treated as the primary defense gap.".format(
                    defense_bypass_count
                )
            )
    else:
        lines.append(
            "Dedicated defense-stress and advanced-mitigation studies are not available in this artifact package yet; use the baseline and criticality detection/recovery columns only as current detector/mitigation evidence."
        )
    if current and detector:
        lines.append(
            "On the {} detected low-recovery cases, the current one-step FDIA-aware selector left {:.3f} kWh residual degradation, while `detector_mitigated_only` reduced residual degradation to {:.3f} kWh and recovered {:.3f} kWh.".format(
                current["case_count"],
                current["total_residual_kwh"],
                detector["total_residual_kwh"],
                detector["total_recovered_kwh"],
            )
        )
    if best_mitigation:
        lines.append(
            "The best-case mitigation table shows the largest individual recovery for `{}`, reducing residual loss by {:.3f} kWh.".format(
                best_mitigation["source_case_id"],
                best_mitigation["residual_reduction_kwh"],
            )
        )
    lines.extend(
        [
            "",
            "## Recommended Manuscript Use",
            "",
            "Use Table 1 for attack-family ranking, Table 2 for worst baseline cases, Tables 3-5 for completed critical-observation studies, and Table 10 for the evidence audit. Tables 6-9 should be used only when their source studies are present in the manifest.",
        ]
    )
    if missing_inputs:
        lines.extend(["", "## Missing Inputs", ""])
        lines.extend(["- {}".format(item) for item in missing_inputs])
    lines.extend(["", "## Evidence Audit", ""])
    lines.append("The artifact manifest records {} input/provenance rows.".format(len(audit_rows)))
    return "\n".join(lines) + "\n"


def build_readme(created_tables, created_figures, narrative_path, output_dir, results_dir, claim_boundary):
    return "\n".join(
        [
            "# IEEE 123 Paper Artifacts",
            "",
            "This folder contains paper-facing outputs generated from completed IEEE 123 vulnerability simulations. The source simulations are not rerun by this artifact builder.",
            "",
            "## Key Files",
            "",
            "- Narrative: `{}`".format(relative(narrative_path)),
            "- Manifest: `{}`".format(relative(output_dir / "ieee123_paper_artifacts_manifest.json")),
            "- Freeze marker: `{}`".format(relative(results_dir / "IEEE123_CASE_STUDY_FREEZE.md")),
            "",
            "## Tables",
            "",
            *["- `{}`".format(path) for path in created_tables],
            "",
            "## Figures",
            "",
            *["- `{}`".format(path) for path in created_figures],
            "",
            "## Claim Boundary",
            "",
            claim_boundary,
            "",
        ]
    )


def build_freeze_marker(manifest, output_dir, results_dir):
    row_counts = manifest.get("row_counts", {})
    missing_count = len(manifest.get("missing_inputs", []))
    figure_count = len(manifest.get("figures", []))
    table_bundle_count = int(len(manifest.get("tables", [])) / 2)
    freeze_status = manifest.get("freeze_status", freeze_status_for(results_dir))
    claim_boundary = manifest.get("claim_boundary", claim_boundary_for(results_dir, row_counts))
    freeze_date = str(manifest.get("generated_at", "")).split("T")[0]
    if not freeze_date:
        freeze_date = datetime.now().date().isoformat()
    lines = [
        "# IEEE 123 Case Study Freeze",
        "",
        "Freeze date: {}".format(freeze_date),
        "",
        "Status: {}".format(freeze_status),
        "",
        "This folder is the retained IEEE 123 evidence package:",
        "",
        "```text",
        relative(results_dir),
        "```",
        "",
        "Final paper artifact package:",
        "",
        "```text",
        relative(output_dir),
        "```",
        "",
        "Final manifest:",
        "",
        "```text",
        relative(output_dir / "ieee123_paper_artifacts_manifest.json"),
        "```",
        "",
        "Frozen evidence counts:",
        "",
        "```text",
        "baseline attack-family rows: {}".format(row_counts.get("attack_family", 0)),
        "baseline case rows: {}".format(row_counts.get("baseline_cases", 0)),
        "action-mask criticality rows completed: {} of 41".format(row_counts.get("action_mask", 0)),
        "voltage single-target rows completed: {} of 130".format(row_counts.get("voltage_single", 0)),
        "branchflow single-target ranking rows recorded: {} from the 138-target registry; no-op-only targets do not produce ranking rows".format(row_counts.get("branchflow_single", 0)),
        "branchflow subset ablation rows: {}".format(row_counts.get("branchflow_subset", 0)),
        "defense-stress groups: {}".format(row_counts.get("defense_stress", 0)),
        "advanced mitigation variant rows: {}".format(row_counts.get("advanced_mitigation", 0)),
        "paper table bundles: {}".format(table_bundle_count),
        "paper figures: {}".format(figure_count),
        "missing input files: {}".format(missing_count),
        "```",
        "",
        "Freeze rule:",
        "",
        "```text",
        "Do not overwrite, delete, or reinterpret IEEE 123 result files while implementing IEEE 8500.",
        "Any new IEEE 123 run after this exhaustive-criticality update should be clearly labeled as a later addendum or a new version.",
        "```",
        "",
        "Scientific boundary:",
        "",
        "```text",
        claim_boundary,
        "IEEE 8500 behavior is not claimed here and must be evaluated separately when the files are available.",
        "```",
        "",
    ]
    return "\n".join(lines)


def main():
    global RESULTS_DIR, INPUTS
    parser = argparse.ArgumentParser(
        description="Generate IEEE 123 TSG paper tables, figures, narrative, manifest, and freeze marker."
    )
    parser.add_argument(
        "--results-dir",
        default="paper_results/tsg_ieee123",
        help="Completed IEEE 123 result directory to read from.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory relative to RL_Testing unless absolute; defaults to <results-dir>/paper_artifacts.",
    )
    parser.add_argument(
        "--skip-freeze",
        action="store_true",
        help="Generate artifacts but do not write IEEE123_CASE_STUDY_FREEZE.md.",
    )
    args = parser.parse_args()

    RESULTS_DIR = resolve_path(args.results_dir, DEFAULT_RESULTS_DIR)
    INPUTS = build_inputs(RESULTS_DIR)
    output_dir = resolve_path(args.output_dir, RESULTS_DIR / "paper_artifacts")
    table_dir = output_dir / "tables"
    figure_dir = output_dir / "figures"
    missing_inputs = []
    raw_inputs = {name: read_csv(path, missing_inputs) for name, path in INPUTS.items() if path.suffix == ".csv"}
    missing_inputs, scoped_out_inputs = filter_scoped_missing_inputs(missing_inputs, RESULTS_DIR)

    attack_rows = normalize_attack_family(raw_inputs["baseline_attack_ranking"])
    worst_case_rows = normalize_worst_cases(raw_inputs["baseline_cases"])
    action_rows = normalize_action_mask(raw_inputs["action_mask_ranking"])
    voltage_rows = normalize_branchflow_single(raw_inputs["voltage_single_ranking"])
    branchflow_rows = normalize_branchflow_single(raw_inputs["branchflow_single_ranking"])
    branchflow_subset_rows = normalize_branchflow_subset(raw_inputs["branchflow_subset_summary"])
    defense_rows = normalize_defense_stress(raw_inputs["defense_stress_group_summary"])
    low_recovery_rows = raw_inputs["defense_stress_low_recovery"]
    advanced_rows = normalize_advanced_mitigation(raw_inputs["advanced_mitigation_summary"])
    best_case_rows = normalize_best_mitigation_cases(raw_inputs["advanced_mitigation_best_by_case"])
    audit_rows = build_evidence_audit(raw_inputs, missing_inputs)
    row_counts = {
        "attack_family": len(attack_rows),
        "baseline_cases": len(raw_inputs["baseline_cases"]),
        "worst_baseline_cases_table": len(worst_case_rows),
        "action_mask": len(action_rows),
        "voltage_single": len(voltage_rows),
        "branchflow_single": len(branchflow_rows),
        "branchflow_subset": len(branchflow_subset_rows),
        "defense_stress": len(defense_rows),
        "low_recovery_cases": len(low_recovery_rows),
        "advanced_mitigation": len(advanced_rows),
        "best_mitigation_by_case": len(best_case_rows),
        "evidence_audit": len(audit_rows),
    }
    claim_boundary = claim_boundary_for(RESULTS_DIR, row_counts)

    created_tables = []
    created_tables.extend(
        write_table_bundle(
            table_dir,
            "table_01_attack_family_ranking",
            attack_rows,
            [
                "damage_rank",
                "attack",
                "case_count",
                "mean_degradation_kwh",
                "total_degradation_kwh",
                "max_degradation_kwh",
                "damaging_cases",
                "damaging_case_rate_pct",
                "detection_rate_pct",
                "mitigation_recovery_pct",
            ],
            "Table 1. IEEE 123 Attack-Family Ranking",
        )
    )
    created_tables.extend(
        write_table_bundle(
            table_dir,
            "table_02_worst_baseline_cases",
            worst_case_rows,
            [
                "case_id",
                "attack",
                "scenario_seed",
                "physical_degradation_kwh",
                "restored_energy_loss_kwh",
                "residual_after_mitigation_kwh",
                "fdia_detected",
                "mitigation_recovery_pct",
                "switch_changes_vs_clean",
                "load_changes_vs_clean",
            ],
            "Table 2. IEEE 123 Worst Baseline Attack Cases",
            md_limit=20,
        )
    )
    created_tables.extend(
        write_table_bundle(
            table_dir,
            "table_03_action_mask_criticality_exhaustive",
            action_rows,
            [
                "target_observation_id",
                "component_type",
                "component_name",
                "case_count",
                "attack_applied_count",
                "mean_degradation_kwh",
                "max_degradation_kwh",
                "damaging_cases",
                "detection_rate_pct",
                "mitigation_recovery_pct",
            ],
            "Table 3. IEEE 123 Exhaustive Action-Mask Criticality",
        )
    )
    created_tables.extend(
        write_table_bundle(
            table_dir,
            "table_04_voltage_single_criticality_exhaustive",
            voltage_rows,
            [
                "target_observation_id",
                "component_name",
                "measurement_index",
                "case_count",
                "attack_applied_count",
                "mean_degradation_kwh",
                "max_degradation_kwh",
                "damaging_cases",
                "detection_rate_pct",
                "mitigation_recovery_pct",
            ],
            "Table 4. IEEE 123 Exhaustive Single Voltage Criticality",
            md_limit=20,
        )
    )
    created_tables.extend(
        write_table_bundle(
            table_dir,
            "table_05_branchflow_single_criticality_exhaustive",
            branchflow_rows,
            [
                "target_observation_id",
                "component_name",
                "measurement_index",
                "case_count",
                "attack_applied_count",
                "mean_degradation_kwh",
                "max_degradation_kwh",
                "damaging_cases",
                "detection_rate_pct",
                "mitigation_recovery_pct",
            ],
            "Table 5. IEEE 123 Exhaustive Single Branchflow Criticality",
            md_limit=20,
        )
    )
    created_tables.extend(
        write_table_bundle(
            table_dir,
            "table_06_branchflow_subset_ablation",
            branchflow_subset_rows,
            [
                "subset_k",
                "case_count",
                "mean_selected_count",
                "total_degradation_kwh",
                "mean_degradation_kwh",
                "max_degradation_kwh",
                "damaging_cases",
                "total_baseline_reproduction_pct",
                "detection_rate_pct",
                "mitigation_recovery_pct",
            ],
            "Table 6. IEEE 123 Coordinated Branchflow Subset Ablation",
        )
    )
    created_tables.extend(
        write_table_bundle(
            table_dir,
            "table_07_defense_stress_summary",
            defense_rows,
            [
                "source_study",
                "attack_group",
                "case_count",
                "damaging_cases",
                "detection_rate_pct",
                "detection_rate_on_damaging_pct",
                "bypass_high_impact_count",
                "total_degradation_kwh",
                "total_residual_kwh",
                "total_recovery_pct",
                "worst_case_id",
                "worst_case_residual_kwh",
            ],
            "Table 7. IEEE 123 Detection and Mitigation Stress Summary",
            md_limit=25,
        )
    )
    created_tables.extend(
        write_table_bundle(
            table_dir,
            "table_08_advanced_mitigation_ablation",
            advanced_rows,
            [
                "variant",
                "variant_family",
                "case_count",
                "total_attacked_degradation_kwh",
                "total_residual_kwh",
                "max_residual_kwh",
                "total_recovered_kwh",
                "total_recovery_pct",
                "cases_improved_vs_current",
                "cases_worse_vs_current",
                "total_residual_reduction_vs_current_kwh",
            ],
            "Table 8. IEEE 123 Advanced Mitigation Ablation",
        )
    )
    created_tables.extend(
        write_table_bundle(
            table_dir,
            "table_09_best_mitigation_by_case",
            best_case_rows,
            [
                "source_case_id",
                "source_attack_group",
                "source_attack",
                "subset_k",
                "scenario_seed",
                "best_variant",
                "current_residual_kwh",
                "best_residual_kwh",
                "residual_reduction_kwh",
                "best_recovery_pct",
            ],
            "Table 9. IEEE 123 Best Advanced Mitigation By Case",
        )
    )
    created_tables.extend(
        write_table_bundle(
            table_dir,
            "table_10_evidence_audit",
            audit_rows,
            ["input_id", "path", "exists", "row_count", "paper_role", "status_note"],
            "Table 10. IEEE 123 Evidence Audit",
            md_limit=30,
        )
    )

    manifest = {
        "experiment": "IEEE 123 TSG paper artifact generation",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "output_dir": relative(output_dir),
        "missing_inputs": sorted(set(missing_inputs)),
        "scoped_out_inputs": scoped_out_inputs,
        "source_inputs": {name: relative(path) for name, path in INPUTS.items()},
        "row_counts": row_counts,
        "claim_boundary": claim_boundary,
        "freeze_status": freeze_status_for(RESULTS_DIR),
    }
    created_figures = generate_figures(
        figure_dir,
        manifest,
        attack_rows,
        action_rows,
        voltage_rows,
        branchflow_rows,
        branchflow_subset_rows,
        defense_rows,
        advanced_rows,
    )

    narrative_path = output_dir / "IEEE123_TSG_Paper_Results_Narrative.md"
    write_text(
        narrative_path,
        build_narrative(
            attack_rows,
            worst_case_rows,
            action_rows,
            voltage_rows,
            branchflow_rows,
            branchflow_subset_rows,
            defense_rows,
            advanced_rows,
            best_case_rows,
            audit_rows,
            manifest["missing_inputs"],
            manifest["claim_boundary"],
        ),
    )
    readme_path = output_dir / "README_IEEE123_PaperArtifacts.md"
    write_text(
        readme_path,
        build_readme(
            created_tables,
            created_figures,
            narrative_path,
            output_dir,
            RESULTS_DIR,
            manifest["claim_boundary"],
        ),
    )

    manifest["tables"] = created_tables
    manifest["figures"] = created_figures
    manifest["narrative"] = relative(narrative_path)
    manifest["readme"] = relative(readme_path)
    manifest_path = output_dir / "ieee123_paper_artifacts_manifest.json"
    write_text(manifest_path, json.dumps(manifest, indent=2, sort_keys=True))

    if not args.skip_freeze:
        freeze_path = RESULTS_DIR / "IEEE123_CASE_STUDY_FREEZE.md"
        write_text(freeze_path, build_freeze_marker(manifest, output_dir, RESULTS_DIR))
        manifest["freeze_marker"] = relative(freeze_path)
        write_text(manifest_path, json.dumps(manifest, indent=2, sort_keys=True))

    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
