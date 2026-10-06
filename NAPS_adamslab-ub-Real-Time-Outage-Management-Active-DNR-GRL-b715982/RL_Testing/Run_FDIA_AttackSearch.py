"""
Search for FDIA cases that cause measurable physical degradation.

The fixed SC1/SC2 scenarios are useful baselines, but some feeders need a
larger random outage/attack search to expose harmful cyber-physical cases. This
runner samples random outage scenarios and stronger FDIA parameters, then
optionally evaluates RL-detector mitigation on the highest-impact cases.
"""

import argparse
import random
from pathlib import Path
from time import perf_counter

import numpy as np

from FDIA_Common import ATTACK_NAMES, apply_attack, mitigate_observation, select_fdia_aware_grl_action
from FDIA_ExperimentCore import (
    REPO_ROOT,
    RestorationExperiment,
    action_delta,
    detector_observation_from_reports,
    physical_impact,
    rl_detection_from_label,
    resolve_path,
    safe_json,
    write_csv,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Search for physically harmful FDIA cases")
    parser.add_argument("--system", default="34bus", choices=["13bus", "34bus", "123bus"])
    parser.add_argument("--trials", type=int, default=200)
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument(
        "--attacks",
        nargs="+",
        default=["voltage_masking", "branchflow_hiding", "energy_inflation", "topology_drop"],
        choices=ATTACK_NAMES,
    )
    parser.add_argument("--restoration-model", default="")
    parser.add_argument("--rl-detector-model", default="")
    parser.add_argument("--all-output", default="paper_results/fdia_attack_search_34bus_all.csv")
    parser.add_argument("--physical-output", default="paper_results/fdia_physical_impact_34bus_search.csv")
    parser.add_argument("--resilience-output", default="paper_results/rl_fdia_resilience_34bus.csv")
    return parser.parse_args()


def resolve_model_path(path):
    if not path:
        return None
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    repo_candidate = REPO_ROOT / candidate
    if repo_candidate.exists():
        return repo_candidate
    return Path.cwd() / candidate


def strong_attack_kwargs(attack_name, rng):
    if attack_name == "voltage_masking":
        return {
            "target_fraction": float(rng.uniform(0.20, 0.80)),
            "reported_voltage": float(rng.uniform(0.97, 1.03)),
        }
    if attack_name == "branchflow_hiding":
        return {
            "target_fraction": float(rng.uniform(0.20, 0.80)),
            "scale": float(rng.uniform(0.00, 0.35)),
        }
    if attack_name == "energy_inflation":
        return {
            "bias": float(rng.uniform(0.20, 0.70)),
            "max_reported": float(rng.uniform(1.05, 1.45)),
        }
    if attack_name == "topology_drop":
        return {
            "drop_fraction": float(rng.uniform(0.05, 0.35)),
            "seed": int(rng.integers(0, 2**31 - 1)),
        }
    return {}


def scenario_label(case_index, scenario_seed):
    return "R{:04d}_seed{}".format(case_index, scenario_seed)


def set_scenario_seed(scenario_seed):
    random.seed(int(scenario_seed))
    np.random.seed(int(scenario_seed) % (2**32 - 1))


def reset_same_random_scenario(experiment, scenario_seed):
    set_scenario_seed(scenario_seed)
    return experiment.get_observation("random")


def evaluate_on_seed(experiment, scenario_seed, action):
    reset_same_random_scenario(experiment, scenario_seed)
    obs_post_action, reward, done, _info = experiment.env.step(np.asarray(action, dtype=int))
    metrics = experiment.metrics_from_observation(obs_post_action, reward=reward, action=action)
    metrics["done"] = bool(done)
    return metrics, obs_post_action


def physical_row_from_case(
    experiment,
    case_id,
    scenario_seed,
    attack_name,
    attack_kwargs,
    attack_metadata,
    bdd_report,
    detector_features,
    clean_action,
    attacked_action,
    clean_metrics,
    attacked_metrics,
):
    switches, load_status = experiment.split_action(attacked_action)
    row = {
        "system": experiment.system,
        "scenario": case_id,
        "scenario_seed": scenario_seed,
        "attack": attack_name,
        "mode": "attacked_unmitigated",
        "attack_kwargs": attack_kwargs,
        "clean_action": clean_action.tolist(),
        "action": attacked_action.tolist(),
        "switch_vector": switches,
        "load_status": load_status,
        "attack_metadata": attack_metadata,
        "bdd_detected": int(bdd_report["detected"]),
        "bdd_score": bdd_report["score"],
        "bdd_detected_channels": bdd_report["detected_channels"],
        "detector_feature_vector": detector_features.tolist(),
    }
    row.update(attacked_metrics)
    row.update(physical_impact(clean_metrics, attacked_metrics))
    row.update(action_delta(clean_action, attacked_action, experiment.num_switches))
    return row


def run_search_case(experiment, case_index, scenario_seed, attack_name, attack_kwargs):
    true_obs = reset_same_random_scenario(experiment, scenario_seed)
    clean_action, clean_policy_ms = experiment.predict_action(true_obs)
    clean_metrics, _clean_post_obs = evaluate_on_seed(experiment, scenario_seed, clean_action)

    policy_obs, attack_metadata = apply_attack(true_obs, attack_name, **attack_kwargs)
    attacked_action, policy_ms = experiment.predict_action(policy_obs)
    attacked_metrics, _attacked_post_obs = evaluate_on_seed(experiment, scenario_seed, attacked_action)
    detector_features, bdd_report = detector_observation_from_reports(true_obs, policy_obs)

    row = physical_row_from_case(
        experiment,
        scenario_label(case_index, scenario_seed),
        scenario_seed,
        attack_name,
        attack_kwargs,
        attack_metadata,
        bdd_report,
        detector_features,
        clean_action,
        attacked_action,
        clean_metrics,
        attacked_metrics,
    )
    row["clean_policy_time_ms"] = clean_policy_ms
    row["policy_time_ms"] = policy_ms
    return row, {
        "true_obs": true_obs,
        "policy_obs": policy_obs,
        "clean_action": clean_action,
        "attacked_action": attacked_action,
        "clean_metrics": clean_metrics,
        "attacked_metrics": attacked_metrics,
        "bdd_report": bdd_report,
        "detector_features": detector_features,
        "attack_metadata": attack_metadata,
    }


def resilience_rows_for_case(experiment, search_row, context, rl_detector_model):
    rows = []
    scenario_seed = int(search_row["scenario_seed"])
    attack_name = search_row["attack"]
    case_id = search_row["scenario"]
    true_obs = context["true_obs"]
    policy_obs = context["policy_obs"]
    clean_action = context["clean_action"]
    clean_metrics = context["clean_metrics"]
    attacked_action = context["attacked_action"]
    attacked_metrics = context["attacked_metrics"]
    detector_features = context["detector_features"]
    bdd_report = context["bdd_report"]

    rows.append(dict(search_row))

    detector_start = perf_counter()
    detector_action, _state = rl_detector_model.predict(detector_features, deterministic=True)
    detector_time_ms = (perf_counter() - detector_start) * 1000.0
    detector_label = int(np.asarray(detector_action).reshape(-1)[0])
    detection = rl_detection_from_label(detector_label, bdd_report)
    mitigated_obs, mitigation_metadata = mitigate_observation(true_obs, policy_obs, detection)
    mitigated_action, policy_time_ms = experiment.predict_action(mitigated_obs)
    mitigated_metrics, _mitigated_post_obs = evaluate_on_seed(experiment, scenario_seed, mitigated_action)
    switches, load_status = experiment.split_action(mitigated_action)

    mitigated_row = {
        "system": experiment.system,
        "scenario": case_id,
        "scenario_seed": scenario_seed,
        "attack": attack_name,
        "mode": "rl_detector_mitigated",
        "clean_action": clean_action.tolist(),
        "action": mitigated_action.tolist(),
        "switch_vector": switches,
        "load_status": load_status,
        "attack_kwargs": search_row.get("attack_kwargs", ""),
        "attack_metadata": context["attack_metadata"],
        "policy_time_ms": policy_time_ms,
        "detector_time_ms": detector_time_ms,
        "rl_detector_label": detection["rl_detector_label"],
        "rl_detector_attack": detection["rl_detector_attack"],
        "rl_detector_detected": int(detection["detected"]),
        "rl_detected_channels": detection["detected_channels"],
        "mitigation_metadata": mitigation_metadata,
        "mitigation_applied": int(mitigation_metadata["mitigation_applied"]),
        "detector_feature_vector": detector_features.tolist(),
    }
    mitigated_row.update(mitigated_metrics)
    mitigated_row.update(physical_impact(clean_metrics, mitigated_metrics))
    mitigated_row.update(action_delta(clean_action, mitigated_action, experiment.num_switches))
    rows.append(mitigated_row)

    decision = select_fdia_aware_grl_action(
        lambda obs: experiment.predict_action(obs),
        lambda action: evaluate_on_seed(experiment, scenario_seed, action)[0],
        policy_obs,
        mitigated_obs,
        detection,
        experiment.num_switches,
    )
    screened_action = np.asarray(decision["action"], dtype=int)
    switches, load_status = experiment.split_action(screened_action)
    screened_row = {
        "system": experiment.system,
        "scenario": case_id,
        "scenario_seed": scenario_seed,
        "attack": attack_name,
        "mode": "rl_detector_fdia_aware_screened",
        "clean_action": clean_action.tolist(),
        "action": screened_action.tolist(),
        "switch_vector": switches,
        "load_status": load_status,
        "attack_kwargs": search_row.get("attack_kwargs", ""),
        "attack_metadata": context["attack_metadata"],
        "policy_time_ms": decision["policy_time_ms"],
        "decision_time_ms": decision["decision_time_ms"],
        "screening_time_ms": decision["screening_time_ms"],
        "mitigation_metadata": mitigation_metadata,
        "selected_candidate": decision["selected_candidate"],
        "candidate_actions": decision["candidate_actions"],
        "fdia_aware_metadata": decision["fdia_aware_metadata"],
    }
    screened_row.update(decision["metrics"])
    screened_row.update(physical_impact(clean_metrics, decision["metrics"]))
    screened_row.update(action_delta(clean_action, screened_action, experiment.num_switches))
    rows.append(screened_row)
    return rows


def main():
    args = parse_args()
    rng = np.random.default_rng(args.seed)
    experiment = RestorationExperiment(args.system, model_path=args.restoration_model or None)

    rows = []
    contexts = {}
    print("FDIA harmful-case search")
    print("System: {} | trials={} | seed={}".format(args.system, args.trials, args.seed))
    for index in range(args.trials):
        attack_name = str(rng.choice(args.attacks))
        scenario_seed = int(rng.integers(0, 2**31 - 1))
        attack_kwargs = strong_attack_kwargs(attack_name, rng)
        row, context = run_search_case(experiment, index, scenario_seed, attack_name, attack_kwargs)
        rows.append(row)
        contexts[row["scenario"]] = context
        if (index + 1) % max(1, args.trials // 10) == 0:
            best = max(float(item["physical_impact_score"]) for item in rows)
            print("  completed {:>4}/{} | current best impact {:.6f}".format(index + 1, args.trials, best))

    rows_sorted = sorted(rows, key=lambda item: float(item["physical_impact_score"]), reverse=True)
    top_rows = rows_sorted[: args.top_k]
    write_csv(rows_sorted, resolve_path(args.all_output))
    write_csv(top_rows, resolve_path(args.physical_output))

    print("Top {} harmful cases:".format(len(top_rows)))
    for row in top_rows:
        print(
            "  {} {} impact={} energy_delta={} action_changed={}".format(
                row["scenario"],
                row["attack"],
                row["physical_impact_score"],
                row["energy_ratio_delta_vs_clean"],
                row["action_changed"],
            )
        )

    detector_path = resolve_model_path(args.rl_detector_model)
    if detector_path is not None and detector_path.exists():
        from stable_baselines3 import PPO

        rl_detector_model = PPO.load(str(detector_path))
        resilience_rows = []
        for row in top_rows:
            resilience_rows.extend(resilience_rows_for_case(experiment, row, contexts[row["scenario"]], rl_detector_model))
        write_csv(resilience_rows, resolve_path(args.resilience_output))
        print("Saved resilience rows: {}".format(resolve_path(args.resilience_output)))
    elif args.rl_detector_model:
        print("RL detector model not found, skipping resilience rows: {}".format(detector_path))

    print("Saved all search rows: {}".format(resolve_path(args.all_output)))
    print("Saved top physical rows: {}".format(resolve_path(args.physical_output)))


if __name__ == "__main__":
    main()
