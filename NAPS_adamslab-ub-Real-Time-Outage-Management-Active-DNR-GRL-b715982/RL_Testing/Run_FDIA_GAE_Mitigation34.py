"""IEEE 34-bus topology/status FDIA detection and mitigation extension.

This runner intentionally leaves the existing no-mitigation impact results
unchanged.  It reuses the selected topology/status FDIA cases, trains a graph
autoencoder (GAE) anomaly detector on clean outage observations, and evaluates
a detection-guided OpenDSS candidate-screening mitigation stage.

The mitigation stage does not overwrite the attacked decision and does not copy
the saved clean action.  When the GAE flags the received observation, candidate
switch/load actions are generated from the attacked action, a trusted-state
controller recomputation, and random local mutations.  Candidates are scored by
OpenDSS physical evaluation, and the best feasible candidate is replayed over
the dynamic horizon.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import numpy as np
import torch

from FDIA_Common import clone_observation, restoration_action_quality
from FDIA_ExperimentCore import action_delta, physical_impact, resolve_path, safe_json, write_csv
from Run_FDIA_DynamicImpact34_NoMitigation import (
    detection_fields,
    impact_is_paper_valid,
    max_value,
    mean,
    metric_is_paper_valid,
    min_value,
    seeded_random_observation,
)
from Run_FDIA_MethodComparison34 import evaluate_on_seed, stable_seed
from Run_FDIA_TargetedDynamicImpact34_NoMitigation import (
    METHOD_LABELS,
    build_policy_observation,
    case_from_search_row,
    decide,
    make_controller,
    seeded_profile_after_action,
    step_row_is_valid,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Graph-autoencoder FDIA detection plus OpenDSS-validated mitigation for IEEE 34-bus."
    )
    parser.add_argument(
        "--source-dir",
        default="paper_results/naps_34bus/targeted_dynamic_no_mitigation",
        help="Existing no-mitigation result directory containing targeted_selected_cases_34bus.csv.",
    )
    parser.add_argument(
        "--selected-file",
        default="targeted_selected_cases_34bus.csv",
        help="Selected topology/status FDIA cases to reuse without changing baseline results.",
    )
    parser.add_argument(
        "--output-dir",
        default="paper_results/naps_34bus/topology_status_gae_mitigation",
        help="New output directory for detection/mitigation results.",
    )
    parser.add_argument("--methods", nargs="+", default=["GRL", "MLP", "BPSO"], choices=["GRL", "MLP", "BPSO"])
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--step-hours", type=int, default=1)
    parser.add_argument("--start-hour", type=int, default=0)
    parser.add_argument("--harm-threshold", type=float, default=1.0e-6)
    parser.add_argument("--max-abs-energy-ratio", type=float, default=2.0)
    parser.add_argument("--max-physical-impact", type=float, default=5.0)
    parser.add_argument("--max-convergence-violation", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=20260610)
    parser.add_argument("--gae-train-samples", type=int, default=120)
    parser.add_argument("--gae-val-fraction", type=float, default=0.25)
    parser.add_argument("--gae-epochs", type=int, default=120)
    parser.add_argument("--gae-hidden-dim", type=int, default=32)
    parser.add_argument("--gae-latent-dim", type=int, default=16)
    parser.add_argument("--gae-learning-rate", type=float, default=1.0e-3)
    parser.add_argument("--gae-threshold-quantile", type=float, default=0.95)
    parser.add_argument("--candidate-samples", type=int, default=96)
    parser.add_argument("--candidate-mutation-max", type=int, default=5)
    parser.add_argument("--mitigation-voltage-weight", type=float, default=1.0)
    parser.add_argument("--mitigation-convergence-weight", type=float, default=2.0)
    parser.add_argument("--bpso-particles", type=int, default=8)
    parser.add_argument("--bpso-iterations", type=int, default=8)
    parser.add_argument("--bpso-seed", type=int, default=5157)
    parser.add_argument("--bpso-load-weight-gain", type=float, default=0.20)
    parser.add_argument("--decision-mask-scope", default="switch_and_load")
    parser.add_argument("--decision-mask-min-fraction", type=float, default=0.20)
    parser.add_argument("--decision-mask-max-fraction", type=float, default=0.70)
    parser.add_argument("--no-decision-channel-projection", action="store_true")
    return parser.parse_args()


def read_rows(path):
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def parse_action(value):
    if isinstance(value, list):
        return np.asarray(value, dtype=int)
    return np.asarray(json.loads(value), dtype=int)


def method_label(method):
    return METHOD_LABELS.get(method, method)


def finite(value, default=0.0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _as_binary_adjacency(obs):
    adj = np.asarray(obs["Adjacency"], dtype=np.float32)
    adj = np.nan_to_num(adj, nan=0.0, posinf=0.0, neginf=0.0)
    adj = (adj > 0.0).astype(np.float32)
    if adj.ndim != 2:
        size = int(math.sqrt(adj.size))
        adj = adj.reshape(size, size)
    adj = np.maximum(adj, adj.T)
    np.fill_diagonal(adj, 0.0)
    return adj.astype(np.float32)


def graph_sample_from_observation(obs, feature_mean=None, feature_std=None):
    voltages = np.asarray(obs["NodeFeat(BusVoltage)"], dtype=np.float32)
    voltages = np.nan_to_num(voltages, nan=0.0, posinf=2.0, neginf=0.0)
    voltages = np.clip(voltages, 0.0, 2.0)
    active = (voltages > 0.01).astype(np.float32)
    adj = _as_binary_adjacency(obs)
    degree = adj.sum(axis=1, keepdims=True).astype(np.float32) / max(float(adj.shape[0] - 1), 1.0)
    x = np.concatenate([voltages, active, degree], axis=1).astype(np.float32)
    if feature_mean is not None and feature_std is not None:
        x = (x - feature_mean) / feature_std
    mask = np.asarray(obs["ActionMasking"], dtype=np.float32).reshape(-1)
    mask = np.nan_to_num(mask, nan=0.0, posinf=1.0, neginf=0.0)
    mask = np.clip(mask, 0.0, 1.0)
    return {"x": x.astype(np.float32), "adj": adj, "mask": mask.astype(np.float32)}


def graph_normalize(adj_tensor):
    n = adj_tensor.shape[0]
    device = adj_tensor.device
    a = adj_tensor + torch.eye(n, dtype=adj_tensor.dtype, device=device)
    degree = a.sum(dim=1).clamp(min=1.0)
    inv_sqrt = torch.pow(degree, -0.5)
    return inv_sqrt[:, None] * a * inv_sqrt[None, :]


class GraphAutoencoder(torch.nn.Module):
    def __init__(self, input_dim, hidden_dim, latent_dim, mask_dim):
        super().__init__()
        self.encoder_1 = torch.nn.Linear(input_dim, hidden_dim)
        self.encoder_2 = torch.nn.Linear(hidden_dim, latent_dim)
        self.feature_decoder = torch.nn.Sequential(
            torch.nn.Linear(latent_dim, hidden_dim),
            torch.nn.ReLU(),
            torch.nn.Linear(hidden_dim, input_dim),
        )
        self.mask_decoder = torch.nn.Sequential(
            torch.nn.Linear(latent_dim, hidden_dim),
            torch.nn.ReLU(),
            torch.nn.Linear(hidden_dim, mask_dim),
        )

    def encode(self, x, adj):
        norm = graph_normalize(adj)
        h = torch.relu(norm @ self.encoder_1(x))
        z = norm @ self.encoder_2(h)
        return z

    def forward(self, x, adj):
        z = self.encode(x, adj)
        x_hat = self.feature_decoder(z)
        adj_logits = (z @ z.T) / math.sqrt(max(float(z.shape[1]), 1.0))
        mask_logits = self.mask_decoder(z.mean(dim=0))
        return x_hat, adj_logits, mask_logits


@dataclass
class GAEBundle:
    model: GraphAutoencoder
    feature_mean: np.ndarray
    feature_std: np.ndarray
    threshold: float
    clean_score_mean: float
    clean_score_std: float
    input_dim: int
    mask_dim: int


def fit_feature_standardizer(samples):
    stacked = np.concatenate([sample["x"] for sample in samples], axis=0)
    mean_vec = stacked.mean(axis=0, keepdims=True).astype(np.float32)
    std_vec = stacked.std(axis=0, keepdims=True).astype(np.float32)
    std_vec[std_vec < 1.0e-6] = 1.0
    return mean_vec, std_vec


def tensor_sample(sample):
    return (
        torch.as_tensor(sample["x"], dtype=torch.float32),
        torch.as_tensor(sample["adj"], dtype=torch.float32),
        torch.as_tensor(sample["mask"], dtype=torch.float32),
    )


def gae_loss(model, sample, weights=(1.0, 1.0, 0.75)):
    x, adj, mask = tensor_sample(sample)
    x_hat, adj_logits, mask_logits = model(x, adj)
    feature_loss = torch.nn.functional.mse_loss(x_hat, x)
    adj_loss = torch.nn.functional.binary_cross_entropy_with_logits(adj_logits, adj)
    mask_loss = torch.nn.functional.binary_cross_entropy_with_logits(mask_logits, mask)
    total = weights[0] * feature_loss + weights[1] * adj_loss + weights[2] * mask_loss
    return total, feature_loss, adj_loss, mask_loss


def gae_score(bundle, obs):
    sample = graph_sample_from_observation(obs, bundle.feature_mean, bundle.feature_std)
    with torch.no_grad():
        total, feature_loss, adj_loss, mask_loss = gae_loss(bundle.model, sample)
    score = float(total.cpu().item())
    return {
        "score": score,
        "feature_reconstruction_error": float(feature_loss.cpu().item()),
        "adjacency_reconstruction_error": float(adj_loss.cpu().item()),
        "action_mask_reconstruction_error": float(mask_loss.cpu().item()),
        "detected": int(score > bundle.threshold),
        "threshold": float(bundle.threshold),
    }


def train_graph_autoencoder(clean_observations, args):
    raw_samples = [graph_sample_from_observation(obs) for obs in clean_observations]
    feature_mean, feature_std = fit_feature_standardizer(raw_samples)
    samples = [graph_sample_from_observation(obs, feature_mean, feature_std) for obs in clean_observations]
    rng = np.random.default_rng(args.seed)
    indices = np.arange(len(samples))
    rng.shuffle(indices)
    val_count = max(1, int(round(len(indices) * float(args.gae_val_fraction))))
    val_indices = indices[:val_count]
    train_indices = indices[val_count:] if val_count < len(indices) else indices
    input_dim = int(samples[0]["x"].shape[1])
    mask_dim = int(samples[0]["mask"].size)
    model = GraphAutoencoder(input_dim, args.gae_hidden_dim, args.gae_latent_dim, mask_dim)
    optimizer = torch.optim.Adam(model.parameters(), lr=float(args.gae_learning_rate))
    history = []
    for epoch in range(1, int(args.gae_epochs) + 1):
        rng.shuffle(train_indices)
        model.train()
        losses = []
        for index in train_indices:
            optimizer.zero_grad()
            total, _feature_loss, _adj_loss, _mask_loss = gae_loss(model, samples[int(index)])
            total.backward()
            optimizer.step()
            losses.append(float(total.detach().cpu().item()))
        model.eval()
        with torch.no_grad():
            train_scores = [float(gae_loss(model, samples[int(index)])[0].cpu().item()) for index in train_indices]
            val_scores = [float(gae_loss(model, samples[int(index)])[0].cpu().item()) for index in val_indices]
        history.append(
            {
                "epoch": epoch,
                "mean_batch_loss": float(np.mean(losses)) if losses else 0.0,
                "train_score_mean": float(np.mean(train_scores)) if train_scores else 0.0,
                "val_score_mean": float(np.mean(val_scores)) if val_scores else 0.0,
                "val_score_max": float(np.max(val_scores)) if val_scores else 0.0,
            }
        )
    model.eval()
    clean_scores = [float(gae_loss(model, sample)[0].detach().cpu().item()) for sample in samples]
    quantile = min(max(float(args.gae_threshold_quantile), 0.0), 1.0)
    threshold = float(np.quantile(clean_scores, quantile))
    threshold += max(1.0e-6, 0.05 * float(np.std(clean_scores)))
    bundle = GAEBundle(
        model=model,
        feature_mean=feature_mean,
        feature_std=feature_std,
        threshold=threshold,
        clean_score_mean=float(np.mean(clean_scores)),
        clean_score_std=float(np.std(clean_scores)),
        input_dim=input_dim,
        mask_dim=mask_dim,
    )
    return bundle, history, clean_scores


def clean_training_observations(args):
    from FDIA_ExperimentCore import RestorationExperiment

    experiment = RestorationExperiment(system="34bus", load_model=False)
    rng = np.random.default_rng(args.seed + 991)
    observations = []
    for _ in range(max(2, int(args.gae_train_samples))):
        seed = int(rng.integers(0, 2**31 - 1))
        observations.append(seeded_random_observation(experiment, seed))
    return observations


def repair_action(action, reference_obs, n_actions):
    repaired = np.asarray(action, dtype=int).reshape(-1).copy()
    if repaired.size != int(n_actions):
        fixed = np.zeros(int(n_actions), dtype=int)
        fixed[: min(repaired.size, n_actions)] = repaired[: min(repaired.size, n_actions)]
        repaired = fixed
    repaired = np.where(repaired > 0, 1, 0).astype(int)
    mask = np.asarray(reference_obs.get("ActionMasking", []), dtype=float).reshape(-1)
    if mask.size == int(n_actions):
        repaired[mask > 0.5] = 0
    return repaired


def mutated_action(base, rng, reference_obs, n_actions, max_flips):
    action = np.asarray(base, dtype=int).copy()
    flip_count = int(rng.integers(1, max(2, int(max_flips) + 1)))
    indices = rng.choice(np.arange(int(n_actions)), size=min(flip_count, int(n_actions)), replace=False)
    action[indices] = 1 - action[indices]
    return repair_action(action, reference_obs, n_actions)


def evaluate_candidate(controller, case, action, args):
    metrics, _obs = evaluate_on_seed(controller.experiment, case.scenario_seed, action)
    if not metric_is_paper_valid(metrics, args):
        return -np.inf, metrics
    score = (
        float(metrics.get("energy_ratio", 0.0))
        - float(args.mitigation_voltage_weight) * float(metrics.get("voltage_violation", 0.0))
        - float(args.mitigation_convergence_weight) * float(metrics.get("convergence_violation", 0.0))
    )
    return score, metrics


def mitigation_search(controller, case, true_obs, attacked_action, reference_action, detected, args):
    start = perf_counter()
    n_actions = int(controller.experiment.n_actions)
    attacked_action = repair_action(attacked_action, true_obs, n_actions)
    reference_action = repair_action(reference_action, true_obs, n_actions)
    if not detected:
        score, metrics = evaluate_candidate(controller, case, attacked_action, args)
        return attacked_action, {
            "mitigation_applied": 0,
            "mitigation_reason": "gae_not_detected",
            "mitigation_candidate_count": 1,
            "mitigation_best_score": score,
            "mitigation_best_metrics": metrics,
            "mitigation_runtime_ms": (perf_counter() - start) * 1000.0,
            "selected_candidate_origin": "attacked_action",
            "reference_action_equals_attacked": int(np.array_equal(reference_action, attacked_action)),
        }

    rng = np.random.default_rng(stable_seed(args.seed, case.scenario_seed, case.case_id, "gae_mitigation"))
    candidates = []

    def add_candidate(origin, action):
        repaired = repair_action(action, true_obs, n_actions)
        key = tuple(int(value) for value in repaired.tolist())
        if key not in {item[0] for item in candidates}:
            candidates.append((key, origin, repaired))

    add_candidate("attacked_action", attacked_action)
    add_candidate("trusted_state_controller_recompute", reference_action)
    for _ in range(max(0, int(args.candidate_samples) // 2)):
        add_candidate("mutation_of_attacked_action", mutated_action(attacked_action, rng, true_obs, n_actions, args.candidate_mutation_max))
    for _ in range(max(0, int(args.candidate_samples) // 3)):
        add_candidate("mutation_of_trusted_recompute", mutated_action(reference_action, rng, true_obs, n_actions, args.candidate_mutation_max))
    for _ in range(max(0, int(args.candidate_samples) - len(candidates))):
        add_candidate("random_physics_screened_action", rng.integers(0, 2, size=n_actions, dtype=int))

    best_score = -np.inf
    best_action = attacked_action
    best_metrics = {}
    best_origin = "attacked_action"
    evaluated = 0
    for _key, origin, action in candidates:
        score, metrics = evaluate_candidate(controller, case, action, args)
        evaluated += 1
        if score > best_score:
            best_score = float(score)
            best_action = np.asarray(action, dtype=int)
            best_metrics = metrics
            best_origin = origin
    return best_action, {
        "mitigation_applied": 1,
        "mitigation_reason": "gae_detected_physics_screening",
        "mitigation_candidate_count": evaluated,
        "mitigation_best_score": best_score,
        "mitigation_best_metrics": best_metrics,
        "mitigation_runtime_ms": (perf_counter() - start) * 1000.0,
        "selected_candidate_origin": best_origin,
        "reference_action_equals_attacked": int(np.array_equal(reference_action, attacked_action)),
        "selected_action_equals_reference_recompute": int(np.array_equal(best_action, reference_action)),
    }


def run_case(controller, selected_row, case, gae, args):
    true_obs = seeded_random_observation(controller.experiment, case.scenario_seed)
    clean_action = parse_action(selected_row["clean_action"])
    attacked_action = parse_action(selected_row["action"])
    reference_action, reference_ms, reference_meta = decide(controller, true_obs, case, "mitigation_reference")
    policy_obs, attack_metadata = build_policy_observation(true_obs, clean_action, case, controller, args)

    clean_detection = gae_score(gae, true_obs)
    attacked_detection = gae_score(gae, policy_obs)
    mitigated_action, mitigation_meta = mitigation_search(
        controller,
        case,
        true_obs,
        attacked_action,
        reference_action,
        bool(attacked_detection["detected"]),
        args,
    )

    clean_trajectory, _clean_obs = seeded_profile_after_action(
        controller.experiment, case.scenario_seed, clean_action, args, capture_profiles=False
    )
    attacked_trajectory, _attacked_obs = seeded_profile_after_action(
        controller.experiment, case.scenario_seed, attacked_action, args, capture_profiles=False
    )
    mitigated_trajectory, _mitigated_obs = seeded_profile_after_action(
        controller.experiment, case.scenario_seed, mitigated_action, args, capture_profiles=False
    )
    return {
        "true_obs": true_obs,
        "policy_obs": policy_obs,
        "clean_action": clean_action,
        "attacked_action": attacked_action,
        "reference_action": reference_action,
        "mitigated_action": mitigated_action,
        "reference_policy_ms": reference_ms,
        "reference_controller_metadata": reference_meta,
        "attack_metadata": attack_metadata,
        "clean_detection": clean_detection,
        "attacked_detection": attacked_detection,
        "mitigation_metadata": mitigation_meta,
        "clean_trajectory": clean_trajectory,
        "attacked_trajectory": attacked_trajectory,
        "mitigated_trajectory": mitigated_trajectory,
    }


def detection_case_rows(case, result):
    rows = []
    for mode, detection in [("clean_dynamic", result["clean_detection"]), ("attacked_dynamic", result["attacked_detection"])]:
        rows.append(
            {
                "system": "34bus",
                "target_method": case.target_method,
                "method": case.target_method,
                "paper_method_label": method_label(case.target_method),
                "case_id": case.case_id,
                "scenario_seed": case.scenario_seed,
                "attack": case.attack if mode == "attacked_dynamic" else "none",
                "mode": mode,
                "gae_score": detection["score"],
                "gae_threshold": detection["threshold"],
                "gae_detected": detection["detected"],
                "feature_reconstruction_error": detection["feature_reconstruction_error"],
                "adjacency_reconstruction_error": detection["adjacency_reconstruction_error"],
                "action_mask_reconstruction_error": detection["action_mask_reconstruction_error"],
            }
        )
    return rows


def step_rows(controller, case, result, mode, args):
    if mode == "clean_dynamic":
        action = result["clean_action"]
        trajectory = result["clean_trajectory"]
        metadata = {"mode": "clean_reference"}
        detection = {"detected": 0, "score": 0.0}
        clean_trajectory = result["clean_trajectory"]
    elif mode == "attacked_dynamic":
        action = result["attacked_action"]
        trajectory = result["attacked_trajectory"]
        metadata = {"mode": "attacked_no_mitigation"}
        detection = result["attacked_detection"]
        clean_trajectory = result["clean_trajectory"]
    else:
        action = result["mitigated_action"]
        trajectory = result["mitigated_trajectory"]
        metadata = result["mitigation_metadata"]
        detection = result["attacked_detection"]
        clean_trajectory = result["clean_trajectory"]

    clean_action = np.asarray(result["clean_action"], dtype=int)
    switches, load_status = controller.experiment.split_action(action)
    rows = []
    for clean_metrics, metrics in zip(clean_trajectory, trajectory):
        row = {
            "system": "34bus",
            "target_method": case.target_method,
            "method": case.target_method,
            "paper_method_label": method_label(case.target_method),
            "case_id": case.case_id,
            "scenario_seed": case.scenario_seed,
            "attack": case.attack,
            "mode": mode,
            "time_step": metrics["time_step"],
            "hour": metrics["hour"],
            "clean_action": clean_action.tolist(),
            "action": np.asarray(action, dtype=int).tolist(),
            "switch_vector": switches,
            "load_status": load_status,
            "controller_metadata": metadata,
            "gae_detected": detection.get("detected", 0),
            "gae_score": detection.get("score", 0.0),
            "gae_threshold": detection.get("threshold", 0.0),
            "mitigation_applied": int(metadata.get("mitigation_applied", 0)),
            "selected_candidate_origin": metadata.get("selected_candidate_origin", ""),
        }
        row.update(metrics)
        row.update(physical_impact(clean_metrics, metrics))
        row.update(action_delta(clean_action, action, controller.experiment.num_switches))
        row["harmful_step"] = int(row["physical_impact_score"] > args.harm_threshold)
        row["paper_valid_step"] = int(step_row_is_valid(row, args))
        rows.append(row)
    return rows


def trajectory_summary(rows):
    valid_rows = [row for row in rows if int(row.get("paper_valid_step", 0)) == 1]
    return {
        "step_count": len(rows),
        "valid_step_count": len(valid_rows),
        "invalid_step_count": len(rows) - len(valid_rows),
        "mean_energy_kw": mean(row["energy_kw"] for row in valid_rows),
        "mean_energy_ratio": mean(row["energy_ratio"] for row in valid_rows),
        "mean_voltage_violation": mean(row["voltage_violation"] for row in valid_rows),
        "mean_reward": mean(row["reward"] for row in valid_rows),
        "mean_physical_impact_score": mean(row["physical_impact_score"] for row in valid_rows),
        "max_physical_impact_score": max_value(row["physical_impact_score"] for row in valid_rows),
        "mean_loads_served": mean(row["loads_served"] for row in valid_rows),
        "mean_loads_shed": mean(row["loads_shed"] for row in valid_rows),
    }


def summarize_case(case, rows, result):
    by_mode = {mode: [row for row in rows if row["mode"] == mode] for mode in ["clean_dynamic", "attacked_dynamic", "mitigated_dynamic"]}
    clean = trajectory_summary(by_mode["clean_dynamic"])
    attacked = trajectory_summary(by_mode["attacked_dynamic"])
    mitigated = trajectory_summary(by_mode["mitigated_dynamic"])
    energy_loss = clean["mean_energy_kw"] - attacked["mean_energy_kw"]
    recovered = mitigated["mean_energy_kw"] - attacked["mean_energy_kw"]
    impact_reduction = attacked["mean_physical_impact_score"] - mitigated["mean_physical_impact_score"]
    paper_valid_case = int(
        clean["step_count"] > 0
        and attacked["step_count"] > 0
        and mitigated["step_count"] > 0
        and clean["invalid_step_count"] == 0
        and attacked["invalid_step_count"] == 0
        and mitigated["invalid_step_count"] == 0
    )
    return {
        "system": "34bus",
        "target_method": case.target_method,
        "method": case.target_method,
        "paper_method_label": method_label(case.target_method),
        "case_id": case.case_id,
        "scenario_seed": case.scenario_seed,
        "attack": case.attack,
        "paper_valid_case": paper_valid_case,
        "clean_valid_step_count": clean["valid_step_count"],
        "attacked_valid_step_count": attacked["valid_step_count"],
        "mitigated_valid_step_count": mitigated["valid_step_count"],
        "clean_invalid_step_count": clean["invalid_step_count"],
        "attacked_invalid_step_count": attacked["invalid_step_count"],
        "mitigated_invalid_step_count": mitigated["invalid_step_count"],
        "gae_clean_score": result["clean_detection"]["score"],
        "gae_attacked_score": result["attacked_detection"]["score"],
        "gae_threshold": result["attacked_detection"]["threshold"],
        "gae_clean_alarm": result["clean_detection"]["detected"],
        "gae_attacked_detected": result["attacked_detection"]["detected"],
        "mitigation_applied": result["mitigation_metadata"].get("mitigation_applied", 0),
        "selected_candidate_origin": result["mitigation_metadata"].get("selected_candidate_origin", ""),
        "clean_mean_energy_kw": clean["mean_energy_kw"],
        "attacked_mean_energy_kw": attacked["mean_energy_kw"],
        "mitigated_mean_energy_kw": mitigated["mean_energy_kw"],
        "energy_loss_kw": energy_loss,
        "energy_recovered_kw": recovered,
        "energy_recovery_fraction": recovered / energy_loss if abs(energy_loss) > 1.0e-9 else 0.0,
        "clean_mean_energy_ratio": clean["mean_energy_ratio"],
        "attacked_mean_energy_ratio": attacked["mean_energy_ratio"],
        "mitigated_mean_energy_ratio": mitigated["mean_energy_ratio"],
        "clean_mean_voltage_violation": clean["mean_voltage_violation"],
        "attacked_mean_voltage_violation": attacked["mean_voltage_violation"],
        "mitigated_mean_voltage_violation": mitigated["mean_voltage_violation"],
        "attacked_mean_physical_impact_score": attacked["mean_physical_impact_score"],
        "mitigated_mean_physical_impact_score": mitigated["mean_physical_impact_score"],
        "physical_impact_reduction": impact_reduction,
        "physical_impact_reduction_fraction": (
            impact_reduction / attacked["mean_physical_impact_score"]
            if attacked["mean_physical_impact_score"] > 1.0e-9
            else 0.0
        ),
        "clean_mean_loads_served": clean["mean_loads_served"],
        "attacked_mean_loads_served": attacked["mean_loads_served"],
        "mitigated_mean_loads_served": mitigated["mean_loads_served"],
        "clean_mean_loads_shed": clean["mean_loads_shed"],
        "attacked_mean_loads_shed": attacked["mean_loads_shed"],
        "mitigated_mean_loads_shed": mitigated["mean_loads_shed"],
    }


def detection_summary(rows):
    groups = {}
    for row in rows:
        groups.setdefault(row["target_method"], []).append(row)
    summary = []
    for method, items in sorted(groups.items()):
        clean_items = [item for item in items if item["mode"] == "clean_dynamic"]
        attacked_items = [item for item in items if item["mode"] == "attacked_dynamic"]
        tp = sum(int(item["gae_detected"]) for item in attacked_items)
        fn = len(attacked_items) - tp
        fp = sum(int(item["gae_detected"]) for item in clean_items)
        tn = len(clean_items) - fp
        summary.append(
            {
                "target_method": method,
                "samples": len(clean_items) + len(attacked_items),
                "attacked_cases": len(attacked_items),
                "clean_cases": len(clean_items),
                "tp": tp,
                "tn": tn,
                "fp": fp,
                "fn": fn,
                "accuracy": (tp + tn) / max(len(clean_items) + len(attacked_items), 1),
                "precision": tp / max(tp + fp, 1),
                "recall_detection_rate": tp / max(tp + fn, 1),
                "false_positive_rate": fp / max(fp + tn, 1),
                "clean_alarm_rate": mean(item["gae_detected"] for item in clean_items),
                "attacked_detection_rate": mean(item["gae_detected"] for item in attacked_items),
                "mean_clean_score": mean(item["gae_score"] for item in clean_items),
                "mean_attacked_score": mean(item["gae_score"] for item in attacked_items),
                "threshold": mean(item["gae_threshold"] for item in items),
            }
        )
    return summary


def method_mitigation_summary(case_rows):
    groups = {}
    for row in case_rows:
        groups.setdefault(row["target_method"], []).append(row)
    summary = []
    for method, items in sorted(groups.items()):
        valid_items = [item for item in items if int(item.get("paper_valid_case", 0)) == 1]
        summary.append(
            {
                "target_method": method,
                "cases": len(items),
                "paper_valid_cases": len(valid_items),
                "paper_invalid_cases": len(items) - len(valid_items),
                "invalid_clean_step_count": sum(int(item.get("clean_invalid_step_count", 0)) for item in items),
                "invalid_attacked_step_count": sum(int(item.get("attacked_invalid_step_count", 0)) for item in items),
                "invalid_mitigated_step_count": sum(int(item.get("mitigated_invalid_step_count", 0)) for item in items),
                "gae_detection_rate": mean(item["gae_attacked_detected"] for item in items),
                "gae_clean_alarm_rate": mean(item["gae_clean_alarm"] for item in items),
                "mitigation_applied_rate": mean(item["mitigation_applied"] for item in items),
                "mean_clean_energy_kw": mean(item["clean_mean_energy_kw"] for item in valid_items),
                "mean_attacked_energy_kw": mean(item["attacked_mean_energy_kw"] for item in valid_items),
                "mean_mitigated_energy_kw": mean(item["mitigated_mean_energy_kw"] for item in valid_items),
                "mean_energy_loss_kw": mean(item["energy_loss_kw"] for item in valid_items),
                "mean_energy_recovered_kw": mean(item["energy_recovered_kw"] for item in valid_items),
                "mean_energy_recovery_fraction": mean(item["energy_recovery_fraction"] for item in valid_items),
                "mean_attacked_physical_impact_score": mean(
                    item["attacked_mean_physical_impact_score"] for item in valid_items
                ),
                "mean_mitigated_physical_impact_score": mean(
                    item["mitigated_mean_physical_impact_score"] for item in valid_items
                ),
                "mean_physical_impact_reduction_fraction": mean(
                    item["physical_impact_reduction_fraction"] for item in valid_items
                ),
                "mean_attacked_loads_shed": mean(item["attacked_mean_loads_shed"] for item in valid_items),
                "mean_mitigated_loads_shed": mean(item["mitigated_mean_loads_shed"] for item in valid_items),
            }
        )
    return summary


def main():
    args = parse_args()
    source_dir = resolve_path(args.source_dir)
    selected_path = source_dir / args.selected_file
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("source selected cases={}".format(selected_path), flush=True)
    print("output_dir={}".format(output_dir), flush=True)
    selected_rows = [row for row in read_rows(selected_path) if row.get("target_method") in set(args.methods)]
    selected_cases = [case_from_search_row(row) for row in selected_rows]
    print("selected cases loaded={}".format(len(selected_cases)), flush=True)

    print("training graph autoencoder on clean outage observations", flush=True)
    clean_obs = clean_training_observations(args)
    gae, history, clean_scores = train_graph_autoencoder(clean_obs, args)
    print(
        "gae threshold={:.6f} clean_score_mean={:.6f} clean_score_std={:.6f}".format(
            gae.threshold,
            gae.clean_score_mean,
            gae.clean_score_std,
        ),
        flush=True,
    )

    controllers = {method: make_controller(method, args) for method in args.methods}
    detection_rows = []
    comparison_rows = []
    case_summary_rows = []
    for index, (row, case) in enumerate(zip(selected_rows, selected_cases), start=1):
        controller = controllers[case.target_method]
        print(
            "mitigation replay {}/{} case={} method={}".format(
                index, len(selected_cases), case.case_id, case.target_method
            ),
            flush=True,
        )
        result = run_case(controller, row, case, gae, args)
        detection_rows.extend(detection_case_rows(case, result))
        case_rows = []
        for mode in ["clean_dynamic", "attacked_dynamic", "mitigated_dynamic"]:
            mode_rows = step_rows(controller, case, result, mode, args)
            comparison_rows.extend(mode_rows)
            case_rows.extend(mode_rows)
        summary = summarize_case(case, case_rows, result)
        summary["switch_changes_mitigated_vs_clean"] = int(
            np.sum(result["mitigated_action"][: controller.experiment.num_switches] != result["clean_action"][: controller.experiment.num_switches])
        )
        summary["load_changes_mitigated_vs_clean"] = int(
            np.sum(result["mitigated_action"][controller.experiment.num_switches :] != result["clean_action"][controller.experiment.num_switches :])
        )
        case_summary_rows.append(summary)
        print(
            "  detected={} clean={:.1f} attacked={:.1f} mitigated={:.1f} recovery={:.2f}".format(
                result["attacked_detection"]["detected"],
                summary["clean_mean_energy_kw"],
                summary["attacked_mean_energy_kw"],
                summary["mitigated_mean_energy_kw"],
                summary["energy_recovery_fraction"],
            ),
            flush=True,
        )

    paths = {
        "detection_cases": output_dir / "gae_detection_cases_34bus.csv",
        "comparison": output_dir / "gae_mitigation_comparison_34bus.csv",
        "case_summary": output_dir / "table_gae_mitigation_case_summary_34bus.csv",
        "detection_summary": output_dir / "table_gae_detection_summary_34bus.csv",
        "mitigation_summary": output_dir / "table_gae_mitigation_summary_34bus.csv",
        "training_history": output_dir / "gae_training_history_34bus.csv",
        "manifest": output_dir / "gae_mitigation_manifest.json",
        "notes": output_dir / "gae_mitigation_notes.md",
    }
    write_csv(detection_rows, paths["detection_cases"])
    write_csv(comparison_rows, paths["comparison"])
    write_csv(case_summary_rows, paths["case_summary"])
    write_csv(detection_summary(detection_rows), paths["detection_summary"])
    write_csv(method_mitigation_summary(case_summary_rows), paths["mitigation_summary"])
    write_csv(history, paths["training_history"])
    manifest = {
        "experiment": "IEEE 34-bus topology/status FDIA graph-autoencoder detection and mitigation",
        "source_selected_cases": str(selected_path),
        "output_dir": str(output_dir),
        "existing_impact_results_modified": False,
        "methods": args.methods,
        "selected_cases": len(selected_cases),
        "horizon": args.horizon,
        "gae_train_samples": len(clean_obs),
        "gae_epochs": args.gae_epochs,
        "gae_threshold": gae.threshold,
        "gae_threshold_quantile": args.gae_threshold_quantile,
        "mitigation": (
            "Detection-guided OpenDSS candidate screening. The attacked action is preserved unless "
            "the GAE detects an anomaly. When detected, candidates are evaluated on OpenDSS and the "
            "best energy/voltage/convergence objective is selected."
        ),
    }
    paths["manifest"].write_text(safe_json(manifest) + "\n")
    notes = [
        "# IEEE 34-Bus GAE Detection and Mitigation",
        "",
        "This extension does not overwrite the existing topology/status FDIA impact results.",
        "",
        "Detector: graph autoencoder trained only on clean outage observations.",
        "Anomaly score combines node-feature, adjacency, and action-mask reconstruction error.",
        "",
        "Mitigation: if the GAE detects an attack, switching/load actions are recomputed by",
        "OpenDSS-validated candidate screening. The saved clean action is not directly copied;",
        "a trusted-state controller recomputation and local/random candidates are physically",
        "evaluated and ranked by energy ratio minus voltage and convergence penalties.",
        "",
        "Important caveat: this is a detection-guided recovery study. It assumes a trusted",
        "reference/state-estimator channel is available for screening after attack detection.",
    ]
    paths["notes"].write_text("\n".join(notes) + "\n")

    for label, path in paths.items():
        print("wrote {}: {}".format(label, path), flush=True)


if __name__ == "__main__":
    main()
