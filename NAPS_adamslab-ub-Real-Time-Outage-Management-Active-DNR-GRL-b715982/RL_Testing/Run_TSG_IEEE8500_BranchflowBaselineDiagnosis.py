"""Diagnose IEEE 8500 baseline branchflow_hiding degradation cases.

This script analyzes the completed IEEE 8500 baseline attack-family study. It
identifies the branchflow_hiding cases that caused physical degradation, then
reconstructs which branchflow observations were selected by the baseline attack
in those cases. It does not change the controller, retrain a model, or apply a
new attack family.
"""

import argparse
import csv
import json
from collections import defaultdict

import numpy as np

from FDIA_ExperimentCore import resolve_path, safe_json, write_csv
from IEEE8500_VulnerabilityRegistry import build_observation_registry
from Run_TSG_IEEE34_BaselineAttackStudy import scenario_observation
from Run_TSG_IEEE8500_Common import add_ieee8500_scenario_args, generate_outage_scenario
from TSG_ControllerConfig import (
    add_controller_args,
    controller_metadata,
    controller_output_dir,
    make_controller_experiment,
)


SYSTEM_NAME = "8500bus"
DEFAULT_OUTPUT_DIR = "paper_results/tsg_ieee8500/branchflow_baseline_diagnosis"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Diagnose damaging IEEE 8500 baseline branchflow_hiding cases."
    )
    parser.add_argument(
        "--baseline-case-summary",
        default="paper_results/tsg_ieee8500/baseline_attack_full_deterministic/tsg_ieee8500_case_summary.csv",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
    )
    add_controller_args(parser)
    parser.add_argument("--max-outage-fraction", type=float, default=0.50)
    parser.add_argument("--max-scenario-generation-attempts", type=int, default=100)
    add_ieee8500_scenario_args(parser)
    parser.add_argument("--default-target-fraction", type=float, default=0.20)
    parser.add_argument("--default-scale", type=float, default=0.25)
    parser.add_argument("--degradation-threshold-kwh", type=float, default=1.0e-9)
    return parser.parse_args()


def _float(row, field, default=0.0):
    try:
        return float(row.get(field, default))
    except (TypeError, ValueError):
        return float(default)


def _int(row, field, default=0):
    try:
        return int(float(row.get(field, default)))
    except (TypeError, ValueError):
        return int(default)


