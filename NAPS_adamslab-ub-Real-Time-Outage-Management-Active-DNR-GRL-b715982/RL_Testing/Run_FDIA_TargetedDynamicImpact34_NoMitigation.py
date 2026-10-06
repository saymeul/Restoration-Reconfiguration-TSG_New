"""Targeted IEEE 34-bus dynamic FDIA impact experiment without mitigation.

This runner is for the paper setting where FDIA must be able to corrupt the
decision inputs actually trusted by each outage-management method:

* GRL receives corrupted graph/measurement/status observations.
* MLP receives corrupted observations, and its DMS feasibility filter is driven
  by the corrupted status/action-mask channel. The raw saved MLP policy is
  effectively constant on the tested 34-bus observations, so the status channel
  is recorded explicitly instead of being hidden as a feature-only attack.
* BPSO optimizes with corrupted perceived status/objective inputs; the selected
  action is then evaluated on the true OpenDSS feeder.

No mitigation or recovery action is evaluated.
"""

from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import numpy as np

from FDIA_Common import apply_attack, clone_observation, restoration_action_quality
from FDIA_DetectorSuite import load_learning_detectors, run_detector_suite
from FDIA_ExperimentCore import BASE_DIR, action_delta, physical_impact, resolve_path, safe_json, write_csv
from Run_FDIA_AttackSearch import strong_attack_kwargs
from Run_FDIA_DynamicImpact34_NoMitigation import (
    DEFAULT_ATTACKS,
    DEFAULT_METHODS,
    detection_fields,
    fmt_float,
    impact_is_paper_valid,
    max_value,
    mean,
    metric_is_paper_valid,
    min_value,
    seeded_random_observation,
    summarize_trajectory,
)
from Run_FDIA_MethodComparison34 import PPOController, evaluate_on_seed, stable_seed

METHOD_LABELS = {"GRL": "GCAPS", "MLP": "MLP", "BPSO": "BPSO"}
PHASE_LABELS = {1: "A", 2: "B", 3: "C"}
MAX_PLOT_VOLTAGE_PU = 2.0
MAX_ENERGY_FACTOR = 1.50


@dataclass(frozen=True)
class TargetedDynamicCase:
    case_id: str
    target_method: str
    source_trial: int
    scenario_seed: int
    attack: str
    attack_kwargs: dict
    decision_kwargs: dict
    search_mean_impact: float = 0.0
    search_max_impact: float = 0.0
    search_harmful_step_rate: float = 0.0


def parse_args():
    parser = argparse.ArgumentParser(
        description="IEEE 34-bus targeted dynamic FDIA impact search without mitigation."
    )
    parser.add_argument("--trials-per-method", type=int, default=30)
    parser.add_argument("--top-k-per-method", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260607)
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--step-hours", type=int, default=1)
    parser.add_argument("--start-hour", type=int, default=0)
    parser.add_argument("--harm-threshold", type=float, default=1.0e-6)
    parser.add_argument(
        "--rank-metric",
        choices=["mean_impact", "max_impact", "cumulative_impact"],
        default="mean_impact",
    )
    parser.add_argument("--max-abs-energy-ratio", type=float, default=2.0)
    parser.add_argument("--max-physical-impact", type=float, default=5.0)
    parser.add_argument("--max-convergence-violation", type=float, default=0.0)
    parser.add_argument("--include-invalid-selection", action="store_true")
    parser.add_argument("--attacks", nargs="+", default=DEFAULT_ATTACKS)
    parser.add_argument("--methods", nargs="+", choices=DEFAULT_METHODS, default=DEFAULT_METHODS)
    parser.add_argument("--bpso-particles", type=int, default=8)
    parser.add_argument("--bpso-iterations", type=int, default=8)
    parser.add_argument("--bpso-seed", type=int, default=5157)
    parser.add_argument(
        "--no-decision-channel-projection",
        action="store_true",
        help="Disable topology/status projection into ActionMasking.",
    )
    parser.add_argument(
        "--decision-mask-scope",
        choices=["switch", "load", "switch_and_load"],
        default="switch",
        help="Which action entries a false topology/status FDIA may mark unavailable.",
    )
    parser.add_argument("--decision-mask-min-fraction", type=float, default=0.20)
    parser.add_argument("--decision-mask-max-fraction", type=float, default=0.70)
    parser.add_argument("--bpso-load-weight-gain", type=float, default=0.20)
    parser.add_argument(
        "--export-profiles",
        action="store_true",
        help="Write per-bus/per-phase voltages and energy-served profiles from the selected replay.",
    )
    parser.add_argument(
        "--no-profile-figures",
        action="store_true",
        help="Skip generated profile figures.",
    )
    parser.add_argument(
        "--learning-detector-dir",
        default="34bus/paper_results/learning_detectors",
    )
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
    parser.add_argument(
        "--output-dir",
        default="paper_results/naps_34bus/targeted_dynamic_no_mitigation",
    )
    return parser.parse_args()


def rank_value(row, rank_metric):
    if rank_metric == "max_impact":
        return float(row.get("max_physical_impact_score", 0.0))
    if rank_metric == "cumulative_impact":
        return float(row.get("cumulative_physical_impact_score", 0.0))
    return float(row.get("mean_physical_impact_score", 0.0))


def action_mask(obs, n_actions):
    mask = np.asarray(obs.get("ActionMasking", []), dtype=float).reshape(-1)
    if mask.size != int(n_actions):
        return np.zeros(int(n_actions), dtype=float)
    return mask


def repair_action_with_mask(action, obs, n_actions):
    raw_action = np.asarray(action, dtype=int).reshape(-1).copy()
    repaired = raw_action.copy()
    mask = action_mask(obs, n_actions)
    repaired[mask > 0.5] = 0
    changed = raw_action != repaired
    return repaired.astype(int), {
        "dms_feasibility_filter_applied": 1,
        "raw_action": raw_action.tolist(),
        "repaired_action": repaired.tolist(),
        "repair_changed_action": int(np.any(changed)),
        "repair_changed_entries": int(np.sum(changed)),
        "masked_action_entries": int(np.sum(mask > 0.5)),
    }


