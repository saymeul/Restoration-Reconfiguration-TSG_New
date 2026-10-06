"""Summarize IEEE 8500 detection and mitigation stress results.

This runner combines the completed IEEE 8500 vulnerability artifacts into one
defense audit:

* baseline attack-family study,
* named action-mask criticality partial results,
* named branchflow single-observation criticality partial results,
* coordinated branchflow top-k subset ablation.

It does not rerun simulations. It only reads existing case-level evidence and
writes normalized detection/mitigation summaries under the IEEE 8500 namespace.
"""

import argparse
import csv
from collections import defaultdict

import numpy as np

from FDIA_ExperimentCore import resolve_path, safe_json, write_csv


CASE_FIELDS = [
    "source_study",
    "attack_category",
    "attack_group",
    "attack",
    "target_observation_id",
    "subset_k",
    "case_id",
    "scenario_seed",
    "damaging_case",
    "improvement_case",
    "fdia_detected",
    "bypass_high_impact",
    "physical_degradation_kwh",
    "restored_energy_loss_kwh",
    "residual_degradation_after_mitigation_kwh",
    "degradation_recovered_kwh",
    "mitigation_recovery_of_degradation_ratio_clipped",
    "detector_score",
    "detected_channels",
    "attacked_action_changed",
    "attacked_switch_changes_vs_clean",
    "attacked_load_changes_vs_clean",
    "mitigation_selected_candidate",
    "baseline_case_id",
    "baseline_physical_degradation_kwh",
    "baseline_reproduction_ratio",
]


