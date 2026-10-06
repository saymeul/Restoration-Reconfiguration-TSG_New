"""Build IEEE 8500 controller-comparison paper artifacts.

This script is intentionally read-only with respect to the individual
case-study folders. It combines completed GRL/MLP IEEE 8500 artifacts and any
available BPSO evidence into clearly labeled comparison tables.
"""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from FDIA_ExperimentCore import resolve_path, safe_json, write_csv


CONTROLLERS = ("GRL", "MLP", "BPSO")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate IEEE 8500 GRL/MLP/BPSO comparison tables and narrative."
    )
    parser.add_argument("--grl-results-dir", default="paper_results/tsg_ieee8500")
    parser.add_argument("--mlp-results-dir", default="paper_results/tsg_ieee8500_mlp")
    parser.add_argument(
        "--bpso-baseline-dir",
        default="paper_results/tsg_ieee8500_bpso/baseline_attack_full_deterministic_p2_i2",
    )
    parser.add_argument(
        "--bpso-action-mask-dir",
        default="paper_results/tsg_ieee8500_bpso/full_criticality_merged/action_mask",
    )
    parser.add_argument(
        "--bpso-branchflow-dir",
        default="paper_results/tsg_ieee8500_bpso/full_criticality_merged/branchflow",
    )
    parser.add_argument(
        "--bpso-defense-dir",
        default="paper_results/tsg_ieee8500_bpso/defense_stress_summary",
    )
    parser.add_argument(
        "--bpso-advanced-dir",
        default="paper_results/tsg_ieee8500_bpso/advanced_mitigation_ablation_exhaustive_criticality",
    )
    parser.add_argument(
        "--output-dir",
        default="paper_results/tsg_ieee8500_controller_comparison",
    )
    return parser.parse_args()


def read_csv_rows(path):
    resolved = resolve_path(path)
    if not resolved.exists():
        return []
    with resolved.open(newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path):
    resolved = resolve_path(path)
    if not resolved.exists():
        return {}
    return json.loads(resolved.read_text())


def safe_float(value, default=0.0):
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def safe_int(value, default=0):
    try:
        if value in ("", None):
            return int(default)
        return int(float(value))
    except (TypeError, ValueError):
        return int(default)


def pct_from_ratio_or_pct(value):
    number = safe_float(value)
    if abs(number) <= 1.0:
        return 100.0 * number
    return number


def relative(path):
    try:
        return str(Path(path).relative_to(resolve_path(".")))
    except ValueError:
        return str(path)


def normalize_attack_rows(controller, rows, evidence_level):
    normalized = []
    for row in rows:
        if "mean_degradation_kwh" in row:
            mean_degradation = safe_float(row.get("mean_degradation_kwh"))
            total_degradation = safe_float(row.get("total_degradation_kwh"))
            max_degradation = safe_float(row.get("max_degradation_kwh"))
            damaging_cases = safe_int(row.get("damaging_cases"))
            detection_pct = safe_float(row.get("detection_rate_pct"))
            recovery_pct = safe_float(row.get("mitigation_recovery_pct"))
        else:
            mean_degradation = safe_float(row.get("mean_physical_degradation_kwh"))
            total_degradation = safe_float(row.get("total_physical_degradation_kwh"))
            max_degradation = safe_float(row.get("max_physical_degradation_kwh"))
            damaging_cases = safe_int(row.get("damaging_case_count"))
            detection_pct = pct_from_ratio_or_pct(row.get("detection_rate"))
            recovery_pct = pct_from_ratio_or_pct(
                row.get("mean_mitigation_recovery_of_degradation_ratio_clipped")
            )

        normalized.append(
            {
                "controller": controller,
                "evidence_level": evidence_level,
                "attack": row.get("attack", ""),
                "case_count": safe_int(row.get("case_count")),
                "mean_degradation_kwh": mean_degradation,
                "total_degradation_kwh": total_degradation,
                "max_degradation_kwh": max_degradation,
                "damaging_cases": damaging_cases,
                "detection_rate_pct": detection_pct,
                "mitigation_recovery_pct": recovery_pct,
            }
        )
    normalized.sort(
        key=lambda item: (
            item["controller"],
            -item["mean_degradation_kwh"],
            -item["max_degradation_kwh"],
            item["attack"],
        )
    )
    return normalized