class MaskedPPOController(PPOController):
    def __init__(self, method, model_path, enforce_action_mask=True):
        super().__init__(method=method, model_path=model_path)
        self.enforce_action_mask = bool(enforce_action_mask)
        if method == "MLP":
            self.method_notes = (
                "PPO MLP policy with DMS feasibility filtering from ActionMasking. "
                "The saved raw MLP policy is constant on tested 34-bus observations; "
                "status/topology FDIA reaches the dispatch decision through this filter."
            )

    def decide(self, obs, case, mode):
        raw_action, policy_time_ms = self.experiment.predict_action(obs)
        metadata = {
            "ppo_policy_class": type(self.experiment.model.policy).__name__,
            "dms_feasibility_filter_enabled": int(self.enforce_action_mask),
        }
        if self.enforce_action_mask:
            action, repair_metadata = repair_action_with_mask(raw_action, obs, self.experiment.n_actions)
            metadata.update(repair_metadata)
        else:
            action = np.asarray(raw_action, dtype=int)
            metadata.update(
                {
                    "raw_action": np.asarray(raw_action, dtype=int).tolist(),
                    "repair_changed_action": 0,
                    "repair_changed_entries": 0,
                }
            )
        return np.asarray(action, dtype=int), float(policy_time_ms), metadata


def simple_voltage_violation(voltages):
    values = np.asarray(voltages, dtype=float).reshape(-1)
    active = values[np.isfinite(values) & (values > 0.01)]
    if active.size == 0:
        return 0.0
    below = np.maximum(0.0, 0.90 - active) / 0.90
    above = np.maximum(0.0, active - 1.10) / 1.10
    return float(np.sum(below + above) / active.size)


def perceived_metrics_from_observation(true_metrics, perceived_obs, action, num_switches):
    metrics = dict(true_metrics)
    energy = fmt_float(np.asarray(perceived_obs.get("EnergySupp", [metrics["energy_ratio"]])).reshape(-1)[0])
    voltage_violation = fmt_float(
        np.asarray(perceived_obs.get("VoltageViolation", [metrics["voltage_violation"]])).reshape(-1)[0]
    )
    convergence = fmt_float(
        np.asarray(perceived_obs.get("ConvergenceViolation", [metrics["convergence_violation"]])).reshape(-1)[0]
    )
    if energy != "":
        metrics["energy_ratio"] = float(energy)
    if "NodeFeat(BusVoltage)" in perceived_obs:
        voltage_violation = simple_voltage_violation(perceived_obs["NodeFeat(BusVoltage)"])
    if voltage_violation != "":
        metrics["voltage_violation"] = float(voltage_violation)
    if convergence != "":
        metrics["convergence_violation"] = float(convergence)
    flows = np.asarray(perceived_obs.get("EdgeFeat(Branchflow)", []), dtype=float).reshape(-1)
    flows = flows[np.isfinite(flows)]
    if flows.size:
        metrics["branchflow_mean"] = float(np.mean(flows))
        metrics["branchflow_max"] = float(np.max(flows))
    action = np.asarray(action, dtype=int)
    metrics["loads_served"] = int(np.sum(action[num_switches:]))
    metrics["loads_shed"] = int(action.size - num_switches - metrics["loads_served"])
    if metrics.get("convergence_violation", 0.0) > 0:
        metrics["reward"] = 0.0
    else:
        metrics["reward"] = float(metrics.get("energy_ratio", 0.0) - metrics.get("voltage_violation", 0.0))
    return metrics


def weighted_load_score(action, case, num_switches, load_count):
    if case.attack != "energy_inflation":
        return 0.0
    selected = case.decision_kwargs.get("weighted_load_indices", [])
    if not selected:
        return 0.0
    weights = np.ones(int(load_count), dtype=float)
    bias = float(case.decision_kwargs.get("load_weight_bias", 0.25))
    for index in selected:
        if 0 <= int(index) < load_count:
            weights[int(index)] += bias
    load_action = np.asarray(action, dtype=int).reshape(-1)[num_switches : num_switches + load_count]
    if load_action.size != load_count:
        return 0.0
    return float(np.sum(load_action * weights) / max(np.sum(weights), 1.0))