GROUP_FIELDS = [
    "source_study",
    "attack_category",
    "attack_group",
    "case_count",
    "damaging_case_count",
    "damaging_case_rate",
    "detected_case_count",
    "detection_rate",
    "detected_damaging_case_count",
    "detection_rate_on_damaging_cases",
    "bypass_high_impact_count",
    "total_physical_degradation_kwh",
    "mean_physical_degradation_kwh",
    "max_physical_degradation_kwh",
    "total_residual_degradation_after_mitigation_kwh",
    "max_residual_degradation_after_mitigation_kwh",
    "total_degradation_recovered_kwh",
    "total_recovery_ratio_on_positive_degradation",
    "mean_clipped_recovery_on_damaging_cases",
    "mean_detector_score",
    "mean_switch_changes_vs_clean",
    "mean_load_changes_vs_clean",
    "worst_case_id",
    "worst_case_residual_degradation_kwh",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build IEEE 8500 detection/mitigation defense stress summaries."
    )
    parser.add_argument(
        "--baseline-cases",
        default="paper_results/tsg_ieee8500/baseline_attack_full_deterministic/tsg_ieee8500_case_summary.csv",
    )
    parser.add_argument(
        "--action-mask-cases",
        default=(
            "paper_results/tsg_ieee8500/full_criticality_merged/action_mask/"
            "tsg_ieee8500_action_mask_criticality_cases.csv"
        ),
    )
    parser.add_argument(
        "--branchflow-single-cases",
        default=(
            "paper_results/tsg_ieee8500/full_criticality_merged/branchflow/"
            "tsg_ieee8500_measurement_criticality_cases.csv"
        ),
    )
    parser.add_argument(
        "--branchflow-subset-cases",
        default=(
            "paper_results/tsg_ieee8500/branchflow_subset_ablation/"
            "tsg_ieee8500_branchflow_subset_ablation_cases.csv"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="paper_results/tsg_ieee8500/defense_stress_summary",
    )
    parser.add_argument("--bypass-loss-threshold-kwh", type=float, default=1.0e-6)
    parser.add_argument("--top-n-worst", type=int, default=25)
    return parser.parse_args()


def _float(row, field, default=0.0):
    try:
        value = row.get(field, default)
        if value == "":
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _int(row, field, default=0):
    try:
        value = row.get(field, default)
        if value == "":
            return int(default)
        return int(float(value))
    except (TypeError, ValueError):
        return int(default)


def read_csv_rows(path):
    resolved = resolve_path(path)
    if not resolved.exists():
        return []
    with resolved.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv_or_header(rows, path, fieldnames):
    if rows:
        write_csv(rows, path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(",".join(fieldnames) + "\n")


def normalize_common(row, source_study, attack_category, attack_group, args):
    physical_degradation = _float(row, "physical_degradation_kwh")
    residual_degradation = _float(row, "residual_degradation_after_mitigation_kwh")
    detected = _int(row, "fdia_detected")
    bypass = _int(row, "bypass_high_impact")
    if "bypass_high_impact" not in row:
        bypass = int((not detected) and physical_degradation > float(args.bypass_loss_threshold_kwh))
    return {
        "source_study": source_study,
        "attack_category": attack_category,
        "attack_group": attack_group,
        "attack": row.get("attack", ""),
        "target_observation_id": row.get("target_observation_id", ""),
        "subset_k": row.get("subset_k", ""),
        "case_id": row.get("case_id", ""),
        "scenario_seed": _int(row, "scenario_seed"),
        "damaging_case": int(physical_degradation > float(args.bypass_loss_threshold_kwh)),
        "improvement_case": _int(row, "improvement_case"),
        "fdia_detected": detected,
        "bypass_high_impact": bypass,
        "physical_degradation_kwh": physical_degradation,
        "restored_energy_loss_kwh": _float(row, "restored_energy_loss_kwh"),
        "residual_degradation_after_mitigation_kwh": residual_degradation,
        "degradation_recovered_kwh": _float(row, "degradation_recovered_kwh"),
        "mitigation_recovery_of_degradation_ratio_clipped": _float(
            row, "mitigation_recovery_of_degradation_ratio_clipped"
        ),
        "detector_score": _float(row, "detector_score"),
        "detected_channels": row.get("detected_channels", ""),
        "attacked_action_changed": _int(row, "attacked_action_changed"),
        "attacked_switch_changes_vs_clean": _int(row, "attacked_switch_changes_vs_clean"),
        "attacked_load_changes_vs_clean": _int(row, "attacked_load_changes_vs_clean"),
        "mitigation_selected_candidate": row.get("mitigation_selected_candidate", ""),
        "baseline_case_id": row.get("baseline_case_id", ""),
        "baseline_physical_degradation_kwh": _float(row, "baseline_physical_degradation_kwh"),
        "baseline_reproduction_ratio": _float(row, "baseline_reproduction_ratio"),
    }


def load_normalized_rows(args):
    normalized = []

    for row in read_csv_rows(args.baseline_cases):
        attack = row.get("attack", "")
        normalized.append(
            normalize_common(
                row,
                "baseline_attack_family",
                "baseline_attack_family",
                attack,
                args,
            )
        )

    for row in read_csv_rows(args.action_mask_cases):
        target = row.get("target_observation_id", "")
        normalized.append(
            normalize_common(
                row,
                "action_mask_single_criticality_partial",
                "action_mask_single",
                target or "action_mask_unknown",
                args,
            )
        )

    for row in read_csv_rows(args.branchflow_single_cases):
        target = row.get("target_observation_id", "")
        normalized.append(
            normalize_common(
                row,
                "branchflow_single_criticality_partial",
                "branchflow_single",
                target or "branchflow_unknown",
                args,
            )
        )

    for row in read_csv_rows(args.branchflow_subset_cases):
        subset_k = row.get("subset_k", "")
        normalized.append(
            normalize_common(
                row,
                "branchflow_coordinated_subset_ablation",
                "branchflow_coordinated_subset",
                "branchflow_subset_k{}".format(subset_k),
                args,
            )
        )

    return normalized


def summarize_groups(case_rows):
    groups = defaultdict(list)
    for row in case_rows:
        key = (row["source_study"], row["attack_category"], row["attack_group"])
        groups[key].append(row)

    summary_rows = []
    for (source_study, attack_category, attack_group), rows in groups.items():
        degradations = np.asarray([row["physical_degradation_kwh"] for row in rows], dtype=float)
        residuals = np.asarray(
            [row["residual_degradation_after_mitigation_kwh"] for row in rows],
            dtype=float,
        )
        detected = np.asarray([row["fdia_detected"] for row in rows], dtype=float)
        detector_scores = np.asarray([row["detector_score"] for row in rows], dtype=float)
        switch_changes = np.asarray([row["attacked_switch_changes_vs_clean"] for row in rows], dtype=float)
        load_changes = np.asarray([row["attacked_load_changes_vs_clean"] for row in rows], dtype=float)
        damaging_rows = [row for row in rows if int(row["damaging_case"]) == 1]
        detected_damaging_rows = [row for row in damaging_rows if int(row["fdia_detected"]) == 1]
        recovery_values = np.asarray(
            [row["mitigation_recovery_of_degradation_ratio_clipped"] for row in damaging_rows],
            dtype=float,
        )
        recovered = np.asarray([row["degradation_recovered_kwh"] for row in rows], dtype=float)
        worst = max(rows, key=lambda row: row["residual_degradation_after_mitigation_kwh"])
        total_degradation = float(np.sum(degradations))
        total_recovered = float(np.sum(recovered))
        summary_rows.append(
            {
                "source_study": source_study,
                "attack_category": attack_category,
                "attack_group": attack_group,
                "case_count": len(rows),
                "damaging_case_count": len(damaging_rows),
                "damaging_case_rate": float(len(damaging_rows) / max(len(rows), 1)),
                "detected_case_count": int(np.sum(detected)),
                "detection_rate": float(np.mean(detected)) if detected.size else 0.0,
                "detected_damaging_case_count": len(detected_damaging_rows),
                "detection_rate_on_damaging_cases": float(
                    len(detected_damaging_rows) / max(len(damaging_rows), 1)
                )
                if damaging_rows
                else 0.0,
                "bypass_high_impact_count": int(
                    np.sum([row["bypass_high_impact"] for row in rows])
                ),
                "total_physical_degradation_kwh": total_degradation,
                "mean_physical_degradation_kwh": float(np.mean(degradations)) if degradations.size else 0.0,
                "max_physical_degradation_kwh": float(np.max(degradations)) if degradations.size else 0.0,
                "total_residual_degradation_after_mitigation_kwh": float(np.sum(residuals)),
                "max_residual_degradation_after_mitigation_kwh": float(np.max(residuals))
                if residuals.size
                else 0.0,
                "total_degradation_recovered_kwh": total_recovered,
                "total_recovery_ratio_on_positive_degradation": (
                    total_recovered / total_degradation if total_degradation > 1.0e-9 else 0.0
                ),
                "mean_clipped_recovery_on_damaging_cases": float(np.mean(recovery_values))
                if recovery_values.size
                else 0.0,
                "mean_detector_score": float(np.mean(detector_scores)) if detector_scores.size else 0.0,
                "mean_switch_changes_vs_clean": float(np.mean(switch_changes)) if switch_changes.size else 0.0,
                "mean_load_changes_vs_clean": float(np.mean(load_changes)) if load_changes.size else 0.0,
                "worst_case_id": worst["case_id"],
                "worst_case_residual_degradation_kwh": worst[
                    "residual_degradation_after_mitigation_kwh"
                ],
            }
        )

    summary_rows.sort(
        key=lambda row: (
            row["total_residual_degradation_after_mitigation_kwh"],
            row["total_physical_degradation_kwh"],
            row["bypass_high_impact_count"],
        ),
        reverse=True,
    )
    return summary_rows


def select_worst_cases(case_rows, top_n):
    rows = sorted(
        case_rows,
        key=lambda row: (
            row["residual_degradation_after_mitigation_kwh"],
            row["physical_degradation_kwh"],
        ),
        reverse=True,
    )
    return rows[: int(top_n)]


def select_bypass_cases(case_rows):
    return sorted(
        [row for row in case_rows if int(row["bypass_high_impact"]) == 1],
        key=lambda row: row["physical_degradation_kwh"],
        reverse=True,
    )


def select_low_recovery_cases(case_rows):
    rows = [
        row
        for row in case_rows
        if int(row["damaging_case"]) == 1
        and int(row["fdia_detected"]) == 1
        and row["mitigation_recovery_of_degradation_ratio_clipped"] < 0.999999
    ]
    return sorted(
        rows,
        key=lambda row: (
            row["residual_degradation_after_mitigation_kwh"],
            row["physical_degradation_kwh"],
        ),
        reverse=True,
    )


def markdown_summary(group_rows, bypass_rows, low_recovery_rows, worst_rows):
    lines = [
        "# IEEE 8500 Defense Stress Summary",
        "",
        "This summary combines completed IEEE 8500 case-level evidence only.",
        "",
        "## Top Residual-Risk Groups",
        "",
        "| Source | Group | Cases | Damaging | Detection | Total degradation kWh | Residual kWh | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in group_rows[:12]:
        lines.append(
            "| {source} | {group} | {cases} | {damaging} | {detect:.3f} | {deg:.3f} | {resid:.3f} | {recovery:.3f} |".format(
                source=row["source_study"],
                group=row["attack_group"],
                cases=row["case_count"],
                damaging=row["damaging_case_count"],
                detect=row["detection_rate"],
                deg=row["total_physical_degradation_kwh"],
                resid=row["total_residual_degradation_after_mitigation_kwh"],
                recovery=row["total_recovery_ratio_on_positive_degradation"],
            )
        )

    lines.extend(
        [
            "",
            "## Bypass Cases",
            "",
            "High-impact bypass cases found: `{}`.".format(len(bypass_rows)),
            "",
            "## Detected But Low-Recovery Cases",
            "",
            "| Source | Group | Case | Degradation kWh | Residual kWh | Recovery |",
            "|---|---|---|---:|---:|---:|",
        ]
    )
    for row in low_recovery_rows[:15]:
        lines.append(
            "| {source} | {group} | {case} | {deg:.3f} | {resid:.3f} | {recovery:.3f} |".format(
                source=row["source_study"],
                group=row["attack_group"],
                case=row["case_id"],
                deg=row["physical_degradation_kwh"],
                resid=row["residual_degradation_after_mitigation_kwh"],
                recovery=row["mitigation_recovery_of_degradation_ratio_clipped"],
            )
        )

    lines.extend(
        [
            "",
            "## Worst Residual Cases",
            "",
            "| Source | Group | Case | Detected | Degradation kWh | Residual kWh |",
            "|---|---|---|---:|---:|---:|",
        ]
    )
    for row in worst_rows[:15]:
        lines.append(
            "| {source} | {group} | {case} | {detected} | {deg:.3f} | {resid:.3f} |".format(
                source=row["source_study"],
                group=row["attack_group"],
                case=row["case_id"],
                detected=row["fdia_detected"],
                deg=row["physical_degradation_kwh"],
                resid=row["residual_degradation_after_mitigation_kwh"],
            )
        )
    lines.append("")
    return "\n".join(lines)


def main():
    args = parse_args()
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    case_rows = load_normalized_rows(args)
    group_rows = summarize_groups(case_rows)
    worst_rows = select_worst_cases(case_rows, args.top_n_worst)
    bypass_rows = select_bypass_cases(case_rows)
    low_recovery_rows = select_low_recovery_cases(case_rows)

    paths = {
        "normalized_cases": output_dir / "tsg_ieee8500_defense_stress_cases.csv",
        "group_summary": output_dir / "tsg_ieee8500_defense_stress_group_summary.csv",
        "worst_residual_cases": output_dir / "tsg_ieee8500_defense_stress_worst_residual_cases.csv",
        "bypass_cases": output_dir / "tsg_ieee8500_defense_stress_bypass_cases.csv",
        "low_recovery_cases": output_dir / "tsg_ieee8500_defense_stress_low_recovery_cases.csv",
        "markdown_summary": output_dir / "tsg_ieee8500_defense_stress_summary.md",
        "manifest": output_dir / "tsg_ieee8500_defense_stress_manifest.json",
    }

    write_csv_or_header(case_rows, paths["normalized_cases"], CASE_FIELDS)
    write_csv_or_header(group_rows, paths["group_summary"], GROUP_FIELDS)
    write_csv_or_header(worst_rows, paths["worst_residual_cases"], CASE_FIELDS)
    write_csv_or_header(bypass_rows, paths["bypass_cases"], CASE_FIELDS)
    write_csv_or_header(low_recovery_rows, paths["low_recovery_cases"], CASE_FIELDS)
    paths["markdown_summary"].write_text(
        markdown_summary(group_rows, bypass_rows, low_recovery_rows, worst_rows) + "\n"
    )

    manifest = {
        "experiment": "IEEE 8500 defense stress summary",
        "system": "8500bus",
        "case_row_count": len(case_rows),
        "group_row_count": len(group_rows),
        "worst_residual_case_count": len(worst_rows),
        "bypass_high_impact_case_count": len(bypass_rows),
        "low_recovery_case_count": len(low_recovery_rows),
        "inputs": {
            "baseline_cases": str(resolve_path(args.baseline_cases)),
            "action_mask_cases": str(resolve_path(args.action_mask_cases)),
            "branchflow_single_cases": str(resolve_path(args.branchflow_single_cases)),
            "branchflow_subset_cases": str(resolve_path(args.branchflow_subset_cases)),
        },
        "outputs": {key: str(value) for key, value in paths.items()},
        "notes": (
            "This artifact summarizes completed IEEE 8500 evidence only; it does "
            "not rerun simulations or infer missing target chunks."
        ),
    }
    paths["manifest"].write_text(safe_json(manifest) + "\n")

    for path in paths.values():
        print("wrote {}".format(path), flush=True)


if __name__ == "__main__":
    main()
