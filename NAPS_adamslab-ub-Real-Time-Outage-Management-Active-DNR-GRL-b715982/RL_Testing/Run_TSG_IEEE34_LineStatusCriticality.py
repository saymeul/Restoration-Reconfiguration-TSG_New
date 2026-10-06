"""IEEE 34-bus named line-status/topology observation criticality study.

This runner attacks one named topology/line-status observation at a time by
corrupting the controller's perceived Adjacency entry for a physical IEEE 34
line. OpenDSS and the outage scenario remain the physical ground truth.
"""

import argparse
import csv

import numpy as np

from FDIA_Common import clone_observation, mitigate_observation, select_fdia_aware_grl_action
from FDIA_DetectorSuite import load_learning_detectors, run_detector_suite
from FDIA_ExperimentCore import (
    RestorationExperiment,
    action_delta,
    physical_impact,
    resolve_path,
    safe_json,
    write_csv,
)
from IEEE34_VulnerabilityRegistry import build_observation_registry, write_registry_outputs
from Run_TSG_IEEE34_BaselineAttackStudy import (
    EPS,
    evaluate_action_on_scenario,
    generate_outage_scenario,
    outage_edges_for_csv,
    scenario_observation,
    trajectory_after_action_on_scenario,
    trajectory_energy_summary,
)
from TSG_ControllerConfig import (
    add_controller_args,
    controller_metadata,
    controller_output_dir,
    experiment_controller_model_path,
    experiment_controller_name,
    make_controller_experiment,
)


DEFAULT_OUTPUT_DIR = "paper_results/tsg_ieee34/line_status_criticality"


CASE_SUMMARY_FIELDS = """system,controller,controller_model_path,case_id,scenario,scenario_seed,scenario_generation_attempt,scenario_root_node,scenario_radius,scenario_subgraph_edge_count,scenario_outage_fraction,outage_edge_count,outage_edges,attack,attack_mode,target_family,target_observation_id,target_component_type,target_component_name,target_node_i,target_node_j,target_physical_meaning,clean_line_status_value,attacked_line_status_value,attack_applied,changed_measurements,clean_restored_energy_kwh,attacked_restored_energy_kwh,mitigated_restored_energy_kwh,restored_energy_loss_kwh,restored_energy_loss_ratio,restored_energy_loss_percent,physical_degradation_kwh,physical_degradation_ratio,physical_degradation_percent,accidental_improvement_kwh,damaging_case,improvement_case,residual_loss_after_mitigation_kwh,residual_degradation_after_mitigation_kwh,energy_recovered_kwh,degradation_recovered_kwh,mitigation_recovery_ratio,mitigation_recovery_of_degradation_ratio,mitigation_recovery_of_degradation_ratio_clipped,fdia_detected,detector_score,detected_channels,bdd_detected,learning_detected,learning_vote_fraction,bypass_high_impact,mitigation_selected_candidate,mitigation_detector_gate,attack_metadata,clean_policy_time_ms,attacked_policy_time_ms,mitigated_policy_time_ms,clean_action,attacked_action,mitigated_action,attacked_action_changed,attacked_switch_changes_vs_clean,attacked_load_changes_vs_clean,mitigated_action_changed,mitigated_switch_changes_vs_clean,mitigated_load_changes_vs_clean,clean_mean_energy_kw,attacked_mean_energy_kw,mitigated_mean_energy_kw,clean_mean_voltage_violation,attacked_mean_voltage_violation,mitigated_mean_voltage_violation,clean_mean_reward,attacked_mean_reward,mitigated_mean_reward""".split(",")

STEP_RESULT_FIELDS = """system,controller,controller_model_path,case_id,scenario,scenario_seed,outage_edge_count,outage_edges,attack,mode,target_family,target_observation_id,target_component_type,target_component_name,target_node_i,target_node_j,time_step,hour,action_changed,switch_changes_vs_clean,load_changes_vs_clean,action,reward,energy_kw,total_demand_kw,energy_ratio,measured_energy_ratio,voltage_violation,convergence_violation,branchflow_mean,branchflow_max,voltage_min,voltage_max,loads_served,loads_shed,initial_reward,initial_energy_ratio,initial_voltage_violation,solve_warning,energy_ratio_delta_vs_clean,energy_kw_delta_vs_clean,voltage_violation_delta_vs_clean,reward_delta_vs_clean,convergence_delta_vs_clean,loads_served_delta_vs_clean,physical_impact_score""".split(",")