class TargetedBPSOController:
    def __init__(self, particles, iterations, seed, load_weight_gain=0.20):
        from FDIA_ExperimentCore import RestorationExperiment

        self.method = "BPSO"
        self.method_status = "ok"
        self.method_notes = (
            "Binary PSO over the 34-bus action vector. Under targeted FDIA, "
            "candidate actions are optimized against corrupted perceived status/objective "
            "inputs and finally evaluated on the true feeder."
        )
        self.experiment = RestorationExperiment(system="34bus", load_model=False)
        self.particles = max(1, int(particles))
        self.iterations = max(1, int(iterations))
        self.seed = int(seed)
        self.load_weight_gain = float(load_weight_gain)

    def decide(self, obs, case, mode):
        rng = np.random.default_rng(stable_seed(self.seed, case.scenario_seed, case.case_id, mode))
        n_actions = int(self.experiment.n_actions)
        n_loads = len(self.experiment.dispatch_loads)
        num_switches = int(self.experiment.num_switches)
        mask = action_mask(obs, n_actions)

        def repair(position):
            action = np.asarray(position, dtype=int).reshape(-1).copy()
            if action.size != n_actions:
                repaired = np.zeros(n_actions, dtype=int)
                repaired[: min(action.size, n_actions)] = action[: min(action.size, n_actions)]
                action = repaired
            action = np.where(action > 0, 1, 0).astype(int)
            action[mask > 0.5] = 0
            return action

        def score(position):
            action = repair(position)
            true_metrics, true_post_obs = evaluate_on_seed(self.experiment, case.scenario_seed, action)
            perceived_metrics = true_metrics
            perceived_metadata = {"perceived_objective_attack_applied": 0}
            if mode.startswith("attacked"):
                perceived_obs, perceived_attack_metadata = apply_attack(
                    clone_observation(true_post_obs),
                    case.attack,
                    **case.attack_kwargs,
                )
                perceived_metrics = perceived_metrics_from_observation(
                    true_metrics,
                    perceived_obs,
                    action,
                    num_switches,
                )
                perceived_metadata = {
                    "perceived_objective_attack_applied": 1,
                    "perceived_attack_metadata": perceived_attack_metadata,
                    "perceived_quality_inputs": {
                        "energy_ratio": perceived_metrics.get("energy_ratio", 0.0),
                        "voltage_violation": perceived_metrics.get("voltage_violation", 0.0),
                        "convergence_violation": perceived_metrics.get("convergence_violation", 0.0),
                    },
                }
            quality = restoration_action_quality(perceived_metrics)
            quality += self.load_weight_gain * weighted_load_score(action, case, num_switches, n_loads)
            return float(quality), true_metrics, perceived_metrics, action, perceived_metadata

        start = perf_counter()
        positions = rng.integers(0, 2, size=(self.particles, n_actions), dtype=int)
        positions = np.asarray([repair(item) for item in positions], dtype=int)
        velocities = rng.normal(0.0, 0.25, size=(self.particles, n_actions))
        personal_best_positions = positions.copy()
        personal_best_scores = np.full(self.particles, -np.inf, dtype=float)
        global_best_position = positions[0].copy()
        global_best_score = -np.inf
        global_best_true_metrics = None
        global_best_perceived_metrics = None
        global_best_perceived_metadata = {}
        best_iteration = 0
        candidate_evaluations = 0

        for iteration in range(self.iterations):
            for particle_index in range(self.particles):
                value, true_metrics, perceived_metrics, action, perceived_metadata = score(positions[particle_index])
                candidate_evaluations += 1
                if value > personal_best_scores[particle_index]:
                    personal_best_scores[particle_index] = value
                    personal_best_positions[particle_index] = action
                if value > global_best_score:
                    global_best_score = value
                    global_best_position = action
                    global_best_true_metrics = true_metrics
                    global_best_perceived_metrics = perceived_metrics
                    global_best_perceived_metadata = perceived_metadata
                    best_iteration = iteration

            inertia = 0.72
            cognitive = 1.49
            social = 1.49
            r1 = rng.random(size=(self.particles, n_actions))
            r2 = rng.random(size=(self.particles, n_actions))
            velocities = (
                inertia * velocities
                + cognitive * r1 * (personal_best_positions - positions)
                + social * r2 * (global_best_position - positions)
            )
            probabilities = 1.0 / (1.0 + np.exp(-np.clip(velocities, -20.0, 20.0)))
            positions = (rng.random(size=(self.particles, n_actions)) < probabilities).astype(int)
            positions = np.asarray([repair(item) for item in positions], dtype=int)

        elapsed_ms = (perf_counter() - start) * 1000.0
        metadata = {
            "bpso_particles": self.particles,
            "bpso_iterations": self.iterations,
            "bpso_candidate_evaluations": candidate_evaluations,
            "bpso_best_iteration": int(best_iteration),
            "bpso_best_perceived_quality": float(global_best_score),
            "bpso_best_true_metrics": global_best_true_metrics or {},
            "bpso_best_perceived_metrics": global_best_perceived_metrics or {},
            "bpso_enforced_action_mask": 1,
        }
        metadata.update(global_best_perceived_metadata)
        return repair(global_best_position), float(elapsed_ms), metadata


def make_controller(method, args):
    method = method.upper()
    if method == "GRL":
        return MaskedPPOController(
            method="GRL",
            model_path=BASE_DIR / "34bus" / "TrainedModels" / "GCAPS_34.zip",
            enforce_action_mask=True,
        )
    if method == "MLP":
        return MaskedPPOController(
            method="MLP",
            model_path=BASE_DIR / "34bus" / "TrainedModels" / "MLP_34.zip",
            enforce_action_mask=True,
        )
    if method == "BPSO":
        return TargetedBPSOController(
            particles=args.bpso_particles,
            iterations=args.bpso_iterations,
            seed=args.bpso_seed,
            load_weight_gain=args.bpso_load_weight_gain,
        )
    raise ValueError("Unsupported method: {}".format(method))


def action_scope_indices(scope, num_switches, n_actions):
    if scope == "switch":
        return np.arange(0, num_switches, dtype=int)
    if scope == "load":
        return np.arange(num_switches, n_actions, dtype=int)
    return np.arange(0, n_actions, dtype=int)


def project_topology_status_to_action_mask(policy_obs, true_obs, clean_action, case, num_switches, args):
    metadata = {
        "decision_channel_projection": "none",
        "action_mask_changed_entries": 0,
        "action_mask_selected_indices": [],
    }
    if args.no_decision_channel_projection or case.attack != "topology_drop":
        return policy_obs, metadata

    rng = np.random.default_rng(int(case.decision_kwargs.get("projection_seed", 1)))
    n_actions = int(np.asarray(true_obs["ActionMasking"]).reshape(-1).size)
    current_mask = action_mask(policy_obs, n_actions).copy()
    true_mask = action_mask(true_obs, n_actions)
    clean_action = np.asarray(clean_action, dtype=int).reshape(-1)
    scope = str(case.decision_kwargs.get("mask_scope", args.decision_mask_scope))
    scope_indices = action_scope_indices(scope, num_switches, n_actions)
    available = scope_indices[true_mask[scope_indices] < 0.5]
    preferred = available[clean_action[available] > 0] if available.size else np.array([], dtype=int)
    candidates = preferred if preferred.size else available
    if candidates.size == 0:
        return policy_obs, metadata

    fraction = float(case.decision_kwargs.get("mask_fraction", args.decision_mask_min_fraction))
    fraction = max(0.0, min(1.0, fraction))
    count = max(1, int(math.ceil(candidates.size * fraction)))
    count = min(count, candidates.size)
    selected = np.sort(rng.choice(candidates, size=count, replace=False).astype(int))
    current_mask[selected] = 1.0
    policy_obs["ActionMasking"] = current_mask
    metadata = {
        "decision_channel_projection": "false_topology_status_to_action_mask",
        "projection_note": (
            "False topology/status data marks selected available actions as unavailable. "
            "The controller optimizes/filters with this corrupted decision input; "
            "final physical impact is evaluated on the true feeder."
        ),
        "mask_scope": scope,
        "mask_fraction": fraction,
        "candidate_count": int(candidates.size),
        "action_mask_changed_entries": int(np.sum(current_mask != true_mask)),
        "action_mask_selected_indices": selected.tolist(),
        "selected_switch_indices": [int(index) for index in selected if int(index) < num_switches],
        "selected_load_indices": [int(index - num_switches) for index in selected if int(index) >= num_switches],
    }
    return policy_obs, metadata


