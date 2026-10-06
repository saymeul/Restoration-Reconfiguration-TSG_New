"""Graph-learning detector for IEEE 34-bus stealthy a=Hc FDIA.

This script trains a separate graph-based FDIA detector. It does not reuse the
GCAPS restoration policy as a detector. Instead, it builds bus-level graph
features from IEEE 34-bus measurements and trains a compact GCN classifier to
distinguish clean observations from stealth a=Hc measurement attacks.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from time import perf_counter

import numpy as np
import torch

from FDIA_ExperimentCore import RestorationExperiment, resolve_path, safe_json, write_csv
from Run_FDIA_StealthHCDetection34 import (
    MEASUREMENT_KEYS,
    add_bdd_summary,
    binary_metrics,
    build_dataset_rows,
    collect_clean_measurements,
    fit_measurement_subspace,
    stable_random_seeds,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="IEEE 34-bus graph-learning detector for stealth a=Hc FDIA."
    )
    parser.add_argument("--seed", type=int, default=9042026)
    parser.add_argument("--calibration-samples", type=int, default=160)
    parser.add_argument("--train-samples", type=int, default=240)
    parser.add_argument("--test-samples", type=int, default=120)
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
    parser.add_argument("--hidden-dim", type=int, default=48)
    parser.add_argument("--epochs", type=int, default=180)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=1.0e-3)
    parser.add_argument("--weight-decay", type=float, default=1.0e-4)
    parser.add_argument("--dropout", type=float, default=0.15)
    parser.add_argument("--decision-threshold", type=float, default=0.50)
    parser.add_argument(
        "--output-dir",
        default="paper_results/naps_34bus/stealth_hc_graph_detector",
        help="Output directory under RL_Testing unless absolute.",
    )
    return parser.parse_args()


class GraphFDIADetector(torch.nn.Module):
    def __init__(self, input_dim, hidden_dim, dropout):
        super().__init__()
        self.gcn1 = torch.nn.Linear(input_dim, hidden_dim)
        self.gcn2 = torch.nn.Linear(hidden_dim, hidden_dim)
        self.dropout = torch.nn.Dropout(float(dropout))
        self.classifier = torch.nn.Sequential(
            torch.nn.Linear(2 * hidden_dim, hidden_dim),
            torch.nn.ReLU(),
            torch.nn.Dropout(float(dropout)),
            torch.nn.Linear(hidden_dim, 1),
        )

    def forward(self, x, adjacency_norm):
        h = torch.matmul(adjacency_norm, x)
        h = torch.relu(self.gcn1(h))
        h = self.dropout(h)
        h = torch.matmul(adjacency_norm, h)
        h = torch.relu(self.gcn2(h))
        mean_pool = torch.mean(h, dim=1)
        max_pool = torch.max(h, dim=1).values
        graph_embedding = torch.cat([mean_pool, max_pool], dim=1)
        return self.classifier(graph_embedding).squeeze(-1)


def normalized_adjacency(obs):
    adjacency = np.asarray(obs["Adjacency"], dtype=float)
    adjacency = np.where(np.isfinite(adjacency), adjacency, 0.0)
    adjacency = np.maximum(adjacency, adjacency.T)
    adjacency = adjacency + np.eye(adjacency.shape[0], dtype=float)
    degree = np.sum(adjacency, axis=1)
    degree[degree <= 1.0e-12] = 1.0
    inv_sqrt = 1.0 / np.sqrt(degree)
    return (inv_sqrt[:, None] * adjacency * inv_sqrt[None, :]).astype(np.float32)


def edge_indices_from_experiment(experiment):
    node_list = list(experiment.init_module.node_list)
    node_index = {str(node): index for index, node in enumerate(node_list)}
    edge_list = list(experiment.init_module.edge_list)
    edge_indices = []
    for edge in edge_list:
        u, v = str(edge[0]), str(edge[1])
        if u in node_index and v in node_index:
            edge_indices.append((node_index[u], node_index[v]))
    return node_list, edge_indices


def graph_features_from_observation(obs, edge_indices):
    voltages = np.asarray(obs["NodeFeat(BusVoltage)"], dtype=float)
    voltages = np.nan_to_num(voltages, nan=0.0, posinf=0.0, neginf=0.0)
    n_nodes = int(voltages.shape[0])
    flows = np.asarray(obs["EdgeFeat(Branchflow)"], dtype=float).reshape(-1)
    flows = np.nan_to_num(flows, nan=0.0, posinf=0.0, neginf=0.0)

    incident_sum = np.zeros(n_nodes, dtype=float)
    incident_max = np.zeros(n_nodes, dtype=float)
    incident_count = np.zeros(n_nodes, dtype=float)
    for edge_idx, (u, v) in enumerate(edge_indices):
        if edge_idx >= flows.size:
            break
        value = abs(float(flows[edge_idx]))
        for node in (u, v):
            incident_sum[node] += value
            incident_max[node] = max(incident_max[node], value)
            incident_count[node] += 1.0
    incident_mean = incident_sum / np.maximum(incident_count, 1.0)

    energy = float(np.asarray(obs["EnergySupp"], dtype=float).reshape(-1)[0])
    energy_feature = np.full(n_nodes, energy, dtype=float)
    active_phase_fraction = np.mean(voltages > 0.01, axis=1)
    node_degree = incident_count / max(float(np.max(incident_count)), 1.0)

    features = np.column_stack(
        [
            voltages,
            incident_sum,
            incident_mean,
            incident_max,
            energy_feature,
            active_phase_fraction,
            node_degree,
        ]
    )
    return features.astype(np.float32)


def graph_dataset_from_pairs(pair_records, edge_indices):
    features = []
    labels = []
    case_ids = []
    scenario_seeds = []
    for pair in pair_records:
        features.append(graph_features_from_observation(pair["clean_obs"], edge_indices))
        labels.append(0)
        case_ids.append(pair["case_id"])
        scenario_seeds.append(int(pair["scenario_seed"]))
        features.append(graph_features_from_observation(pair["attacked_obs"], edge_indices))
        labels.append(1)
        case_ids.append(pair["case_id"])
        scenario_seeds.append(int(pair["scenario_seed"]))
    return (
        np.stack(features).astype(np.float32),
        np.array(labels, dtype=np.int64),
        case_ids,
        scenario_seeds,
    )


def standardize_graph_features(X_train, X_test):
    mean = np.mean(X_train, axis=(0, 1), keepdims=True)
    std = np.std(X_train, axis=(0, 1), keepdims=True)
    std[std < 1.0e-6] = 1.0
    return ((X_train - mean) / std).astype(np.float32), ((X_test - mean) / std).astype(np.float32), mean, std


def train_graph_detector(X_train, y_train, X_test, y_test, adjacency_norm, args):
    torch.manual_seed(int(args.seed))
    np.random.seed(int(args.seed) % (2**32 - 1))
    device = torch.device("cpu")
    model = GraphFDIADetector(
        input_dim=int(X_train.shape[-1]),
        hidden_dim=int(args.hidden_dim),
        dropout=float(args.dropout),
    ).to(device)
    adjacency_tensor = torch.as_tensor(adjacency_norm, dtype=torch.float32, device=device)
    X_train_tensor = torch.as_tensor(X_train, dtype=torch.float32, device=device)
    y_train_tensor = torch.as_tensor(y_train.astype(np.float32), dtype=torch.float32, device=device)
    X_test_tensor = torch.as_tensor(X_test, dtype=torch.float32, device=device)
    y_test_tensor = torch.as_tensor(y_test.astype(np.float32), dtype=torch.float32, device=device)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=float(args.learning_rate),
        weight_decay=float(args.weight_decay),
    )
    loss_fn = torch.nn.BCEWithLogitsLoss()
    batch_size = max(1, int(args.batch_size))
    history = []
    start = perf_counter()

    for epoch in range(int(args.epochs)):
        model.train()
        order = torch.randperm(X_train_tensor.shape[0])
        losses = []
        for start_idx in range(0, len(order), batch_size):
            batch_idx = order[start_idx : start_idx + batch_size]
            logits = model(X_train_tensor[batch_idx], adjacency_tensor)
            loss = loss_fn(logits, y_train_tensor[batch_idx])
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach().cpu().item()))
        if epoch == 0 or epoch == int(args.epochs) - 1 or (epoch + 1) % 25 == 0:
            model.eval()
            with torch.no_grad():
                train_logits = model(X_train_tensor, adjacency_tensor)
                test_logits = model(X_test_tensor, adjacency_tensor)
                train_loss = float(loss_fn(train_logits, y_train_tensor).cpu().item())
                test_loss = float(loss_fn(test_logits, y_test_tensor).cpu().item())
            history.append(
                {
                    "epoch": int(epoch + 1),
                    "mean_batch_loss": float(np.mean(losses)) if losses else 0.0,
                    "train_loss": train_loss,
                    "test_loss": test_loss,
                }
            )

    model.eval()
    with torch.no_grad():
        logits = model(X_test_tensor, adjacency_tensor)
        probabilities = torch.sigmoid(logits).cpu().numpy().astype(float)
        train_logits = model(X_train_tensor, adjacency_tensor)
        train_probabilities = torch.sigmoid(train_logits).cpu().numpy().astype(float)
    runtime = perf_counter() - start
    return model, probabilities, train_probabilities, history, runtime


def add_predictions_to_rows(rows_test, probabilities, threshold):
    for row, probability in zip(rows_test, probabilities):
        prediction = int(float(probability) >= float(threshold))
        row["graph_detector_probability"] = float(probability)
        row["graph_detector_detected"] = int(prediction)
        row["graph_detector_predicted_label"] = "stealth_hc" if prediction else "clean"


def write_manifest(output_dir, args, node_list, edge_indices, summary_rows, history, feature_mean, feature_std):
    manifest = {
        "experiment": "IEEE 34-bus graph-learning detector for stealth a=Hc FDIA",
        "system": "34bus",
        "attack": "stealth_hc",
        "restoration_policy_used_as_detector": False,
        "detector_type": "separate graph convolutional FDIA classifier",
        "measurement_keys": MEASUREMENT_KEYS,
        "node_count": len(node_list),
        "edge_count": len(edge_indices),
        "node_feature_description": [
            "phase A/B/C bus voltage",
            "incident branch-flow sum",
            "incident branch-flow mean",
            "incident branch-flow max",
            "energy supplied repeated at each node",
            "active phase fraction",
            "normalized node degree",
        ],
        "subspace_rank": int(args.subspace_rank),
        "train_pairs": int(args.train_samples),
        "test_pairs": int(args.test_samples),
        "epochs": int(args.epochs),
        "hidden_dim": int(args.hidden_dim),
        "decision_threshold": float(args.decision_threshold),
        "summary": summary_rows,
        "training_history": history,
        "feature_mean": np.asarray(feature_mean).reshape(-1).tolist(),
        "feature_std": np.asarray(feature_std).reshape(-1).tolist(),
        "important_note": (
            "This is a detector, not the GCAPS/GRL restoration controller. "
            "It evaluates whether graph representation learning improves detection "
            "of stealth a=Hc measurement attacks that bypass projection-residual BDD."
        ),
    }
    path = output_dir / "graph_stealth_hc_detection_manifest.json"
    path.write_text(json.dumps(json.loads(safe_json(manifest)), indent=2) + "\n")
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

    rows_train, _flat_train, y_train_flat, pairs_train = build_dataset_rows(
        experiment,
        train_seeds,
        "train",
        measurement_map,
        subspace,
        rng,
        args,
    )
    rows_test, _flat_test, y_test_flat, pairs_test = build_dataset_rows(
        experiment,
        test_seeds,
        "test",
        measurement_map,
        subspace,
        rng,
        args,
    )

    node_list, edge_indices = edge_indices_from_experiment(experiment)
    X_train_graph, y_train_graph, _train_case_ids, _train_seeds = graph_dataset_from_pairs(
        pairs_train,
        edge_indices,
    )
    X_test_graph, y_test_graph, _test_case_ids, _test_seeds = graph_dataset_from_pairs(
        pairs_test,
        edge_indices,
    )
    X_train_graph, X_test_graph, feature_mean, feature_std = standardize_graph_features(
        X_train_graph,
        X_test_graph,
    )

    adjacency_norm = normalized_adjacency(calibration_obs[0][1])
    model, probabilities, train_probabilities, history, runtime = train_graph_detector(
        X_train_graph,
        y_train_graph,
        X_test_graph,
        y_test_graph,
        adjacency_norm,
        args,
    )
    predictions = (probabilities >= float(args.decision_threshold)).astype(int)
    train_predictions = (train_probabilities >= float(args.decision_threshold)).astype(int)

    add_predictions_to_rows(rows_test, probabilities, args.decision_threshold)

    summary_rows = add_bdd_summary(rows_test, y_test_flat)
    graph_summary = binary_metrics("graph_learning_gcn_detector", y_test_graph, predictions)
    graph_summary.update(
        {
            "family": "graph_learning",
            "feature_mode": "bus_voltage_incident_flow_graph",
            "model": "two_layer_gcn_global_pool",
            "train_samples": int(X_train_graph.shape[0]),
            "test_samples": int(X_test_graph.shape[0]),
            "runtime_sec": float(runtime),
            "train_accuracy": binary_metrics(
                "graph_learning_gcn_detector_train",
                y_train_graph,
                train_predictions,
            )["accuracy"],
        }
    )
    summary_rows.append(graph_summary)

    cases_path = output_dir / "graph_stealth_hc_detection_cases_34bus.csv"
    summary_path = output_dir / "table_graph_stealth_hc_detection_summary_34bus.csv"
    history_path = output_dir / "graph_stealth_hc_training_history_34bus.csv"
    model_path = output_dir / "graph_stealth_hc_detector_34bus.pt"
    all_rows = rows_train + rows_test
    write_csv(all_rows, cases_path)
    write_csv(summary_rows, summary_path)
    write_csv(history, history_path)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "feature_mean": feature_mean,
            "feature_std": feature_std,
            "node_list": node_list,
            "edge_indices": edge_indices,
            "args": vars(args),
        },
        model_path,
    )
    manifest_path = write_manifest(
        output_dir,
        args,
        node_list,
        edge_indices,
        summary_rows,
        history,
        feature_mean,
        feature_std,
    )

    print("wrote {}".format(cases_path), flush=True)
    print("wrote {}".format(summary_path), flush=True)
    print("wrote {}".format(history_path), flush=True)
    print("wrote {}".format(model_path), flush=True)
    print("wrote {}".format(manifest_path), flush=True)


if __name__ == "__main__":
    main()
