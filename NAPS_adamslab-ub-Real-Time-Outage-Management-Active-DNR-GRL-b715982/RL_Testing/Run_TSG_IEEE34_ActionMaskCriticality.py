"""IEEE 34-bus action-mask observation criticality study.

This runner attacks one named ActionMasking observation at a time and measures
how much physical restoration performance changes. It is the first focused
critical-observation experiment for the TSG vulnerability-assessment paper.
"""

import argparse

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


CASE_SUMMARY_FIELDS = """system,controller,controller_model_path,case_id,scenario,scenario_seed,scenario_generation_attempt,scenario_root_node,scenario_radius,scenario_subgraph_edge_count,scenario_outage_fraction,outage_edge_count,outage_edges,attack,attack_mode,target_observation_id,target_family,target_component_type,target_component_name,target_action_index,target_physical_meaning,clean_target_mask_value,clean_target_action_value,attacked_target_action_value,mitigated_target_action_value,attack_applied,clean_restored_energy_kwh,attacked_restored_energy_kwh,mitigated_restored_energy_kwh,restored_energy_loss_kwh,restored_energy_loss_ratio,restored_energy_loss_percent,physical_degradation_kwh,physical_degradation_ratio,physical_degradation_percent,accidental_improvement_kwh,damaging_case,improvement_case,residual_loss_after_mitigation_kwh,residual_degradation_after_mitigation_kwh,energy_recovered_kwh,degradation_recovered_kwh,mitigation_recovery_ratio,mitigation_recovery_of_degradation_ratio,mitigation_recovery_of_degradation_ratio_clipped,fdia_detected,detector_score,detected_channels,bdd_detected,learning_detected,learning_vote_fraction,bypass_high_impact,mitigation_selected_candidate,mitigation_detector_gate,attack_metadata,clean_policy_time_ms,attacked_policy_time_ms,mitigated_policy_time_ms,clean_action,attacked_action,mitigated_action,attacked_action_changed,attacked_switch_changes_vs_clean,attacked_load_changes_vs_clean,mitigated_action_changed,mitigated_switch_changes_vs_clean,mitigated_load_changes_vs_clean,clean_mean_energy_kw,attacked_mean_energy_kw,mitigated_mean_energy_kw,clean_mean_voltage_violation,attacked_mean_voltage_violation,mitigated_mean_voltage_violation,clean_mean_reward,attacked_mean_reward,mitigated_mean_reward""".split(",")

STEP_RESULT_FIELDS = """system,controller,controller_model_path,case_id,scenario,scenario_seed,outage_edge_count,outage_edges,attack,mode,target_observation_id,target_component_type,target_component_name,target_action_index,time_step,hour,action_changed,switch_changes_vs_clean,load_changes_vs_clean,action,reward,energy_kw,total_demand_kw,energy_ratio,measured_energy_ratio,voltage_violation,convergence_violation,branchflow_mean,branchflow_max,voltage_min,voltage_max,loads_served,loads_shed,initial_reward,initial_energy_ratio,initial_voltage_violation,solve_warning,energy_ratio_delta_vs_clean,energy_kw_delta_vs_clean,voltage_violation_delta_vs_clean,reward_delta_vs_clean,convergence_delta_vs_clean,loads_served_delta_vs_clean,physical_impact_score""".split(",")

CRITICALITY_FIELDS = """target_observation_id,target_component_type,target_component_name,target_action_index,case_count,attack_applied_count,attack_applied_rate,mean_restored_energy_loss_kwh,max_restored_energy_loss_kwh,mean_physical_degradation_kwh,max_physical_degradation_kwh,mean_accidental_improvement_kwh,max_accidental_improvement_kwh,damaging_case_count,damaging_case_rate,improvement_case_count,improvement_case_rate,mean_restored_energy_loss_percent,mean_physical_degradation_percent,mean_residual_degradation_after_mitigation_kwh,mean_mitigation_recovery_of_degradation_ratio,mean_mitigation_recovery_of_degradation_ratio_clipped,mean_mitigation_recovery_ratio,detection_rate,bypass_high_impact_rate,action_changed_rate,mean_switch_changes_vs_clean,mean_load_changes_vs_clean,criticality_rank""".split(",")
SYSTEM_NAME = "34bus"
DEFAULT_OUTPUT_DIR = "paper_results/tsg_ieee34/action_mask_criticality"