def build_policy_observation(true_obs, clean_action, case, controller, args):
    policy_obs, base_metadata = apply_attack(
        clone_observation(true_obs),
        case.attack,
        **case.attack_kwargs,
    )
    policy_obs, decision_metadata = project_topology_status_to_action_mask(
        policy_obs,
        true_obs,
        clean_action,
        case,
        controller.experiment.num_switches,
        args,
    )
    attack_metadata = {
        "base_observation_attack": base_metadata,
        "decision_channel_attack": decision_metadata,
        "attack_surface": (
            "observation_plus_decision_channel"
            if decision_metadata.get("decision_channel_projection") != "none"
            else "observation_only"
        ),
    }
    return policy_obs, attack_metadata


def targeted_attack_parameters(attack, rng, args, method):
    attack_kwargs = strong_attack_kwargs(attack, rng)
    decision_kwargs = {
        "projection_seed": int(rng.integers(0, 2**31 - 1)),
        "mask_scope": args.decision_mask_scope,
    }
    if attack == "topology_drop":
        low = min(args.decision_mask_min_fraction, args.decision_mask_max_fraction)
        high = max(args.decision_mask_min_fraction, args.decision_mask_max_fraction)
        decision_kwargs["mask_fraction"] = float(rng.uniform(low, high))
    if attack == "energy_inflation":
        load_count = 10
        count = max(1, int(math.ceil(load_count * float(rng.uniform(0.20, 0.60)))))
        selected = sorted(rng.choice(load_count, size=count, replace=False).astype(int).tolist())
        decision_kwargs["weighted_load_indices"] = selected
        decision_kwargs["load_weight_bias"] = float(rng.uniform(0.20, 0.70))
    decision_kwargs["target_method"] = method
    return attack_kwargs, decision_kwargs


def make_case(target_method, trial_index, rng, args):
    scenario_seed = int(rng.integers(0, 2**31 - 1))
    attack = str(rng.choice(args.attacks))
    attack_kwargs, decision_kwargs = targeted_attack_parameters(attack, rng, args, target_method)
    return TargetedDynamicCase(
        case_id="T{}_{}_{:04d}_seed{}".format(
            target_method.lower(),
            attack.replace("_", ""),
            trial_index,
            scenario_seed,
        ),
        target_method=target_method,
        source_trial=trial_index,
        scenario_seed=scenario_seed,
        attack=attack,
        attack_kwargs=attack_kwargs,
        decision_kwargs=decision_kwargs,
    )


def decide(controller, obs, case, mode):
    return controller.decide(clone_observation(obs), case, mode)


def set_scenario_seed(scenario_seed):
    random.seed(int(scenario_seed))
    np.random.seed(int(scenario_seed) % (2**32 - 1))


def seeded_profile_after_action(experiment, scenario_seed, action, args, capture_profiles=False):
    """Run the dynamic trajectory and optionally keep the exact observations.

    This mirrors RestorationExperiment.trajectory_after_action, but returns the
    per-step observations when profile export is requested. The impact rows and
    profile rows can therefore be written from the same simulation pass.
    """
    action = np.asarray(action, dtype=int)
    set_scenario_seed(scenario_seed)
    first_metrics, first_obs = experiment.evaluate_action("random", action)
    trajectory = []
    observations = []
    try:
        experiment._configure_daily_mode(args.step_hours)
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
        if capture_profiles:
            observations.append(obs)

    if not trajectory:
        first_metrics.update({"time_step": 0, "hour": args.start_hour, "solve_warning": ""})
        trajectory.append(first_metrics)
        if capture_profiles:
            observations.append(first_obs)
    return trajectory, observations


def run_targeted_case(controller, case, learning_detectors, args, capture_profiles=False):
    true_obs = seeded_random_observation(controller.experiment, case.scenario_seed)
    clean_action, clean_policy_ms, clean_controller_metadata = decide(controller, true_obs, case, "clean")
    clean_trajectory, clean_observations = seeded_profile_after_action(
        controller.experiment,
        case.scenario_seed,
        clean_action,
        args,
        capture_profiles=capture_profiles,
    )

    policy_obs, attack_metadata = build_policy_observation(true_obs, clean_action, case, controller, args)
    detection = run_detector_suite(true_obs, policy_obs, learning_detectors=learning_detectors)
    attacked_action, attacked_policy_ms, attacked_controller_metadata = decide(
        controller,
        policy_obs,
        case,
        "attacked_dynamic",
    )
    attacked_trajectory, attacked_observations = seeded_profile_after_action(
        controller.experiment,
        case.scenario_seed,
        attacked_action,
        args,
        capture_profiles=capture_profiles,
    )
    summary = summarize_trajectory(
        clean_trajectory,
        attacked_trajectory,
        clean_action,
        attacked_action,
        controller.experiment.num_switches,
        args,
    )
    return {
        "true_obs": true_obs,
        "policy_obs": policy_obs,
        "clean_action": clean_action,
        "attacked_action": attacked_action,
        "clean_policy_ms": clean_policy_ms,
        "attacked_policy_ms": attacked_policy_ms,
        "clean_controller_metadata": clean_controller_metadata,
        "attacked_controller_metadata": attacked_controller_metadata,
        "clean_trajectory": clean_trajectory,
        "attacked_trajectory": attacked_trajectory,
        "clean_observations": clean_observations,
        "attacked_observations": attacked_observations,
        "attack_metadata": attack_metadata,
        "detection": detection,
        "summary": summary,
    }


def search_row_from_result(case, result, args):
    controller_meta = result["attacked_controller_metadata"]
    row = {
        "system": "34bus",
        "target_method": case.target_method,
        "method": case.target_method,
        "case_id": case.case_id,
        "source_trial": case.source_trial,
        "scenario": "random",
        "scenario_seed": case.scenario_seed,
        "attack": case.attack,
        "attack_kwargs": case.attack_kwargs,
        "attack_kwargs_json": safe_json(case.attack_kwargs),
        "decision_attack_kwargs": case.decision_kwargs,
        "decision_attack_kwargs_json": safe_json(case.decision_kwargs),
        "attack_metadata": result["attack_metadata"],
        "clean_policy_time_ms": result["clean_policy_ms"],
        "policy_time_ms": result["attacked_policy_ms"],
        "clean_action": np.asarray(result["clean_action"], dtype=int).tolist(),
        "action": np.asarray(result["attacked_action"], dtype=int).tolist(),
        "controller_metadata": controller_meta,
        "raw_policy_action_changed": int(
            np.asarray(controller_meta.get("raw_action", result["attacked_action"]), dtype=int).tolist()
            != np.asarray(result["clean_controller_metadata"].get("raw_action", result["clean_action"]), dtype=int).tolist()
        ),
        "dms_repair_changed_action": int(controller_meta.get("repair_changed_action", 0)),
        "dms_repair_changed_entries": int(controller_meta.get("repair_changed_entries", 0)),
    }
    row.update(detection_fields(result["detection"], case.attack))
    row.update(result["summary"])
    row["rank_value"] = rank_value(row, args.rank_metric)
    return row


