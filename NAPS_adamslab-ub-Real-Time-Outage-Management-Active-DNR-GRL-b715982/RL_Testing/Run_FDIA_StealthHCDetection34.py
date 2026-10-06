"""IEEE 34-bus stealthy a=Hc FDIA detection experiment.

This runner is intentionally separate from the targeted topology/status FDIA
impact runner. It evaluates a detection-focused threat model where the attack
vector is constructed inside a learned clean measurement subspace, i.e. a = Hc.

The repository does not include a full AC WLS state estimator for IEEE 34-bus.
Here, H is an experimental linear measurement-subspace proxy fitted from clean
OpenDSS observations. A projection-residual BDD that uses the same H is expected
to miss attacks in range(H), which captures the classical stealth-FDIA idea
without mixing it with the topology/status restoration-impact attack.
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

from FDIA_Common import clone_observation, detect_fdia
from FDIA_ExperimentCore import BASE_DIR, RestorationExperiment, action_delta, physical_impact, resolve_path, safe_json, write_csv
from FDIA_Learning_Models import predict_detector_model, train_detector_model
from Run_FDIA_MethodComparison34 import BPSOController, PPOController, evaluate_on_seed, set_scenario_seed


MEASUREMENT_KEYS = ["NodeFeat(BusVoltage)", "EdgeFeat(Branchflow)", "EnergySupp"]
METHOD_LABELS = {"GRL": "GCAPS", "MLP": "MLP", "BPSO": "BPSO"}


@dataclass(frozen=True)
class MeasurementMap:
    keys: list[str]
    shapes: dict[str, tuple[int, ...]]
    slices: dict[str, tuple[int, int]]
    size: int


@dataclass(frozen=True)
class StealthCase:
    case_id: str
    scenario_seed: int
    attack: str = "stealth_hc"


def parse_args():
    parser = argparse.ArgumentParser(
        description="IEEE 34-bus stealthy a=Hc FDIA detection experiment."
    )
    parser.add_argument("--seed", type=int, default=8042026)
    parser.add_argument("--calibration-samples", type=int, default=120)
    parser.add_argument("--train-samples", type=int, default=120)
    parser.add_argument("--test-samples", type=int, default=80)
    parser.add_argument("--subspace-rank", type=int, default=12)
    parser.add_argument("--bdd-quantile", type=float, default=0.99)
    parser.add_argument("--bdd-threshold-scale", type=float, default=1.05)
    parser.add_argument("--attack-scale-min", type=float, default=0.75)
    parser.add_argument("--attack-scale-max", type=float, default=3.00)
    parser.add_argument("--max-attack-attempts", type=int, default=40)
    parser.add_argument("--voltage-min", type=float, default=0.70)
    parser.add_argument("--voltage-max", type=float, default=1.30)
    parser.add_argument("--energy-min", type=float, default=0.00)
    parser.add_argument("--energy-max", type=float, default=1.50)
    parser.add_argument("--branchflow-abs-max", type=float, default=10.0)
    parser.add_argument(
        "--learning-models",
        nargs="+",
        default=["centroid", "knn", "linear_torch", "mlp_torch"],
        choices=["centroid", "knn", "linear_torch", "mlp_torch"],
    )
    parser.add_argument("--learning-epochs", type=int, default=60)
    parser.add_argument(
        "--decision-methods",
        nargs="+",
        default=["GRL", "MLP", "BPSO"],
        choices=["GRL", "MLP", "BPSO"],
    )
    parser.add_argument("--decision-probe-cases", type=int, default=5)
    parser.add_argument("--skip-decision-probe", action="store_true")
    parser.add_argument("--bpso-particles", type=int, default=8)
    parser.add_argument("--bpso-iterations", type=int, default=8)
    parser.add_argument("--bpso-seed", type=int, default=5157)
    parser.add_argument(
        "--output-dir",
        default="paper_results/naps_34bus/stealth_hc_detection",
        help="Output directory under RL_Testing unless absolute.",
    )
    return parser.parse_args()


def stable_random_seeds(rng, count):
    return [int(value) for value in rng.integers(1, 2**31 - 1, size=int(count))]


def seeded_observation(experiment, scenario_seed):
    set_scenario_seed(int(scenario_seed))
    return experiment.get_observation("random")


def build_measurement_map(obs, keys):
    slices = {}
    shapes = {}
    cursor = 0
    for key in keys:
        values = np.asarray(obs[key], dtype=float)
        size = int(values.size)
        shapes[key] = tuple(values.shape)
        slices[key] = (cursor, cursor + size)
        cursor += size
    return MeasurementMap(keys=list(keys), shapes=shapes, slices=slices, size=cursor)


def measurement_vector(obs, measurement_map):
    chunks = []
    for key in measurement_map.keys:
        values = np.asarray(obs[key], dtype=float).reshape(-1)
        values = np.nan_to_num(values, nan=0.0, posinf=1.0e6, neginf=-1.0e6)
        chunks.append(values)
    return np.concatenate(chunks).astype(float)


def observation_from_measurement_vector(reference_obs, measurement_map, vector):
    attacked = clone_observation(reference_obs)
    vector = np.asarray(vector, dtype=float).reshape(-1)
    for key in measurement_map.keys:
        start, end = measurement_map.slices[key]
        attacked[key] = vector[start:end].reshape(measurement_map.shapes[key]).astype(float)
    return attacked


def collect_clean_measurements(experiment, seeds, measurement_map=None):
    observations = []
    rows = []
    if measurement_map is None:
        first_obs = seeded_observation(experiment, seeds[0])
        measurement_map = build_measurement_map(first_obs, MEASUREMENT_KEYS)
        observations.append((seeds[0], first_obs))
        rows.append(measurement_vector(first_obs, measurement_map))
        remaining = seeds[1:]
    else:
        remaining = seeds
    for seed in remaining:
        obs = seeded_observation(experiment, seed)
        observations.append((seed, obs))
        rows.append(measurement_vector(obs, measurement_map))
    return measurement_map, observations, np.vstack(rows).astype(float)


def fit_measurement_subspace(clean_matrix, rank, bdd_quantile, threshold_scale):
    clean_matrix = np.asarray(clean_matrix, dtype=float)
    mean = np.mean(clean_matrix, axis=0)
    std = np.std(clean_matrix, axis=0)
    std[std < 1.0e-8] = 1.0
    normalized = (clean_matrix - mean) / std
    _u, singular_values, vt = np.linalg.svd(normalized, full_matrices=False)
    rank = max(1, min(int(rank), int(vt.shape[0])))
    basis = vt[:rank].T.astype(float)
    residuals = np.array([projection_residual(value, basis) for value in normalized], dtype=float)
    threshold = float(np.quantile(residuals, float(bdd_quantile)) * float(threshold_scale))
    threshold = max(threshold, float(np.max(residuals)) * 1.000001, 1.0e-10)
    return {
        "mean": mean,
        "std": std,
        "basis": basis,
        "rank": int(rank),
        "singular_values": singular_values[:rank].astype(float),
        "calibration_residuals": residuals,
        "bdd_threshold": threshold,
        "bdd_quantile": float(bdd_quantile),
        "bdd_threshold_scale": float(threshold_scale),
    }


def normalize_measurement(vector, subspace):
    return (np.asarray(vector, dtype=float) - subspace["mean"]) / subspace["std"]


def projection_residual(normalized_vector, basis):
    normalized_vector = np.asarray(normalized_vector, dtype=float).reshape(-1)
    projection = basis @ (basis.T @ normalized_vector)
    return float(np.linalg.norm(normalized_vector - projection) / math.sqrt(max(normalized_vector.size, 1)))


def state_estimator_bdd(vector, subspace):
    normalized = normalize_measurement(vector, subspace)
    residual = projection_residual(normalized, subspace["basis"])
    threshold = float(subspace["bdd_threshold"])
    return {
        "detected": int(residual > threshold),
        "residual": float(residual),
        "threshold": threshold,
        "score": float(residual / threshold) if threshold > 0 else 0.0,
    }


def unpack_measurements(measurement_map, vector):
    unpacked = {}
    vector = np.asarray(vector, dtype=float).reshape(-1)
    for key in measurement_map.keys:
        start, end = measurement_map.slices[key]
        unpacked[key] = vector[start:end].reshape(measurement_map.shapes[key])
    return unpacked


def plausible_measurement(reference_vector, attacked_vector, measurement_map, args):
    values = unpack_measurements(measurement_map, attacked_vector)
    reference = unpack_measurements(measurement_map, reference_vector)
    voltages = np.asarray(values["NodeFeat(BusVoltage)"], dtype=float)
    reference_voltages = np.asarray(reference["NodeFeat(BusVoltage)"], dtype=float)
    active_voltage = np.isfinite(reference_voltages) & (reference_voltages > 0.01)
    if np.any(active_voltage):
        active = voltages[active_voltage]
        if not np.all(np.isfinite(active)):
            return False
        if float(np.min(active)) < float(args.voltage_min) or float(np.max(active)) > float(args.voltage_max):
            return False
    inactive = voltages[~active_voltage]
    if inactive.size and float(np.max(np.abs(np.nan_to_num(inactive)))) > 0.05:
        return False

    flows = np.asarray(values["EdgeFeat(Branchflow)"], dtype=float).reshape(-1)
    if not np.all(np.isfinite(flows)):
        return False
    if flows.size and float(np.max(np.abs(flows))) > float(args.branchflow_abs_max):
        return False

    energy = float(np.asarray(values["EnergySupp"], dtype=float).reshape(-1)[0])
    return bool(np.isfinite(energy) and float(args.energy_min) <= energy <= float(args.energy_max))


def measurement_change_metrics(clean_obs, attacked_obs):
    direct = detect_fdia(clean_obs, attacked_obs)
    residuals = direct["residuals"]
    return {
        "measurement_voltage_mae_active": float(residuals.get("voltage_mae_active", 0.0)),
        "measurement_voltage_max_abs": float(residuals.get("voltage_max_abs", 0.0)),
        "measurement_voltage_changed_fraction": float(residuals.get("voltage_changed_fraction", 0.0)),
        "measurement_branchflow_mae": float(residuals.get("branchflow_mae", 0.0)),
        "measurement_branchflow_relative_mae": float(residuals.get("branchflow_relative_mae", 0.0)),
        "measurement_branchflow_max_abs": float(residuals.get("branchflow_max_abs", 0.0)),
        "measurement_energy_abs": float(residuals.get("energy_abs", 0.0)),
        "direct_channel_bdd_detected": int(bool(direct.get("detected", False))),
        "direct_channel_bdd_score": float(direct.get("score", 0.0)),
        "direct_channel_bdd_channels": direct.get("detected_channels", []),
    }


def make_stealth_hc_attack(clean_obs, measurement_map, subspace, rng, args):
    clean_vector = measurement_vector(clean_obs, measurement_map)
    basis = subspace["basis"]
    rank = int(subspace["rank"])
    for attempt in range(max(1, int(args.max_attack_attempts))):
        direction = rng.normal(0.0, 1.0, size=rank)
        norm = float(np.linalg.norm(direction))
        if norm <= 1.0e-12:
            continue
        direction = direction / norm
        amplitude = float(rng.uniform(float(args.attack_scale_min), float(args.attack_scale_max)))
        for shrink in range(10):
            coefficients = direction * amplitude
            attack_normalized = basis @ coefficients
            attacked_vector = clean_vector + attack_normalized * subspace["std"]
            if plausible_measurement(clean_vector, attacked_vector, measurement_map, args):
                attacked_obs = observation_from_measurement_vector(clean_obs, measurement_map, attacked_vector)
                clean_bdd = state_estimator_bdd(clean_vector, subspace)
                attacked_bdd = state_estimator_bdd(attacked_vector, subspace)
                return attacked_obs, {
                    "attempt": int(attempt),
                    "shrink_steps": int(shrink),
                    "attack_scale": float(amplitude),
                    "attack_normalized_l2": float(np.linalg.norm(attack_normalized)),
                    "attack_normalized_inf": float(np.max(np.abs(attack_normalized))),
                    "state_bdd_clean_detected": int(clean_bdd["detected"]),
                    "state_bdd_attacked_detected": int(attacked_bdd["detected"]),
                    "state_bdd_attack_induced_detected": int(
                        bool(attacked_bdd["detected"]) and not bool(clean_bdd["detected"])
                    ),
                    "state_bdd_clean_residual": clean_bdd["residual"],
                    "state_bdd_attacked_residual": attacked_bdd["residual"],
                    "state_bdd_residual_delta": float(attacked_bdd["residual"] - clean_bdd["residual"]),
                }
            amplitude *= 0.5
    attacked_obs = observation_from_measurement_vector(clean_obs, measurement_map, clean_vector)
    clean_bdd = state_estimator_bdd(clean_vector, subspace)
    return attacked_obs, {
        "attempt": -1,
        "shrink_steps": -1,
        "attack_scale": 0.0,
        "attack_normalized_l2": 0.0,
        "attack_normalized_inf": 0.0,
        "state_bdd_clean_detected": int(clean_bdd["detected"]),
        "state_bdd_attacked_detected": int(clean_bdd["detected"]),
        "state_bdd_attack_induced_detected": 0,
        "state_bdd_clean_residual": clean_bdd["residual"],
        "state_bdd_attacked_residual": clean_bdd["residual"],
        "state_bdd_residual_delta": 0.0,
        "attack_generation_warning": "no plausible nonzero attack found",
    }


def build_dataset_rows(experiment, seeds, split, measurement_map, subspace, rng, args):
    rows = []
    feature_rows = []
    labels = []
    pair_records = []
    for index, scenario_seed in enumerate(seeds):
        clean_obs = seeded_observation(experiment, scenario_seed)
        attacked_obs, attack_meta = make_stealth_hc_attack(clean_obs, measurement_map, subspace, rng, args)
        clean_vector = measurement_vector(clean_obs, measurement_map)
        attacked_vector = measurement_vector(attacked_obs, measurement_map)
        clean_bdd = state_estimator_bdd(clean_vector, subspace)
        attacked_bdd = state_estimator_bdd(attacked_vector, subspace)

        case_id = "Shc_{}_{:04d}_seed{}".format(split, index, scenario_seed)
        clean_row = {
            "case_id": case_id,
            "split": split,
            "label": "clean",
            "y_binary": 0,
            "scenario_seed": int(scenario_seed),
            "state_bdd_detected": int(clean_bdd["detected"]),
            "state_bdd_residual": clean_bdd["residual"],
            "state_bdd_threshold": clean_bdd["threshold"],
            "state_bdd_score": clean_bdd["score"],
            "direct_channel_bdd_detected": 0,
            "direct_channel_bdd_score": 0.0,
            "direct_channel_bdd_channels": [],
            "attack_scale": 0.0,
            "attack_normalized_l2": 0.0,
            "attack_normalized_inf": 0.0,
            "state_bdd_residual_delta": 0.0,
        }
        attacked_row = {
            "case_id": case_id,
            "split": split,
            "label": "stealth_hc",
            "y_binary": 1,
            "scenario_seed": int(scenario_seed),
            "state_bdd_detected": int(attacked_bdd["detected"]),
            "state_bdd_residual": attacked_bdd["residual"],
            "state_bdd_threshold": attacked_bdd["threshold"],
            "state_bdd_score": attacked_bdd["score"],
            **attack_meta,
            **measurement_change_metrics(clean_obs, attacked_obs),
        }
        rows.extend([clean_row, attacked_row])
        feature_rows.extend([clean_vector, attacked_vector])
        labels.extend([0, 1])
        pair_records.append(
            {
                "case_id": case_id,
                "scenario_seed": int(scenario_seed),
                "clean_obs": clean_obs,
                "attacked_obs": attacked_obs,
                "clean_vector": clean_vector,
                "attacked_vector": attacked_vector,
                "attack_meta": attack_meta,
            }
        )
    return rows, np.vstack(feature_rows).astype(np.float32), np.array(labels, dtype=np.int64), pair_records


def binary_metrics(detector_name, y_true, y_pred):
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    total = max(int(y_true.size), 1)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    f1 = 2.0 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    accuracy = (tp + tn) / total
    return {
        "detector": detector_name,
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


def train_and_evaluate_learning(X_train, y_train, X_test, y_test, rows_test, args):
    summary_rows = []
    model_rows = []
    predictions = []
    start = perf_counter()
    for model_name in args.learning_models:
        model_start = perf_counter()
        model = train_detector_model(
            model_name,
            X_train,
            y_train,
            random_state=int(args.seed),
            epochs=int(args.learning_epochs),
        )
        y_pred = predict_detector_model(model, X_test)
        predictions.append(y_pred.astype(int))
        metrics = binary_metrics("raw_measurement_learning_{}".format(model_name), y_test, y_pred)
        metrics.update(
            {
                "family": "raw_measurement_learning",
                "feature_mode": "raw_measurement_vector",
                "model": model_name,
                "train_samples": int(X_train.shape[0]),
                "test_samples": int(X_test.shape[0]),
                "runtime_sec": float(perf_counter() - model_start),
            }
        )
        summary_rows.append(metrics)
        model_rows.append(
            {
                "model": model_name,
                "feature_mode": "raw_measurement_vector",
                "train_samples": int(X_train.shape[0]),
                "test_samples": int(X_test.shape[0]),
                "accuracy": metrics["accuracy"],
                "precision": metrics["precision"],
                "recall_detection_rate": metrics["recall_detection_rate"],
                "false_positive_rate": metrics["false_positive_rate"],
                "f1": metrics["f1"],
                "runtime_sec": metrics["runtime_sec"],
            }
        )
        for row, pred in zip(rows_test, y_pred):
            row["raw_learning_{}_predicted_label".format(model_name)] = "stealth_hc" if int(pred) == 1 else "clean"
            row["raw_learning_{}_detected".format(model_name)] = int(pred)

    if predictions:
        stacked = np.vstack(predictions)
        vote_fraction = np.mean(stacked == 1, axis=0)
        ensemble_pred = (vote_fraction >= 0.5).astype(int)
        metrics = binary_metrics("raw_measurement_learning_majority_vote", y_test, ensemble_pred)
        metrics.update(
            {
                "family": "raw_measurement_learning",
                "feature_mode": "raw_measurement_vector",
                "model": "majority_vote",
                "train_samples": int(X_train.shape[0]),
                "test_samples": int(X_test.shape[0]),
                "runtime_sec": float(perf_counter() - start),
            }
        )
        summary_rows.append(metrics)
        for row, pred, vote in zip(rows_test, ensemble_pred, vote_fraction):
            row["raw_learning_majority_vote_detected"] = int(pred)
            row["raw_learning_vote_fraction"] = float(vote)
    return summary_rows, model_rows


def make_controller(method, args):
    method = method.upper()
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
            enforce_action_mask=True,
        )
    raise ValueError("Unsupported method: {}".format(method))


def run_decision_probe(pair_records, args):
    rows = []
    if args.skip_decision_probe or int(args.decision_probe_cases) <= 0:
        return rows
    selected = pair_records[: int(args.decision_probe_cases)]
    controllers = {method: make_controller(method, args) for method in args.decision_methods}
    for pair in selected:
        case = StealthCase(case_id=pair["case_id"], scenario_seed=int(pair["scenario_seed"]))
        for method, controller in controllers.items():
            clean_action, clean_policy_ms, _clean_meta = controller.decide(pair["clean_obs"], case, "clean")
            attacked_action, attacked_policy_ms, attacked_meta = controller.decide(
                pair["attacked_obs"], case, "attacked_stealth_hc"
            )
            clean_metrics, _ = evaluate_on_seed(controller.experiment, case.scenario_seed, clean_action)
            attacked_metrics, _ = evaluate_on_seed(controller.experiment, case.scenario_seed, attacked_action)
            row = {
                "case_id": case.case_id,
                "scenario_seed": case.scenario_seed,
                "method": method,
                "paper_method_label": METHOD_LABELS.get(method, method),
                "attack": case.attack,
                "clean_policy_time_ms": float(clean_policy_ms),
                "attacked_policy_time_ms": float(attacked_policy_ms),
                "clean_energy_ratio": clean_metrics.get("energy_ratio", 0.0),
                "attacked_energy_ratio": attacked_metrics.get("energy_ratio", 0.0),
                "clean_voltage_violation": clean_metrics.get("voltage_violation", 0.0),
                "attacked_voltage_violation": attacked_metrics.get("voltage_violation", 0.0),
                "clean_reward": clean_metrics.get("reward", 0.0),
                "attacked_reward": attacked_metrics.get("reward", 0.0),
                "attacked_controller_metadata": attacked_meta,
            }
            row.update(physical_impact(clean_metrics, attacked_metrics))
            row.update(action_delta(clean_action, attacked_action, controller.experiment.num_switches))
            rows.append(row)
    return rows


def add_bdd_summary(rows_test, y_test):
    state_pred = np.array([int(row["state_bdd_detected"]) for row in rows_test], dtype=int)
    direct_pred = np.array([int(row["direct_channel_bdd_detected"]) for row in rows_test], dtype=int)
    attacked_rows = [row for row in rows_test if row.get("label") == "stealth_hc"]
    state_summary = binary_metrics("state_estimator_projection_bdd", y_test, state_pred)
    state_summary.update(
        {
            "family": "model_based_bdd",
            "feature_mode": "projection_residual",
            "model": "measurement_subspace_H",
            "note": "This is the classical a=Hc bypass target; attacks in range(H) should not increase this residual.",
        }
    )
    direct_summary = binary_metrics("legacy_direct_channel_residual_check", y_test, direct_pred)
    direct_summary.update(
        {
            "family": "direct_residual_check",
            "feature_mode": "direct_clean_vs_received_difference",
            "model": "existing_project_detector",
            "note": "This uses hidden clean-reference channel differences and is not the classical state-estimation BDD.",
        }
    )
    if attacked_rows:
        clean_alarm_rate = float(np.mean([int(row.get("state_bdd_clean_detected", 0)) for row in attacked_rows]))
        attacked_alarm_rate = float(np.mean([int(row.get("state_bdd_attacked_detected", 0)) for row in attacked_rows]))
        attack_induced_rate = float(
            np.mean([int(row.get("state_bdd_attack_induced_detected", 0)) for row in attacked_rows])
        )
        residual_deltas = [float(row.get("state_bdd_residual_delta", 0.0)) for row in attacked_rows]
        paired_state_summary = {
            "detector": "state_estimator_projection_bdd_attack_induced",
            "samples": len(attacked_rows),
            "tp": "",
            "tn": "",
            "fp": "",
            "fn": "",
            "accuracy": "",
            "precision": "",
            "recall_detection_rate": attack_induced_rate,
            "false_positive_rate": "",
            "specificity": "",
            "f1": "",
            "family": "model_based_bdd",
            "feature_mode": "paired_projection_residual_delta",
            "model": "measurement_subspace_H",
            "clean_alarm_rate": clean_alarm_rate,
            "attacked_alarm_rate": attacked_alarm_rate,
            "attack_induced_detection_rate": attack_induced_rate,
            "mean_attack_residual_delta": float(np.mean(residual_deltas)),
            "max_abs_attack_residual_delta": float(np.max(np.abs(residual_deltas))),
            "note": (
                "For a=Hc stealth, this is the key BDD metric: whether the attack "
                "creates a new residual alarm beyond the clean case."
            ),
        }
        paired_direct_summary = {
            "detector": "legacy_direct_channel_residual_attack_induced",
            "samples": len(attacked_rows),
            "tp": "",
            "tn": "",
            "fp": "",
            "fn": "",
            "accuracy": "",
            "precision": "",
            "recall_detection_rate": float(np.mean([int(row["direct_channel_bdd_detected"]) for row in attacked_rows])),
            "false_positive_rate": "",
            "specificity": "",
            "f1": "",
            "family": "direct_residual_check",
            "feature_mode": "direct_clean_vs_received_difference",
            "model": "existing_project_detector",
            "attack_induced_detection_rate": float(
                np.mean([int(row["direct_channel_bdd_detected"]) for row in attacked_rows])
            ),
            "note": "Direct channel comparison sees the changed measurements; this is not the classical SE residual BDD.",
        }
        return [state_summary, direct_summary, paired_state_summary, paired_direct_summary]
    return [state_summary, direct_summary]


def write_manifest(output_dir, args, measurement_map, subspace, rows, summary_rows, decision_rows):
    attacked_rows = [row for row in rows if row.get("label") == "stealth_hc" and row.get("split") == "test"]
    clean_rows = [row for row in rows if row.get("label") == "clean" and row.get("split") == "test"]
    max_residual_delta = max(
        [abs(float(row.get("state_bdd_residual_delta", 0.0))) for row in attacked_rows] or [0.0]
    )
    manifest = {
        "experiment": "IEEE 34-bus stealthy a=Hc FDIA detection",
        "system": "34bus",
        "attack": "stealth_hc",
        "mitigation_included": False,
        "separate_from_topology_status_impact_study": True,
        "measurement_keys": measurement_map.keys,
        "measurement_shapes": {key: list(value) for key, value in measurement_map.shapes.items()},
        "measurement_vector_size": int(measurement_map.size),
        "h_model": (
            "PCA measurement-subspace proxy fitted from clean OpenDSS observations. "
            "The repository does not provide a full AC WLS state-estimation H/Jacobian."
        ),
        "attack_formula": "a = Hc in normalized measurement coordinates",
        "subspace_rank": int(subspace["rank"]),
        "bdd_threshold": float(subspace["bdd_threshold"]),
        "bdd_quantile": float(subspace["bdd_quantile"]),
        "calibration_samples": int(args.calibration_samples),
        "train_samples_per_class_pairs": int(args.train_samples),
        "test_samples_per_class_pairs": int(args.test_samples),
        "learning_models": list(args.learning_models),
        "decision_probe_cases": 0 if args.skip_decision_probe else int(args.decision_probe_cases),
        "test_clean_rows": len(clean_rows),
        "test_attack_rows": len(attacked_rows),
        "max_state_bdd_residual_delta_attack_vs_clean": float(max_residual_delta),
        "summary": summary_rows,
        "decision_probe_rows": len(decision_rows),
        "important_note": (
            "This script evaluates stealth detection. The current topology/status FDIA "
            "results remain the main restoration-impact comparison for GCAPS/GRL, MLP, and BPSO."
        ),
    }
    path = output_dir / "stealth_hc_detection_manifest.json"
    path.write_text(json.dumps(json.loads(safe_json(manifest)), indent=2) + "\n")
    return path


def save_subspace(output_dir, measurement_map, subspace):
    path = output_dir / "stealth_hc_measurement_subspace_34bus.npz"
    np.savez_compressed(
        path,
        mean=subspace["mean"],
        std=subspace["std"],
        basis=subspace["basis"],
        singular_values=subspace["singular_values"],
        calibration_residuals=subspace["calibration_residuals"],
        bdd_threshold=np.array([subspace["bdd_threshold"]], dtype=float),
        measurement_keys=np.array(measurement_map.keys, dtype=object),
    )
    return path


def main():
    args = parse_args()
    random.seed(int(args.seed))
    np.random.seed(int(args.seed) % (2**32 - 1))
    rng = np.random.default_rng(int(args.seed))
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    experiment = RestorationExperiment(system="34bus", load_model=False)
    calibration_seeds = stable_random_seeds(rng, args.calibration_samples)
    train_seeds = stable_random_seeds(rng, args.train_samples)
    test_seeds = stable_random_seeds(rng, args.test_samples)

    measurement_map, _calibration_obs, calibration_matrix = collect_clean_measurements(
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

    rows_train, X_train, y_train, _pairs_train = build_dataset_rows(
        experiment,
        train_seeds,
        "train",
        measurement_map,
        subspace,
        rng,
        args,
    )
    rows_test, X_test, y_test, pairs_test = build_dataset_rows(
        experiment,
        test_seeds,
        "test",
        measurement_map,
        subspace,
        rng,
        args,
    )

    summary_rows = add_bdd_summary(rows_test, y_test)
    learning_summary, model_rows = train_and_evaluate_learning(
        X_train,
        y_train,
        X_test,
        y_test,
        rows_test,
        args,
    )
    summary_rows.extend(learning_summary)

    decision_rows = run_decision_probe(pairs_test, args)
    all_rows = rows_train + rows_test

    cases_path = output_dir / "stealth_hc_detection_cases_34bus.csv"
    summary_path = output_dir / "table_stealth_hc_detection_summary_34bus.csv"
    model_summary_path = output_dir / "stealth_hc_learning_model_summary_34bus.csv"
    decision_path = output_dir / "stealth_hc_restoration_probe_34bus.csv"
    subspace_path = save_subspace(output_dir, measurement_map, subspace)
    write_csv(all_rows, cases_path)
    write_csv(summary_rows, summary_path)
    write_csv(model_rows, model_summary_path)
    if decision_rows:
        write_csv(decision_rows, decision_path)
    manifest_path = write_manifest(output_dir, args, measurement_map, subspace, all_rows, summary_rows, decision_rows)

    print("wrote {}".format(cases_path), flush=True)
    print("wrote {}".format(summary_path), flush=True)
    print("wrote {}".format(model_summary_path), flush=True)
    if decision_rows:
        print("wrote {}".format(decision_path), flush=True)
    print("wrote {}".format(subspace_path), flush=True)
    print("wrote {}".format(manifest_path), flush=True)


if __name__ == "__main__":
    main()
