"""IEEE 34-bus baseline-vs-attack vulnerability study for TSG work.

This runner is intentionally small and conservative. It reuses a trained
restoration controller and OpenDSS evaluator, corrupts only the cyber
observation seen by the controller, and reports restored-energy loss as a
first-class physical metric. By default the controller is GCAPS/GRL; MLP can be
selected explicitly for comparison runs.
"""

import argparse
import math
import random
from pathlib import Path

import networkx as nx
import numpy as np

from FDIA_Common import (
    apply_attack,
    clone_observation,
    mitigate_observation,
    select_fdia_aware_grl_action,
)
from FDIA_DetectorSuite import load_learning_detectors, run_detector_suite
from FDIA_ExperimentCore import (
    BASE_DIR,
    RestorationExperiment,
    action_delta,
    physical_impact,
    resolve_path,
    safe_json,
    write_csv,
)
from IEEE34_VulnerabilityRegistry import write_registry_outputs
from TSG_ControllerConfig import (
    add_controller_args,
    controller_metadata,
    controller_output_dir,
    experiment_controller_model_path,
    experiment_controller_name,
    make_controller_experiment,
)


BASE_ATTACKS = [
    "topology_drop",
    "action_mask_false_unavailable",
    "voltage_masking",
    "branchflow_hiding",
    "energy_inflation",
]

SYSTEM_NAME = "34bus"
DEFAULT_OUTPUT_DIR = "paper_results/tsg_ieee34/baseline_attack_study"
EPS = 1.0e-9


def parse_args():
    parser = argparse.ArgumentParser(
        description="IEEE 34-bus restored-energy vulnerability baseline for GRL observation FDIA."
    )
    parser.add_argument("--cases", type=int, default=3, help="Number of random outage seeds.")
    parser.add_argument("--seed", type=int, default=20260615)
    parser.add_argument("--attacks", nargs="+", default=BASE_ATTACKS)
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--step-hours", type=float, default=1.0)
    parser.add_argument("--start-hour", type=int, default=0)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    add_controller_args(parser)
    parser.add_argument("--max-outage-fraction", type=float, default=0.50)
    parser.add_argument("--max-scenario-generation-attempts", type=int, default=100)

    parser.add_argument("--topology-drop-fraction", type=float, default=0.05)
    parser.add_argument("--action-mask-fraction", type=float, default=0.25)
    parser.add_argument(
        "--action-mask-scope",
        choices=["switch", "load", "switch_and_load"],
        default="switch",
    )
    parser.add_argument("--voltage-target-fraction", type=float, default=0.20)
    parser.add_argument("--voltage-reported", type=float, default=1.0)
    parser.add_argument("--branchflow-target-fraction", type=float, default=0.20)
    parser.add_argument("--branchflow-scale", type=float, default=0.25)
    parser.add_argument("--energy-bias", type=float, default=0.25)
    parser.add_argument("--energy-max-reported", type=float, default=1.25)
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


def set_scenario_seed(seed):
    random.seed(int(seed))
    np.random.seed(int(seed) % (2**32 - 1))