def case_from_search_row(row):
    import json

    return TargetedDynamicCase(
        case_id=row["case_id"],
        target_method=row["target_method"],
        source_trial=int(row["source_trial"]),
        scenario_seed=int(row["scenario_seed"]),
        attack=row["attack"],
        attack_kwargs=json.loads(row["attack_kwargs_json"]),
        decision_kwargs=json.loads(row["decision_attack_kwargs_json"]),
        search_mean_impact=float(row["mean_physical_impact_score"]),
        search_max_impact=float(row["max_physical_impact_score"]),
        search_harmful_step_rate=float(row["harmful_step_rate"]),
    )


def step_row_is_valid(row, args):
    metrics = {
        "energy_ratio": row.get("energy_ratio"),
        "voltage_violation": row.get("voltage_violation"),
        "convergence_violation": row.get("convergence_violation"),
        "reward": row.get("reward"),
    }
    impact = {"physical_impact_score": row.get("physical_impact_score")}
    return metric_is_paper_valid(metrics, args) and impact_is_paper_valid(impact, args)


def append_step_rows(rows, controller, case, result, mode, args):
    if mode == "clean_dynamic":
        action = result["clean_action"]
        action_trajectory = result["clean_trajectory"]
        clean_trajectory = result["clean_trajectory"]
        policy_ms = result["clean_policy_ms"]
        controller_metadata = result["clean_controller_metadata"]
        attack_metadata = {"target": "none"}
        detection = {}
    else:
        action = result["attacked_action"]
        action_trajectory = result["attacked_trajectory"]
        clean_trajectory = result["clean_trajectory"]
        policy_ms = result["attacked_policy_ms"]
        controller_metadata = result["attacked_controller_metadata"]
        attack_metadata = result["attack_metadata"]
        detection = result["detection"]

    clean_action = np.asarray(result["clean_action"], dtype=int)
    switches, load_status = controller.experiment.split_action(action)
    for clean_metrics, action_metrics in zip(clean_trajectory, action_trajectory):
        row = {
            "system": "34bus",
            "method": controller.method,
            "target_method": case.target_method,
            "case_id": case.case_id,
            "source_trial": case.source_trial,
            "scenario": "random",
            "scenario_seed": case.scenario_seed,
            "attack": case.attack,
            "mode": mode,
            "attack_kwargs": case.attack_kwargs,
            "decision_attack_kwargs": case.decision_kwargs,
            "attack_metadata": attack_metadata,
            "search_mean_impact": case.search_mean_impact,
            "search_max_impact": case.search_max_impact,
            "search_harmful_step_rate": case.search_harmful_step_rate,
            "time_step": action_metrics["time_step"],
            "hour": action_metrics["hour"],
            "clean_policy_time_ms": result["clean_policy_ms"],
            "policy_time_ms": policy_ms,
            "clean_action": clean_action.tolist(),
            "action": np.asarray(action, dtype=int).tolist(),
            "switch_vector": switches,
            "load_status": load_status,
            "controller_metadata": controller_metadata,
            "raw_policy_action_changed": int(
                np.asarray(controller_metadata.get("raw_action", action), dtype=int).tolist()
                != np.asarray(result["clean_controller_metadata"].get("raw_action", clean_action), dtype=int).tolist()
            ),
            "dms_repair_changed_action": int(controller_metadata.get("repair_changed_action", 0)),
            "dms_repair_changed_entries": int(controller_metadata.get("repair_changed_entries", 0)),
        }
        if mode == "attacked_dynamic":
            row.update(detection_fields(detection, case.attack))
        else:
            row.update(
                {
                    "fdia_detected": 0,
                    "detector_score": 0.0,
                    "detected_channels": [],
                    "bdd_detected": 0,
                    "bdd_score": 0.0,
                    "bdd_detected_channels": [],
                    "learning_detected": 0,
                    "learning_any_detected": 0,
                    "learning_vote_fraction": 0.0,
                    "learning_detected_count": 0,
                    "learning_detector_count": 0,
                    "learning_predicted_attacks": [],
                    "learning_detected_channels": [],
                    "learning_raw_detected_channels": [],
                    "learning_detector_reports": [],
                    "detector_expected_attack": "clean",
                    "detector_attack_class_correct": 0,
                }
            )
        row.update(action_metrics)
        row.update(physical_impact(clean_metrics, action_metrics))
        row.update(action_delta(clean_action, action, controller.experiment.num_switches))
        row["harmful_step"] = int(row["physical_impact_score"] > args.harm_threshold)
        row["paper_valid_step"] = int(step_row_is_valid(row, args))
        rows.append(row)


def finite_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def valid_voltage(value):
    number = finite_number(value)
    return number is not None and 0.0 <= number <= MAX_PLOT_VOLTAGE_PU


def valid_energy_kw(energy_kw, total_demand_kw):
    energy = finite_number(energy_kw)
    demand = finite_number(total_demand_kw)
    if energy is None:
        return False
    if demand is None or demand <= 0:
        return 0.0 <= energy <= 1.0e6
    return 0.0 <= energy <= MAX_ENERGY_FACTOR * demand


