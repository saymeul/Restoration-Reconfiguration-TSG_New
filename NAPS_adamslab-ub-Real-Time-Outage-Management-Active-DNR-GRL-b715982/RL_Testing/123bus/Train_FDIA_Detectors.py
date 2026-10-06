"""
Train multiple learning-based FDIA detectors from a generated dataset.

This script trains binary detectors (clean vs attacked) and multiclass
detectors (clean vs attack type). It uses only NumPy/PyTorch so it can run in
the existing grl-test environment.
"""

import argparse
import csv
import json
import pickle
from pathlib import Path

import numpy as np

from FDIA_Config import DEFAULT_DETECTOR_DIR, DEFAULT_FDIA_DATASET, resolve_local_path
from FDIA_Learning_Models import predict_detector_model, train_detector_model


MODEL_CHOICES = ["centroid", "knn", "linear_torch", "mlp_torch"]


def encode_labels(labels):
    label_names = np.array(sorted(set(labels)), dtype=object)
    index = {label: idx for idx, label in enumerate(label_names)}
    encoded = np.array([index[label] for label in labels], dtype=np.int64)
    return encoded, label_names


def stratified_split(y, test_size, random_state):
    rng = np.random.default_rng(random_state)
    train_indices = []
    test_indices = []
    for cls in np.unique(y):
        cls_indices = np.where(y == cls)[0]
        rng.shuffle(cls_indices)
        if len(cls_indices) == 1:
            train_indices.extend(cls_indices)
            continue
        n_test = max(1, int(round(len(cls_indices) * test_size)))
        n_test = min(n_test, len(cls_indices) - 1)
        test_indices.extend(cls_indices[:n_test])
        train_indices.extend(cls_indices[n_test:])

    rng.shuffle(train_indices)
    rng.shuffle(test_indices)
    return np.array(train_indices, dtype=np.int64), np.array(test_indices, dtype=np.int64)


def confusion_matrix_np(y_true, y_pred, num_classes):
    matrix = np.zeros((num_classes, num_classes), dtype=int)
    for actual, predicted in zip(y_true, y_pred):
        matrix[int(actual), int(predicted)] += 1
    return matrix


def metrics_from_matrix(matrix):
    total = matrix.sum()
    accuracy = float(np.trace(matrix) / total) if total else 0.0
    supports = matrix.sum(axis=1)
    precisions = []
    recalls = []
    f1s = []

    for idx in range(matrix.shape[0]):
        tp = matrix[idx, idx]
        fp = matrix[:, idx].sum() - tp
        fn = matrix[idx, :].sum() - tp
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        precisions.append(precision)
        recalls.append(recall)
        f1s.append(f1)

    macro_f1 = float(np.mean(f1s)) if f1s else 0.0
    weighted_f1 = float(np.average(f1s, weights=supports)) if supports.sum() else 0.0
    return accuracy, macro_f1, weighted_f1, precisions, recalls, f1s


def report_text(matrix, label_names):
    accuracy, macro_f1, weighted_f1, precisions, recalls, f1s = metrics_from_matrix(matrix)
    lines = [
        "label,precision,recall,f1,support",
    ]
    supports = matrix.sum(axis=1)
    for idx, label in enumerate(label_names):
        lines.append(
            f"{label},{precisions[idx]:.6f},{recalls[idx]:.6f},{f1s[idx]:.6f},{int(supports[idx])}"
        )
    lines.append(f"accuracy,{accuracy:.6f}")
    lines.append(f"macro_f1,{macro_f1:.6f}")
    lines.append(f"weighted_f1,{weighted_f1:.6f}")
    return "\n".join(lines) + "\n"


def save_confusion_matrix(path, matrix, labels):
    with Path(path).open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["actual\\predicted", *labels])
        for label, row in zip(labels, matrix):
            writer.writerow([label, *row.tolist()])


def train_task(X, labels_raw, task_name, model_names, output_dir, test_size, random_state, epochs):
    y, label_names = encode_labels(labels_raw)
    train_idx, test_idx = stratified_split(y, test_size, random_state)
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    rows = []
    task_dir = output_dir / task_name
    task_dir.mkdir(parents=True, exist_ok=True)

    for model_name in model_names:
        print(f"Training {task_name}/{model_name}...")
        model = train_detector_model(model_name, X_train, y_train, random_state=random_state, epochs=epochs)
        y_pred = predict_detector_model(model, X_test)

        matrix = confusion_matrix_np(y_test, y_pred, len(label_names))
        accuracy, macro_f1, weighted_f1, _, _, _ = metrics_from_matrix(matrix)

        bundle = {
            "model": model,
            "label_names": label_names,
            "task": task_name,
            "model_name": model_name,
        }
        model_path = task_dir / f"{model_name}.pkl"
        with model_path.open("wb") as handle:
            pickle.dump(bundle, handle)

        (task_dir / f"{model_name}_classification_report.txt").write_text(report_text(matrix, label_names))
        save_confusion_matrix(task_dir / f"{model_name}_confusion_matrix.csv", matrix, label_names)

        rows.append(
            {
                "task": task_name,
                "model": model_name,
                "accuracy": accuracy,
                "macro_f1": macro_f1,
                "weighted_f1": weighted_f1,
                "model_path": str(model_path),
            }
        )

    return rows


def parse_args():
    parser = argparse.ArgumentParser(description="Train learning-based 123-bus FDIA detectors")
    parser.add_argument(
        "--dataset",
        default=str(DEFAULT_FDIA_DATASET),
        help="Dataset produced by Generate_FDIA_Dataset.py",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_DETECTOR_DIR),
        help="Directory for trained models and reports",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=MODEL_CHOICES,
        choices=MODEL_CHOICES,
        help="Models to train",
    )
    parser.add_argument("--test-size", type=float, default=0.30)
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--epochs", type=int, default=80, help="Epochs for PyTorch models")
    return parser.parse_args()


def main():
    args = parse_args()
    dataset_path = resolve_local_path(args.dataset)
    dataset = np.load(dataset_path, allow_pickle=True)
    X = dataset["X"].astype(np.float32)
    y_attack = dataset["y_attack"].astype(str)
    y_binary = np.where(dataset["y_binary"].astype(int) == 1, "attacked", "clean")

    output_dir = resolve_local_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    rows.extend(train_task(X, y_binary, "binary", args.models, output_dir, args.test_size, args.seed, args.epochs))
    rows.extend(train_task(X, y_attack, "multiclass", args.models, output_dir, args.test_size, args.seed, args.epochs))

    summary_path = output_dir / "model_summary.csv"
    with summary_path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["task", "model", "accuracy", "macro_f1", "weighted_f1", "model_path"],
        )
        writer.writeheader()
        writer.writerows(rows)

    metadata = {
        "dataset": str(dataset_path),
        "num_samples": int(X.shape[0]),
        "num_features": int(X.shape[1]),
        "models": args.models,
        "summary_path": str(summary_path),
    }
    (output_dir / "training_metadata.json").write_text(json.dumps(metadata, indent=2))
    print(f"Saved learning-detector summary: {summary_path}")


if __name__ == "__main__":
    main()
