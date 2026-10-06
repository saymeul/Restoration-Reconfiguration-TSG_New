"""
Detector suite for FDIA-aware GRL restoration experiments.

Each detector produces its own report. A fused report is then passed to the
GRL mitigation layer so restoration actions can use both model-based BDD
evidence and learning-based attack evidence.
"""

import pickle
from pathlib import Path

from FDIA_Common import detect_fdia
from FDIA_Features import DEFAULT_FEATURE_KEYS, observation_to_feature_vector, residuals_to_feature_vector
from FDIA_Learning_Models import predict_detector_model


LEARNING_ATTACK_TO_SYNTHETIC_METRIC = {
    "voltage_masking": "voltage_learning_vote",
    "branchflow_hiding": "branchflow_learning_vote",
    "energy_inflation": "energy_learning_vote",
    "topology_drop": "topology_learning_vote",
    "attacked": "learning_attack_vote",
}


def load_learning_detectors(detector_dir, tasks=None, model_names=None):
    detector_dir = Path(detector_dir)
    tasks = tasks or ["binary", "multiclass"]
    model_names = model_names or ["centroid", "knn", "linear_torch", "mlp_torch"]

    detectors = []
    for task in tasks:
        for model_name in model_names:
            model_path = detector_dir / task / f"{model_name}.pkl"
            if not model_path.exists():
                continue
            with model_path.open("rb") as handle:
                bundle = pickle.load(handle)
            detectors.append(
                {
                    "task": task,
                    "model_name": model_name,
                    "path": str(model_path),
                    "bundle": bundle,
                }
            )
    return detectors


def _learning_label_to_report(detector, label):
    task = detector["task"]
    detected = label != "clean"
    predicted_attack = "unknown" if task == "binary" and detected else label
    synthetic_metric = LEARNING_ATTACK_TO_SYNTHETIC_METRIC.get(
        label if task == "multiclass" else "attacked" if detected else "clean"
    )

    return {
        "detector": f"learning_{task}_{detector['model_name']}",
        "family": "learning",
        "task": task,
        "model": detector["model_name"],
        "detected": bool(detected),
        "predicted_label": label,
        "predicted_attack": predicted_attack,
        "synthetic_channel": synthetic_metric,
        "score": 1.0 if detected else 0.0,
        "model_path": detector["path"],
    }


def _feature_vector_for_detector(obs, detector, feature_keys=None, bdd_report=None):
    bundle = detector["bundle"]
    feature_mode = bundle.get("feature_mode", "observation")
    if feature_mode == "bdd_residuals":
        detector_feature_keys = bundle.get("feature_keys") or feature_keys
        residuals = (bdd_report or {}).get("residuals", {})
        return residuals_to_feature_vector(residuals, detector_feature_keys).reshape(1, -1)

    detector_feature_keys = bundle.get("feature_keys") or feature_keys or DEFAULT_FEATURE_KEYS
    return observation_to_feature_vector(obs, detector_feature_keys).reshape(1, -1)


def run_learning_detectors(obs, learning_detectors, feature_keys=None, bdd_report=None):
    if not learning_detectors:
        return []

    reports = []
    for detector in learning_detectors:
        bundle = detector["bundle"]
        X = _feature_vector_for_detector(obs, detector, feature_keys=feature_keys, bdd_report=bdd_report)
        pred = predict_detector_model(bundle["model"], X)
        label_names = bundle["label_names"]
        label = str(label_names[int(pred[0])])
        reports.append(_learning_label_to_report(detector, label))
    return reports


def fuse_detector_reports(bdd_report, learning_reports, min_learning_vote_fraction=0.50):
    detected_channels = list(bdd_report.get("detected_channels", []))
    learning_detected_channels = []
    learning_raw_detected_channels = []
    learning_predicted_attacks = []
    learning_detected_count = int(sum(report["detected"] for report in learning_reports))
    learning_detector_count = int(len(learning_reports))
    learning_vote_fraction = (
        float(learning_detected_count / learning_detector_count) if learning_detector_count else 0.0
    )
    learning_detected = learning_vote_fraction >= float(min_learning_vote_fraction)
    synthetic_channel_counts = {}

    for report in learning_reports:
        if not report["detected"]:
            continue
        synthetic_channel = report.get("synthetic_channel")
        if synthetic_channel:
            synthetic_channel_counts[synthetic_channel] = synthetic_channel_counts.get(synthetic_channel, 0) + 1
            if synthetic_channel not in learning_raw_detected_channels:
                learning_raw_detected_channels.append(synthetic_channel)
        predicted_attack = report.get("predicted_attack", "unknown")
        if predicted_attack not in learning_predicted_attacks:
            learning_predicted_attacks.append(predicted_attack)

    for synthetic_channel, count in synthetic_channel_counts.items():
        channel_vote_fraction = count / learning_detector_count if learning_detector_count else 0.0
        if channel_vote_fraction < min_learning_vote_fraction:
            continue
        if synthetic_channel not in detected_channels:
            detected_channels.append(synthetic_channel)
        learning_detected_channels.append(synthetic_channel)

    return {
        "detected": bool(bdd_report.get("detected", False) or learning_detected),
        "score": float(max(float(bdd_report.get("score", 0.0)), learning_vote_fraction)),
        "detected_channels": detected_channels,
        "thresholds": dict(bdd_report.get("thresholds", {})),
        "residuals": {
            "bdd_residuals": bdd_report.get("residuals", {}),
            "learning_vote_fraction": learning_vote_fraction,
            "learning_vote_threshold": float(min_learning_vote_fraction),
            "learning_detected_count": learning_detected_count,
            "learning_detector_count": learning_detector_count,
            "learning_predicted_attacks": learning_predicted_attacks,
            "learning_detected_channels": learning_detected_channels,
            "learning_raw_detected_channels": learning_raw_detected_channels,
        },
        "bdd_report": bdd_report,
        "learning_reports": learning_reports,
        "learning_detected": bool(learning_detected),
        "learning_vote_fraction": learning_vote_fraction,
        "learning_vote_threshold": float(min_learning_vote_fraction),
        "learning_any_detected": bool(learning_detected_count > 0),
        "learning_detected_count": learning_detected_count,
        "learning_detector_count": learning_detector_count,
        "learning_predicted_attacks": learning_predicted_attacks,
        "learning_detected_channels": learning_detected_channels,
        "learning_raw_detected_channels": learning_raw_detected_channels,
    }


def run_detector_suite(
    reference_obs,
    received_obs,
    learning_detectors=None,
    feature_keys=None,
    min_learning_vote_fraction=0.50,
):
    bdd_report = detect_fdia(reference_obs, received_obs)
    learning_reports = run_learning_detectors(
        received_obs,
        learning_detectors or [],
        feature_keys,
        bdd_report=bdd_report,
    )
    return fuse_detector_reports(
        bdd_report,
        learning_reports,
        min_learning_vote_fraction=min_learning_vote_fraction,
    )