def profile_voltage_rows(controller, case, result, mode):
    observations_key = "clean_observations" if mode == "clean_dynamic" else "attacked_observations"
    trajectory_key = "clean_trajectory" if mode == "clean_dynamic" else "attacked_trajectory"
    observations = result.get(observations_key, [])
    trajectory = result.get(trajectory_key, [])
    node_list = list(getattr(controller.experiment.state_module, "node_list", []))
    nodes_conn = list(getattr(controller.experiment.state_module, "nodes_conn", []))
    rows = []
    for step, obs in enumerate(observations):
        voltages = np.asarray(obs["NodeFeat(BusVoltage)"], dtype=float)
        metrics = trajectory[step] if step < len(trajectory) else {"time_step": step, "hour": step}
        for bus_index, bus in enumerate(node_list):
            present_phases = set()
            if bus_index < len(nodes_conn):
                present_phases = {int(value) for value in np.asarray(nodes_conn[bus_index]).reshape(-1)}
            for phase_index in (1, 2, 3):
                array_phase = phase_index - 1
                voltage = float(voltages[bus_index, array_phase])
                is_valid = valid_voltage(voltage)
                rows.append(
                    {
                        "case_id": case.case_id,
                        "target_method": case.target_method,
                        "method": controller.method,
                        "paper_method_label": METHOD_LABELS.get(controller.method, controller.method),
                        "scenario_seed": case.scenario_seed,
                        "attack": case.attack,
                        "mode": mode,
                        "time_step": metrics["time_step"],
                        "hour": metrics["hour"],
                        "bus_index": bus_index,
                        "bus": bus,
                        "phase": PHASE_LABELS[phase_index],
                        "phase_index": phase_index,
                        "phase_present_base": int(phase_index in present_phases),
                        "phase_active": int(is_valid and voltage > 0.01),
                        "voltage_valid": int(is_valid),
                        "voltage_pu": voltage if is_valid else "",
                    }
                )
    return rows


def profile_energy_rows(controller, case, result, mode, args):
    trajectory_key = "clean_trajectory" if mode == "clean_dynamic" else "attacked_trajectory"
    trajectory = result.get(trajectory_key, [])
    clean_trajectory = result.get("clean_trajectory", [])
    rows = []
    for step, metrics in enumerate(trajectory):
        if mode == "attacked_dynamic" and step < len(clean_trajectory):
            impact = physical_impact(clean_trajectory[step], metrics)
        else:
            impact = {
                "energy_ratio_delta_vs_clean": 0.0,
                "energy_kw_delta_vs_clean": 0.0,
                "voltage_violation_delta_vs_clean": 0.0,
                "reward_delta_vs_clean": 0.0,
                "convergence_delta_vs_clean": 0.0,
                "loads_served_delta_vs_clean": 0,
                "physical_impact_score": 0.0,
            }
        energy_kw = float(metrics.get("energy_kw", 0.0))
        total_demand_kw = float(metrics.get("total_demand_kw", 0.0))
        energy_valid = valid_energy_kw(energy_kw, total_demand_kw)
        row = {
            "case_id": case.case_id,
            "target_method": case.target_method,
            "method": controller.method,
            "paper_method_label": METHOD_LABELS.get(controller.method, controller.method),
            "scenario_seed": case.scenario_seed,
            "attack": case.attack,
            "mode": mode,
            "time_step": metrics["time_step"],
            "hour": metrics["hour"],
            "step_hours": args.step_hours,
            "energy_valid": int(energy_valid),
            "energy_kw": energy_kw if energy_valid else "",
            "energy_served_kwh": energy_kw * float(args.step_hours) if energy_valid else "",
            "total_demand_kw": total_demand_kw,
            "energy_ratio": metrics.get("energy_ratio", ""),
            "voltage_violation": metrics.get("voltage_violation", ""),
            "convergence_violation": metrics.get("convergence_violation", ""),
            "reward": metrics.get("reward", ""),
            "loads_served": metrics.get("loads_served", ""),
            "loads_shed": metrics.get("loads_shed", ""),
            "source": "integrated_selected_replay",
        }
        row.update(impact)
        rows.append(row)
    return rows


def append_profile_rows(voltage_rows, energy_rows, controller, case, result, args):
    for mode in ("clean_dynamic", "attacked_dynamic"):
        voltage_rows.extend(profile_voltage_rows(controller, case, result, mode))
        energy_rows.extend(profile_energy_rows(controller, case, result, mode, args))


def summarize_energy_rows(rows):
    groups = {}
    for row in rows:
        key = (row["target_method"], row["paper_method_label"], row["mode"], row["time_step"], row["hour"])
        groups.setdefault(key, []).append(row)
    summary = []
    for (method, label, mode, time_step, hour), items in sorted(groups.items()):
        valid_items = [item for item in items if int(item.get("energy_valid", 0)) == 1]
        summary.append(
            {
                "target_method": method,
                "paper_method_label": label,
                "mode": mode,
                "time_step": time_step,
                "hour": hour,
                "case_count": len({item["case_id"] for item in items}),
                "valid_energy_case_count": len({item["case_id"] for item in valid_items}),
                "mean_energy_served_kwh": mean(item["energy_served_kwh"] for item in valid_items),
                "min_energy_served_kwh": min_value(item["energy_served_kwh"] for item in valid_items),
                "max_energy_served_kwh": max_value(item["energy_served_kwh"] for item in valid_items),
                "mean_energy_kw": mean(item["energy_kw"] for item in valid_items),
                "mean_energy_ratio": mean(item["energy_ratio"] for item in items),
                "mean_voltage_violation": mean(item["voltage_violation"] for item in items),
                "mean_physical_impact_score": mean(item["physical_impact_score"] for item in items),
            }
        )
    return summary


def summarize_voltage_rows(rows):
    groups = {}
    for row in rows:
        key = (
            row["target_method"],
            row["paper_method_label"],
            row["mode"],
            row["time_step"],
            row["hour"],
            row["bus_index"],
            row["bus"],
            row["phase"],
            row["phase_index"],
        )
        groups.setdefault(key, []).append(row)
    summary = []
    for (method, label, mode, time_step, hour, bus_index, bus, phase, phase_index), items in sorted(groups.items()):
        valid_items = [item for item in items if int(item.get("voltage_valid", 0)) == 1]
        summary.append(
            {
                "target_method": method,
                "paper_method_label": label,
                "mode": mode,
                "time_step": time_step,
                "hour": hour,
                "bus_index": bus_index,
                "bus": bus,
                "phase": phase,
                "phase_index": phase_index,
                "phase_present_base": max(int(item["phase_present_base"]) for item in items),
                "active_case_fraction": mean(item["phase_active"] for item in items),
                "valid_voltage_case_fraction": mean(item["voltage_valid"] for item in items),
                "mean_voltage_pu": mean(item["voltage_pu"] for item in valid_items),
                "min_voltage_pu": min_value(item["voltage_pu"] for item in valid_items),
                "max_voltage_pu": max_value(item["voltage_pu"] for item in valid_items),
            }
        )
    return summary