def write_csv_or_header(rows, path, fieldnames):
    if rows:
        write_csv(rows, path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(",".join(fieldnames) + "\n")


def parse_args():
    parser = argparse.ArgumentParser(
        description="IEEE 34-bus named ActionMasking observation criticality experiment."
    )
    parser.add_argument("--cases", type=int, default=3, help="Number of random outage seeds.")
    parser.add_argument("--seed", type=int, default=20260615)
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--step-hours", type=float, default=1.0)
    parser.add_argument("--start-hour", type=int, default=0)
    parser.add_argument("--max-outage-fraction", type=float, default=0.50)
    parser.add_argument("--max-scenario-generation-attempts", type=int, default=100)
    parser.add_argument(
        "--target-scope",
        choices=["switch", "load", "switch_and_load"],
        default="switch",
        help="ActionMasking observations to attack.",
    )
    parser.add_argument(
        "--attack-mode",
        choices=["false_unavailable", "false_available"],
        default="false_unavailable",
        help="false_unavailable sets an action mask entry to 1; false_available sets it to 0.",
    )
    parser.add_argument(
        "--include-noop",
        action="store_true",
        help="Keep rows where the requested corruption does not change the mask value.",
    )
    parser.add_argument(
        "--max-targets",
        type=int,
        default=0,
        help="Optional smoke-test limit on number of target observations. 0 means all.",
    )
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    add_controller_args(parser)
    parser.add_argument("--bypass-loss-threshold-kwh", type=float, default=1.0e-6)

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


def target_entries(experiment, scope):
    entries = [
        entry
        for entry in build_observation_registry(experiment)
        if entry.observation_key == "ActionMasking"
    ]
    if scope == "switch":
        entries = [
            entry
            for entry in entries
            if entry.component_type in ("sectionalizing_switch", "tie_switch")
        ]
    elif scope == "load":
        entries = [entry for entry in entries if entry.component_type == "dispatch_load"]
    else:
        entries = [
            entry
            for entry in entries
            if entry.component_type
            in ("sectionalizing_switch", "tie_switch", "dispatch_load")
        ]
    return sorted(entries, key=lambda entry: int(entry.index[0]))


def corrupt_action_mask_entry(obs, target_entry, attack_mode):
    attacked = clone_observation(obs)
    mask = np.asarray(attacked["ActionMasking"], dtype=float).reshape(-1).copy()
    target_index = int(target_entry.index[0])
    original_value = float(mask[target_index])
    if attack_mode == "false_unavailable":
        attacked_value = 1.0
    else:
        attacked_value = 0.0
    mask[target_index] = attacked_value
    attacked["ActionMasking"] = mask
    changed = abs(attacked_value - original_value) > 1.0e-9
    return attacked, {
        "target": "ActionMasking",
        "attack": "action_mask_{}".format(attack_mode),
        "target_observation_id": target_entry.observation_id,
        "target_component_type": target_entry.component_type,
        "target_component_name": target_entry.component_name,
        "target_action_index": target_index,
        "original_mask_value": original_value,
        "attacked_mask_value": attacked_value,
        "attack_applied": int(changed),
    }


def case_energy_summary(result, args):
    clean = trajectory_energy_summary(result["clean_trajectory"], args.step_hours)
    attacked = trajectory_energy_summary(result["attacked_trajectory"], args.step_hours)
    mitigated = trajectory_energy_summary(result["mitigated_trajectory"], args.step_hours)
    energy_loss = clean["restored_energy_kwh"] - attacked["restored_energy_kwh"]
    recovered = mitigated["restored_energy_kwh"] - attacked["restored_energy_kwh"]
    residual_loss = clean["restored_energy_kwh"] - mitigated["restored_energy_kwh"]
    return clean, attacked, mitigated, energy_loss, recovered, residual_loss


def case_summary(case_id, scenario, target_entry, attack_mode, result, args):
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
    target_index = int(target_entry.index[0])
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
        "attack": "action_mask_{}".format(attack_mode),
        "attack_mode": attack_mode,
        "target_observation_id": target_entry.observation_id,
        "target_family": target_entry.family,
        "target_component_type": target_entry.component_type,
        "target_component_name": target_entry.component_name,
        "target_action_index": target_index,
        "target_physical_meaning": target_entry.physical_meaning,
        "clean_target_mask_value": float(np.asarray(result["true_obs"]["ActionMasking"])[target_index]),
        "clean_target_action_value": int(np.asarray(result["clean_action"], dtype=int)[target_index]),
        "attacked_target_action_value": int(np.asarray(result["attacked_action"], dtype=int)[target_index]),
        "mitigated_target_action_value": int(np.asarray(result["mitigated_action"], dtype=int)[target_index]),
        "attack_applied": int(result["attack_metadata"].get("attack_applied", 0)),
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
        "attack_metadata": result["attack_metadata"],
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


def step_rows(case_id, scenario, target_entry, attack_mode, result):
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
                "attack": "action_mask_{}".format(attack_mode),
                "mode": mode,
                "target_observation_id": target_entry.observation_id,
                "target_component_type": target_entry.component_type,
                "target_component_name": target_entry.component_name,
                "target_action_index": int(target_entry.index[0]),
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
            row["target_observation_id"],
            row["target_component_type"],
            row["target_component_name"],
            row["target_action_index"],
        )
        groups.setdefault(key, []).append(row)

    ranking = []
    for (observation_id, component_type, component_name, action_index), rows in sorted(groups.items()):
        applied_rows = [row for row in rows if int(row.get("attack_applied", 0)) == 1]
        metric_rows = applied_rows or rows
        signed_losses = [row["restored_energy_loss_kwh"] for row in metric_rows]
        degradations = [row["physical_degradation_kwh"] for row in metric_rows]
        improvements = [row["accidental_improvement_kwh"] for row in metric_rows]
        damaging_rows = [row for row in metric_rows if row["damaging_case"]]
        improvement_rows = [row for row in metric_rows if row["improvement_case"]]
        degradation_recovery_values = [
            row["mitigation_recovery_of_degradation_ratio"] for row in damaging_rows
        ]
        degradation_recovery_clipped_values = [
            row["mitigation_recovery_of_degradation_ratio_clipped"] for row in damaging_rows
        ]
        ranking.append(
            {
                "target_observation_id": observation_id,
                "target_component_type": component_type,
                "target_component_name": component_name,
                "target_action_index": action_index,
                "case_count": len(rows),
                "attack_applied_count": len(applied_rows),
                "attack_applied_rate": len(applied_rows) / max(len(rows), 1),
                "mean_restored_energy_loss_kwh": float(np.mean(signed_losses)),
                "max_restored_energy_loss_kwh": float(np.max(signed_losses)),
                "mean_physical_degradation_kwh": float(np.mean(degradations)),
                "max_physical_degradation_kwh": float(np.max(degradations)),
                "mean_accidental_improvement_kwh": float(np.mean(improvements)),
                "max_accidental_improvement_kwh": float(np.max(improvements)),
                "damaging_case_count": len(damaging_rows),
                "damaging_case_rate": float(len(damaging_rows) / len(metric_rows)) if metric_rows else 0.0,
                "improvement_case_count": len(improvement_rows),
                "improvement_case_rate": float(len(improvement_rows) / len(metric_rows)) if metric_rows else 0.0,
                "mean_restored_energy_loss_percent": float(
                    np.mean([row["restored_energy_loss_percent"] for row in metric_rows])
                ),
                "mean_physical_degradation_percent": float(
                    np.mean([row["physical_degradation_percent"] for row in metric_rows])
                ),
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
                "bypass_high_impact_rate": float(
                    np.mean([row["bypass_high_impact"] for row in metric_rows])
                ),
                "action_changed_rate": float(
                    np.mean([row["attacked_action_changed"] for row in metric_rows])
                ),
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


def run_target_case(experiment, scenario, target_entry, attack_mode, learning_detectors, args):
    true_obs = scenario_observation(experiment, scenario)
    clean_action, clean_policy_ms = experiment.predict_action(true_obs)
    policy_obs, attack_metadata = corrupt_action_mask_entry(true_obs, target_entry, attack_mode)
    if not args.include_noop and int(attack_metadata["attack_applied"]) == 0:
        return None

    clean_trajectory, _clean_first_obs = trajectory_after_action_on_scenario(
        experiment,
        scenario,
        clean_action,
        args,
    )
    detection = run_detector_suite(true_obs, policy_obs, learning_detectors=learning_detectors)
    attacked_action, attacked_policy_ms = experiment.predict_action(policy_obs)
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
    output_dir = resolve_path(
        controller_output_dir(args.output_dir, DEFAULT_OUTPUT_DIR, SYSTEM_NAME, args.controller)
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    registry_experiment = make_controller_experiment(SYSTEM_NAME, args, load_model=False)
    registry_outputs = write_registry_outputs(registry_experiment, output_dir / "registries")

    learning_detectors = []
    if args.use_learning_detectors:
        learning_detectors = load_learning_detectors(
            resolve_path(args.learning_detector_dir),
            tasks=args.learning_tasks,
            model_names=args.learning_models,
        )

    experiment = make_controller_experiment(SYSTEM_NAME, args, load_model=True)
    targets = target_entries(experiment, args.target_scope)
    if int(args.max_targets) > 0:
        targets = targets[: int(args.max_targets)]

    rng = np.random.default_rng(int(args.seed))
    case_rows = []
    all_step_rows = []
    skipped = 0

    for case_index in range(int(args.cases)):
        scenario_seed = int(rng.integers(1, 2**31 - 1))
        scenario = generate_outage_scenario(experiment, scenario_seed, args)
        for target in targets:
            case_id = "C{:04d}_{}_{}".format(
                case_index,
                args.attack_mode,
                target.observation_id.replace(".", "_"),
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
                target,
                args.attack_mode,
                learning_detectors,
                args,
            )
            if result is None:
                skipped += 1
                continue
            case_rows.append(case_summary(case_id, scenario, target, args.attack_mode, result, args))
            all_step_rows.extend(step_rows(case_id, scenario, target, args.attack_mode, result))

    criticality_rows = aggregate_criticality(case_rows)
    paths = {
        "case_summary": output_dir / "tsg_ieee34_action_mask_criticality_cases.csv",
        "step_results": output_dir / "tsg_ieee34_action_mask_criticality_steps.csv",
        "criticality_ranking": output_dir / "tsg_ieee34_action_mask_criticality_ranking.csv",
        "manifest": output_dir / "tsg_ieee34_action_mask_criticality_manifest.json",
    }
    write_csv_or_header(case_rows, paths["case_summary"], CASE_SUMMARY_FIELDS)
    write_csv_or_header(all_step_rows, paths["step_results"], STEP_RESULT_FIELDS)
    write_csv_or_header(criticality_rows, paths["criticality_ranking"], CRITICALITY_FIELDS)

    manifest = {
        "experiment": "IEEE 34-bus named ActionMasking observation criticality study",
        "system": "34bus",
        **controller_metadata(SYSTEM_NAME, args),
        "cases": int(args.cases),
        "target_scope": args.target_scope,
        "attack_mode": args.attack_mode,
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
        "learning_detectors_enabled": bool(args.use_learning_detectors),
        "learning_detector_count": len(learning_detectors),
        "registry_outputs": {key: str(value) for key, value in registry_outputs.items()},
        "outputs": {key: str(value) for key, value in paths.items()},
        "notes": (
            "Each case corrupts one named ActionMasking observation seen by the controller. "
            "OpenDSS remains the physical ground truth for clean, attacked, and mitigated action evaluation. "
            "Outage scenarios are generated once as explicit edge sets and replayed deterministically."
        ),
    }
    paths["manifest"].write_text(safe_json(manifest) + "\n")

    print("wrote {}".format(paths["case_summary"]), flush=True)
    print("wrote {}".format(paths["criticality_ranking"]), flush=True)
    print("wrote {}".format(paths["manifest"]), flush=True)


if __name__ == "__main__":
    main()
