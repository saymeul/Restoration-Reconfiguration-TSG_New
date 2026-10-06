"""IEEE 123 coordinated branchflow subset ablation.

The baseline branchflow_hiding attack hides a fraction of all positive
branchflow observations at once. Single-channel criticality was weak, so this
runner replays the damaging baseline branchflow cases while hiding only the
top-k selected branchflow observations. This tests whether the baseline effect
is coordinated rather than single-sensor driven.
"""

import argparse
import csv
import json

import numpy as np

import Run_TSG_IEEE34_BaselineAttackStudy as baseline
from FDIA_Common import clone_observation, mitigate_observation, select_fdia_aware_grl_action
from FDIA_DetectorSuite import load_learning_detectors, run_detector_suite
from FDIA_ExperimentCore import resolve_path, safe_json, write_csv
from IEEE123_VulnerabilityRegistry import build_observation_registry, write_registry_outputs
from TSG_ControllerConfig import (
    add_controller_args,
    controller_metadata,
    controller_output_dir,
    make_controller_experiment,
)


SYSTEM_NAME = "123bus"
DEFAULT_OUTPUT_DIR = "paper_results/tsg_ieee123/branchflow_subset_ablation"


def parse_args():
    parser = argparse.ArgumentParser(
        description="IEEE 123 branchflow_hiding coordinated top-k subset ablation."
    )
    parser.add_argument(
        "--damaging-cases",
        default=(
            "paper_results/tsg_ieee123/branchflow_baseline_diagnosis/"
            "tsg_ieee123_branchflow_baseline_damaging_cases.csv"
        ),
    )
    parser.add_argument("--k-values", nargs="+", default=["1", "2", "3", "5", "10", "full"])
    parser.add_argument("--branchflow-target-fraction", type=float, default=0.20)
    parser.add_argument("--branchflow-scale", type=float, default=0.25)
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--step-hours", type=float, default=1.0)
    parser.add_argument("--start-hour", type=int, default=0)
    parser.add_argument("--max-outage-fraction", type=float, default=0.50)
    parser.add_argument("--max-scenario-generation-attempts", type=int, default=100)
    parser.add_argument("--bypass-loss-threshold-kwh", type=float, default=1.0e-6)
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
    )
    add_controller_args(parser)

    parser.add_argument("--use-learning-detectors", action="store_true")
    parser.add_argument("--learning-detector-dir", default="123bus/paper_results/learning_detectors")
    parser.add_argument(
        "--learning-tasks",
        nargs="+",
        default=["binary", "multiclass"],
        choices=["binary", "multiclass"],
    )
    parser.add_argument(
        "--learning-models",
        nargs="+",
        default=["mlp_torch", "knn", "linear_torch", "centroid"],
        choices=["mlp_torch", "knn", "linear_torch", "centroid"],
    )
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


def load_damaging_cases(path):
    rows = []
    with resolve_path(path).open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            out = dict(row)
            out["scenario_seed"] = _int(out, "scenario_seed")
            out["baseline_physical_degradation_kwh"] = _float(out, "physical_degradation_kwh")
            out["baseline_restored_energy_loss_kwh"] = _float(out, "restored_energy_loss_kwh")
            rows.append(out)
    return sorted(rows, key=lambda item: item["baseline_physical_degradation_kwh"], reverse=True)


def parse_k_value(k_value, selected_count):
    text = str(k_value).strip().lower()
    if text == "full":
        return selected_count, "full"
    k = int(text)
    return min(max(k, 0), selected_count), str(k)


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


def corrupt_branchflow_subset(true_obs, selected_indices, scale, target_by_measurement_index):
    attacked = clone_observation(true_obs)
    flows = np.asarray(attacked["EdgeFeat(Branchflow)"], dtype=float).reshape(-1)
    selected_indices = np.asarray(selected_indices, dtype=int)
    original = flows[selected_indices].copy() if selected_indices.size else np.asarray([])
    flows[selected_indices] = flows[selected_indices] * float(scale)
    selected_targets = []
    for measurement_index in selected_indices:
        target = target_by_measurement_index.get(int(measurement_index))
        selected_targets.append(target.observation_id if target is not None else str(measurement_index))
    return attacked, {
        "target": "EdgeFeat(Branchflow)",
        "attack": "branchflow_subset_hiding",
        "scale": float(scale),
        "changed_measurements": int(selected_indices.size),
        "mean_abs_change": float(np.mean(np.abs(original - flows[selected_indices])))
        if selected_indices.size
        else 0.0,
        "selected_measurement_indices": [int(index) for index in selected_indices],
        "selected_observation_ids": selected_targets,
    }