def top_attack_rows(attack_rows):
    best_by_controller = {}
    for row in attack_rows:
        current = best_by_controller.get(row["controller"])
        if current is None or (
            row["mean_degradation_kwh"],
            row["max_degradation_kwh"],
            row["damaging_cases"],
        ) > (
            current["mean_degradation_kwh"],
            current["max_degradation_kwh"],
            current["damaging_cases"],
        ):
            best_by_controller[row["controller"]] = row
    return [best_by_controller[key] for key in CONTROLLERS if key in best_by_controller]


def artifact_manifest(results_dir):
    return read_json(Path(results_dir) / "paper_artifacts" / "ieee8500_paper_artifacts_manifest.json")


def evidence_rows(
    grl_dir,
    mlp_dir,
    bpso_dir,
    bpso_action_mask_dir,
    bpso_branchflow_dir,
    bpso_defense_dir,
    bpso_advanced_dir,
):
    grl_manifest = artifact_manifest(grl_dir)
    mlp_manifest = artifact_manifest(mlp_dir)
    bpso_manifest = read_json(Path(bpso_dir) / "tsg_ieee8500_manifest.json")
    bpso_action_rows = read_csv_rows(
        Path(bpso_action_mask_dir) / "tsg_ieee8500_action_mask_criticality_ranking.csv"
    )
    bpso_action_case_rows = read_csv_rows(
        Path(bpso_action_mask_dir) / "tsg_ieee8500_action_mask_criticality_cases.csv"
    )
    bpso_branchflow_rows = read_csv_rows(
        Path(bpso_branchflow_dir) / "tsg_ieee8500_measurement_criticality_cases.csv"
    )
    bpso_defense_rows = read_csv_rows(
        Path(bpso_defense_dir) / "tsg_ieee8500_defense_stress_group_summary.csv"
    )
    bpso_advanced_rows = read_csv_rows(
        Path(bpso_advanced_dir) / "tsg_ieee8500_advanced_mitigation_variant_summary.csv"
    )
    rows = []
    for controller, manifest, level in [
        ("GRL", grl_manifest, "full_frozen_case_study"),
        ("MLP", mlp_manifest, "full_frozen_case_study"),
    ]:
        counts = manifest.get("row_counts", {})
        rows.append(
            {
                "controller": controller,
                "evidence_level": level,
                "baseline_attack_rows": counts.get("attack_family", 0),
                "baseline_case_rows": counts.get("baseline_cases", 0),
                "action_mask_rows": counts.get("action_mask", 0),
                "voltage_rows": counts.get("voltage_single", 0),
                "branchflow_rows": counts.get("branchflow_single", 0),
                "branchflow_subset_rows": counts.get("branchflow_subset", 0),
                "defense_stress_rows": counts.get("defense_stress", 0),
                "advanced_mitigation_rows": counts.get("advanced_mitigation", 0),
                "missing_inputs": len(manifest.get("missing_inputs", [])),
                "notes": manifest.get("claim_boundary", ""),
            }
        )
    rows.append(
        {
            "controller": "BPSO",
            "evidence_level": "scoped_p2_i2_action_mask_frozen",
            "baseline_attack_rows": len(bpso_manifest.get("attacks", [])),
            "baseline_case_rows": safe_int(bpso_manifest.get("cases"))
            * len(bpso_manifest.get("attacks", [])),
            "action_mask_rows": len(bpso_action_rows),
            "voltage_rows": 0,
            "branchflow_rows": len(bpso_branchflow_rows),
            "branchflow_subset_rows": 0,
            "defense_stress_rows": len(bpso_defense_rows),
            "advanced_mitigation_rows": len(bpso_advanced_rows),
            "missing_inputs": 0 if bpso_manifest else 1,
            "notes": (
                "BPSO baseline is complete for the documented p2/i2 budget; action-mask "
                "criticality is complete over the current target registry ({} case rows). ".format(
                    len(bpso_action_case_rows)
                )
                +
                "Voltage and branchflow observation criticality are not claimed for this BPSO variant because its current objective uses ActionMasking as the decision-relevant cyber input."
            ),
        }
    )
    return rows