def load_branchflow_rows(path, threshold):
    rows = []
    with resolve_path(path).open(newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            if raw.get("attack") != "branchflow_hiding":
                continue
            row = dict(raw)
            row["_physical_degradation_kwh"] = _float(row, "physical_degradation_kwh")
            row["_restored_energy_loss_kwh"] = _float(row, "restored_energy_loss_kwh")
            row["_damaging_case"] = int(row["_physical_degradation_kwh"] > float(threshold))
            rows.append(row)
    return rows


def parse_attack_metadata(row, args):
    try:
        metadata = json.loads(row.get("attack_metadata", "{}"))
    except json.JSONDecodeError:
        metadata = {}
    kwargs = metadata.get("attack_kwargs", {}) if isinstance(metadata, dict) else {}
    return {
        "target_fraction": float(kwargs.get("target_fraction", args.default_target_fraction)),
        "scale": float(kwargs.get("scale", args.default_scale)),
        "changed_measurements_reported": int(metadata.get("changed_measurements", 0))
        if isinstance(metadata, dict)
        else 0,
        "mean_abs_change_reported": float(metadata.get("mean_abs_change", 0.0))
        if isinstance(metadata, dict)
        else 0.0,
    }


def branchflow_targets(experiment):
    entries = [
        entry
        for entry in build_observation_registry(experiment)
        if entry.family == "branchflow" and entry.attackable and entry.current_grl_input
    ]
    return sorted(entries, key=lambda entry: str(entry.observation_id))


def selected_branchflows(values, target_fraction):
    flat = np.asarray(values, dtype=float).reshape(-1)
    valid_indices = np.where(np.isfinite(flat) & (flat > 0.0))[0]
    if valid_indices.size == 0:
        return np.array([], dtype=int)
    count = max(1, int(np.ceil(valid_indices.size * float(target_fraction))))
    scores = flat[valid_indices]
    order = np.argsort(scores)[::-1]
    return valid_indices[order[:count]]


def scenario_from_row(experiment, row, args):
    scenario_seed = _int(row, "scenario_seed")
    return generate_outage_scenario(experiment, scenario_seed, args)


def action_delta_summary(row):
    clean = row.get("clean_action", "")
    attacked = row.get("attacked_action", "")
    mitigated = row.get("mitigated_action", "")
    return {
        "attacked_action_changed": _int(row, "attacked_action_changed"),
        "attacked_switch_changes_vs_clean": _int(row, "attacked_switch_changes_vs_clean"),
        "attacked_load_changes_vs_clean": _int(row, "attacked_load_changes_vs_clean"),
        "mitigated_action_changed": _int(row, "mitigated_action_changed"),
        "mitigated_switch_changes_vs_clean": _int(row, "mitigated_switch_changes_vs_clean"),
        "mitigated_load_changes_vs_clean": _int(row, "mitigated_load_changes_vs_clean"),
        "clean_action": clean,
        "attacked_action": attacked,
        "mitigated_action": mitigated,
    }


def main():
    args = parse_args()
    output_dir = resolve_path(
        controller_output_dir(args.output_dir, DEFAULT_OUTPUT_DIR, SYSTEM_NAME, args.controller)
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    branchflow_rows = load_branchflow_rows(
        args.baseline_case_summary,
        args.degradation_threshold_kwh,
    )
    damaging_rows = [row for row in branchflow_rows if row["_damaging_case"]]

    experiment = make_controller_experiment(SYSTEM_NAME, args, load_model=True)
    targets = branchflow_targets(experiment)
    targets_by_measurement_index = {
        int(target.index[0]): (runner_index, target)
        for runner_index, target in enumerate(targets)
    }

    case_rows = []
    channel_rows = []
    aggregate = defaultdict(
        lambda: {
            "selected_case_count": 0,
            "damaging_selected_case_count": 0,
            "all_case_abs_values": [],
            "damaging_case_abs_values": [],
            "damaging_case_degradations": [],
        }
    )

    for row in branchflow_rows:
        attack_config = parse_attack_metadata(row, args)
        scenario = scenario_from_row(experiment, row, args)
        obs = scenario_observation(experiment, scenario)
        branchflows = np.asarray(obs["EdgeFeat(Branchflow)"], dtype=float).reshape(-1)
        finite_branchflows = np.nan_to_num(branchflows, nan=0.0, posinf=0.0, neginf=0.0)
        selected = selected_branchflows(finite_branchflows, attack_config["target_fraction"])
        selected_set = set(int(index) for index in selected)
        changed_measurements_reconstructed = int(len(selected))
        abs_selected = np.abs(finite_branchflows[selected]) if selected.size else np.asarray([])
        damaging = int(row["_damaging_case"])

        case_out = {
            "case_id": row.get("case_id", ""),
            "scenario_seed": _int(row, "scenario_seed"),
            "scenario_root_node": row.get("scenario_root_node", ""),
            "scenario_radius": _int(row, "scenario_radius"),
            "outage_edge_count": _int(row, "outage_edge_count"),
            "outage_edges": row.get("outage_edges", ""),
            "target_fraction": attack_config["target_fraction"],
            "scale": attack_config["scale"],
            "changed_measurements_reported": attack_config["changed_measurements_reported"],
            "changed_measurements_reconstructed": changed_measurements_reconstructed,
            "mean_abs_change_reported": attack_config["mean_abs_change_reported"],
            "mean_selected_abs_branchflow": float(np.mean(abs_selected)) if selected.size else 0.0,
            "max_selected_abs_branchflow": float(np.max(abs_selected)) if selected.size else 0.0,
            "restored_energy_loss_kwh": row["_restored_energy_loss_kwh"],
            "physical_degradation_kwh": row["_physical_degradation_kwh"],
            "damaging_case": damaging,
            "fdia_detected": _int(row, "fdia_detected"),
            "detector_score": _float(row, "detector_score"),
            "detected_channels": row.get("detected_channels", ""),
            "mitigation_recovery_of_degradation_ratio_clipped": _float(
                row, "mitigation_recovery_of_degradation_ratio_clipped"
            ),
            "selected_measurement_indices": json.dumps(sorted(selected_set)),
        }
        case_out.update(action_delta_summary(row))
        case_rows.append(case_out)

        for measurement_index in selected:
            measurement_index = int(measurement_index)
            runner_index, target = targets_by_measurement_index.get(
                measurement_index,
                (-1, None),
            )
            observation_id = (
                target.observation_id
                if target is not None
                else "branchflow.measurement_{}".format(measurement_index)
            )
            component_name = target.component_name if target is not None else ""
            abs_value = float(abs(finite_branchflows[measurement_index]))
            channel_rows.append(
                {
                    "case_id": row.get("case_id", ""),
                    "scenario_seed": _int(row, "scenario_seed"),
                    "damaging_case": damaging,
                    "physical_degradation_kwh": row["_physical_degradation_kwh"],
                    "target_observation_id": observation_id,
                    "runner_target_index": int(runner_index),
                    "target_measurement_index": int(measurement_index),
                    "target_component_name": component_name,
                    "clean_branchflow": float(finite_branchflows[measurement_index]),
                    "abs_clean_branchflow": abs_value,
                }
            )
            agg = aggregate[observation_id]
            agg["runner_target_index"] = int(runner_index)
            agg["target_measurement_index"] = int(measurement_index)
            agg["target_component_name"] = component_name
            agg["selected_case_count"] += 1
            agg["all_case_abs_values"].append(abs_value)
            if damaging:
                agg["damaging_selected_case_count"] += 1
                agg["damaging_case_abs_values"].append(abs_value)
                agg["damaging_case_degradations"].append(row["_physical_degradation_kwh"])

    ranking_rows = []
    for observation_id, agg in aggregate.items():
        all_values = np.asarray(agg["all_case_abs_values"], dtype=float)
        damaging_values = np.asarray(agg["damaging_case_abs_values"], dtype=float)
        damaging_degradations = np.asarray(agg["damaging_case_degradations"], dtype=float)
        ranking_rows.append(
            {
                "target_observation_id": observation_id,
                "runner_target_index": int(agg["runner_target_index"]),
                "target_measurement_index": int(agg["target_measurement_index"]),
                "target_component_name": agg["target_component_name"],
                "selected_case_count": int(agg["selected_case_count"]),
                "damaging_selected_case_count": int(agg["damaging_selected_case_count"]),
                "damaging_selected_case_rate": float(
                    agg["damaging_selected_case_count"] / max(agg["selected_case_count"], 1)
                ),
                "mean_abs_branchflow_selected_all_cases": float(np.mean(all_values))
                if all_values.size
                else 0.0,
                "mean_abs_branchflow_selected_damaging_cases": float(np.mean(damaging_values))
                if damaging_values.size
                else 0.0,
                "max_abs_branchflow_selected_damaging_cases": float(np.max(damaging_values))
                if damaging_values.size
                else 0.0,
                "mean_physical_degradation_when_selected_damaging": float(
                    np.mean(damaging_degradations)
                )
                if damaging_degradations.size
                else 0.0,
                "max_physical_degradation_when_selected_damaging": float(
                    np.max(damaging_degradations)
                )
                if damaging_degradations.size
                else 0.0,
            }
        )

    ranking_rows.sort(
        key=lambda item: (
            item["damaging_selected_case_count"],
            item["max_physical_degradation_when_selected_damaging"],
            item["mean_abs_branchflow_selected_damaging_cases"],
            item["selected_case_count"],
        ),
        reverse=True,
    )
    for rank, row in enumerate(ranking_rows, start=1):
        row["diagnosis_rank"] = rank

    damaging_case_rows = [row for row in case_rows if row["damaging_case"]]
    damaging_case_rows.sort(key=lambda row: row["physical_degradation_kwh"], reverse=True)
    case_rows.sort(key=lambda row: (row["damaging_case"], row["physical_degradation_kwh"]), reverse=True)

    paths = {
        "case_diagnosis": output_dir / "tsg_ieee8500_branchflow_baseline_case_diagnosis.csv",
        "damaging_cases": output_dir / "tsg_ieee8500_branchflow_baseline_damaging_cases.csv",
        "selected_channels": output_dir / "tsg_ieee8500_branchflow_baseline_selected_channels.csv",
        "channel_ranking": output_dir / "tsg_ieee8500_branchflow_baseline_channel_ranking.csv",
        "manifest": output_dir / "tsg_ieee8500_branchflow_baseline_diagnosis_manifest.json",
    }
    write_csv(case_rows, paths["case_diagnosis"])
    write_csv(damaging_case_rows, paths["damaging_cases"])
    write_csv(channel_rows, paths["selected_channels"])
    write_csv(ranking_rows, paths["channel_ranking"])

    degradation_values = [row["_physical_degradation_kwh"] for row in damaging_rows]
    manifest = {
        "experiment": "IEEE 8500 branchflow_hiding baseline diagnosis",
        "system": SYSTEM_NAME,
        **controller_metadata(SYSTEM_NAME, args),
        "baseline_case_summary": str(resolve_path(args.baseline_case_summary)),
        "branchflow_case_count": len(branchflow_rows),
        "damaging_case_count": len(damaging_rows),
        "total_positive_physical_degradation_kwh": float(np.sum(degradation_values))
        if degradation_values
        else 0.0,
        "max_positive_physical_degradation_kwh": float(np.max(degradation_values))
        if degradation_values
        else 0.0,
        "degradation_threshold_kwh": float(args.degradation_threshold_kwh),
        "outputs": {key: str(value) for key, value in paths.items()},
        "notes": (
            "Selected branchflow channels are reconstructed from clean observations "
            "using the same top-positive-flow target_fraction used by baseline "
            "branchflow_hiding."
        ),
    }
    paths["manifest"].write_text(safe_json(manifest) + "\n")

    print("wrote {}".format(paths["case_diagnosis"]), flush=True)
    print("wrote {}".format(paths["damaging_cases"]), flush=True)
    print("wrote {}".format(paths["selected_channels"]), flush=True)
    print("wrote {}".format(paths["channel_ranking"]), flush=True)
    print("wrote {}".format(paths["manifest"]), flush=True)


if __name__ == "__main__":
    main()