def run_subset_case(experiment, scenario, selected_indices, learning_detectors, args, target_by_measurement_index):
    true_obs = baseline.scenario_observation(experiment, scenario)
    clean_action, clean_policy_ms = experiment.predict_action(true_obs)
    clean_trajectory, _clean_first_obs = baseline.trajectory_after_action_on_scenario(
        experiment,
        scenario,
        clean_action,
        args,
    )

    policy_obs, attack_metadata = corrupt_branchflow_subset(
        true_obs,
        selected_indices,
        args.branchflow_scale,
        target_by_measurement_index,
    )
    detection = run_detector_suite(
        true_obs,
        policy_obs,
        learning_detectors=learning_detectors,
    )
    attacked_action, attacked_policy_ms = experiment.predict_action(policy_obs)
    attacked_trajectory, _attacked_first_obs = baseline.trajectory_after_action_on_scenario(
        experiment,
        scenario,
        attacked_action,
        args,
    )

    mitigated_obs, observation_mitigation = mitigate_observation(true_obs, policy_obs, detection)

    def predict_action_fn(obs):
        return experiment.predict_action(obs)

    def evaluate_action_fn(action):
        metrics, _obs = baseline.evaluate_action_on_scenario(experiment, scenario, action)
        return metrics

    fdia_aware = select_fdia_aware_grl_action(
        predict_action_fn,
        evaluate_action_fn,
        policy_obs,
        mitigated_obs,
        detection,
        experiment.num_switches,
    )
    fdia_aware["observation_mitigation"] = observation_mitigation
    mitigated_action = np.asarray(fdia_aware["action"], dtype=int)
    mitigated_trajectory, _mitigated_first_obs = baseline.trajectory_after_action_on_scenario(
        experiment,
        scenario,
        mitigated_action,
        args,
    )

    return {
        "experiment": experiment,
        "scenario": scenario,
        "true_obs": true_obs,
        "policy_obs": policy_obs,
        "clean_action": clean_action,
        "attacked_action": attacked_action,
        "mitigated_action": mitigated_action,
        "clean_policy_ms": clean_policy_ms,
        "attacked_policy_ms": attacked_policy_ms,
        "attack_metadata": attack_metadata,
        "detection": detection,
        "fdia_aware": fdia_aware,
        "clean_trajectory": clean_trajectory,
        "attacked_trajectory": attacked_trajectory,
        "mitigated_trajectory": mitigated_trajectory,
    }


def summarize_case(case_id, scenario, result, args, case_info, k_label, selected_count, full_selected_count):
    row = baseline.case_summary(case_id, scenario, "branchflow_subset_{}".format(k_label), result, args)
    row["system"] = "123bus"
    baseline_degradation = float(case_info["baseline_physical_degradation_kwh"])
    physical_degradation = float(row["physical_degradation_kwh"])
    row["subset_k"] = k_label
    row["subset_selected_count"] = int(selected_count)
    row["full_selected_count"] = int(full_selected_count)
    row["baseline_case_id"] = case_info.get("case_id", "")
    row["baseline_physical_degradation_kwh"] = baseline_degradation
    row["baseline_restored_energy_loss_kwh"] = float(case_info["baseline_restored_energy_loss_kwh"])
    row["baseline_reproduction_ratio"] = (
        physical_degradation / baseline_degradation if baseline_degradation > 1.0e-9 else 0.0
    )
    row["baseline_degradation_gap_kwh"] = baseline_degradation - physical_degradation
    return row


def aggregate_by_k(case_rows):
    groups = {}
    for row in case_rows:
        groups.setdefault(row["subset_k"], []).append(row)

    summary = []
    for k_label, rows in groups.items():
        degradations = np.asarray([float(row["physical_degradation_kwh"]) for row in rows], dtype=float)
        baseline_degradations = np.asarray(
            [float(row["baseline_physical_degradation_kwh"]) for row in rows],
            dtype=float,
        )
        reproduction = np.asarray([float(row["baseline_reproduction_ratio"]) for row in rows], dtype=float)
        damaging = [row for row in rows if int(row["damaging_case"]) == 1]
        detected = np.asarray([int(row["fdia_detected"]) for row in rows], dtype=float)
        recovery = np.asarray(
            [float(row["mitigation_recovery_of_degradation_ratio_clipped"]) for row in damaging],
            dtype=float,
        )
        summary.append(
            {
                "subset_k": k_label,
                "case_count": len(rows),
                "mean_selected_count": float(np.mean([int(row["subset_selected_count"]) for row in rows])),
                "total_physical_degradation_kwh": float(np.sum(degradations)),
                "mean_physical_degradation_kwh": float(np.mean(degradations)),
                "max_physical_degradation_kwh": float(np.max(degradations)),
                "damaging_case_count": len(damaging),
                "damaging_case_rate": float(len(damaging) / max(len(rows), 1)),
                "total_baseline_physical_degradation_kwh": float(np.sum(baseline_degradations)),
                "mean_baseline_reproduction_ratio": float(np.mean(reproduction)),
                "max_baseline_reproduction_ratio": float(np.max(reproduction)),
                "total_baseline_reproduction_ratio": float(
                    np.sum(degradations) / np.sum(baseline_degradations)
                )
                if np.sum(baseline_degradations) > 1.0e-9
                else 0.0,
                "detection_rate": float(np.mean(detected)),
                "mean_mitigation_recovery_of_degradation_ratio_clipped": float(np.mean(recovery))
                if recovery.size
                else 0.0,
            }
        )

    def sort_key(row):
        if row["subset_k"] == "full":
            return 10**9
        return int(row["subset_k"])

    return sorted(summary, key=sort_key)