def markdown_table(rows, columns):
    lines = [
        "| " + " | ".join(label for _key, label in columns) + " |",
        "| " + " | ".join("---" for _key, _label in columns) + " |",
    ]
    for row in rows:
        values = []
        for key, _label in columns:
            value = row.get(key, "")
            if isinstance(value, float):
                value = "{:.6f}".format(value)
            values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def write_table(rows, csv_path, md_path, columns):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_csv(rows, csv_path)
    md_path.write_text(markdown_table(rows, columns))


def narrative(attack_rows, top_rows, evidence):
    lines = [
        "# IEEE 8500 Controller Comparison Narrative",
        "",
        "Generated: {}".format(datetime.now().isoformat(timespec="seconds")),
        "",
        "## Evidence Boundary",
        "",
        "GRL and MLP rows come from frozen IEEE 8500 case-study artifacts. BPSO now includes a frozen scoped p2/i2 evidence package: complete 30-case baseline, current action-mask criticality target-registry evidence, defense-stress summary, and advanced mitigation ablation.",
        "",
        "## Baseline Attack-Family Comparison",
        "",
    ]
    for row in top_rows:
        lines.append(
            "- {}: most damaging available attack is `{}` with mean degradation {:.3f} kWh over {} cases; evidence level `{}`.".format(
                row["controller"],
                row["attack"],
                row["mean_degradation_kwh"],
                row["case_count"],
                row["evidence_level"],
            )
        )
    lines.extend(
        [
            "",
            "## BPSO Interpretation",
            "",
            "The current BPSO implementation uses the received `ActionMasking` channel as an optimizer constraint and scores candidates on the physical OpenDSS outage scenario. Therefore action-mask/status attacks are directly decision-relevant for this BPSO variant, while voltage, branchflow, topology, and energy false-data channels require a richer perceived-objective BPSO model before they should be claimed as fully comparable vulnerabilities.",
            "",
            "## Completion Status",
            "",
        ]
    )
    for row in evidence:
        lines.append(
            "- {}: {}; baseline cases {}, action-mask rows {}, voltage rows {}, branchflow rows {}, defense rows {}.".format(
                row["controller"],
                row["evidence_level"],
                row["baseline_case_rows"],
                row["action_mask_rows"],
                row["voltage_rows"],
                row["branchflow_rows"],
                row["defense_stress_rows"],
            )
        )
    lines.append("")
    return "\n".join(lines)