def write_energy_figure(summary_rows, output_path):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        return "matplotlib unavailable: {}".format(exc)

    attacked = [row for row in summary_rows if row.get("mode") == "attacked_dynamic"]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    colors = {"GCAPS": "#2f6f8f", "MLP": "#b85750", "BPSO": "#6f8f3f"}
    for label in ["GCAPS", "MLP", "BPSO"]:
        items = [row for row in attacked if row.get("paper_method_label") == label]
        items.sort(key=lambda row: int(row["hour"]))
        if not items:
            continue
        ax.plot(
            [int(row["hour"]) for row in items],
            [float(row["mean_energy_served_kwh"]) for row in items],
            marker="o",
            linewidth=1.8,
            markersize=3.2,
            color=colors.get(label),
            label=label,
        )
    ax.set_xlabel("Hour")
    ax.set_ylabel("Mean Energy Served (kWh)")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return str(output_path)


def write_profile_outputs(output_dir, voltage_rows, energy_rows, args):
    if not args.export_profiles:
        return {}
    voltage_path = output_dir / "profile_voltage_bus_phase_34bus.csv"
    energy_path = output_dir / "profile_energy_served_34bus.csv"
    voltage_summary_path = output_dir / "table_voltage_profile_summary_34bus.csv"
    energy_summary_path = output_dir / "table_energy_served_by_method_34bus.csv"
    voltage_summary = summarize_voltage_rows(voltage_rows)
    energy_summary = summarize_energy_rows(energy_rows)
    write_csv(voltage_rows, voltage_path)
    write_csv(energy_rows, energy_path)
    write_csv(voltage_summary, voltage_summary_path)
    write_csv(energy_summary, energy_summary_path)
    figure_note = "figures skipped"
    if not args.no_profile_figures:
        figure_note = write_energy_figure(
            energy_summary,
            output_dir / "fig_energy_served_kwh_attacked_34bus.png",
        )
    manifest = {
        "profile_logging": "integrated_selected_replay",
        "voltage_csv": str(voltage_path),
        "energy_csv": str(energy_path),
        "voltage_summary_csv": str(voltage_summary_path),
        "energy_summary_csv": str(energy_summary_path),
        "figure_output": figure_note,
        "voltage_rows": len(voltage_rows),
        "energy_rows": len(energy_rows),
        "note": (
            "Profile rows are written from the same selected-case clean/attacked "
            "trajectory objects used to create targeted_method_comparison_34bus.csv."
        ),
    }
    profile_manifest_path = output_dir / "profile_integrated_manifest.json"
    profile_manifest_path.write_text(safe_json(manifest) + "\n")
    return {
        "voltage_path": voltage_path,
        "energy_path": energy_path,
        "voltage_summary_path": voltage_summary_path,
        "energy_summary_path": energy_summary_path,
        "profile_manifest_path": profile_manifest_path,
        "figure_note": figure_note,
    }


def run_search(args, learning_detectors):
    rng = np.random.default_rng(args.seed)
    controllers = {method: make_controller(method, args) for method in args.methods}
    search_rows = []
    for method in args.methods:
        controller = controllers[method]
        print("target search method={} trials={}".format(method, args.trials_per_method), flush=True)
        for trial_index in range(int(args.trials_per_method)):
            start = perf_counter()
            case = make_case(method, trial_index, rng, args)
            result = run_targeted_case(controller, case, learning_detectors, args)
            row = search_row_from_result(case, result, args)
            row["trial_runtime_sec"] = perf_counter() - start
            search_rows.append(row)
            print(
                "  {} {}/{} {} mean_impact={:.6f} max_impact={:.6f} action_changed={}".format(
                    method,
                    trial_index + 1,
                    args.trials_per_method,
                    case.attack,
                    row["mean_physical_impact_score"],
                    row["max_physical_impact_score"],
                    row["action_changed"],
                ),
                flush=True,
            )
    return search_rows


def select_cases(search_rows, args):
    selected_rows = []
    for method in args.methods:
        candidates = [
            row
            for row in search_rows
            if row["target_method"] == method
            and (args.include_invalid_selection or int(row.get("paper_valid_case", 0)) == 1)
        ]
        candidates = sorted(
            candidates,
            key=lambda row: (
                rank_value(row, args.rank_metric),
                float(row.get("max_physical_impact_score", 0.0)),
                int(row.get("action_changed", 0)),
            ),
            reverse=True,
        )
        selected_rows.extend(candidates[: max(0, int(args.top_k_per_method))])
    return selected_rows


def run_selected_cases(selected_cases, args, learning_detectors):
    controllers = {method: make_controller(method, args) for method in args.methods}
    rows = []
    voltage_rows = []
    energy_rows = []
    for index, case in enumerate(selected_cases, start=1):
        controller = controllers[case.target_method]
        print(
            "selected replay {}/{} {} target={} attack={}".format(
                index,
                len(selected_cases),
                case.case_id,
                case.target_method,
                case.attack,
            ),
            flush=True,
        )
        result = run_targeted_case(
            controller,
            case,
            learning_detectors,
            args,
            capture_profiles=args.export_profiles,
        )
        append_step_rows(rows, controller, case, result, "clean_dynamic", args)
        append_step_rows(rows, controller, case, result, "attacked_dynamic", args)
        if args.export_profiles:
            append_profile_rows(voltage_rows, energy_rows, controller, case, result, args)
    return rows, voltage_rows, energy_rows


