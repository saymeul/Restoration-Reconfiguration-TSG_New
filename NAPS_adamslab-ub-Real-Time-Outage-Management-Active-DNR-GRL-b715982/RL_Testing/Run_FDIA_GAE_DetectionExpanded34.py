"""Expanded IEEE 34-bus topology/status FDIA detection evaluation.

This runner is detection-only.  It does not change the existing impact or
mitigation results.  It trains the same graph-autoencoder detector used by the
mitigation extension on clean outage observations, then evaluates paired clean
and topology/status-FDIA observations over randomized IEEE 34-bus scenarios for
GCAPS/GRL, MLP, and BPSO.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from FDIA_ExperimentCore import resolve_path, safe_json, write_csv
from Run_FDIA_GAE_Mitigation34 import clean_training_observations, gae_score, train_graph_autoencoder
from Run_FDIA_TargetedDynamicImpact34_NoMitigation import (
    METHOD_LABELS,
    TargetedDynamicCase,
    build_policy_observation,
    decide,
    make_controller,
    seeded_random_observation,
    targeted_attack_parameters,
)


METHOD_ORDER = ["GRL", "MLP", "BPSO"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Expanded graph-autoencoder topology/status FDIA detection evaluation for IEEE 34-bus."
    )
    parser.add_argument("--output-dir", default="paper_results/naps_34bus/topology_status_gae_detection_expanded")
    parser.add_argument("--methods", nargs="+", default=METHOD_ORDER, choices=METHOD_ORDER)
    parser.add_argument("--samples-per-method", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260611)
    parser.add_argument("--attack", default="topology_drop", choices=["topology_drop"])
    parser.add_argument("--gae-train-samples", type=int, default=240)
    parser.add_argument("--gae-val-fraction", type=float, default=0.25)
    parser.add_argument("--gae-epochs", type=int, default=80)
    parser.add_argument("--gae-hidden-dim", type=int, default=32)
    parser.add_argument("--gae-latent-dim", type=int, default=16)
    parser.add_argument("--gae-learning-rate", type=float, default=1.0e-3)
    parser.add_argument("--gae-threshold-quantile", type=float, default=0.95)
    parser.add_argument("--bpso-particles", type=int, default=8)
    parser.add_argument("--bpso-iterations", type=int, default=8)
    parser.add_argument("--bpso-seed", type=int, default=5157)
    parser.add_argument("--bpso-load-weight-gain", type=float, default=0.20)
    parser.add_argument("--decision-mask-scope", default="switch_and_load")
    parser.add_argument("--decision-mask-min-fraction", type=float, default=0.20)
    parser.add_argument("--decision-mask-max-fraction", type=float, default=0.70)
    parser.add_argument("--no-decision-channel-projection", action="store_true")
    return parser.parse_args()


def method_label(method):
    if method == "GRL":
        return "GCAPS/GRL"
    return METHOD_LABELS.get(method, method)


def safe_div(numerator, denominator):
    return float(numerator) / float(denominator) if denominator else 0.0


def f1_score(precision, recall):
    return safe_div(2.0 * precision * recall, precision + recall)


def detection_summary(rows):
    summary = []
    for method in [item for item in METHOD_ORDER if item in {row["target_method"] for row in rows}]:
        method_rows = [row for row in rows if row["target_method"] == method]
        summary.append(metrics_row(method_label(method), method_rows))
    summary.append(metrics_row("Overall", rows))
    return summary


def metrics_row(label, rows):
    tp = sum(1 for row in rows if int(row["expected_attack"]) == 1 and int(row["gae_detected"]) == 1)
    tn = sum(1 for row in rows if int(row["expected_attack"]) == 0 and int(row["gae_detected"]) == 0)
    fp = sum(1 for row in rows if int(row["expected_attack"]) == 0 and int(row["gae_detected"]) == 1)
    fn = sum(1 for row in rows if int(row["expected_attack"]) == 1 and int(row["gae_detected"]) == 0)
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    specificity = safe_div(tn, tn + fp)
    accuracy = safe_div(tp + tn, tp + tn + fp + fn)
    f1 = f1_score(precision, recall)
    return {
        "Method": label,
        "Clean Samples": tn + fp,
        "Attack Samples": tp + fn,
        "TP": tp,
        "TN": tn,
        "FP": fp,
        "FN": fn,
        "Accuracy": accuracy,
        "Precision": precision,
        "Recall": recall,
        "F1-score": f1,
        "Specificity": specificity,
    }


def make_random_case(method, sample_index, scenario_seed, rng, args):
    attack_kwargs, decision_kwargs = targeted_attack_parameters(args.attack, rng, args, method)
    return TargetedDynamicCase(
        case_id="E{}_{}_{:04d}_seed{}".format(method.lower(), args.attack.replace("_", ""), sample_index, scenario_seed),
        target_method=method,
        source_trial=sample_index,
        scenario_seed=scenario_seed,
        attack=args.attack,
        attack_kwargs=attack_kwargs,
        decision_kwargs=decision_kwargs,
    )


def append_detection_row(rows, case, mode, expected_attack, detection, attack_metadata=None):
    rows.append(
        {
            "system": "34bus",
            "target_method": case.target_method,
            "paper_method_label": method_label(case.target_method),
            "case_id": case.case_id,
            "sample_index": case.source_trial,
            "scenario_seed": case.scenario_seed,
            "attack": case.attack if expected_attack else "clean",
            "mode": mode,
            "expected_attack": int(expected_attack),
            "gae_detected": int(detection["detected"]),
            "gae_score": float(detection["score"]),
            "gae_feature_reconstruction_error": float(detection["feature_reconstruction_error"]),
            "gae_adjacency_reconstruction_error": float(detection["adjacency_reconstruction_error"]),
            "gae_action_mask_reconstruction_error": float(detection["action_mask_reconstruction_error"]),
            "gae_threshold": float(detection["threshold"]),
            "attack_kwargs_json": safe_json(case.attack_kwargs if expected_attack else {}),
            "decision_attack_kwargs_json": safe_json(case.decision_kwargs if expected_attack else {}),
            "attack_metadata_json": safe_json(attack_metadata or {}),
        }
    )


def evaluate_method(method, gae, args):
    controller = make_controller(method, args)
    rng = np.random.default_rng(int(args.seed) + 1009 * (METHOD_ORDER.index(method) + 1))
    rows = []
    for sample_index in range(int(args.samples_per_method)):
        scenario_seed = int(rng.integers(0, 2**31 - 1))
        case = make_random_case(method, sample_index, scenario_seed, rng, args)
        true_obs = seeded_random_observation(controller.experiment, scenario_seed)
        clean_action, _policy_ms, _metadata = decide(controller, true_obs, case, "expanded_detection_clean")
        policy_obs, attack_metadata = build_policy_observation(true_obs, clean_action, case, controller, args)

        clean_detection = gae_score(gae, true_obs)
        attacked_detection = gae_score(gae, policy_obs)
        append_detection_row(rows, case, "clean_outage_only", 0, clean_detection)
        append_detection_row(rows, case, "topology_status_fdia", 1, attacked_detection, attack_metadata)

        if (sample_index + 1) % 20 == 0 or sample_index + 1 == int(args.samples_per_method):
            print("{} detection samples {}/{}".format(method, sample_index + 1, int(args.samples_per_method)), flush=True)
    return rows


def write_publication_table(path, rows):
    fieldnames = [
        "Method",
        "Clean Samples",
        "Attack Samples",
        "TP",
        "TN",
        "FP",
        "FN",
        "Accuracy",
        "Precision",
        "Recall",
        "F1-score",
        "Specificity",
    ]
    with Path(path).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main():
    args = parse_args()
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("output_dir={}".format(output_dir), flush=True)
    print("training expanded-detection GAE on clean outage observations", flush=True)
    clean_obs = clean_training_observations(args)
    gae, history, clean_scores = train_graph_autoencoder(clean_obs, args)
    print(
        "gae threshold={:.6f} clean_score_mean={:.6f} clean_score_std={:.6f}".format(
            gae.threshold, gae.clean_score_mean, gae.clean_score_std
        ),
        flush=True,
    )

    rows = []
    for method in args.methods:
        rows.extend(evaluate_method(method, gae, args))

    summary = detection_summary(rows)
    paths = {
        "cases": output_dir / "expanded_gae_detection_cases_34bus.csv",
        "summary": output_dir / "table_expanded_gae_detection_publication_34bus.csv",
        "training_history": output_dir / "expanded_gae_training_history_34bus.csv",
        "manifest": output_dir / "expanded_gae_detection_manifest.json",
    }
    write_csv(rows, paths["cases"])
    write_publication_table(paths["summary"], summary)
    write_csv(history, paths["training_history"])
    manifest = {
        "experiment": "Expanded IEEE 34-bus topology/status FDIA graph-autoencoder detection evaluation",
        "attack": args.attack,
        "methods": args.methods,
        "samples_per_method": args.samples_per_method,
        "clean_samples_total": int(args.samples_per_method) * len(args.methods),
        "attack_samples_total": int(args.samples_per_method) * len(args.methods),
        "gae_train_samples": len(clean_obs),
        "gae_epochs": args.gae_epochs,
        "gae_threshold": gae.threshold,
        "gae_threshold_quantile": args.gae_threshold_quantile,
        "clean_score_mean": gae.clean_score_mean,
        "clean_score_std": gae.clean_score_std,
        "output_dir": str(output_dir),
    }
    paths["manifest"].write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    for name, path in paths.items():
        print("wrote {}: {}".format(name, path), flush=True)
    for row in summary:
        print(row, flush=True)


if __name__ == "__main__":
    main()