def finite_number(value, default=0.0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not np.isfinite(number):
        return default
    return number


def action_scope_indices(scope, num_switches, n_actions):
    if scope == "switch":
        return np.arange(0, num_switches, dtype=int)
    if scope == "load":
        return np.arange(num_switches, n_actions, dtype=int)
    return np.arange(0, n_actions, dtype=int)


def action_mask_false_unavailable(obs, clean_action, experiment, fraction, scope, seed):
    attacked = clone_observation(obs)
    true_mask = np.asarray(obs["ActionMasking"], dtype=float).reshape(-1)
    mask = np.asarray(attacked["ActionMasking"], dtype=float).reshape(-1).copy()
    clean_action = np.asarray(clean_action, dtype=int).reshape(-1)
    n_actions = int(mask.size)
    scope_indices = action_scope_indices(scope, experiment.num_switches, n_actions)

    available = scope_indices[true_mask[scope_indices] < 0.5]
    preferred = available[clean_action[available] > 0] if available.size else np.array([], dtype=int)
    candidates = preferred if preferred.size else available
    if candidates.size == 0:
        return attacked, {
            "target": "ActionMasking",
            "changed_measurements": 0,
            "reason": "no_available_candidate_actions",
        }

    rng = np.random.default_rng(int(seed))
    count = max(1, int(np.ceil(float(fraction) * candidates.size)))
    count = min(count, int(candidates.size))
    selected = np.sort(rng.choice(candidates, size=count, replace=False).astype(int))
    mask[selected] = 1.0
    attacked["ActionMasking"] = mask

    return attacked, {
        "target": "ActionMasking",
        "attack": "action_mask_false_unavailable",
        "mask_scope": scope,
        "mask_fraction": float(fraction),
        "candidate_count": int(candidates.size),
        "changed_measurements": int(np.sum(mask != true_mask)),
        "selected_action_indices": selected.tolist(),
        "selected_switch_indices": [int(index) for index in selected if int(index) < experiment.num_switches],
        "selected_load_indices": [
            int(index - experiment.num_switches) for index in selected if int(index) >= experiment.num_switches
        ],
    }


def attack_kwargs_for_args(attack_name, args, seed):
    if attack_name == "topology_drop":
        return {"drop_fraction": float(args.topology_drop_fraction), "seed": int(seed)}
    if attack_name == "voltage_masking":
        return {
            "target_fraction": float(args.voltage_target_fraction),
            "reported_voltage": float(args.voltage_reported),
        }
    if attack_name == "branchflow_hiding":
        return {
            "target_fraction": float(args.branchflow_target_fraction),
            "scale": float(args.branchflow_scale),
        }
    if attack_name == "energy_inflation":
        return {
            "bias": float(args.energy_bias),
            "max_reported": float(args.energy_max_reported),
        }
    return {}


def apply_named_attack(true_obs, clean_action, experiment, attack_name, case_seed, args):
    if attack_name == "action_mask_false_unavailable":
        return action_mask_false_unavailable(
            true_obs,
            clean_action,
            experiment,
            args.action_mask_fraction,
            args.action_mask_scope,
            case_seed,
        )
    kwargs = attack_kwargs_for_args(attack_name, args, case_seed)
    attacked, metadata = apply_attack(clone_observation(true_obs), attack_name, **kwargs)
    metadata = dict(metadata)
    metadata["attack_kwargs"] = kwargs
    return attacked, metadata


def canonical_edge(edge):
    u, v = edge
    return tuple(sorted((str(u), str(v))))


def outage_edges_for_csv(outage_edges):
    return [[u, v] for u, v in sorted(canonical_edge(edge) for edge in outage_edges)]


def resolve_graph_edge(graph, edge):
    u, v = canonical_edge(edge)
    if (u, v) in graph.edges:
        return u, v
    if (v, u) in graph.edges:
        return v, u
    raise KeyError("Outage edge {} is not present in the IEEE 34 graph.".format((u, v)))


def generate_outage_scenario(experiment, scenario_seed, args):
    G_init = experiment.init_module.G_init
    G_base = experiment.init_module.G_base
    nodes = sorted(G_init.nodes())
    max_radius = nx.diameter(G_init)

    for attempt in range(int(args.max_scenario_generation_attempts)):
        rng = np.random.default_rng(int(scenario_seed) + 1_000_003 * attempt)
        root_node = nodes[int(rng.integers(0, len(nodes)))]
        radius = int(math.ceil(float(rng.uniform(0.0, max_radius / 2.0))))
        subgraph = nx.ego_graph(G_base, root_node, radius=radius, undirected=False)
        sub_edges = sorted(set(canonical_edge(edge) for edge in subgraph.edges()))
        if not sub_edges:
            continue

        outage_fraction = float(rng.uniform(0.0, float(args.max_outage_fraction)))
        outage_count = int(math.ceil(len(sub_edges) * outage_fraction))
        outage_count = max(1, min(outage_count, len(sub_edges)))
        selected_indices = np.sort(
            rng.choice(len(sub_edges), size=outage_count, replace=False).astype(int)
        )
        outage_edges = sorted(sub_edges[int(index)] for index in selected_indices)
        return {
            "scenario": "deterministic_outage_edges",
            "scenario_seed": int(scenario_seed),
            "generation_attempt": int(attempt),
            "root_node": str(root_node),
            "radius": int(radius),
            "subgraph_edge_count": int(len(sub_edges)),
            "outage_fraction": outage_fraction,
            "outage_edges": outage_edges,
            "outage_edge_count": int(len(outage_edges)),
        }

    raise RuntimeError(
        "Could not generate a non-empty IEEE 34 outage scenario for seed {} after {} attempts.".format(
            scenario_seed,
            args.max_scenario_generation_attempts,
        )
    )


def apply_outage_edges(experiment, outage_edges):
    DSSCktObj, G_init, _conv_flag = experiment.init_module.initialize()
    experiment.env.DSSCktObj = DSSCktObj
    experiment.env.G = G_init.copy()

    normalized_edges = [resolve_graph_edge(G_init, edge) for edge in outage_edges]
    for outage_edge in normalized_edges:
        branch_name = G_init.edges[outage_edge]["label"][0]
        experiment.env.DSSCktObj.dss.Text.Command("Open {} term=1".format(branch_name))
        experiment.env.DSSCktObj.dss.Solution.Solve()

    experiment.env.G.remove_edges_from(normalized_edges)
    experiment.env.outedges = normalized_edges
    return experiment.state_module.get_state(
        experiment.env.DSSCktObj,
        experiment.env.G,
        experiment.env.outedges,
    )


def validate_observation(obs, scenario):
    branchflows = np.asarray(obs["EdgeFeat(Branchflow)"], dtype=float)
    voltages = np.asarray(obs["NodeFeat(BusVoltage)"], dtype=float)
    if np.isnan(branchflows).sum() > 0 or not np.isfinite(branchflows).all():
        raise RuntimeError(
            "Invalid branchflow values for deterministic outage scenario seed {} edges {}.".format(
                scenario["scenario_seed"],
                scenario["outage_edges"],
            )
        )
    if np.isnan(voltages).sum() > 0 or not np.isfinite(voltages).all() or float(np.max(voltages)) > 100000.0:
        raise RuntimeError(
            "Invalid voltage values for deterministic outage scenario seed {} edges {}.".format(
                scenario["scenario_seed"],
                scenario["outage_edges"],
            )
        )


def scenario_observation(experiment, scenario):
    if hasattr(experiment, "set_current_scenario"):
        experiment.set_current_scenario(scenario)
    obs = apply_outage_edges(experiment, scenario["outage_edges"])
    validate_observation(obs, scenario)
    return obs


def evaluate_action_on_scenario(experiment, scenario, action):
    scenario_observation(experiment, scenario)
    action = np.asarray(action, dtype=int)
    obs_post_action, reward, done, _info = experiment.env.step(action)
    metrics = experiment.metrics_from_observation(obs_post_action, reward=reward, action=action)
    metrics["done"] = bool(done)
    return metrics, obs_post_action


def trajectory_after_action_on_scenario(experiment, scenario, action, args):
    action = np.asarray(action, dtype=int)
    first_metrics, first_obs = evaluate_action_on_scenario(experiment, scenario, action)
    trajectory = []
    try:
        experiment._configure_daily_mode(float(args.step_hours))
    except Exception as exc:
        first_metrics["time_command_warning"] = str(exc)

    for step in range(int(args.horizon)):
        hour = int(args.start_hour + step * args.step_hours)
        solve_warning = ""
        try:
            experiment._advance_time(hour)
        except Exception as exc:
            solve_warning = str(exc)
        obs = experiment.current_observation()
        metrics = experiment.metrics_from_observation(obs, action=action)
        if step == 0:
            metrics.update(
                {
                    "initial_reward": first_metrics["reward"],
                    "initial_energy_ratio": first_metrics["energy_ratio"],
                    "initial_voltage_violation": first_metrics["voltage_violation"],
                }
            )
        metrics.update({"time_step": step, "hour": hour, "solve_warning": solve_warning})
        trajectory.append(metrics)

    if not trajectory:
        first_metrics.update({"time_step": 0, "hour": args.start_hour, "solve_warning": ""})
        trajectory.append(first_metrics)
    return trajectory, first_obs


def trajectory_energy_summary(trajectory, step_hours):
    valid = []
    voltage = []
    reward = []
    for metrics in trajectory:
        energy_kw = finite_number(metrics.get("energy_kw"), default=np.nan)
        if np.isfinite(energy_kw) and energy_kw >= 0.0:
            valid.append(energy_kw)
        voltage.append(finite_number(metrics.get("voltage_violation"), default=0.0))
        reward.append(finite_number(metrics.get("reward"), default=0.0))

    energy_kwh = float(np.sum(valid) * float(step_hours)) if valid else 0.0
    return {
        "valid_step_count": len(valid),
        "step_count": len(trajectory),
        "restored_energy_kwh": energy_kwh,
        "mean_energy_kw": float(np.mean(valid)) if valid else 0.0,
        "min_energy_kw": float(np.min(valid)) if valid else 0.0,
        "mean_voltage_violation": float(np.mean(voltage)) if voltage else 0.0,
        "mean_reward": float(np.mean(reward)) if reward else 0.0,
    }


def case_summary(case_id, scenario, attack_name, result, args):
    clean = trajectory_energy_summary(result["clean_trajectory"], args.step_hours)
    attacked = trajectory_energy_summary(result["attacked_trajectory"], args.step_hours)
    mitigated = trajectory_energy_summary(result["mitigated_trajectory"], args.step_hours)
    energy_loss = clean["restored_energy_kwh"] - attacked["restored_energy_kwh"]
    physical_degradation = max(0.0, energy_loss)
    accidental_improvement = max(0.0, -energy_loss)
    residual_loss = clean["restored_energy_kwh"] - mitigated["restored_energy_kwh"]
    residual_degradation = max(0.0, residual_loss)
    recovered = mitigated["restored_energy_kwh"] - attacked["restored_energy_kwh"]
    recovery_ratio = recovered / energy_loss if abs(energy_loss) > EPS else 0.0
    energy_loss_ratio = energy_loss / clean["restored_energy_kwh"] if clean["restored_energy_kwh"] > EPS else 0.0
    physical_degradation_ratio = (
        physical_degradation / clean["restored_energy_kwh"]
        if clean["restored_energy_kwh"] > EPS
        else 0.0
    )
    degradation_recovered = physical_degradation - residual_degradation
    degradation_recovery_ratio = (
        degradation_recovered / physical_degradation
        if physical_degradation > EPS
        else 0.0
    )
    degradation_recovery_ratio_clipped = min(1.0, max(0.0, degradation_recovery_ratio))
    detection = result["detection"]
    mitigation_metadata = result["fdia_aware"].get("fdia_aware_metadata", {})
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
        "attack": attack_name,
        "clean_restored_energy_kwh": clean["restored_energy_kwh"],
        "attacked_restored_energy_kwh": attacked["restored_energy_kwh"],
        "mitigated_restored_energy_kwh": mitigated["restored_energy_kwh"],
        "restored_energy_loss_kwh": energy_loss,
        "restored_energy_loss_ratio": energy_loss_ratio,
        "restored_energy_loss_percent": 100.0 * energy_loss_ratio,
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
        "valid_clean_steps": clean["valid_step_count"],
        "valid_attacked_steps": attacked["valid_step_count"],
        "valid_mitigated_steps": mitigated["valid_step_count"],
    }