def main():
    args = parse_args()
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    table_dir = output_dir / "tables"

    grl_rows = normalize_attack_rows(
        "GRL",
        read_csv_rows(
            Path(args.grl_results_dir)
            / "paper_artifacts"
            / "tables"
            / "table_01_attack_family_ranking.csv"
        ),
        "full_frozen_case_study",
    )
    mlp_rows = normalize_attack_rows(
        "MLP",
        read_csv_rows(
            Path(args.mlp_results_dir)
            / "paper_artifacts"
            / "tables"
            / "table_01_attack_family_ranking.csv"
        ),
        "full_frozen_case_study",
    )
    bpso_rows = normalize_attack_rows(
        "BPSO",
        read_csv_rows(Path(args.bpso_baseline_dir) / "tsg_ieee8500_attack_ranking.csv"),
        "scoped_p2_i2_action_mask_frozen",
    )
    attack_rows = grl_rows + mlp_rows + bpso_rows
    top_rows = top_attack_rows(attack_rows)
    evidence = evidence_rows(
        args.grl_results_dir,
        args.mlp_results_dir,
        args.bpso_baseline_dir,
        args.bpso_action_mask_dir,
        args.bpso_branchflow_dir,
        args.bpso_defense_dir,
        args.bpso_advanced_dir,
    )

    attack_columns = [
        ("controller", "Controller"),
        ("evidence_level", "Evidence"),
        ("attack", "Attack"),
        ("case_count", "Cases"),
        ("mean_degradation_kwh", "Mean Degradation kWh"),
        ("max_degradation_kwh", "Max Degradation kWh"),
        ("damaging_cases", "Damaging Cases"),
        ("detection_rate_pct", "Detection %"),
        ("mitigation_recovery_pct", "Mitigation Recovery %"),
    ]
    evidence_columns = [
        ("controller", "Controller"),
        ("evidence_level", "Evidence"),
        ("baseline_case_rows", "Baseline Cases"),
        ("action_mask_rows", "Action Mask Rows"),
        ("voltage_rows", "Voltage Rows"),
        ("branchflow_rows", "Branchflow Rows"),
        ("branchflow_subset_rows", "Subset Rows"),
        ("defense_stress_rows", "Defense Rows"),
        ("advanced_mitigation_rows", "Advanced Rows"),
        ("missing_inputs", "Missing Inputs"),
    ]

    paths = {
        "attack_family_comparison_csv": table_dir / "table_01_attack_family_controller_comparison.csv",
        "attack_family_comparison_md": table_dir / "table_01_attack_family_controller_comparison.md",
        "top_attack_csv": table_dir / "table_02_top_attack_by_controller.csv",
        "top_attack_md": table_dir / "table_02_top_attack_by_controller.md",
        "evidence_csv": table_dir / "table_03_controller_evidence_completeness.csv",
        "evidence_md": table_dir / "table_03_controller_evidence_completeness.md",
        "narrative": output_dir / "IEEE8500_Controller_Comparison_Narrative.md",
        "manifest": output_dir / "ieee8500_controller_comparison_manifest.json",
    }

    write_table(
        attack_rows,
        paths["attack_family_comparison_csv"],
        paths["attack_family_comparison_md"],
        attack_columns,
    )
    write_table(top_rows, paths["top_attack_csv"], paths["top_attack_md"], attack_columns)
    write_table(evidence, paths["evidence_csv"], paths["evidence_md"], evidence_columns)
    paths["narrative"].write_text(narrative(attack_rows, top_rows, evidence))

    manifest = {
        "experiment": "IEEE 8500 controller comparison artifact generation",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "grl_results_dir": str(resolve_path(args.grl_results_dir)),
        "mlp_results_dir": str(resolve_path(args.mlp_results_dir)),
        "bpso_baseline_dir": str(resolve_path(args.bpso_baseline_dir)),
        "bpso_action_mask_dir": str(resolve_path(args.bpso_action_mask_dir)),
        "bpso_branchflow_dir": str(resolve_path(args.bpso_branchflow_dir)),
        "bpso_defense_dir": str(resolve_path(args.bpso_defense_dir)),
        "bpso_advanced_dir": str(resolve_path(args.bpso_advanced_dir)),
        "output_dir": str(output_dir),
        "row_counts": {
            "attack_family_comparison": len(attack_rows),
            "top_attack_by_controller": len(top_rows),
            "evidence_completeness": len(evidence),
        },
        "outputs": {key: relative(value) for key, value in paths.items()},
        "claim_boundary": (
            "Use GRL/MLP rows for frozen full-observation controller claims. Use "
            "BPSO rows as frozen scoped p2/i2 evidence for baseline attacks, "
            "action-mask/status criticality, detection, and mitigation only; "
            "voltage and branchflow BPSO observation criticality are not claimed "
            "without a richer BPSO perceived-objective model."
        ),
    }
    paths["manifest"].write_text(safe_json(manifest) + "\n")
    print(safe_json(manifest), flush=True)


if __name__ == "__main__":
    main()
