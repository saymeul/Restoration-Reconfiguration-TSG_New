"""Dynamic IEEE 34-bus FDIA impact experiment without mitigation.

This runner supports the conference-paper scope where GRL is the primary
outage-management controller and MLP/BPSO are comparison baselines.  It does
not evaluate any corrected, mitigated, or FDIA-aware action.  The workflow is:

1. Search random IEEE 34-bus outage/FDIA cases using GRL and rank them by
   multi-step physical impact over the loadshape horizon.
2. Replay the top dynamic-impact cases for GRL, MLP, and BPSO.
3. Record attack-detection evidence for the attacked observation.

The attack corrupts only the cyber observation seen by a controller/detector.
The selected restoration action is always evaluated on the true OpenDSS feeder.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import numpy as np

from FDIA_Common import ATTACK_NAMES, apply_attack
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
from Run_FDIA_AttackSearch import strong_attack_kwargs
from Run_FDIA_MethodComparison34 import BPSOController, PPOController, clone_observation


DEFAULT_ATTACKS = ["voltage_masking", "branchflow_hiding", "energy_inflation", "topology_drop"]
DEFAULT_METHODS = ["GRL", "MLP", "BPSO"]


@dataclass(frozen=True)
class DynamicCase:
    case_id: str
    source_trial: int
    scenario_seed: int
    attack: str
    attack_kwargs: dict
    search_mean_impact: float = 0.0
    search_max_impact: float = 0.0
    search_harmful_step_rate: float = 0.0


def parse_args():
    parser = argparse.ArgumentParser(
        description="IEEE 34-bus dynamic FDIA impact search/comparison without mitigation."
    )
    parser.add_argument("--trials", type=int, default=120, help="GRL dynamic attack-search trials.")
    parser.add_argument("--top-k", type=int, default=10, help="Top dynamic cases to replay.")
    parser.add_argument("--seed", type=int, default=20260605, help="Random seed for attack search.")
    parser.add_argument("--horizon", type=int, default=24, help="Dynamic loadshape time steps.")
    parser.add_argument("--step-hours", type=int, default=1, help="OpenDSS daily-mode step size in hours.")
    parser.add_argument("--start-hour", type=int, default=0, help="Starting loadshape hour.")
    parser.add_argument("--harm-threshold", type=float, default=1.0e-6)
    parser.add_argument(
        "--include-invalid-selection",
        action="store_true",
        help="Allow numerically invalid/non-paper-ready dynamic cases to be selected.",
    )
    parser.add_argument(
        "--max-abs-energy-ratio",
        type=float,
        default=2.0,
        help="Paper-valid bound on abs(energy_ratio) for clean and attacked trajectories.",
    )
    parser.add_argument(
        "--max-physical-impact",
        type=float,
        default=5.0,
        help="Paper-valid bound on per-step physical impact score.",
    )
    parser.add_argument(
        "--max-convergence-violation",
        type=float,
        default=0.0,
        help="Paper-valid upper bound on convergence_violation.",
    )
    parser.add_argument(
        "--rank-metric",
        choices=["mean_impact", "max_impact", "cumulative_impact"],
        default="mean_impact",
        help="Metric used to select top cases from the dynamic search.",
    )
    parser.add_argument(
        "--attacks",
        nargs="+",
        choices=[name for name in ATTACK_NAMES if name != "clean"],
        default=DEFAULT_ATTACKS,
    )
    parser.add_argument(
        "--methods",
        nargs="+",
        choices=DEFAULT_METHODS,
        default=DEFAULT_METHODS,
        help="Methods to replay on selected dynamic cases.",
    )
    parser.add_argument("--bpso-particles", type=int, default=8)
    parser.add_argument("--bpso-iterations", type=int, default=8)
    parser.add_argument("--bpso-seed", type=int, default=5157)
    parser.add_argument(
        "--allow-masked-switch-actions",
        action="store_true",
        help="Allow BPSO to close switches marked unavailable by ActionMasking.",
    )
    parser.add_argument(
        "--learning-detector-dir",
        default="34bus/paper_results/learning_detectors",
        help="Directory containing 34-bus learning detector pkl files.",
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
        default="paper_results/naps_34bus/dynamic_no_mitigation",
        help="Output directory under RL_Testing unless absolute.",
    )
    return parser.parse_args()


def fmt_float(value):
    if value is None:
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    if not math.isfinite(number):
        return ""
    return float(number)


def set_scenario_seed(scenario_seed):
    random.seed(int(scenario_seed))
    np.random.seed(int(scenario_seed) % (2**32 - 1))


def seeded_random_observation(experiment, scenario_seed):
    set_scenario_seed(scenario_seed)
    return experiment.get_observation("random")


def seeded_trajectory_after_action(experiment, scenario_seed, action, args):
    set_scenario_seed(scenario_seed)
    return experiment.trajectory_after_action(
        "random",
        action,
        horizon=args.horizon,
        step_hours=args.step_hours,
        start_hour=args.start_hour,
    )


def finite_values(values):
    clean = []
    for value in values:
        number = fmt_float(value)
        if number == "":
            continue
        clean.append(float(number))
    return clean


def mean(values):
    values = finite_values(values)
    return float(np.mean(values)) if values else 0.0


def min_value(values):
    values = finite_values(values)
    return float(np.min(values)) if values else 0.0


def max_value(values):
    values = finite_values(values)
    return float(np.max(values)) if values else 0.0


def metric_is_paper_valid(metrics, args):
    energy_ratio = fmt_float(metrics.get("energy_ratio"))
    voltage_violation = fmt_float(metrics.get("voltage_violation"))
    convergence_violation = fmt_float(metrics.get("convergence_violation"))
    reward = fmt_float(metrics.get("reward"))
    if energy_ratio == "" or voltage_violation == "" or convergence_violation == "" or reward == "":
        return False
    return (
        abs(float(energy_ratio)) <= float(args.max_abs_energy_ratio)
        and abs(float(voltage_violation)) <= 100.0
        and float(convergence_violation) <= float(args.max_convergence_violation)
        and abs(float(reward)) <= 1.0e6
    )


def impact_is_paper_valid(impact_row, args):
    impact = fmt_float(impact_row.get("physical_impact_score"))
    if impact == "":
        return False
    return 0.0 <= float(impact) <= float(args.max_physical_impact)


def detection_fields(detection, expected_attack):
    predicted_attacks = list(detection.get("learning_predicted_attacks", []))
    class_correct = int(expected_attack in predicted_attacks)
    bdd_report = detection.get("bdd_report", {})
    return {
        "fdia_detected": int(bool(detection.get("detected", False))),
        "detector_score": float(detection.get("score", 0.0)),
        "detected_channels": detection.get("detected_channels", []),
        "bdd_detected": int(bool(bdd_report.get("detected", False))),
        "bdd_score": float(bdd_report.get("score", 0.0)),
        "bdd_detected_channels": bdd_report.get("detected_channels", []),
        "learning_detected": int(bool(detection.get("learning_detected", False))),
        "learning_any_detected": int(bool(detection.get("learning_any_detected", False))),
        "learning_vote_fraction": float(detection.get("learning_vote_fraction", 0.0)),
        "learning_detected_count": int(detection.get("learning_detected_count", 0)),
        "learning_detector_count": int(detection.get("learning_detector_count", 0)),
        "learning_predicted_attacks": predicted_attacks,
        "learning_detected_channels": detection.get("learning_detected_channels", []),
        "learning_raw_detected_channels": detection.get("learning_raw_detected_channels", []),
        "learning_detector_reports": detection.get("learning_reports", []),
        "detector_expected_attack": expected_attack,
        "detector_attack_class_correct": class_correct,
    }


def summarize_trajectory(clean_trajectory, action_trajectory, clean_action, action, num_switches, args):
    impact_rows = [physical_impact(clean, attacked) for clean, attacked in zip(clean_trajectory, action_trajectory)]
    impact_scores = [row["physical_impact_score"] for row in impact_rows]
    energy_losses = [max(0.0, -row["energy_ratio_delta_vs_clean"]) for row in impact_rows]
    voltage_deltas = [max(0.0, row["voltage_violation_delta_vs_clean"]) for row in impact_rows]
    reward_losses = [max(0.0, -row["reward_delta_vs_clean"]) for row in impact_rows]
    harmful_steps = int(sum(1 for value in impact_scores if value > args.harm_threshold))
    invalid_time_steps = 0
    for clean_metrics, action_metrics, impact_row in zip(clean_trajectory, action_trajectory, impact_rows):
        if not metric_is_paper_valid(clean_metrics, args):
            invalid_time_steps += 1
            continue
        if not metric_is_paper_valid(action_metrics, args):
            invalid_time_steps += 1
            continue
        if not impact_is_paper_valid(impact_row, args):
            invalid_time_steps += 1
    delta = action_delta(clean_action, action, num_switches)
    return {
        "time_steps": len(action_trajectory),
        "invalid_time_steps": invalid_time_steps,
        "paper_valid_case": int(invalid_time_steps == 0),
        "mean_energy_ratio": mean(row["energy_ratio"] for row in action_trajectory),
        "min_energy_ratio": min_value(row["energy_ratio"] for row in action_trajectory),
        "mean_clean_energy_ratio": mean(row["energy_ratio"] for row in clean_trajectory),
        "min_clean_energy_ratio": min_value(row["energy_ratio"] for row in clean_trajectory),
        "mean_voltage_violation": mean(row["voltage_violation"] for row in action_trajectory),
        "max_voltage_violation": max_value(row["voltage_violation"] for row in action_trajectory),
        "mean_reward": mean(row["reward"] for row in action_trajectory),
        "mean_physical_impact_score": mean(impact_scores),
        "max_physical_impact_score": max_value(impact_scores),
        "cumulative_physical_impact_score": float(np.sum(finite_values(impact_scores))),
        "cumulative_energy_ratio_loss": float(np.sum(finite_values(energy_losses))),
        "mean_voltage_violation_delta": mean(voltage_deltas),
        "max_voltage_violation_delta": max_value(voltage_deltas),
        "cumulative_reward_loss": float(np.sum(finite_values(reward_losses))),
        "harmful_steps": harmful_steps,
        "harmful_step_rate": float(harmful_steps / len(action_trajectory)) if action_trajectory else 0.0,
        "action_changed": delta["action_changed"],
        "switch_changes_vs_clean": delta["switch_changes_vs_clean"],
        "load_changes_vs_clean": delta["load_changes_vs_clean"],
    }


def rank_value(row, rank_metric):
    if rank_metric == "max_impact":
        return float(row.get("max_physical_impact_score", 0.0))
    if rank_metric == "cumulative_impact":
        return float(row.get("cumulative_physical_impact_score", 0.0))
    return float(row.get("mean_physical_impact_score", 0.0))


def dynamic_case_from_search_row(row):
    return DynamicCase(
        case_id=row["case_id"],
        source_trial=int(row["source_trial"]),
        scenario_seed=int(row["scenario_seed"]),
        attack=row["attack"],
        attack_kwargs=json.loads(row["attack_kwargs_json"]),
        search_mean_impact=float(row["mean_physical_impact_score"]),
        search_max_impact=float(row["max_physical_impact_score"]),
        search_harmful_step_rate=float(row["harmful_step_rate"]),
    )


def make_controller(method, args):
    if method == "GRL":
        return PPOController(
            method="GRL",
            model_path=BASE_DIR / "34bus" / "TrainedModels" / "GCAPS_34.zip",
        )
    if method == "MLP":
        return PPOController(
            method="MLP",
            model_path=BASE_DIR / "34bus" / "TrainedModels" / "MLP_34.zip",
        )
    if method == "BPSO":
        return BPSOController(
            particles=args.bpso_particles,
            iterations=args.bpso_iterations,
            seed=args.bpso_seed,
            enforce_action_mask=not args.allow_masked_switch_actions,
        )
    raise ValueError("Unsupported method: {}".format(method))


def decide(controller, obs, case, mode):
    method_case = type(
        "MethodCase",
        (),
        {
            "scenario_seed": int(case.scenario_seed),
            "attack": case.attack,
            "attack_kwargs": case.attack_kwargs,
        },
    )()
    return controller.decide(clone_observation(obs), method_case, mode)


def run_grl_search_trial(experiment, trial_index, rng, learning_detectors, args):
    scenario_seed = int(rng.integers(0, 2**31 - 1))
    attack = str(rng.choice(args.attacks))
    attack_kwargs = strong_attack_kwargs(attack, rng)
    case_id = "D{:04d}_seed{}".format(trial_index, scenario_seed)

    true_obs = seeded_random_observation(experiment, scenario_seed)
    clean_action, clean_policy_ms = experiment.predict_action(true_obs)
    policy_obs, attack_metadata = apply_attack(clone_observation(true_obs), attack, **attack_kwargs)
    detection = run_detector_suite(true_obs, policy_obs, learning_detectors=learning_detectors)
    attacked_action, attacked_policy_ms = experiment.predict_action(policy_obs)

    clean_trajectory, _ = seeded_trajectory_after_action(experiment, scenario_seed, clean_action, args)
    attacked_trajectory, _ = seeded_trajectory_after_action(experiment, scenario_seed, attacked_action, args)
    summary = summarize_trajectory(
        clean_trajectory,
        attacked_trajectory,
        clean_action,
        attacked_action,
        experiment.num_switches,
        args,
    )
    switches, load_status = experiment.split_action(attacked_action)
    row = {
        "system": "34bus",
        "primary_method": "GRL",
        "case_id": case_id,
        "source_trial": trial_index,
        "scenario": "random",
        "scenario_seed": scenario_seed,
        "attack": attack,
        "attack_kwargs": attack_kwargs,
        "attack_kwargs_json": safe_json(attack_kwargs),
        "attack_metadata": attack_metadata,
        "clean_policy_time_ms": clean_policy_ms,
        "policy_time_ms": attacked_policy_ms,
        "clean_action": clean_action.tolist(),
        "action": attacked_action.tolist(),
        "switch_vector": switches,
        "load_status": load_status,
    }
    row.update(detection_fields(detection, attack))
    row.update(summary)
    row["rank_value"] = rank_value(row, args.rank_metric)
    return row


def run_dynamic_search(args, learning_detectors):
    rng = np.random.default_rng(args.seed)
    experiment = RestorationExperiment("34bus")
    rows = []
    for trial_index in range(int(args.trials)):
        start = perf_counter()
        row = run_grl_search_trial(experiment, trial_index, rng, learning_detectors, args)
        row["trial_runtime_sec"] = perf_counter() - start
        rows.append(row)
        if (trial_index + 1) % 10 == 0 or trial_index == 0:
            print(
                "search {}/{} {} {} mean_impact={:.6f} max_impact={:.6f}".format(
                    trial_index + 1,
                    args.trials,
                    row["case_id"],
                    row["attack"],
                    row["mean_physical_impact_score"],
                    row["max_physical_impact_score"],
                ),
                flush=True,
            )
    return rows


def append_step_rows(
    rows,
    controller,
    case,
    mode,
    clean_action,
    action,
    clean_trajectory,
    action_trajectory,
    clean_policy_ms,
    policy_ms,
    attack_metadata,
    detection,
    controller_metadata,
    args,
):
    switches, load_status = controller.experiment.split_action(action)
    for clean_metrics, action_metrics in zip(clean_trajectory, action_trajectory):
        row = {
            "system": "34bus",
            "method": controller.method,
            "case_id": case.case_id,
            "source_trial": case.source_trial,
            "scenario": "random",
            "scenario_seed": case.scenario_seed,
            "attack": case.attack,
            "mode": mode,
            "attack_kwargs": case.attack_kwargs,
            "attack_metadata": attack_metadata,
            "search_mean_impact": case.search_mean_impact,
            "search_max_impact": case.search_max_impact,
            "search_harmful_step_rate": case.search_harmful_step_rate,
            "time_step": action_metrics["time_step"],
            "hour": action_metrics["hour"],
            "clean_policy_time_ms": clean_policy_ms,
            "policy_time_ms": policy_ms,
            "clean_action": clean_action.tolist(),
            "action": np.asarray(action, dtype=int).tolist(),
            "switch_vector": switches,
            "load_status": load_status,
            "controller_metadata": controller_metadata,
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
        rows.append(row)


def run_method_case(controller, case, learning_detectors, args):
    true_obs = seeded_random_observation(controller.experiment, case.scenario_seed)
    clean_action, clean_policy_ms, clean_controller_metadata = decide(controller, true_obs, case, "clean")
    clean_trajectory, _ = seeded_trajectory_after_action(
        controller.experiment, case.scenario_seed, clean_action, args
    )

    policy_obs, attack_metadata = apply_attack(
        clone_observation(true_obs),
        case.attack,
        **case.attack_kwargs,
    )
    detection = run_detector_suite(true_obs, policy_obs, learning_detectors=learning_detectors)
    attacked_action, attacked_policy_ms, attacked_controller_metadata = decide(
        controller, policy_obs, case, "attacked_dynamic"
    )
    attacked_trajectory, _ = seeded_trajectory_after_action(
        controller.experiment, case.scenario_seed, attacked_action, args
    )

    rows = []
    append_step_rows(
        rows,
        controller,
        case,
        "clean_dynamic",
        clean_action,
        clean_action,
        clean_trajectory,
        clean_trajectory,
        clean_policy_ms,
        clean_policy_ms,
        {"target": "none"},
        {},
        clean_controller_metadata,
        args,
    )
    append_step_rows(
        rows,
        controller,
        case,
        "attacked_dynamic",
        clean_action,
        attacked_action,
        clean_trajectory,
        attacked_trajectory,
        clean_policy_ms,
        attacked_policy_ms,
        attack_metadata,
        detection,
        attacked_controller_metadata,
        args,
    )
    return rows


def run_method_comparison(cases, args, learning_detectors):
    all_rows = []
    for method in args.methods:
        controller = make_controller(method, args)
        print("method {} cases={}".format(method, len(cases)), flush=True)
        for index, case in enumerate(cases, start=1):
            start = perf_counter()
            case_rows = run_method_case(controller, case, learning_detectors, args)
            elapsed = perf_counter() - start
            all_rows.extend(case_rows)
            attacked = [row for row in case_rows if row["mode"] == "attacked_dynamic"]
            print(
                "  {} {}/{} {} {} mean_impact={:.6f} max_impact={:.6f} runtime_sec={:.2f}".format(
                    method,
                    index,
                    len(cases),
                    case.case_id,
                    case.attack,
                    mean(row["physical_impact_score"] for row in attacked),
                    max_value(row["physical_impact_score"] for row in attacked),
                    elapsed,
                ),
                flush=True,
            )
    return all_rows


def group_key(row, keys):
    return tuple(row.get(key, "") for key in keys)


def summarize_step_rows(rows):
    groups = {}
    for row in rows:
        key = group_key(row, ["method", "attack", "mode"])
        groups.setdefault(key, []).append(row)

    summary = []
    for (method, attack, mode), items in sorted(groups.items()):
        case_ids = sorted({item["case_id"] for item in items})
        attacked_items = [item for item in items if item["mode"] == "attacked_dynamic"]
        summary.append(
            {
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
                "harmful_step_rate": mean(item["harmful_step"] for item in attacked_items),
                "action_changed_rate": mean(item["action_changed"] for item in attacked_items),
                "mean_switch_changes_vs_clean": mean(item["switch_changes_vs_clean"] for item in attacked_items),
                "mean_load_changes_vs_clean": mean(item["load_changes_vs_clean"] for item in attacked_items),
                "mean_policy_time_ms": mean(item["policy_time_ms"] for item in items),
                "fdia_detected_rate": mean(item["fdia_detected"] for item in attacked_items),
                "bdd_detected_rate": mean(item["bdd_detected"] for item in attacked_items),
                "learning_detected_rate": mean(item["learning_detected"] for item in attacked_items),
                "attack_class_correct_rate": mean(
                    item["detector_attack_class_correct"] for item in attacked_items
                ),
            }
        )
    return summary


def detection_summary(rows):
    seen = {}
    for row in rows:
        if row.get("mode") != "attacked_dynamic":
            continue
        key = (row["case_id"], row["attack"])
        seen.setdefault(key, row)

    groups = {}
    for (_case_id, attack), row in seen.items():
        groups.setdefault(attack, []).append(row)

    summary = []
    for attack, items in sorted(groups.items()):
        summary.append(
            {
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
    if seen:
        items = list(seen.values())
        summary.append(
            {
                "attack": "all",
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


def read_csv_rows(path):
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_manifest(output_dir, args, selected_cases, search_rows, comparison_rows):
    manifest = {
        "experiment": "IEEE 34-bus dynamic FDIA impact without mitigation",
        "primary_method": "GRL",
        "comparison_methods": args.methods,
        "attacks": args.attacks,
        "trials": args.trials,
        "top_k": args.top_k,
        "rank_metric": args.rank_metric,
        "horizon": args.horizon,
        "step_hours": args.step_hours,
        "start_hour": args.start_hour,
        "seed": args.seed,
        "bpso_particles": args.bpso_particles,
        "bpso_iterations": args.bpso_iterations,
        "selected_cases": [case.case_id for case in selected_cases],
        "search_rows": len(search_rows),
        "comparison_rows": len(comparison_rows),
        "mitigation_included": False,
    }
    path = output_dir / "dynamic_no_mitigation_manifest.json"
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

    search_rows = run_dynamic_search(args, learning_detectors)
    search_path = output_dir / "dynamic_attack_search_34bus.csv"
    write_csv(search_rows, search_path)

    selected_rows = sorted(
        [
            row
            for row in search_rows
            if args.include_invalid_selection or int(row.get("paper_valid_case", 0)) == 1
        ],
        key=lambda item: (rank_value(item, args.rank_metric), item["max_physical_impact_score"]),
        reverse=True,
    )[: max(0, int(args.top_k))]
    selected_cases = [dynamic_case_from_search_row(row) for row in selected_rows]
    selected_path = output_dir / "dynamic_selected_cases_34bus.csv"
    write_csv(selected_rows, selected_path)

    print("selected cases={}".format(len(selected_cases)), flush=True)
    for index, case in enumerate(selected_cases, start=1):
        print(
            "  selected {}/{} {} {} mean_impact={:.6f} max_impact={:.6f}".format(
                index,
                len(selected_cases),
                case.case_id,
                case.attack,
                case.search_mean_impact,
                case.search_max_impact,
            ),
            flush=True,
        )

    comparison_rows = run_method_comparison(selected_cases, args, learning_detectors)
    comparison_path = output_dir / "dynamic_method_comparison_34bus.csv"
    write_csv(comparison_rows, comparison_path)

    method_summary_path = output_dir / "table_dynamic_method_summary_34bus.csv"
    write_csv(summarize_step_rows(comparison_rows), method_summary_path)

    detector_summary_path = output_dir / "table_dynamic_detection_summary_34bus.csv"
    write_csv(detection_summary(comparison_rows), detector_summary_path)

    manifest_path = write_manifest(output_dir, args, selected_cases, search_rows, comparison_rows)
    print("wrote {}".format(search_path), flush=True)
    print("wrote {}".format(selected_path), flush=True)
    print("wrote {}".format(comparison_path), flush=True)
    print("wrote {}".format(method_summary_path), flush=True)
    print("wrote {}".format(detector_summary_path), flush=True)
    print("wrote {}".format(manifest_path), flush=True)


if __name__ == "__main__":
    main()
