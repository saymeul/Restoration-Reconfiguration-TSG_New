"""Universal IEEE 34-bus dynamic FDIA search without mitigation.

Option B1 experiment:

* Use the same existing FDIA attack space for GRL, MLP, and BPSO.
* Evaluate each sampled attack against all three methods.
* Select common attack cases by aggregate dynamic physical impact.

This is intentionally strict: the attack functions are not modified to make
BPSO vulnerable. If BPSO is unaffected because its current implementation does
not use the corrupted observation channel, that remains an honest result.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np

from FDIA_DetectorSuite import load_learning_detectors
from FDIA_ExperimentCore import resolve_path, safe_json, write_csv
from Run_FDIA_AttackSearch import strong_attack_kwargs
from Run_FDIA_DynamicImpact34_NoMitigation import (
    DEFAULT_ATTACKS,
    DEFAULT_METHODS,
    DynamicCase,
    detection_summary,
    fmt_float,
    impact_is_paper_valid,
    make_controller,
    metric_is_paper_valid,
    run_method_case,
    summarize_step_rows,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Universal/common IEEE 34-bus dynamic FDIA search for GRL, MLP, and BPSO."
    )
    parser.add_argument("--trials", type=int, default=60)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20260606)
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--step-hours", type=int, default=1)
    parser.add_argument("--start-hour", type=int, default=0)
    parser.add_argument("--harm-threshold", type=float, default=1.0e-6)
    parser.add_argument(
        "--objective",
        choices=["mean_impact", "min_impact"],
        default="mean_impact",
        help="Universal selection score across methods.",
    )
    parser.add_argument(
        "--include-invalid-selection",
        action="store_true",
        help="Allow numerically invalid/non-paper-ready universal cases to be selected.",
    )
    parser.add_argument("--max-abs-energy-ratio", type=float, default=2.0)
    parser.add_argument("--max-physical-impact", type=float, default=5.0)
    parser.add_argument("--max-convergence-violation", type=float, default=0.0)
    parser.add_argument("--attacks", nargs="+", default=DEFAULT_ATTACKS)
    parser.add_argument("--methods", nargs="+", choices=DEFAULT_METHODS, default=DEFAULT_METHODS)
    parser.add_argument("--bpso-particles", type=int, default=8)
    parser.add_argument("--bpso-iterations", type=int, default=8)
    parser.add_argument("--bpso-seed", type=int, default=5157)
    parser.add_argument("--allow-masked-switch-actions", action="store_true")
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
        default="paper_results/naps_34bus/universal_dynamic_no_mitigation",
    )
    return parser.parse_args()


def finite(values):
    cleaned = []
    for value in values:
        number = fmt_float(value)
        if number == "":
            continue
        cleaned.append(float(number))
    return cleaned


def mean(values):
    values = finite(values)
    return float(np.mean(values)) if values else 0.0


def max_value(values):
    values = finite(values)
    return float(np.max(values)) if values else 0.0


def min_value(values):
    values = finite(values)
    return float(np.min(values)) if values else 0.0


def step_row_is_valid(row, args):
    metrics = {
        "energy_ratio": row.get("energy_ratio"),
        "voltage_violation": row.get("voltage_violation"),
        "convergence_violation": row.get("convergence_violation"),
        "reward": row.get("reward"),
    }
    impact = {"physical_impact_score": row.get("physical_impact_score")}
    return metric_is_paper_valid(metrics, args) and impact_is_paper_valid(impact, args)


def summarize_case_rows(rows, args):
    methods = sorted({row["method"] for row in rows})
    summary = {}
    all_valid = True
    for method in methods:
        method_rows = [row for row in rows if row["method"] == method]
        attacked = [row for row in method_rows if row["mode"] == "attacked_dynamic"]
        clean = [row for row in method_rows if row["mode"] == "clean_dynamic"]
        valid = all(step_row_is_valid(row, args) for row in method_rows)
        all_valid = all_valid and valid
        impacts = [row["physical_impact_score"] for row in attacked]
        harmful_steps = [1 if float(row["physical_impact_score"]) > args.harm_threshold else 0 for row in attacked]
        summary[method] = {
            "valid": int(valid),
            "mean_impact": mean(impacts),
            "max_impact": max_value(impacts),
            "harmful_step_rate": mean(harmful_steps),
            "action_changed_rate": mean(row["action_changed"] for row in attacked),
            "mean_energy_ratio": mean(row["energy_ratio"] for row in attacked),
            "mean_clean_energy_ratio": mean(row["energy_ratio"] for row in clean),
            "min_energy_ratio": min_value(row["energy_ratio"] for row in attacked),
            "mean_voltage_violation": mean(row["voltage_violation"] for row in attacked),
            "max_voltage_violation": max_value(row["voltage_violation"] for row in attacked),
            "mean_policy_time_ms": mean(row["policy_time_ms"] for row in attacked),
        }

    method_impacts = [summary[method]["mean_impact"] for method in methods]
    positive_methods = int(sum(1 for value in method_impacts if value > args.harm_threshold))
    universal_mean = mean(method_impacts)
    universal_min = min_value(method_impacts)
    return summary, {
        "paper_valid_all_methods": int(all_valid),
        "universal_mean_impact": universal_mean,
        "universal_min_impact": universal_min,
        "universal_max_method_impact": max_value(method_impacts),
        "positive_impact_method_count": positive_methods,
        "positive_impact_method_fraction": float(positive_methods / len(methods)) if methods else 0.0,
    }


def universal_score(row, args):
    if args.objective == "min_impact":
        return float(row["universal_min_impact"])
    return float(row["universal_mean_impact"])


def make_case(trial_index, rng, args):
    scenario_seed = int(rng.integers(0, 2**31 - 1))
    attack = str(rng.choice(args.attacks))
    attack_kwargs = strong_attack_kwargs(attack, rng)
    return DynamicCase(
        case_id="U{:04d}_seed{}".format(trial_index, scenario_seed),
        source_trial=trial_index,
        scenario_seed=scenario_seed,
        attack=attack,
        attack_kwargs=attack_kwargs,
    )


def flatten_search_row(case, method_summary, universal_summary):
    row = {
        "system": "34bus",
        "case_id": case.case_id,
        "source_trial": case.source_trial,
        "scenario": "random",
        "scenario_seed": case.scenario_seed,
        "attack": case.attack,
        "attack_kwargs": case.attack_kwargs,
        "attack_kwargs_json": safe_json(case.attack_kwargs),
    }
    row.update(universal_summary)
    for method, summary in sorted(method_summary.items()):
        prefix = method.lower()
        for key, value in summary.items():
            row["{}_{}".format(prefix, key)] = value
    return row


def write_manifest(output_dir, args, search_rows, selected_rows, comparison_rows):
    manifest = {
        "experiment": "IEEE 34-bus universal dynamic FDIA impact without mitigation",
        "option": "B1_strict_current_threat_model",
        "methods": args.methods,
        "attacks": args.attacks,
        "objective": args.objective,
        "trials": args.trials,
        "top_k": args.top_k,
        "horizon": args.horizon,
        "step_hours": args.step_hours,
        "start_hour": args.start_hour,
        "seed": args.seed,
        "bpso_particles": args.bpso_particles,
        "bpso_iterations": args.bpso_iterations,
        "search_rows": len(search_rows),
        "selected_rows": len(selected_rows),
        "comparison_rows": len(comparison_rows),
        "mitigation_included": False,
        "note": (
            "Existing FDIA functions are applied unchanged to all methods. "
            "BPSO is not given a special attack channel."
        ),
    }
    path = output_dir / "universal_dynamic_no_mitigation_manifest.json"
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

    controllers = {method: make_controller(method, args) for method in args.methods}
    rng = np.random.default_rng(args.seed)
    search_rows = []
    case_rows_by_id = {}

    for trial_index in range(int(args.trials)):
        case = make_case(trial_index, rng, args)
        rows = []
        print(
            "trial {}/{} {} {}".format(trial_index + 1, args.trials, case.case_id, case.attack),
            flush=True,
        )
        for method in args.methods:
            rows.extend(run_method_case(controllers[method], case, learning_detectors, args))
        method_summary, universal_summary = summarize_case_rows(rows, args)
        search_row = flatten_search_row(case, method_summary, universal_summary)
        search_row["universal_score"] = universal_score(search_row, args)
        search_rows.append(search_row)
        case_rows_by_id[case.case_id] = rows
        print(
            "  score={:.6f} mean={:.6f} min={:.6f} positive_methods={} valid={}".format(
                search_row["universal_score"],
                search_row["universal_mean_impact"],
                search_row["universal_min_impact"],
                search_row["positive_impact_method_count"],
                search_row["paper_valid_all_methods"],
            ),
            flush=True,
        )

    candidates = [
        row
        for row in search_rows
        if args.include_invalid_selection or int(row.get("paper_valid_all_methods", 0)) == 1
    ]
    selected_rows = sorted(
        candidates,
        key=lambda row: (
            float(row["universal_score"]),
            float(row["positive_impact_method_count"]),
            float(row["universal_max_method_impact"]),
        ),
        reverse=True,
    )[: max(0, int(args.top_k))]

    selected_ids = {row["case_id"] for row in selected_rows}
    comparison_rows = []
    for case_id in selected_ids:
        comparison_rows.extend(case_rows_by_id[case_id])

    search_path = output_dir / "universal_attack_search_34bus.csv"
    selected_path = output_dir / "universal_selected_cases_34bus.csv"
    comparison_path = output_dir / "universal_method_comparison_34bus.csv"
    method_summary_path = output_dir / "table_universal_method_summary_34bus.csv"
    detector_summary_path = output_dir / "table_universal_detection_summary_34bus.csv"

    write_csv(search_rows, search_path)
    write_csv(selected_rows, selected_path)
    write_csv(comparison_rows, comparison_path)
    write_csv(summarize_step_rows(comparison_rows), method_summary_path)
    write_csv(detection_summary(comparison_rows), detector_summary_path)
    manifest_path = write_manifest(output_dir, args, search_rows, selected_rows, comparison_rows)

    print("selected cases={}".format(len(selected_rows)), flush=True)
    for index, row in enumerate(selected_rows, start=1):
        print(
            "  selected {}/{} {} {} score={:.6f} grl={:.6f} mlp={:.6f} bpso={:.6f}".format(
                index,
                len(selected_rows),
                row["case_id"],
                row["attack"],
                float(row["universal_score"]),
                float(row.get("grl_mean_impact", 0.0)),
                float(row.get("mlp_mean_impact", 0.0)),
                float(row.get("bpso_mean_impact", 0.0)),
            ),
            flush=True,
        )

    print("wrote {}".format(search_path), flush=True)
    print("wrote {}".format(selected_path), flush=True)
    print("wrote {}".format(comparison_path), flush=True)
    print("wrote {}".format(method_summary_path), flush=True)
    print("wrote {}".format(detector_summary_path), flush=True)
    print("wrote {}".format(manifest_path), flush=True)


if __name__ == "__main__":
    main()