def main():
    args = parse_args()
    output_dir = resolve_path(
        controller_output_dir(args.output_dir, DEFAULT_OUTPUT_DIR, SYSTEM_NAME, args.controller)
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    registry_outputs = write_registry_outputs(
        make_controller_experiment(SYSTEM_NAME, args, load_model=False),
        output_dir / "registries",
    )
    learning_detectors = []
    if args.use_learning_detectors:
        learning_detectors = load_learning_detectors(
            resolve_path(args.learning_detector_dir),
            tasks=args.learning_tasks,
            model_names=args.learning_models,
        )

    damaging_cases = load_damaging_cases(args.damaging_cases)
    experiment = make_controller_experiment(SYSTEM_NAME, args, load_model=True)
    targets = branchflow_targets(experiment)
    target_by_measurement_index = {int(target.index[0]): target for target in targets}

    case_rows = []
    for case_index, case_info in enumerate(damaging_cases):
        scenario = baseline.generate_outage_scenario(experiment, int(case_info["scenario_seed"]), args)
        true_obs = baseline.scenario_observation(experiment, scenario)
        branchflows = np.asarray(true_obs["EdgeFeat(Branchflow)"], dtype=float).reshape(-1)
        full_selected = selected_branchflows(branchflows, args.branchflow_target_fraction)
        for k_value in args.k_values:
            k_count, k_label = parse_k_value(k_value, len(full_selected))
            selected = full_selected[:k_count]
            case_id = "BFAB_C{:04d}_K{}_seed{}".format(
                case_index,
                k_label,
                int(case_info["scenario_seed"]),
            )
            print(
                "running {} selected={}/{}".format(case_id, len(selected), len(full_selected)),
                flush=True,
            )
            result = run_subset_case(
                experiment,
                scenario,
                selected,
                learning_detectors,
                args,
                target_by_measurement_index,
            )
            row = summarize_case(
                case_id,
                scenario,
                result,
                args,
                case_info,
                k_label,
                len(selected),
                len(full_selected),
            )
            case_rows.append(row)

    summary_rows = aggregate_by_k(case_rows)
    paths = {
        "case_summary": output_dir / "tsg_ieee123_branchflow_subset_ablation_cases.csv",
        "k_summary": output_dir / "tsg_ieee123_branchflow_subset_ablation_k_summary.csv",
        "manifest": output_dir / "tsg_ieee123_branchflow_subset_ablation_manifest.json",
    }
    write_csv(case_rows, paths["case_summary"])
    write_csv(summary_rows, paths["k_summary"])
    manifest = {
        "experiment": "IEEE 123 branchflow_hiding top-k subset ablation",
        "system": SYSTEM_NAME,
        **controller_metadata(SYSTEM_NAME, args),
        "damaging_cases_input": str(resolve_path(args.damaging_cases)),
        "damaging_case_count": len(damaging_cases),
        "k_values": args.k_values,
        "branchflow_target_fraction": float(args.branchflow_target_fraction),
        "branchflow_scale": float(args.branchflow_scale),
        "case_row_count": len(case_rows),
        "summary_row_count": len(summary_rows),
        "learning_detectors_enabled": bool(args.use_learning_detectors),
        "learning_detector_count": len(learning_detectors),
        "registry_outputs": {key: str(value) for key, value in registry_outputs.items()},
        "outputs": {key: str(value) for key, value in paths.items()},
        "notes": (
            "Ablates the coordinated baseline branchflow_hiding attack by hiding "
            "only the first k top-positive branchflow observations selected in "
            "each damaging baseline case."
        ),
    }
    paths["manifest"].write_text(safe_json(manifest) + "\n")

    print("wrote {}".format(paths["case_summary"]), flush=True)
    print("wrote {}".format(paths["k_summary"]), flush=True)
    print("wrote {}".format(paths["manifest"]), flush=True)


if __name__ == "__main__":
    main()