def summarize_step_rows(rows):
    groups = {}
    for row in rows:
        key = (row.get("target_method", ""), row.get("method", ""), row.get("attack", ""), row.get("mode", ""))
        groups.setdefault(key, []).append(row)
    summary = []
    for (target_method, method, attack, mode), items in sorted(groups.items()):
        case_ids = sorted({item["case_id"] for item in items})
        attacked = [item for item in items if item["mode"] == "attacked_dynamic"]
        summary.append(
            {
                "target_method": target_method,
                "method": method,
                "attack": attack,
                "mode": mode,
                "case_count": len(case_ids),
                "time_step_rows": len(items),
                "mean_energy_ratio": mean(item["energy_ratio"] for item in items),
                "min_energy_ratio": min_value(item["energy_ratio"] for item in items),
                "mean_voltage_violation": mean(item["voltage_violation"] for item in items),
                "max_voltage_violation": max_value(item["voltage_violation"] for item in items),
                "mean_reward": mean(item["reward"] for item in items),
                "mean_physical_impact_score": mean(item["physical_impact_score"] for item in items),
                "max_physical_impact_score": max_value(item["physical_impact_score"] for item in items),
                "harmful_step_rate": mean(item["harmful_step"] for item in attacked),
                "action_changed_rate": mean(item["action_changed"] for item in attacked),
                "raw_policy_action_changed_rate": mean(item["raw_policy_action_changed"] for item in attacked),
                "dms_repair_changed_rate": mean(item["dms_repair_changed_action"] for item in attacked),
                "mean_switch_changes_vs_clean": mean(item["switch_changes_vs_clean"] for item in attacked),
                "mean_load_changes_vs_clean": mean(item["load_changes_vs_clean"] for item in attacked),
                "mean_policy_time_ms": mean(item["policy_time_ms"] for item in items),
                "fdia_detected_rate": mean(item["fdia_detected"] for item in attacked),
                "bdd_detected_rate": mean(item["bdd_detected"] for item in attacked),
                "learning_detected_rate": mean(item["learning_detected"] for item in attacked),
                "attack_class_correct_rate": mean(item["detector_attack_class_correct"] for item in attacked),
            }
        )
    return summary


def detection_summary(rows):
    seen = {}
    for row in rows:
        if row.get("mode") != "attacked_dynamic":
            continue
        key = (row["target_method"], row["case_id"], row["attack"])
        seen.setdefault(key, row)
    groups = {}
    for (target_method, _case_id, attack), row in seen.items():
        groups.setdefault((target_method, attack), []).append(row)
    summary = []
    for (target_method, attack), items in sorted(groups.items()):
        summary.append(
            {
                "target_method": target_method,
                "attack": attack,
                "samples": len(items),
                "fdia_detected_rate": mean(item["fdia_detected"] for item in items),
                "bdd_detected_rate": mean(item["bdd_detected"] for item in items),
                "learning_detected_rate": mean(item["learning_detected"] for item in items),
                "learning_any_detected_rate": mean(item["learning_any_detected"] for item in items),
                "mean_learning_vote_fraction": mean(item["learning_vote_fraction"] for item in items),
                "attack_class_correct_rate": mean(item["detector_attack_class_correct"] for item in items),
            }
        )
    return summary


def write_manifest(output_dir, args, search_rows, selected_rows, comparison_rows):
    manifest = {
        "experiment": "IEEE 34-bus targeted dynamic FDIA impact without mitigation",
        "methods": args.methods,
        "attacks": args.attacks,
        "trials_per_method": args.trials_per_method,
        "top_k_per_method": args.top_k_per_method,
        "rank_metric": args.rank_metric,
        "horizon": args.horizon,
        "step_hours": args.step_hours,
        "start_hour": args.start_hour,
        "seed": args.seed,
        "bpso_particles": args.bpso_particles,
        "bpso_iterations": args.bpso_iterations,
        "decision_channel_projection_enabled": not args.no_decision_channel_projection,
        "decision_mask_scope": args.decision_mask_scope,
        "search_rows": len(search_rows),
        "selected_rows": len(selected_rows),
        "comparison_rows": len(comparison_rows),
        "profile_logging_enabled": bool(args.export_profiles),
        "profile_logging_source": "integrated_selected_replay" if args.export_profiles else "none",
        "mitigation_included": False,
        "important_note": (
            "The saved 34-bus MLP policy was observed to be constant under feature-only "
            "FDIA probes. MLP impact in this runner is therefore attributed to corrupted "
            "topology/status data entering the DMS feasibility filter, not to raw MLP "
            "feature sensitivity."
        ),
    }
    path = output_dir / "targeted_dynamic_no_mitigation_manifest.json"
    path.write_text(safe_json(manifest) + "\n")
    return path


def main():
    args = parse_args()
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    detector_dir = resolve_path(args.learning_detector_dir)
    learning_detectors = load_learning_detectors(
        detector_dir,
        tasks=args.learning_tasks,
        model_names=args.learning_models,
    )
    print("learning_detectors={}".format(len(learning_detectors)), flush=True)
    print("output_dir={}".format(output_dir), flush=True)

    search_rows = run_search(args, learning_detectors)
    selected_rows = select_cases(search_rows, args)
    selected_cases = [case_from_search_row(row) for row in selected_rows]
    comparison_rows, voltage_rows, energy_rows = run_selected_cases(selected_cases, args, learning_detectors)

    search_path = output_dir / "targeted_attack_search_34bus.csv"
    selected_path = output_dir / "targeted_selected_cases_34bus.csv"
    comparison_path = output_dir / "targeted_method_comparison_34bus.csv"
    method_summary_path = output_dir / "table_targeted_method_summary_34bus.csv"
    detector_summary_path = output_dir / "table_targeted_detection_summary_34bus.csv"

    write_csv(search_rows, search_path)
    write_csv(selected_rows, selected_path)
    write_csv(comparison_rows, comparison_path)
    write_csv(summarize_step_rows(comparison_rows), method_summary_path)
    write_csv(detection_summary(comparison_rows), detector_summary_path)
    profile_outputs = write_profile_outputs(output_dir, voltage_rows, energy_rows, args)
    manifest_path = write_manifest(output_dir, args, search_rows, selected_rows, comparison_rows)

    print("selected cases={}".format(len(selected_cases)), flush=True)
    for index, row in enumerate(selected_rows, start=1):
        print(
            "  selected {}/{} target={} {} mean_impact={:.6f} max_impact={:.6f}".format(
                index,
                len(selected_rows),
                row["target_method"],
                row["attack"],
                float(row["mean_physical_impact_score"]),
                float(row["max_physical_impact_score"]),
            ),
            flush=True,
        )
    print("wrote {}".format(search_path), flush=True)
    print("wrote {}".format(selected_path), flush=True)
    print("wrote {}".format(comparison_path), flush=True)
    print("wrote {}".format(method_summary_path), flush=True)
    print("wrote {}".format(detector_summary_path), flush=True)
    for key in [
        "voltage_path",
        "energy_path",
        "voltage_summary_path",
        "energy_summary_path",
        "profile_manifest_path",
    ]:
        if key in profile_outputs:
            print("wrote {}".format(profile_outputs[key]), flush=True)
    if "figure_note" in profile_outputs:
        print("figure {}".format(profile_outputs["figure_note"]), flush=True)
    print("wrote {}".format(manifest_path), flush=True)


if __name__ == "__main__":
    main()