CRITICALITY_FIELDS = """target_family,target_observation_id,target_component_type,target_component_name,target_node_i,target_node_j,case_count,attack_applied_count,attack_applied_rate,mean_abs_change,max_abs_change,mean_restored_energy_loss_kwh,max_restored_energy_loss_kwh,mean_physical_degradation_kwh,max_physical_degradation_kwh,mean_physical_degradation_percent,damaging_case_count,damaging_case_rate,mean_accidental_improvement_kwh,max_accidental_improvement_kwh,improvement_case_count,improvement_case_rate,mean_residual_degradation_after_mitigation_kwh,mean_mitigation_recovery_of_degradation_ratio,mean_mitigation_recovery_of_degradation_ratio_clipped,mean_mitigation_recovery_ratio,detection_rate,bypass_high_impact_rate,action_changed_rate,mean_switch_changes_vs_clean,mean_load_changes_vs_clean,criticality_rank""".split(",")

FAMILY_FIELDS = """target_family,case_count,target_count,mean_physical_degradation_kwh,max_physical_degradation_kwh,damaging_case_count,damaging_case_rate,action_changed_count,action_changed_rate,detection_rate,bypass_high_impact_rate""".split(",")


def parse_args():
    parser = argparse.ArgumentParser(
        description="IEEE 34-bus named line-status/topology criticality experiment."
    )
    add_controller_args(parser)
    parser.add_argument("--cases", type=int, default=30, help="Number of deterministic outage scenarios.")
    parser.add_argument("--seed", type=int, default=20260615)
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--step-hours", type=float, default=1.0)
    parser.add_argument("--start-hour", type=int, default=0)
    parser.add_argument(
        "--attack-mode",
        choices=["false_open", "false_closed", "flip"],
        default="false_open",
        help=(
            "false_open sets an observed connected line to open; false_closed hides "
            "an observed open/outage line as connected; flip toggles either state."
        ),
    )
    parser.add_argument(
        "--include-noop",
        action="store_true",
        help="Keep rows where the requested line-status corruption does not change the observation.",
    )
    parser.add_argument(
        "--max-targets",
        type=int,
        default=0,
        help="Optional smoke-test limit on number of named topology targets.",
    )
    parser.add_argument(
        "--target-start-index",
        type=int,
        default=0,
        help="Zero-based start index into the sorted named topology target list.",
    )
    parser.add_argument(
        "--target-count",
        type=int,
        default=0,
        help="Optional number of targets to evaluate after --target-start-index.",
    )
    parser.add_argument(
        "--merge-case-files",
        nargs="+",
        default=None,
        help="Merge completed chunk case CSVs and recompute ranking/family outputs without running simulations.",
    )
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--write-step-results", action="store_true")
    parser.add_argument("--bypass-loss-threshold-kwh", type=float, default=1.0e-6)

    parser.add_argument("--max-outage-fraction", type=float, default=0.50)
    parser.add_argument("--max-scenario-generation-attempts", type=int, default=100)

    parser.add_argument("--use-learning-detectors", action="store_true")
    parser.add_argument("--learning-detector-dir", default="34bus/paper_results/learning_detectors")
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


def target_entries(experiment):
    entries = [
        entry
        for entry in build_observation_registry(experiment)
        if entry.family == "topology" and entry.attackable and entry.current_grl_input
    ]
    return sorted(entries, key=lambda entry: str(entry.observation_id))


INT_CASE_FIELDS = {
    "scenario_seed",
    "scenario_generation_attempt",
    "scenario_radius",
    "scenario_subgraph_edge_count",
    "outage_edge_count",
    "target_node_i",
    "target_node_j",
    "attack_applied",
    "changed_measurements",
    "damaging_case",
    "improvement_case",
    "fdia_detected",
    "bdd_detected",
    "learning_detected",
    "bypass_high_impact",
    "mitigation_detector_gate",
    "attacked_action_changed",
    "attacked_switch_changes_vs_clean",
    "attacked_load_changes_vs_clean",
    "mitigated_action_changed",
    "mitigated_switch_changes_vs_clean",
    "mitigated_load_changes_vs_clean",
}

FLOAT_CASE_FIELDS = {
    "scenario_outage_fraction",
    "clean_line_status_value",
    "attacked_line_status_value",
    "clean_restored_energy_kwh",
    "attacked_restored_energy_kwh",
    "mitigated_restored_energy_kwh",
    "restored_energy_loss_kwh",
    "restored_energy_loss_ratio",
    "restored_energy_loss_percent",
    "physical_degradation_kwh",
    "physical_degradation_ratio",
    "physical_degradation_percent",
    "accidental_improvement_kwh",
    "residual_loss_after_mitigation_kwh",
    "residual_degradation_after_mitigation_kwh",
    "energy_recovered_kwh",
    "degradation_recovered_kwh",
    "mitigation_recovery_ratio",
    "mitigation_recovery_of_degradation_ratio",
    "mitigation_recovery_of_degradation_ratio_clipped",
    "detector_score",
    "learning_vote_fraction",
    "clean_policy_time_ms",
    "attacked_policy_time_ms",
    "mitigated_policy_time_ms",
    "clean_mean_energy_kw",
    "attacked_mean_energy_kw",
    "mitigated_mean_energy_kw",
    "clean_mean_voltage_violation",
    "attacked_mean_voltage_violation",
    "mitigated_mean_voltage_violation",
    "clean_mean_reward",
    "attacked_mean_reward",
    "mitigated_mean_reward",
}