def step_rows(case_id, scenario, attack_name, result):
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
                "attack": attack_name,
                "mode": mode,
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


def aggregate_attack_ranking(summary_rows):
    groups = {}
    for row in summary_rows:
        groups.setdefault(row["attack"], []).append(row)
    ranking = []
    for attack, rows in sorted(groups.items()):
        damaging_rows = [r for r in rows if r["damaging_case"]]
        improvement_rows = [r for r in rows if r["improvement_case"]]
        degradation_recovery_values = [
            r["mitigation_recovery_of_degradation_ratio"] for r in damaging_rows
        ]
        degradation_recovery_clipped_values = [
            r["mitigation_recovery_of_degradation_ratio_clipped"] for r in damaging_rows
        ]
        ranking.append(
            {
                "attack": attack,
                "case_count": len(rows),
                "mean_restored_energy_loss_kwh": float(np.mean([r["restored_energy_loss_kwh"] for r in rows])),
                "max_restored_energy_loss_kwh": float(np.max([r["restored_energy_loss_kwh"] for r in rows])),
                "mean_restored_energy_loss_percent": float(
                    np.mean([r["restored_energy_loss_percent"] for r in rows])
                ),
                "mean_physical_degradation_kwh": float(
                    np.mean([r["physical_degradation_kwh"] for r in rows])
                ),
                "total_physical_degradation_kwh": float(
                    np.sum([r["physical_degradation_kwh"] for r in rows])
                ),
                "max_physical_degradation_kwh": float(
                    np.max([r["physical_degradation_kwh"] for r in rows])
                ),
                "mean_physical_degradation_percent": float(
                    np.mean([r["physical_degradation_percent"] for r in rows])
                ),
                "damaging_case_count": len(damaging_rows),
                "damaging_case_rate": float(len(damaging_rows) / len(rows)) if rows else 0.0,
                "mean_accidental_improvement_kwh": float(
                    np.mean([r["accidental_improvement_kwh"] for r in rows])
                ),
                "max_accidental_improvement_kwh": float(
                    np.max([r["accidental_improvement_kwh"] for r in rows])
                ),
                "improvement_case_count": len(improvement_rows),
                "improvement_case_rate": float(len(improvement_rows) / len(rows)) if rows else 0.0,
                "mean_residual_degradation_after_mitigation_kwh": float(
                    np.mean([r["residual_degradation_after_mitigation_kwh"] for r in rows])
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
                    np.mean([r["mitigation_recovery_ratio"] for r in rows])
                ),
                "detection_rate": float(np.mean([r["fdia_detected"] for r in rows])),
                "bypass_high_impact_rate": float(np.mean([r["bypass_high_impact"] for r in rows])),
                "mean_attacked_switch_changes_vs_clean": float(
                    np.mean([r["attacked_switch_changes_vs_clean"] for r in rows])
                ),
                "mean_attacked_load_changes_vs_clean": float(
                    np.mean([r["attacked_load_changes_vs_clean"] for r in rows])
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
    for index, row in enumerate(ranking, start=1):
        row["damage_rank"] = index
    return ranking


def run_case(experiment, scenario, attack_name, case_seed, learning_detectors, args):
    true_obs = scenario_observation(experiment, scenario)
    clean_action, clean_policy_ms = experiment.predict_action(true_obs)
    clean_trajectory, _clean_first_obs = trajectory_after_action_on_scenario(
        experiment,
        scenario,
        clean_action,
        args,
    )

    policy_obs, attack_metadata = apply_named_attack(
        true_obs,
        clean_action,
        experiment,
        attack_name,
        case_seed,
        args,
    )
    detection = run_detector_suite(
        true_obs,
        policy_obs,
        learning_detectors=learning_detectors,
    )
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

    experiment = make_controller_experiment(SYSTEM_NAME, args, load_model=True)
    rng = np.random.default_rng(int(args.seed))
    summary_rows = []
    all_step_rows = []

    for case_index in range(int(args.cases)):
        scenario_seed = int(rng.integers(1, 2**31 - 1))
        scenario = generate_outage_scenario(experiment, scenario_seed, args)
        for attack_index, attack_name in enumerate(args.attacks):
            case_seed = int(rng.integers(1, 2**31 - 1))
            case_id = "B{:04d}_{}_seed{}".format(case_index, attack_name, scenario_seed)
            print("running {} attack={}".format(case_id, attack_name), flush=True)
            result = run_case(
                experiment,
                scenario,
                attack_name,
                case_seed + attack_index,
                learning_detectors,
                args,
            )
            summary_rows.append(case_summary(case_id, scenario, attack_name, result, args))
            all_step_rows.extend(step_rows(case_id, scenario, attack_name, result))

    ranking_rows = aggregate_attack_ranking(summary_rows)
    paths = {
        "case_summary": output_dir / "tsg_ieee34_case_summary.csv",
        "step_results": output_dir / "tsg_ieee34_step_results.csv",
        "attack_ranking": output_dir / "tsg_ieee34_attack_ranking.csv",
        "manifest": output_dir / "tsg_ieee34_manifest.json",
    }
    write_csv(summary_rows, paths["case_summary"])
    write_csv(all_step_rows, paths["step_results"])
    write_csv(ranking_rows, paths["attack_ranking"])

    manifest = {
        "experiment": "IEEE 34-bus TSG baseline-vs-attack restored-energy vulnerability study",
        "system": "34bus",
        **controller_metadata(SYSTEM_NAME, args),
        "cases": int(args.cases),
        "attacks": args.attacks,
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
            "Attacks corrupt only controller observations. Clean, attacked, and mitigated "
            "actions are evaluated on the same explicit OpenDSS outage-edge scenario."
        ),
    }
    paths["manifest"].write_text(safe_json(manifest) + "\n")

    print("wrote {}".format(paths["case_summary"]), flush=True)
    print("wrote {}".format(paths["attack_ranking"]), flush=True)
    print("wrote {}".format(paths["manifest"]), flush=True)


if __name__ == "__main__":
    main()
