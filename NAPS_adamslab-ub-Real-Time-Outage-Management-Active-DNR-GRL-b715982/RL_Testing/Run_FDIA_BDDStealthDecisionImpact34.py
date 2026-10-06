"""IEEE 34-bus BDD-stealthy decision-aware FDIA experiment.

This is a coordinated FDIA setting, separate from the earlier experiments:

* a = Hc measurement corruption is used to bypass projection-residual BDD.
* decision/status corruption is applied before restoration decisions so GRL,
  MLP, and BPSO can be physically impacted.
* a separate graph-learning detector is evaluated against ordinary static
  raw-measurement learning baselines.

The final restoration actions are never edited after the methods decide; all
attacks are applied to cyber inputs before decision making.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import numpy as np
import torch

from FDIA_Common import clone_observation, detect_fdia
from FDIA_ExperimentCore import (
    BASE_DIR,
    action_delta,
    physical_impact,
    resolve_path,
    safe_json,
    write_csv,
)
from FDIA_Learning_Models import predict_detector_model, train_detector_model
from Run_FDIA_DynamicImpact34_NoMitigation import (
    impact_is_paper_valid,
    max_value,
    mean,
    metric_is_paper_valid,
    min_value,
    seeded_random_observation,
    summarize_trajectory,
)
from Run_FDIA_MethodComparison34 import BPSOController
from Run_FDIA_StealthHCDetection34 import (
    build_dataset_rows,
    collect_clean_measurements,
    fit_measurement_subspace,
    make_stealth_hc_attack,
    measurement_vector,
    stable_random_seeds,
    state_estimator_bdd,
)
from Run_FDIA_StealthHCGraphDetector34 import (
    edge_indices_from_experiment,
    graph_dataset_from_pairs,
    graph_features_from_observation,
    normalized_adjacency,
    standardize_graph_features,
    train_graph_detector,
)
from Run_FDIA_TargetedDynamicImpact34_NoMitigation import (
    METHOD_LABELS,
    MaskedPPOController,
    action_mask,
    action_scope_indices,
    seeded_profile_after_action,
)


ATTACK_NAME = "bdd_stealth_decision_fdia"


@dataclass(frozen=True)
class CoordinatedCase:
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
        description="IEEE 34-bus BDD-stealthy decision-aware FDIA impact and detection experiment."
    )
    parser.add_argument("--seed", type=int, default=11042026)
    parser.add_argument("--methods", nargs="+", default=["GRL", "MLP", "BPSO"], choices=["GRL", "MLP", "BPSO"])
    parser.add_argument("--trials-per-method", type=int, default=20)
    parser.add_argument("--top-k-per-method", type=int, default=5)
    parser.add_argument("--rank-metric", choices=["mean_impact", "max_impact"], default="mean_impact")
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--step-hours", type=int, default=1)
    parser.add_argument("--start-hour", type=int, default=0)
    parser.add_argument("--harm-threshold", type=float, default=1.0e-6)
    parser.add_argument("--max-abs-energy-ratio", type=float, default=2.0)
    parser.add_argument("--max-convergence-violation", type=float, default=0.0)
    parser.add_argument("--max-physical-impact", type=float, default=5.0)
    parser.add_argument("--calibration-samples", type=int, default=160)
    parser.add_argument("--detector-train-samples", type=int, default=240)
    parser.add_argument("--detector-test-samples", type=int, default=120)
    parser.add_argument("--subspace-rank", type=int, default=12)
    parser.add_argument("--bdd-quantile", type=float, default=0.99)
    parser.add_argument("--bdd-threshold-scale", type=float, default=1.05)
    parser.add_argument("--attack-scale-min", type=float, default=0.75)
    parser.add_argument("--attack-scale-max", type=float, default=3.0)
    parser.add_argument("--max-attack-attempts", type=int, default=40)
    parser.add_argument("--voltage-min", type=float, default=0.70)
    parser.add_argument("--voltage-max", type=float, default=1.30)
    parser.add_argument("--energy-min", type=float, default=0.00)
    parser.add_argument("--energy-max", type=float, default=1.50)
    parser.add_argument("--branchflow-abs-max", type=float, default=10.0)
    parser.add_argument("--decision-mask-scope", choices=["switch", "load", "switch_and_load"], default="switch_and_load")
    parser.add_argument("--decision-mask-min-fraction", type=float, default=0.20)
    parser.add_argument("--decision-mask-max-fraction", type=float, default=0.70)
    parser.add_argument("--bpso-particles", type=int, default=8)
    parser.add_argument("--bpso-iterations", type=int, default=8)
    parser.add_argument("--bpso-seed", type=int, default=5157)
    parser.add_argument(
        "--raw-learning-models",
        nargs="+",
        default=["centroid", "knn", "linear_torch", "mlp_torch"],
        choices=["centroid", "knn", "linear_torch", "mlp_torch"],
    )
    parser.add_argument("--raw-learning-epochs", type=int, default=60)
    parser.add_argument("--graph-hidden-dim", type=int, default=48)
    parser.add_argument("--graph-epochs", type=int, default=180)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=1.0e-3)
    parser.add_argument("--weight-decay", type=float, default=1.0e-4)
    parser.add_argument("--dropout", type=float, default=0.15)
    parser.add_argument("--decision-threshold", type=float, default=0.50)
    parser.add_argument(
        "--output-dir",
        default="paper_results/naps_34bus/bdd_stealthy_decision_fdia",
    )
    return parser.parse_args()


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
        return BPSOController(
            particles=args.bpso_particles,
            iterations=args.bpso_iterations,
            seed=args.bpso_seed,
            enforce_action_mask=True,
        )
    raise ValueError("Unsupported method: {}".format(method))


def decide(controller, obs, case, mode):
    return controller.decide(clone_observation(obs), case, mode)


def generate_case(method, trial_index, rng, args):
    low = min(args.decision_mask_min_fraction, args.decision_mask_max_fraction)
    high = max(args.decision_mask_min_fraction, args.decision_mask_max_fraction)
    scenario_seed = int(rng.integers(1, 2**31 - 1))
    stealth_seed = int(rng.integers(1, 2**31 - 1))
    projection_seed = int(rng.integers(1, 2**31 - 1))
    return CoordinatedCase(
        case_id="C{}_stealthdecision_{:04d}_seed{}".format(method.lower(), trial_index, scenario_seed),
        target_method=method,
        source_trial=int(trial_index),
        scenario_seed=scenario_seed,
        attack=ATTACK_NAME,
        attack_kwargs={
            "measurement_attack": "a=Hc",
            "stealth_seed": stealth_seed,
        },
        decision_kwargs={
            "decision_projection": "false_status_to_action_mask",
            "projection_seed": projection_seed,
            "mask_scope": args.decision_mask_scope,
            "mask_fraction": float(rng.uniform(low, high)),
        },
    )


def case_from_search_row(row):
    return CoordinatedCase(
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


def apply_decision_status_projection(policy_obs, true_obs, clean_action, case, num_switches, args):
    metadata = {
        "decision_channel_projection": "false_status_to_action_mask",
        "action_mask_changed_entries": 0,
        "action_mask_selected_indices": [],
    }
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
        metadata["decision_channel_projection"] = "none_no_candidates"
        return policy_obs, metadata

    fraction = float(case.decision_kwargs.get("mask_fraction", args.decision_mask_min_fraction))
    fraction = max(0.0, min(1.0, fraction))
    count = max(1, int(math.ceil(candidates.size * fraction)))
    count = min(count, candidates.size)
    selected = np.sort(rng.choice(candidates, size=count, replace=False).astype(int))
    current_mask[selected] = 1.0
    policy_obs["ActionMasking"] = current_mask
    metadata.update(
        {
            "mask_scope": scope,
            "mask_fraction": fraction,
            "candidate_count": int(candidates.size),
            "action_mask_changed_entries": int(np.sum(current_mask != true_mask)),
            "action_mask_selected_indices": selected.tolist(),
            "selected_switch_indices": [int(index) for index in selected if int(index) < num_switches],
            "selected_load_indices": [int(index - num_switches) for index in selected if int(index) >= num_switches],
            "projection_note": (
                "False status/action-availability data marks selected available actions as unavailable. "
                "The controller decides with this corrupted input; physical impact is evaluated on the true feeder."
            ),
        }
    )
    return policy_obs, metadata


def train_raw_learning_models(X_train, y_train, X_test, y_test, args):
    models = []
    rows = []
    for model_name in args.raw_learning_models:
        start = perf_counter()
        model = train_detector_model(
            model_name,
            X_train.astype(np.float32),
            y_train.astype(np.int64),
            random_state=int(args.seed),
            epochs=int(args.raw_learning_epochs),
        )
        pred = predict_detector_model(model, X_test.astype(np.float32)).astype(int)
        metric = binary_metrics("raw_measurement_learning_{}".format(model_name), y_test, pred)
        rows.append(
            {
                "detector": metric["detector"],
                "family": "raw_measurement_learning",
                "model": model_name,
                "accuracy": metric["accuracy"],
                "precision": metric["precision"],
                "recall_detection_rate": metric["recall_detection_rate"],
                "false_positive_rate": metric["false_positive_rate"],
                "f1": metric["f1"],
                "runtime_sec": float(perf_counter() - start),
            }
        )
        models.append({"model_name": model_name, "model": model})
    return models, rows


def binary_metrics(name, y_true, y_pred):
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    accuracy = (tp + tn) / max(int(y_true.size), 1)
    return {
        "detector": name,
        "samples": int(y_true.size),
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall_detection_rate": float(recall),
        "false_positive_rate": float(fpr),
        "specificity": float(specificity),
        "f1": float(f1),
    }


def predict_raw_learning(raw_models, measurement):
    if not raw_models:
        return {"raw_learning_vote_fraction": 0.0, "raw_learning_detected": 0, "raw_learning_predictions": []}
    X = np.asarray(measurement, dtype=np.float32).reshape(1, -1)
    predictions = []
    for item in raw_models:
        pred = int(predict_detector_model(item["model"], X)[0])
        predictions.append({"model": item["model_name"], "detected": pred})
    vote = float(np.mean([item["detected"] for item in predictions]))
    return {
        "raw_learning_vote_fraction": vote,
        "raw_learning_detected": int(vote >= 0.5),
        "raw_learning_predictions": predictions,
    }


def predict_graph_detector(graph_bundle, obs):
    features = graph_features_from_observation(obs, graph_bundle["edge_indices"])
    features = ((features[None, :, :] - graph_bundle["feature_mean"]) / graph_bundle["feature_std"]).astype(np.float32)
    model = graph_bundle["model"]
    model.eval()
    with torch.no_grad():
        X = torch.as_tensor(features, dtype=torch.float32)
        adjacency = torch.as_tensor(graph_bundle["adjacency_norm"], dtype=torch.float32)
        probability = float(torch.sigmoid(model(X, adjacency)).cpu().numpy().reshape(-1)[0])
    return {
        "graph_detector_probability": probability,
        "graph_detector_detected": int(probability >= graph_bundle["threshold"]),
    }


def detection_record(true_obs, measurement_obs, policy_obs, measurement_map, subspace, raw_models, graph_bundle):
    clean_vector = measurement_vector(true_obs, measurement_map)
    attacked_vector = measurement_vector(measurement_obs, measurement_map)
    clean_bdd = state_estimator_bdd(clean_vector, subspace)
    attacked_bdd = state_estimator_bdd(attacked_vector, subspace)
    direct = detect_fdia(true_obs, policy_obs)
    raw = predict_raw_learning(raw_models, attacked_vector)
    graph = predict_graph_detector(graph_bundle, policy_obs)
    return {
        "projection_bdd_clean_detected": int(clean_bdd["detected"]),
        "projection_bdd_attacked_detected": int(attacked_bdd["detected"]),
        "projection_bdd_attack_induced_detected": int(
            bool(attacked_bdd["detected"]) and not bool(clean_bdd["detected"])
        ),
        "projection_bdd_clean_residual": clean_bdd["residual"],
        "projection_bdd_attacked_residual": attacked_bdd["residual"],
        "projection_bdd_residual_delta": float(attacked_bdd["residual"] - clean_bdd["residual"]),
        "projection_bdd_threshold": attacked_bdd["threshold"],
        "legacy_direct_residual_detected": int(bool(direct.get("detected", False))),
        "legacy_direct_residual_score": float(direct.get("score", 0.0)),
        "legacy_direct_residual_channels": direct.get("detected_channels", []),
        **raw,
        **graph,
        "fdia_detected": int(graph["graph_detector_detected"]),
    }


def run_case(controller, case, measurement_map, subspace, raw_models, graph_bundle, args):
    true_obs = seeded_random_observation(controller.experiment, case.scenario_seed)
    clean_action, clean_policy_ms, clean_meta = decide(controller, true_obs, case, "clean")
    clean_trajectory, _clean_obs_traj = seeded_profile_after_action(
        controller.experiment,
        case.scenario_seed,
        clean_action,
        args,
        capture_profiles=False,
    )

    stealth_rng = np.random.default_rng(int(case.attack_kwargs.get("stealth_seed", 1)))
    measurement_obs, stealth_meta = make_stealth_hc_attack(true_obs, measurement_map, subspace, stealth_rng, args)
    policy_obs, decision_meta = apply_decision_status_projection(
        clone_observation(measurement_obs),
        true_obs,
        clean_action,
        case,
        controller.experiment.num_switches,
        args,
    )
    detection = detection_record(true_obs, measurement_obs, policy_obs, measurement_map, subspace, raw_models, graph_bundle)
    attacked_action, attacked_policy_ms, attacked_meta = decide(controller, policy_obs, case, "attacked_dynamic")
    attacked_trajectory, _attacked_obs_traj = seeded_profile_after_action(
        controller.experiment,
        case.scenario_seed,
        attacked_action,
        args,
        capture_profiles=False,
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
        "measurement_obs": measurement_obs,
        "policy_obs": policy_obs,
        "clean_action": clean_action,
        "attacked_action": attacked_action,
        "clean_policy_ms": clean_policy_ms,
        "attacked_policy_ms": attacked_policy_ms,
        "clean_controller_metadata": clean_meta,
        "attacked_controller_metadata": attacked_meta,
        "clean_trajectory": clean_trajectory,
        "attacked_trajectory": attacked_trajectory,
        "attack_metadata": {
            "measurement_attack": stealth_meta,
            "decision_channel_attack": decision_meta,
            "attack_surface": "measurement_subspace_plus_decision_status_channel",
        },
        "detection": detection,
        "summary": summary,
    }


def rank_value(row, args):
    if args.rank_metric == "max_impact":
        return float(row.get("max_physical_impact_score", 0.0))
    return float(row.get("mean_physical_impact_score", 0.0))


def paper_valid_case(row):
    return int(row.get("invalid_time_steps", 0)) == 0 and int(row.get("projection_bdd_attack_induced_detected", 1)) == 0


def search_row_from_result(case, result, args):
    attacked_meta = result["attacked_controller_metadata"]
    row = {
        "system": "34bus",
        "target_method": case.target_method,
        "method": case.target_method,
        "paper_method_label": METHOD_LABELS.get(case.target_method, case.target_method),
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
        "controller_metadata": attacked_meta,
        "raw_policy_action_changed": int(
            np.asarray(attacked_meta.get("raw_action", result["attacked_action"]), dtype=int).tolist()
            != np.asarray(result["clean_controller_metadata"].get("raw_action", result["clean_action"]), dtype=int).tolist()
        ),
        "dms_repair_changed_action": int(attacked_meta.get("repair_changed_action", 0)),
        "dms_repair_changed_entries": int(attacked_meta.get("repair_changed_entries", 0)),
    }
    row.update(result["detection"])
    row.update(result["summary"])
    row["paper_valid_case"] = int(paper_valid_case(row))
    row["rank_value"] = rank_value(row, args)
    return row


def run_search(args, measurement_map, subspace, raw_models, graph_bundle):
    rng = np.random.default_rng(int(args.seed) + 17)
    controllers = {method: make_controller(method, args) for method in args.methods}
    rows = []
    for method in args.methods:
        controller = controllers[method]
        for trial in range(int(args.trials_per_method)):
            case = generate_case(method, trial, rng, args)
            start = perf_counter()
            result = run_case(controller, case, measurement_map, subspace, raw_models, graph_bundle, args)
            row = search_row_from_result(case, result, args)
            row["trial_runtime_sec"] = float(perf_counter() - start)
            rows.append(row)
            print(
                "{} {}/{} impact={:.6f} max={:.6f} action_changed={} bdd_induced={} graph={}".format(
                    method,
                    trial + 1,
                    args.trials_per_method,
                    row["mean_physical_impact_score"],
                    row["max_physical_impact_score"],
                    row["action_changed"],
                    row["projection_bdd_attack_induced_detected"],
                    row["graph_detector_detected"],
                ),
                flush=True,
            )
    return rows


def select_cases(search_rows, args):
    selected = []
    for method in args.methods:
        candidates = [
            row
            for row in search_rows
            if row["target_method"] == method
            and int(row.get("paper_valid_case", 0)) == 1
            and int(row.get("action_changed", 0)) == 1
        ]
        if not candidates:
            candidates = [
                row
                for row in search_rows
                if row["target_method"] == method and int(row.get("paper_valid_case", 0)) == 1
            ]
        candidates = sorted(
            candidates,
            key=lambda row: (
                rank_value(row, args),
                float(row.get("max_physical_impact_score", 0.0)),
                int(row.get("graph_detector_detected", 0)),
            ),
            reverse=True,
        )
        selected.extend(candidates[: max(0, int(args.top_k_per_method))])
    return selected


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
    clean_action = np.asarray(result["clean_action"], dtype=int)
    if mode == "clean_dynamic":
        action = clean_action
        trajectory = result["clean_trajectory"]
        policy_ms = result["clean_policy_ms"]
        controller_meta = result["clean_controller_metadata"]
        detection = {}
    else:
        action = np.asarray(result["attacked_action"], dtype=int)
        trajectory = result["attacked_trajectory"]
        policy_ms = result["attacked_policy_ms"]
        controller_meta = result["attacked_controller_metadata"]
        detection = result["detection"]
    switches, load_status = controller.experiment.split_action(action)
    for clean_metrics, metrics in zip(result["clean_trajectory"], trajectory):
        row = {
            "system": "34bus",
            "target_method": case.target_method,
            "method": controller.method,
            "paper_method_label": METHOD_LABELS.get(controller.method, controller.method),
            "case_id": case.case_id,
            "source_trial": case.source_trial,
            "scenario": "random",
            "scenario_seed": case.scenario_seed,
            "attack": case.attack,
            "mode": mode,
            "time_step": metrics["time_step"],
            "hour": metrics["hour"],
            "clean_policy_time_ms": result["clean_policy_ms"],
            "policy_time_ms": policy_ms,
            "clean_action": clean_action.tolist(),
            "action": action.tolist(),
            "switch_vector": switches,
            "load_status": load_status,
            "controller_metadata": controller_meta,
            "attack_metadata": result["attack_metadata"] if mode == "attacked_dynamic" else {"target": "none"},
            "energy_ratio": metrics.get("energy_ratio", 0.0),
            "energy_kw": metrics.get("energy_kw", 0.0),
            "total_demand_kw": metrics.get("total_demand_kw", 0.0),
            "voltage_violation": metrics.get("voltage_violation", 0.0),
            "convergence_violation": metrics.get("convergence_violation", 0.0),
            "reward": metrics.get("reward", 0.0),
            "voltage_min": metrics.get("voltage_min", 0.0),
            "voltage_max": metrics.get("voltage_max", 0.0),
            "loads_served": metrics.get("loads_served", 0),
            "loads_shed": metrics.get("loads_shed", 0),
            "raw_policy_action_changed": int(
                np.asarray(controller_meta.get("raw_action", action), dtype=int).tolist()
                != np.asarray(result["clean_controller_metadata"].get("raw_action", clean_action), dtype=int).tolist()
            ),
            "dms_repair_changed_action": int(controller_meta.get("repair_changed_action", 0)),
            "dms_repair_changed_entries": int(controller_meta.get("repair_changed_entries", 0)),
        }
        if mode == "attacked_dynamic":
            row.update(detection)
        else:
            row.update(
                {
                    "fdia_detected": 0,
                    "projection_bdd_attack_induced_detected": 0,
                    "projection_bdd_attacked_detected": 0,
                    "legacy_direct_residual_detected": 0,
                    "raw_learning_detected": 0,
                    "raw_learning_vote_fraction": 0.0,
                    "graph_detector_detected": 0,
                    "graph_detector_probability": 0.0,
                }
            )
        row.update(physical_impact(clean_metrics, metrics))
        row.update(action_delta(clean_action, action, controller.experiment.num_switches))
        row["harmful_step"] = int(row["physical_impact_score"] > args.harm_threshold)
        row["paper_valid_step"] = int(step_row_is_valid(row, args))
        rows.append(row)


def run_selected(selected_cases, args, measurement_map, subspace, raw_models, graph_bundle):
    controllers = {method: make_controller(method, args) for method in args.methods}
    rows = []
    for index, case in enumerate(selected_cases, start=1):
        controller = controllers[case.target_method]
        print(
            "selected replay {}/{} {} target={}".format(index, len(selected_cases), case.case_id, case.target_method),
            flush=True,
        )
        result = run_case(controller, case, measurement_map, subspace, raw_models, graph_bundle, args)
        append_step_rows(rows, controller, case, result, "clean_dynamic", args)
        append_step_rows(rows, controller, case, result, "attacked_dynamic", args)
    return rows


def summarize_step_rows(rows):
    groups = {}
    for row in rows:
        key = (row["target_method"], row["method"], row["attack"], row["mode"])
        groups.setdefault(key, []).append(row)
    summary = []
    for (target_method, method, attack, mode), items in sorted(groups.items()):
        attacked = [item for item in items if item["mode"] == "attacked_dynamic"]
        case_ids = sorted({item["case_id"] for item in items})
        summary.append(
            {
                "target_method": target_method,
                "method": method,
                "paper_method_label": METHOD_LABELS.get(method, method),
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
                "projection_bdd_attack_induced_rate": mean(
                    item["projection_bdd_attack_induced_detected"] for item in attacked
                ),
                "legacy_direct_residual_detected_rate": mean(item["legacy_direct_residual_detected"] for item in attacked),
                "raw_learning_detected_rate": mean(item["raw_learning_detected"] for item in attacked),
                "mean_raw_learning_vote_fraction": mean(item["raw_learning_vote_fraction"] for item in attacked),
                "graph_detector_detected_rate": mean(item["graph_detector_detected"] for item in attacked),
                "mean_graph_detector_probability": mean(item["graph_detector_probability"] for item in attacked),
            }
        )
    return summary


def detection_summary(rows):
    seen = {}
    for row in rows:
        if row["mode"] != "attacked_dynamic":
            continue
        seen.setdefault((row["target_method"], row["case_id"]), row)
    groups = {}
    for (target_method, _case_id), row in seen.items():
        groups.setdefault(target_method, []).append(row)
    summary = []
    for target_method, items in sorted(groups.items()):
        summary.append(
            {
                "target_method": target_method,
                "attack": ATTACK_NAME,
                "samples": len(items),
                "projection_bdd_attack_induced_rate": mean(
                    item["projection_bdd_attack_induced_detected"] for item in items
                ),
                "projection_bdd_attacked_alarm_rate": mean(item["projection_bdd_attacked_detected"] for item in items),
                "legacy_direct_residual_detected_rate": mean(item["legacy_direct_residual_detected"] for item in items),
                "raw_learning_detected_rate": mean(item["raw_learning_detected"] for item in items),
                "mean_raw_learning_vote_fraction": mean(item["raw_learning_vote_fraction"] for item in items),
                "graph_detector_detected_rate": mean(item["graph_detector_detected"] for item in items),
                "mean_graph_detector_probability": mean(item["graph_detector_probability"] for item in items),
            }
        )
    return summary


def train_detectors(args, experiment, output_dir):
    rng = np.random.default_rng(int(args.seed) + 100)
    calibration_seeds = stable_random_seeds(rng, args.calibration_samples)
    train_seeds = stable_random_seeds(rng, args.detector_train_samples)
    test_seeds = stable_random_seeds(rng, args.detector_test_samples)
    measurement_map, calibration_obs, calibration_matrix = collect_clean_measurements(
        experiment,
        calibration_seeds,
        measurement_map=None,
    )
    subspace = fit_measurement_subspace(
        calibration_matrix,
        rank=args.subspace_rank,
        bdd_quantile=args.bdd_quantile,
        threshold_scale=args.bdd_threshold_scale,
    )
    rows_train, X_train, y_train, pairs_train = build_dataset_rows(
        experiment,
        train_seeds,
        "detector_train",
        measurement_map,
        subspace,
        rng,
        args,
    )
    rows_test, X_test, y_test, pairs_test = build_dataset_rows(
        experiment,
        test_seeds,
        "detector_test",
        measurement_map,
        subspace,
        rng,
        args,
    )
    raw_models, raw_training_rows = train_raw_learning_models(X_train, y_train, X_test, y_test, args)

    node_list, edge_indices = edge_indices_from_experiment(experiment)
    X_train_graph, y_train_graph, _ids_train, _seeds_train = graph_dataset_from_pairs(pairs_train, edge_indices)
    X_test_graph, y_test_graph, _ids_test, _seeds_test = graph_dataset_from_pairs(pairs_test, edge_indices)
    X_train_graph, X_test_graph, feature_mean, feature_std = standardize_graph_features(X_train_graph, X_test_graph)
    adjacency_norm = normalized_adjacency(calibration_obs[0][1])
    graph_model, graph_probs, train_graph_probs, history, runtime = train_graph_detector(
        X_train_graph,
        y_train_graph,
        X_test_graph,
        y_test_graph,
        adjacency_norm,
        args,
    )
    graph_pred = (graph_probs >= float(args.decision_threshold)).astype(int)
    train_graph_pred = (train_graph_probs >= float(args.decision_threshold)).astype(int)
    graph_metric = binary_metrics("graph_learning_gcn_detector", y_test_graph, graph_pred)
    train_graph_metric = binary_metrics("graph_learning_gcn_detector_train", y_train_graph, train_graph_pred)
    graph_training_row = {
        "detector": "graph_learning_gcn_detector",
        "family": "graph_learning",
        "model": "two_layer_gcn_global_pool",
        "accuracy": graph_metric["accuracy"],
        "precision": graph_metric["precision"],
        "recall_detection_rate": graph_metric["recall_detection_rate"],
        "false_positive_rate": graph_metric["false_positive_rate"],
        "f1": graph_metric["f1"],
        "train_accuracy": train_graph_metric["accuracy"],
        "runtime_sec": float(runtime),
    }
    graph_bundle = {
        "model": graph_model,
        "edge_indices": edge_indices,
        "feature_mean": feature_mean,
        "feature_std": feature_std,
        "adjacency_norm": adjacency_norm,
        "threshold": float(args.decision_threshold),
    }
    torch.save(
        {
            "state_dict": graph_model.state_dict(),
            "feature_mean": feature_mean,
            "feature_std": feature_std,
            "edge_indices": edge_indices,
            "node_list": node_list,
            "args": vars(args),
        },
        output_dir / "bdd_stealth_graph_detector_34bus.pt",
    )
    write_csv(raw_training_rows + [graph_training_row], output_dir / "table_bdd_stealth_detector_training_summary_34bus.csv")
    write_csv(history, output_dir / "bdd_stealth_graph_training_history_34bus.csv")
    write_csv(rows_train + rows_test, output_dir / "bdd_stealth_detector_dataset_cases_34bus.csv")
    return measurement_map, subspace, raw_models, graph_bundle, raw_training_rows + [graph_training_row], history


def write_manifest(output_dir, args, search_rows, selected_rows, comparison_rows, detector_training_rows):
    manifest = {
        "experiment": "IEEE 34-bus BDD-stealthy decision-aware coordinated FDIA",
        "attack": ATTACK_NAME,
        "methods": args.methods,
        "trials_per_method": args.trials_per_method,
        "top_k_per_method": args.top_k_per_method,
        "horizon": args.horizon,
        "mitigation_included": False,
        "attack_components": [
            "a=Hc measurement-subspace attack for projection-residual BDD bypass",
            "false status/action-availability corruption before restoration decision",
        ],
        "not_pure_measurement_only": True,
        "projection_bdd_model": (
            "PCA measurement-subspace proxy H because this repository does not include a full AC WLS state estimator."
        ),
        "decision_impact_note": (
            "MLP and BPSO impact is attributed to corrupted decision-relevant status/action availability; "
            "actions are not edited after the method decides."
        ),
        "detector_training_summary": detector_training_rows,
        "search_rows": len(search_rows),
        "selected_rows": len(selected_rows),
        "comparison_rows": len(comparison_rows),
    }
    path = output_dir / "bdd_stealth_manifest.json"
    path.write_text(json.dumps(json.loads(safe_json(manifest)), indent=2) + "\n")
    return path


def main():
    args = parse_args()
    args.hidden_dim = int(args.graph_hidden_dim)
    args.epochs = int(args.graph_epochs)
    random.seed(int(args.seed))
    np.random.seed(int(args.seed) % (2**32 - 1))
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print("output_dir={}".format(output_dir), flush=True)

    detector_experiment = make_controller("BPSO", args).experiment
    measurement_map, subspace, raw_models, graph_bundle, detector_training_rows, _history = train_detectors(
        args,
        detector_experiment,
        output_dir,
    )

    search_rows = run_search(args, measurement_map, subspace, raw_models, graph_bundle)
    selected_rows = select_cases(search_rows, args)
    selected_cases = [case_from_search_row(row) for row in selected_rows]
    comparison_rows = run_selected(selected_cases, args, measurement_map, subspace, raw_models, graph_bundle)

    search_path = output_dir / "bdd_stealth_attack_search_34bus.csv"
    selected_path = output_dir / "bdd_stealth_selected_cases_34bus.csv"
    comparison_path = output_dir / "bdd_stealth_method_comparison_34bus.csv"
    method_summary_path = output_dir / "table_bdd_stealth_method_summary_34bus.csv"
    detection_summary_path = output_dir / "table_bdd_stealth_detection_summary_34bus.csv"

    write_csv(search_rows, search_path)
    write_csv(selected_rows, selected_path)
    write_csv(comparison_rows, comparison_path)
    write_csv(summarize_step_rows(comparison_rows), method_summary_path)
    write_csv(detection_summary(comparison_rows), detection_summary_path)
    manifest_path = write_manifest(output_dir, args, search_rows, selected_rows, comparison_rows, detector_training_rows)

    print("selected cases={}".format(len(selected_cases)), flush=True)
    for index, row in enumerate(selected_rows, start=1):
        print(
            "selected {}/{} {} target={} impact={:.6f} bdd_induced={} graph={}".format(
                index,
                len(selected_rows),
                row["case_id"],
                row["target_method"],
                float(row["mean_physical_impact_score"]),
                row["projection_bdd_attack_induced_detected"],
                row["graph_detector_detected"],
            ),
            flush=True,
        )
    print("wrote {}".format(search_path), flush=True)
    print("wrote {}".format(selected_path), flush=True)
    print("wrote {}".format(comparison_path), flush=True)
    print("wrote {}".format(method_summary_path), flush=True)
    print("wrote {}".format(detection_summary_path), flush=True)
    print("wrote {}".format(manifest_path), flush=True)


if __name__ == "__main__":
    main()