def _csv_case_value(field, value):
    if value == "":
        return ""
    if field in INT_CASE_FIELDS:
        try:
            return int(float(value))
        except ValueError:
            return value
    if field in FLOAT_CASE_FIELDS:
        try:
            return float(value)
        except ValueError:
            return value
    return value


def load_case_rows(csv_paths):
    rows = []
    seen_case_ids = set()
    duplicate_case_ids = []
    for csv_path in csv_paths:
        path = resolve_path(csv_path)
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            for raw_row in reader:
                row = {field: _csv_case_value(field, value) for field, value in raw_row.items()}
                case_id = row.get("case_id")
                if case_id in seen_case_ids:
                    duplicate_case_ids.append(case_id)
                seen_case_ids.add(case_id)
                rows.append(row)
    if duplicate_case_ids:
        raise ValueError(
            "Duplicate case_id values found while merging chunks: {}".format(
                ", ".join(sorted(set(duplicate_case_ids))[:10])
            )
        )
    return rows


def write_csv_or_header(rows, path, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        write_csv(rows, path)
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.DictWriter(handle, fieldnames=fieldnames).writeheader()


def corrupt_line_status_entry(obs, target_entry, args):
    attacked = clone_observation(obs)
    adjacency = np.asarray(attacked["Adjacency"], dtype=float).copy()
    node_i = int(target_entry.index[0])
    node_j = int(target_entry.index[1])
    if node_i < 0 or node_j < 0:
        raise ValueError("Target {} has invalid adjacency index {}.".format(target_entry.observation_id, target_entry.index))

    original = float(adjacency[node_i, node_j])
    if args.attack_mode == "false_open":
        corrupted = 0.0
    elif args.attack_mode == "false_closed":
        corrupted = 1.0
    elif args.attack_mode == "flip":
        corrupted = 0.0 if original > 0.5 else 1.0
    else:
        raise ValueError("Unsupported line-status attack mode: {}".format(args.attack_mode))

    adjacency[node_i, node_j] = corrupted
    adjacency[node_j, node_i] = corrupted
    attacked["Adjacency"] = adjacency
    changed = abs(corrupted - original) > EPS
    return attacked, {
        "target": "Adjacency",
        "attack": "line_status_{}".format(args.attack_mode),
        "attack_mode": args.attack_mode,
        "target_observation_id": target_entry.observation_id,
        "target_component_type": target_entry.component_type,
        "target_component_name": target_entry.component_name,
        "target_node_i": node_i,
        "target_node_j": node_j,
        "original_value": original,
        "attacked_value": float(corrupted),
        "changed_measurements": int(changed),
        "attack_applied": int(changed),
        "mean_abs_change": abs(float(corrupted) - original),
        "max_abs_change": abs(float(corrupted) - original),
    }


def case_energy_summary(result, args):
    clean = trajectory_energy_summary(result["clean_trajectory"], args.step_hours)
    attacked = trajectory_energy_summary(result["attacked_trajectory"], args.step_hours)
    mitigated = trajectory_energy_summary(result["mitigated_trajectory"], args.step_hours)
    energy_loss = clean["restored_energy_kwh"] - attacked["restored_energy_kwh"]
    recovered = mitigated["restored_energy_kwh"] - attacked["restored_energy_kwh"]
    residual_loss = clean["restored_energy_kwh"] - mitigated["restored_energy_kwh"]
    return clean, attacked, mitigated, energy_loss, recovered, residual_loss


def case_summary(case_id, scenario, target_entry, result, args):
    clean, attacked, mitigated, energy_loss, recovered, residual_loss = case_energy_summary(result, args)
    clean_energy = clean["restored_energy_kwh"]
    loss_ratio = energy_loss / clean_energy if clean_energy > EPS else 0.0
    recovery_ratio = recovered / energy_loss if abs(energy_loss) > EPS else 0.0
    physical_degradation = max(0.0, energy_loss)
    accidental_improvement = max(0.0, -energy_loss)
    physical_degradation_ratio = physical_degradation / clean_energy if clean_energy > EPS else 0.0
    residual_degradation = max(0.0, residual_loss)
    degradation_recovered = physical_degradation - residual_degradation
    degradation_recovery_ratio = (
        degradation_recovered / physical_degradation
        if physical_degradation > EPS
        else 0.0
    )
    degradation_recovery_ratio_clipped = min(1.0, max(0.0, degradation_recovery_ratio))
    detection = result["detection"]
    delta_attacked = action_delta(
        result["clean_action"],
        result["attacked_action"],
        result["experiment"].num_switches,
    )
    delta_mitigated = action_delta(
        result["clean_action"],
        result["mitigated_action"],
        result["experiment"].num_switches,
    )
    mitigation_metadata = result["fdia_aware"].get("fdia_aware_metadata", {})
    attack_metadata = result["attack_metadata"]
    return {
        "system": "34bus",
        "controller": experiment_controller_name(result["experiment"]),
        "controller_model_path": experiment_controller_model_path(result["experiment"]),
        "case_id": case_id,
        "scenario": scenario["scenario"],
        "scenario_seed": int(scenario["scenario_seed"]),
        "scenario_generation_attempt": int(scenario["generation_attempt"]),
        "scenario_root_node": scenario["root_node"],
        "scenario_radius": int(scenario["radius"]),
        "scenario_subgraph_edge_count": int(scenario["subgraph_edge_count"]),
        "scenario_outage_fraction": float(scenario["outage_fraction"]),
        "outage_edge_count": int(scenario["outage_edge_count"]),
        "outage_edges": outage_edges_for_csv(scenario["outage_edges"]),
        "attack": attack_metadata.get("attack", ""),
        "attack_mode": attack_metadata.get("attack_mode", ""),
        "target_family": target_entry.family,
        "target_observation_id": target_entry.observation_id,
        "target_component_type": target_entry.component_type,
        "target_component_name": target_entry.component_name,
        "target_node_i": int(target_entry.index[0]),
        "target_node_j": int(target_entry.index[1]),
        "target_physical_meaning": target_entry.physical_meaning,
        "clean_line_status_value": float(attack_metadata.get("original_value", 0.0)),
        "attacked_line_status_value": float(attack_metadata.get("attacked_value", 0.0)),
        "attack_applied": int(attack_metadata.get("attack_applied", 0)),
        "changed_measurements": int(attack_metadata.get("changed_measurements", 0)),
        "clean_restored_energy_kwh": clean["restored_energy_kwh"],
        "attacked_restored_energy_kwh": attacked["restored_energy_kwh"],
        "mitigated_restored_energy_kwh": mitigated["restored_energy_kwh"],
        "restored_energy_loss_kwh": energy_loss,
        "restored_energy_loss_ratio": loss_ratio,
        "restored_energy_loss_percent": 100.0 * loss_ratio,
        "physical_degradation_kwh": physical_degradation,
        "physical_degradation_ratio": physical_degradation_ratio,
        "physical_degradation_percent": 100.0 * physical_degradation_ratio,
        "accidental_improvement_kwh": accidental_improvement,
        "damaging_case": int(physical_degradation > EPS),
        "improvement_case": int(accidental_improvement > EPS),
        "residual_loss_after_mitigation_kwh": residual_loss,
        "residual_degradation_after_mitigation_kwh": residual_degradation,
        "energy_recovered_kwh": recovered,
        "degradation_recovered_kwh": degradation_recovered,
        "mitigation_recovery_ratio": recovery_ratio,
        "mitigation_recovery_of_degradation_ratio": degradation_recovery_ratio,
        "mitigation_recovery_of_degradation_ratio_clipped": degradation_recovery_ratio_clipped,
        "fdia_detected": int(bool(detection.get("detected", False))),
        "detector_score": float(detection.get("score", 0.0)),
        "detected_channels": detection.get("detected_channels", []),
        "bdd_detected": int(bool(detection.get("bdd_report", {}).get("detected", False))),
        "learning_detected": int(bool(detection.get("learning_detected", False))),
        "learning_vote_fraction": float(detection.get("learning_vote_fraction", 0.0)),
        "bypass_high_impact": int(
            (not bool(detection.get("detected", False)))
            and energy_loss > float(args.bypass_loss_threshold_kwh)
        ),
        "mitigation_selected_candidate": result["fdia_aware"].get("selected_candidate", ""),
        "mitigation_detector_gate": int(bool(mitigation_metadata.get("detector_gate", False))),
        "attack_metadata": attack_metadata,
        "clean_policy_time_ms": result["clean_policy_ms"],
        "attacked_policy_time_ms": result["attacked_policy_ms"],
        "mitigated_policy_time_ms": result["fdia_aware"].get("policy_time_ms", 0.0),
        "clean_action": np.asarray(result["clean_action"], dtype=int).tolist(),
        "attacked_action": np.asarray(result["attacked_action"], dtype=int).tolist(),
        "mitigated_action": np.asarray(result["mitigated_action"], dtype=int).tolist(),
        "attacked_action_changed": delta_attacked["action_changed"],
        "attacked_switch_changes_vs_clean": delta_attacked["switch_changes_vs_clean"],
        "attacked_load_changes_vs_clean": delta_attacked["load_changes_vs_clean"],
        "mitigated_action_changed": delta_mitigated["action_changed"],
        "mitigated_switch_changes_vs_clean": delta_mitigated["switch_changes_vs_clean"],
        "mitigated_load_changes_vs_clean": delta_mitigated["load_changes_vs_clean"],
        "clean_mean_energy_kw": clean["mean_energy_kw"],
        "attacked_mean_energy_kw": attacked["mean_energy_kw"],
        "mitigated_mean_energy_kw": mitigated["mean_energy_kw"],
        "clean_mean_voltage_violation": clean["mean_voltage_violation"],
        "attacked_mean_voltage_violation": attacked["mean_voltage_violation"],
        "mitigated_mean_voltage_violation": mitigated["mean_voltage_violation"],
        "clean_mean_reward": clean["mean_reward"],
        "attacked_mean_reward": attacked["mean_reward"],
        "mitigated_mean_reward": mitigated["mean_reward"],
    }


def step_rows(case_id, scenario, target_entry, result):
    rows = []
    clean_trajectory = result["clean_trajectory"]
    modes = [
        ("clean_baseline", result["clean_action"], result["clean_trajectory"]),
        ("attacked_no_defense", result["attacked_action"], result["attacked_trajectory"]),
        ("mitigated", result["mitigated_action"], result["mitigated_trajectory"]),
    ]
    for mode, action, trajectory in modes:
        for clean_metrics, metrics in zip(clean_trajectory, trajectory):
            if mode == "clean_baseline":
                impact = {
                    "energy_ratio_delta_vs_clean": 0.0,
                    "energy_kw_delta_vs_clean": 0.0,
                    "voltage_violation_delta_vs_clean": 0.0,
                    "reward_delta_vs_clean": 0.0,
                    "convergence_delta_vs_clean": 0.0,
                    "loads_served_delta_vs_clean": 0,
                    "physical_impact_score": 0.0,
                }
            else:
                impact = physical_impact(clean_metrics, metrics)
            delta = action_delta(result["clean_action"], action, result["experiment"].num_switches)
            row = {
                "system": "34bus",
                "controller": experiment_controller_name(result["experiment"]),
                "controller_model_path": experiment_controller_model_path(result["experiment"]),
                "case_id": case_id,
                "scenario": scenario["scenario"],
                "scenario_seed": int(scenario["scenario_seed"]),
                "outage_edge_count": int(scenario["outage_edge_count"]),
                "outage_edges": outage_edges_for_csv(scenario["outage_edges"]),
                "attack": result["attack_metadata"].get("attack", ""),
                "mode": mode,
                "target_family": target_entry.family,
                "target_observation_id": target_entry.observation_id,
                "target_component_type": target_entry.component_type,
                "target_component_name": target_entry.component_name,
                "target_node_i": int(target_entry.index[0]),
                "target_node_j": int(target_entry.index[1]),
                "time_step": metrics.get("time_step", ""),
                "hour": metrics.get("hour", ""),
                "action_changed": delta["action_changed"],
                "switch_changes_vs_clean": delta["switch_changes_vs_clean"],
                "load_changes_vs_clean": delta["load_changes_vs_clean"],
                "action": np.asarray(action, dtype=int).tolist(),
            }
            row.update(metrics)
            row.update(impact)
            rows.append(row)
    return rows


def aggregate_criticality(case_rows):
    groups = {}
    for row in case_rows:
        key = (
            row["target_family"],
            row["target_observation_id"],
            row["target_component_type"],
            row["target_component_name"],
            row["target_node_i"],
            row["target_node_j"],
        )
        groups.setdefault(key, []).append(row)

    ranking = []
    for (family, observation_id, component_type, component_name, node_i, node_j), rows in sorted(groups.items()):
        applied_rows = [row for row in rows if int(row.get("attack_applied", 0)) == 1]
        metric_rows = applied_rows or rows
        damaging_rows = [row for row in metric_rows if int(row["damaging_case"]) == 1]
        improvement_rows = [row for row in metric_rows if int(row["improvement_case"]) == 1]
        degradation_recovery_values = [
            row["mitigation_recovery_of_degradation_ratio"] for row in damaging_rows
        ]
        degradation_recovery_clipped_values = [
            row["mitigation_recovery_of_degradation_ratio_clipped"] for row in damaging_rows
        ]
        abs_changes = [abs(row["attacked_line_status_value"] - row["clean_line_status_value"]) for row in metric_rows]
        ranking.append(
            {
                "target_family": family,
                "target_observation_id": observation_id,
                "target_component_type": component_type,
                "target_component_name": component_name,
                "target_node_i": node_i,
                "target_node_j": node_j,
                "case_count": len(rows),
                "attack_applied_count": len(applied_rows),
                "attack_applied_rate": len(applied_rows) / max(len(rows), 1),
                "mean_abs_change": float(np.mean(abs_changes)) if abs_changes else 0.0,
                "max_abs_change": float(np.max(abs_changes)) if abs_changes else 0.0,
                "mean_restored_energy_loss_kwh": float(
                    np.mean([row["restored_energy_loss_kwh"] for row in metric_rows])
                ),
                "max_restored_energy_loss_kwh": float(
                    np.max([row["restored_energy_loss_kwh"] for row in metric_rows])
                ),
                "mean_physical_degradation_kwh": float(
                    np.mean([row["physical_degradation_kwh"] for row in metric_rows])
                ),
                "max_physical_degradation_kwh": float(
                    np.max([row["physical_degradation_kwh"] for row in metric_rows])
                ),
                "mean_physical_degradation_percent": float(
                    np.mean([row["physical_degradation_percent"] for row in metric_rows])
                ),
                "damaging_case_count": len(damaging_rows),
                "damaging_case_rate": float(len(damaging_rows) / len(metric_rows)) if metric_rows else 0.0,
                "mean_accidental_improvement_kwh": float(
                    np.mean([row["accidental_improvement_kwh"] for row in metric_rows])
                ),
                "max_accidental_improvement_kwh": float(
                    np.max([row["accidental_improvement_kwh"] for row in metric_rows])
                ),
                "improvement_case_count": len(improvement_rows),
                "improvement_case_rate": float(len(improvement_rows) / len(metric_rows)) if metric_rows else 0.0,
                "mean_residual_degradation_after_mitigation_kwh": float(
                    np.mean([row["residual_degradation_after_mitigation_kwh"] for row in metric_rows])
                ),
                "mean_mitigation_recovery_of_degradation_ratio": float(
                    np.mean(degradation_recovery_values)
                    if degradation_recovery_values
                    else 0.0
                ),
                "mean_mitigation_recovery_of_degradation_ratio_clipped": float(
                    np.mean(degradation_recovery_clipped_values)
                    if degradation_recovery_clipped_values
                    else 0.0
                ),
                "mean_mitigation_recovery_ratio": float(
                    np.mean([row["mitigation_recovery_ratio"] for row in metric_rows])
                ),
                "detection_rate": float(np.mean([row["fdia_detected"] for row in metric_rows])),
                "bypass_high_impact_rate": float(np.mean([row["bypass_high_impact"] for row in metric_rows])),
                "action_changed_rate": float(np.mean([row["attacked_action_changed"] for row in metric_rows])),
                "mean_switch_changes_vs_clean": float(
                    np.mean([row["attacked_switch_changes_vs_clean"] for row in metric_rows])
                ),
                "mean_load_changes_vs_clean": float(
                    np.mean([row["attacked_load_changes_vs_clean"] for row in metric_rows])
                ),
            }
        )

    ranking.sort(
        key=lambda row: (
            row["mean_physical_degradation_kwh"],
            row["max_physical_degradation_kwh"],
            row["damaging_case_rate"],
        ),
        reverse=True,
    )
    for rank, row in enumerate(ranking, start=1):
        row["criticality_rank"] = rank
    return ranking


def aggregate_by_family(case_rows):
    groups = {}
    for row in case_rows:
        groups.setdefault(row["target_family"], []).append(row)
    rows = []
    for family, family_rows in sorted(groups.items()):
        damaging_rows = [row for row in family_rows if int(row["damaging_case"]) == 1]
        changed_rows = [row for row in family_rows if int(row["attacked_action_changed"]) == 1]
        rows.append(
            {
                "target_family": family,
                "case_count": len(family_rows),
                "target_count": len(set(row["target_observation_id"] for row in family_rows)),
                "mean_physical_degradation_kwh": float(
                    np.mean([row["physical_degradation_kwh"] for row in family_rows])
                ),
                "max_physical_degradation_kwh": float(
                    np.max([row["physical_degradation_kwh"] for row in family_rows])
                ),
                "damaging_case_count": len(damaging_rows),
                "damaging_case_rate": float(len(damaging_rows) / len(family_rows)) if family_rows else 0.0,
                "action_changed_count": len(changed_rows),
                "action_changed_rate": float(len(changed_rows) / len(family_rows)) if family_rows else 0.0,
                "detection_rate": float(np.mean([row["fdia_detected"] for row in family_rows])),
                "bypass_high_impact_rate": float(np.mean([row["bypass_high_impact"] for row in family_rows])),
            }
        )
    return rows


def same_action(left, right):
    return np.array_equal(np.asarray(left, dtype=int), np.asarray(right, dtype=int))


def prepare_scenario_context(experiment, scenario, args):
    true_obs = scenario_observation(experiment, scenario)
    clean_action, clean_policy_ms = experiment.predict_action(true_obs)
    clean_trajectory, _clean_first_obs = trajectory_after_action_on_scenario(
        experiment,
        scenario,
        clean_action,
        args,
    )
    return {
        "true_obs": true_obs,
        "clean_action": clean_action,
        "clean_policy_ms": clean_policy_ms,
        "clean_trajectory": clean_trajectory,
    }


def run_target_case(experiment, scenario, scenario_context, target_entry, learning_detectors, args):
    true_obs = scenario_context["true_obs"]
    clean_action = scenario_context["clean_action"]
    clean_policy_ms = scenario_context["clean_policy_ms"]
    clean_trajectory = scenario_context["clean_trajectory"]
    policy_obs, attack_metadata = corrupt_line_status_entry(true_obs, target_entry, args)
    if not args.include_noop and int(attack_metadata["attack_applied"]) == 0:
        return None

    detection = run_detector_suite(true_obs, policy_obs, learning_detectors=learning_detectors)
    attacked_action, attacked_policy_ms = experiment.predict_action(policy_obs)
    if same_action(attacked_action, clean_action):
        attacked_trajectory = clean_trajectory
    else:
        attacked_trajectory, _attacked_first_obs = trajectory_after_action_on_scenario(
            experiment,
            scenario,
            attacked_action,
            args,
        )

    mitigated_obs, observation_mitigation = mitigate_observation(true_obs, policy_obs, detection)

    def predict_action_fn(obs):
        return experiment.predict_action(obs)

    def evaluate_action_fn(action):
        metrics, _obs = evaluate_action_on_scenario(experiment, scenario, action)
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
    if same_action(mitigated_action, clean_action):
        mitigated_trajectory = clean_trajectory
    elif same_action(mitigated_action, attacked_action):
        mitigated_trajectory = attacked_trajectory
    else:
        mitigated_trajectory, _mitigated_first_obs = trajectory_after_action_on_scenario(
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


def main():
    args = parse_args()
    args.output_dir = controller_output_dir(
        args.output_dir,
        DEFAULT_OUTPUT_DIR,
        "34bus",
        args.controller,
    )
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "case_summary": output_dir / "tsg_ieee34_line_status_criticality_cases.csv",
        "criticality_ranking": output_dir / "tsg_ieee34_line_status_criticality_ranking.csv",
        "family_summary": output_dir / "tsg_ieee34_line_status_criticality_family_summary.csv",
        "manifest": output_dir / "tsg_ieee34_line_status_criticality_manifest.json",
    }
    if args.write_step_results:
        paths["step_results"] = output_dir / "tsg_ieee34_line_status_criticality_steps.csv"

    if args.merge_case_files is not None:
        case_rows = load_case_rows(args.merge_case_files)
        criticality_rows = aggregate_criticality(case_rows)
        family_rows = aggregate_by_family(case_rows)
        write_csv_or_header(case_rows, paths["case_summary"], CASE_SUMMARY_FIELDS)
        write_csv_or_header(criticality_rows, paths["criticality_ranking"], CRITICALITY_FIELDS)
        write_csv_or_header(family_rows, paths["family_summary"], FAMILY_FIELDS)
        manifest = {
            "experiment": "IEEE 34-bus named line-status/topology criticality study",
            "system": "34bus",
            "merge_mode": True,
            "input_case_files": [str(resolve_path(path)) for path in args.merge_case_files],
            "merged_case_count": len(case_rows),
            "merged_target_count": len(set(row["target_observation_id"] for row in case_rows)),
            "attack_mode": args.attack_mode,
            "outputs": {key: str(value) for key, value in paths.items()},
            "notes": (
                "This output merges completed deterministic target chunks and recomputes "
                "criticality/family summaries from the merged case rows."
            ),
        }
        paths["manifest"].write_text(safe_json(manifest) + "\n")
        print("wrote {}".format(paths["case_summary"]), flush=True)
        print("wrote {}".format(paths["criticality_ranking"]), flush=True)
        print("wrote {}".format(paths["family_summary"]), flush=True)
        print("wrote {}".format(paths["manifest"]), flush=True)
        return

    registry_experiment = make_controller_experiment("34bus", args, load_model=False)
    registry_outputs = write_registry_outputs(registry_experiment, output_dir / "registries")

    learning_detectors = []
    if args.use_learning_detectors:
        learning_detectors = load_learning_detectors(
            resolve_path(args.learning_detector_dir),
            tasks=args.learning_tasks,
            model_names=args.learning_models,
        )

    experiment = make_controller_experiment("34bus", args, load_model=True)
    all_targets = target_entries(experiment)
    target_start = max(0, int(args.target_start_index))
    if target_start > len(all_targets):
        raise ValueError(
            "--target-start-index {} is beyond the available target count {}".format(
                target_start,
                len(all_targets),
            )
        )
    if int(args.target_count) > 0:
        target_end = min(target_start + int(args.target_count), len(all_targets))
    elif int(args.max_targets) > 0:
        target_end = min(target_start + int(args.max_targets), len(all_targets))
    else:
        target_end = len(all_targets)
    targets = all_targets[target_start:target_end]

    rng = np.random.default_rng(int(args.seed))
    case_rows = []
    all_step_rows = []
    skipped = 0

    for case_index in range(int(args.cases)):
        scenario_seed = int(rng.integers(1, 2**31 - 1))
        scenario = generate_outage_scenario(experiment, scenario_seed, args)
        scenario_context = prepare_scenario_context(experiment, scenario, args)
        for target in targets:
            case_id = "L{:04d}_{}_{}".format(
                case_index,
                args.attack_mode,
                target.observation_id.replace(".", "_").replace("-", "_"),
            )
            print(
                "running {} seed={} target={}".format(
                    case_id,
                    scenario_seed,
                    target.observation_id,
                ),
                flush=True,
            )
            result = run_target_case(
                experiment,
                scenario,
                scenario_context,
                target,
                learning_detectors,
                args,
            )
            if result is None:
                skipped += 1
                continue
            case_rows.append(case_summary(case_id, scenario, target, result, args))
            if args.write_step_results:
                all_step_rows.extend(step_rows(case_id, scenario, target, result))

    criticality_rows = aggregate_criticality(case_rows)
    family_rows = aggregate_by_family(case_rows) if case_rows else []

    write_csv_or_header(case_rows, paths["case_summary"], CASE_SUMMARY_FIELDS)
    write_csv_or_header(criticality_rows, paths["criticality_ranking"], CRITICALITY_FIELDS)
    write_csv_or_header(family_rows, paths["family_summary"], FAMILY_FIELDS)
    if args.write_step_results:
        write_csv_or_header(all_step_rows, paths["step_results"], STEP_RESULT_FIELDS)

    manifest = {
        "experiment": "IEEE 34-bus named line-status/topology criticality study",
        "system": "34bus",
        **controller_metadata("34bus", args),
        "cases": int(args.cases),
        "attack_mode": args.attack_mode,
        "full_target_count": len(all_targets),
        "target_start_index": target_start,
        "target_end_index_exclusive": target_end,
        "target_count": len(targets),
        "executed_case_count": len(case_rows),
        "skipped_noop_count": skipped,
        "horizon": int(args.horizon),
        "step_hours": float(args.step_hours),
        "start_hour": int(args.start_hour),
        "seed": int(args.seed),
        "scenario_mode": "deterministic_outage_edges",
        "max_outage_fraction": float(args.max_outage_fraction),
        "max_scenario_generation_attempts": int(args.max_scenario_generation_attempts),
        "write_step_results": bool(args.write_step_results),
        "learning_detectors_enabled": bool(args.use_learning_detectors),
        "learning_detector_count": len(learning_detectors),
        "registry_outputs": {key: str(value) for key, value in registry_outputs.items()},
        "outputs": {key: str(value) for key, value in paths.items()},
        "notes": (
            "Each case corrupts one named topology Adjacency observation seen by the controller. "
            "OpenDSS remains the physical ground truth for clean, attacked, and mitigated action evaluation. "
            "false_open reports a connected line as open; false_closed reports an open/outage line as connected."
        ),
    }
    paths["manifest"].write_text(safe_json(manifest) + "\n")

    print("wrote {}".format(paths["case_summary"]), flush=True)
    print("wrote {}".format(paths["criticality_ranking"]), flush=True)
    print("wrote {}".format(paths["family_summary"]), flush=True)
    print("wrote {}".format(paths["manifest"]), flush=True)


if __name__ == "__main__":
    main()
