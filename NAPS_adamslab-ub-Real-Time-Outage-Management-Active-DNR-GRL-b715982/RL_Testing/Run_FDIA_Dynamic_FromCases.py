"""
Replay harmful seeded FDIA cases as multi-step OpenDSS trajectories.

The fixed SC1/SC2 dynamic runner is useful for simple baselines. This runner is
for the stronger publication setting: take harmful cases discovered by random
search or robustness validation, replay the same random outage seed, and record
clean-vs-attacked-vs-RL-mitigated physical evolution over loadshape time.
"""

import argparse
import csv
import json
import math
import random
from pathlib import Path
from time import perf_counter

import numpy as np

from FDIA_Common import ATTACK_NAMES, apply_attack, mitigate_observation
from FDIA_ExperimentCore import (
    REPO_ROOT,
    RestorationExperiment,
    action_delta,
    detector_observation_from_reports,
    physical_impact,
    resolve_path,
    rl_detection_from_label,
    write_csv,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Dynamic FDIA validation from seeded harmful cases")
    parser.add_argument("--system", required=True, choices=["13bus", "34bus", "123bus"])
    parser.add_argument(
        "--case-csv",
        default="paper_results/robustness_validation/robustness_top_cases_filtered.csv",
        help="CSV containing scenario_seed, attack, and attack_kwargs columns",
    )
    parser.add_argument(
        "--rl-detector-model",
        default="RL_Training/Trained_Models/FDIA_Detectors/RLFDIA_{system}_final.zip",
        help="Path or template for trained RL FDIA detector",
    )
    parser.add_argument("--output", default="")
    parser.add_argument("--max-cases", type=int, default=5)
    parser.add_argument("--min-impact", type=float, default=1.0e-6)
    parser.add_argument("--attacks", nargs="+", default=[name for name in ATTACK_NAMES if name != "clean"],
                        choices=ATTACK_NAMES)
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--step-hours", type=int, default=1)
    parser.add_argument("--start-hour", type=int, default=0)
    return parser.parse_args()


def read_csv(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError("Missing case CSV: {}".format(path))
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def as_float(row, key, default=0.0):
    try:
        value = row.get(key, "")
        if value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(row, key, default=0):
    try:
        value = row.get(key, "")
        if value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_json_dict(value):
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def parse_json_list(value):
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, list) else None


def parse_action(value):
    parsed = parse_json_list(value)
    if parsed is None:
        return None
    return np.asarray(parsed, dtype=int)


def source_row_has_physical_validity_fields(row):
    return (
        "convergence_violation" in row
        and "convergence_delta_vs_clean" in row
        and "energy_ratio" in row
        and "energy_ratio_delta_vs_clean" in row
    )


def source_row_is_paper_valid(row):
    if not source_row_has_physical_validity_fields(row):
        return True

    convergence = as_float(row, "convergence_violation", math.nan)
    clean_convergence = convergence - as_float(row, "convergence_delta_vs_clean", 0.0)
    energy_ratio = as_float(row, "energy_ratio", math.nan)
    clean_energy_ratio = energy_ratio - as_float(row, "energy_ratio_delta_vs_clean", 0.0)
    impact = as_float(row, "physical_impact_score", math.nan)
    return (
        math.isfinite(convergence)
        and math.isfinite(clean_convergence)
        and convergence <= 0.0
        and clean_convergence <= 0.0
        and math.isfinite(energy_ratio)
        and math.isfinite(clean_energy_ratio)
        and abs(energy_ratio) <= 2.0
        and abs(clean_energy_ratio) <= 2.0
        and math.isfinite(impact)
        and 0.0 <= impact <= 5.0
    )


def resolve_model_path(path_template, system):
    if not path_template:
        return None
    path_text = path_template.format(system=system)
    candidate = Path(path_text)
    if candidate.is_absolute():
        return candidate
    repo_candidate = REPO_ROOT / candidate
    if repo_candidate.exists():
        return repo_candidate
    return Path.cwd() / candidate


def output_path_for(args):
    if args.output:
        return resolve_path(args.output)
    return resolve_path("paper_results/rl_fdia_resilience_dynamic_{}_search.csv".format(args.system))


def set_scenario_seed(scenario_seed):
    random.seed(int(scenario_seed))
    np.random.seed(int(scenario_seed) % (2**32 - 1))


def seeded_random_observation(experiment, scenario_seed):
    set_scenario_seed(scenario_seed)
    return experiment.get_observation("random")


def seeded_trajectory_after_action(experiment, scenario_seed, action, horizon, step_hours, start_hour):
    set_scenario_seed(scenario_seed)
    return experiment.trajectory_after_action(
        "random",
        action,
        horizon=horizon,
        step_hours=step_hours,
        start_hour=start_hour,
    )


def select_cases(rows, args):
    selected = []
    seen = set()
    for row in rows:
        if row.get("system") != args.system:
            continue
        if row.get("attack") not in args.attacks or row.get("attack") == "clean":
            continue
        if not row.get("scenario_seed"):
            continue
        if as_float(row, "physical_impact_score") < args.min_impact:
            continue
        if not source_row_is_paper_valid(row):
            continue
        key = (row.get("system"), row.get("scenario"), row.get("attack"), row.get("scenario_seed"))
        if key in seen:
            continue
        seen.add(key)
        selected.append(row)

    selected = sorted(selected, key=lambda item: as_float(item, "physical_impact_score"), reverse=True)
    if args.max_cases > 0:
        selected = selected[: args.max_cases]
    return selected


def base_row(experiment, source_row, mode, action, clean_action, policy_time_ms, extra=None):
    switches, load_status = experiment.split_action(action)
    row = {
        "system": experiment.system,
        "scenario": source_row.get("scenario", ""),
        "scenario_seed": source_row.get("scenario_seed", ""),
        "attack": source_row.get("attack", ""),
        "mode": mode,
        "source_physical_impact_score": source_row.get("physical_impact_score", ""),
        "validation_seed": source_row.get("validation_seed", ""),
        "source_top_rank": source_row.get("top_rank", source_row.get("filtered_top_rank", "")),
        "attack_kwargs": source_row.get("attack_kwargs", ""),
        "clean_action": clean_action.tolist(),
        "action": action.tolist(),
        "switch_vector": switches,
        "load_status": load_status,
        "policy_time_ms": policy_time_ms,
    }
    if extra:
        row.update(extra)
    return row


def append_trajectory_rows(
    rows,
    experiment,
    source_row,
    mode,
    clean_action,
    action,
    clean_trajectory,
    action_trajectory,
    policy_time_ms,
    extra=None,
):
    for clean_metrics, action_metrics in zip(clean_trajectory, action_trajectory):
        row = base_row(experiment, source_row, mode, action, clean_action, policy_time_ms, extra=extra)
        row.update(
            {
                "time_step": action_metrics["time_step"],
                "hour": action_metrics["hour"],
            }
        )
        row.update(action_metrics)
        row.update(physical_impact(clean_metrics, action_metrics))
        row.update(action_delta(clean_action, action, experiment.num_switches))
        rows.append(row)


def dynamic_rows_for_case(experiment, source_row, detector_model, args):
    scenario_seed = as_int(source_row, "scenario_seed")
    attack_name = source_row.get("attack", "")
    attack_kwargs = parse_json_dict(source_row.get("attack_kwargs", ""))

    true_obs = seeded_random_observation(experiment, scenario_seed)
    source_clean_action = parse_action(source_row.get("clean_action", ""))
    source_attacked_action = parse_action(source_row.get("action", ""))
    if source_clean_action is not None and source_attacked_action is not None:
        clean_action = source_clean_action
        attacked_action = source_attacked_action
        clean_policy_ms = as_float(source_row, "clean_policy_time_ms")
        attacked_policy_ms = as_float(source_row, "policy_time_ms")
    else:
        clean_action, clean_policy_ms = experiment.predict_action(true_obs)

    policy_obs, attack_metadata = apply_attack(true_obs, attack_name, **attack_kwargs)
    if source_clean_action is None or source_attacked_action is None:
        attacked_action, attacked_policy_ms = experiment.predict_action(policy_obs)

    detector_features, bdd_report = detector_observation_from_reports(true_obs, policy_obs)

    clean_trajectory, _ = seeded_trajectory_after_action(
        experiment,
        scenario_seed,
        clean_action,
        args.horizon,
        args.step_hours,
        args.start_hour,
    )
    attacked_trajectory, _ = seeded_trajectory_after_action(
        experiment,
        scenario_seed,
        attacked_action,
        args.horizon,
        args.step_hours,
        args.start_hour,
    )

    rows = []
    attacked_extra = {
        "clean_policy_time_ms": clean_policy_ms,
        "attack_metadata": attack_metadata,
        "bdd_detected": int(bdd_report["detected"]),
        "bdd_score": bdd_report["score"],
        "bdd_detected_channels": bdd_report["detected_channels"],
        "detector_feature_vector": detector_features.tolist(),
    }
    append_trajectory_rows(
        rows,
        experiment,
        source_row,
        "attacked_unmitigated_dynamic",
        clean_action,
        attacked_action,
        clean_trajectory,
        attacked_trajectory,
        attacked_policy_ms,
        extra=attacked_extra,
    )

    if detector_model is None:
        return rows

    detector_start = perf_counter()
    detector_action, _state = detector_model.predict(detector_features, deterministic=True)
    detector_time_ms = (perf_counter() - detector_start) * 1000.0
    detector_label = int(np.asarray(detector_action).reshape(-1)[0])
    detection = rl_detection_from_label(detector_label, bdd_report)
    mitigated_obs, mitigation_metadata = mitigate_observation(true_obs, policy_obs, detection)
    mitigated_action, mitigated_policy_ms = experiment.predict_action(mitigated_obs)
    mitigated_trajectory, _ = seeded_trajectory_after_action(
        experiment,
        scenario_seed,
        mitigated_action,
        args.horizon,
        args.step_hours,
        args.start_hour,
    )

    mitigated_extra = {
        "clean_policy_time_ms": clean_policy_ms,
        "detector_time_ms": detector_time_ms,
        "attack_metadata": attack_metadata,
        "rl_detector_label": detection["rl_detector_label"],
        "rl_detector_attack": detection["rl_detector_attack"],
        "rl_detector_detected": int(detection["detected"]),
        "rl_detected_channels": detection["detected_channels"],
        "mitigation_metadata": mitigation_metadata,
        "mitigation_applied": int(mitigation_metadata["mitigation_applied"]),
        "detector_feature_vector": detector_features.tolist(),
    }
    append_trajectory_rows(
        rows,
        experiment,
        source_row,
        "rl_detector_mitigated_dynamic",
        clean_action,
        mitigated_action,
        clean_trajectory,
        mitigated_trajectory,
        mitigated_policy_ms,
        extra=mitigated_extra,
    )
    return rows


def main():
    args = parse_args()
    case_path = resolve_path(args.case_csv)
    cases = select_cases(read_csv(case_path), args)
    if not cases:
        raise RuntimeError("No matching harmful seeded cases found for {}".format(args.system))

    detector_path = resolve_model_path(args.rl_detector_model, args.system)
    detector_model = None
    if detector_path is not None:
        if not detector_path.exists():
            raise FileNotFoundError("Missing RL detector model: {}".format(detector_path))
        from stable_baselines3 import PPO

        detector_model = PPO.load(str(detector_path))

    experiment = RestorationExperiment(args.system)
    rows = []
    print("Seeded dynamic FDIA validation")
    print("System: {} | cases={} | horizon={} | case_csv={}".format(
        args.system,
        len(cases),
        args.horizon,
        case_path,
    ))
    print("RL detector: {}".format(detector_path if detector_path else "not loaded"))

    for index, case in enumerate(cases, start=1):
        case_rows = dynamic_rows_for_case(experiment, case, detector_model, args)
        rows.extend(case_rows)
        max_attacked = max(
            as_float(row, "physical_impact_score")
            for row in case_rows
            if row.get("mode") == "attacked_unmitigated_dynamic"
        )
        max_mitigated = max(
            [
                as_float(row, "physical_impact_score")
                for row in case_rows
                if row.get("mode") == "rl_detector_mitigated_dynamic"
            ]
            or [0.0]
        )
        print(
            "  {}/{} {} {} max_attacked={:.6f} max_mitigated={:.6f}".format(
                index,
                len(cases),
                case.get("scenario", ""),
                case.get("attack", ""),
                max_attacked,
                max_mitigated,
            )
        )

    output_path = output_path_for(args)
    write_csv(rows, output_path)
    print("Saved CSV: {}".format(output_path))


if __name__ == "__main__":
    main()
