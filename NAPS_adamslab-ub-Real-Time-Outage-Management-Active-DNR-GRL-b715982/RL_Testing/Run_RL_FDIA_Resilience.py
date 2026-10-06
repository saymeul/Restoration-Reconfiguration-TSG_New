"""
Run the updated RL-driven FDIA resilience concept.

Pipeline:
    true OpenDSS state
    -> FDIA-corrupted observation
    -> physical impact measurement
    -> RL FDIA detector decision
    -> mitigation
    -> GCAPS restoration action
    -> OpenDSS physical evaluation
"""

import argparse
from pathlib import Path

import numpy as np

from FDIA_Common import ATTACK_NAMES, apply_attack
from FDIA_ExperimentCore import (
    REPO_ROOT,
    RestorationExperiment,
    detector_observation_from_reports,
    resolve_path,
    rl_detection_from_label,
    run_dynamic_physical_impact,
    run_dynamic_rl_mitigated_case,
    run_fdia_aware_screened_case,
    run_one_step_physical_impact,
    run_rl_mitigated_case,
    write_csv,
)


def parse_args():
    parser = argparse.ArgumentParser(description="RL-based FDIA resilience runner")
    parser.add_argument("--system", default="13bus", choices=["13bus", "34bus", "123bus"])
    parser.add_argument("--scenarios", nargs="+", default=["SC1", "SC2"], choices=["SC1", "SC2", "random"])
    parser.add_argument("--attacks", nargs="+", default=[name for name in ATTACK_NAMES if name != "clean"],
                        choices=ATTACK_NAMES)
    parser.add_argument("--restoration-model", default="", help="Optional path to GCAPS restoration model")
    parser.add_argument(
        "--rl-detector-model",
        default="",
        help="Path to trained RL FDIA detector .zip. If omitted, only physical impact is measured.",
    )
    parser.add_argument("--dynamic", action="store_true", help="Record loadshape trajectory after selected actions")
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--step-hours", type=int, default=1)
    parser.add_argument("--start-hour", type=int, default=0)
    parser.add_argument("--skip-screened", action="store_true",
                        help="Skip FDIA-aware candidate screening after RL detection")
    parser.add_argument(
        "--output",
        default="paper_results/rl_fdia_resilience.csv",
        help="Output CSV path. Relative paths are resolved from RL_Testing.",
    )
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


def rl_detection_for_case(experiment, scenario_name, attack_name, rl_detector_model):
    true_obs = experiment.get_observation(scenario_name)
    policy_obs, _metadata = apply_attack(true_obs, attack_name)
    detector_features, bdd_report = detector_observation_from_reports(true_obs, policy_obs)
    detector_action, _state = rl_detector_model.predict(detector_features, deterministic=True)
    detector_label = int(np.asarray(detector_action).reshape(-1)[0])
    return rl_detection_from_label(detector_label, bdd_report)


def main():
    args = parse_args()
    restoration_model_path = args.restoration_model or None
    detector_path = resolve_model_path(args.rl_detector_model)
    experiment = RestorationExperiment(args.system, model_path=restoration_model_path)

    rl_detector_model = None
    if detector_path is not None:
        from stable_baselines3 import PPO

        rl_detector_model = PPO.load(str(detector_path))

    rows = []
    print("RL-based FDIA resilience experiment")
    print("System: {} | dynamic={} | restoration_model={}".format(args.system, args.dynamic, experiment.model_path))
    print("RL detector: {}".format(detector_path if detector_path else "not loaded"))
    print("Scenario | Attack              | Rows")
    print("-" * 70)

    for scenario_name in args.scenarios:
        for attack_name in args.attacks:
            if attack_name == "clean":
                continue

            before_count = len(rows)
            if args.dynamic:
                rows.extend(
                    run_dynamic_physical_impact(
                        experiment,
                        scenario_name,
                        attack_name,
                        horizon=args.horizon,
                        step_hours=args.step_hours,
                        start_hour=args.start_hour,
                    )
                )
                if rl_detector_model is not None:
                    rows.extend(
                        run_dynamic_rl_mitigated_case(
                            experiment,
                            scenario_name,
                            attack_name,
                            rl_detector_model,
                            horizon=args.horizon,
                            step_hours=args.step_hours,
                            start_hour=args.start_hour,
                        )
                    )
            else:
                impact_row, _context = run_one_step_physical_impact(experiment, scenario_name, attack_name)
                rows.append(impact_row)
                if rl_detector_model is not None:
                    rows.append(run_rl_mitigated_case(experiment, scenario_name, attack_name, rl_detector_model))
                    if not args.skip_screened:
                        detection = rl_detection_for_case(experiment, scenario_name, attack_name, rl_detector_model)
                        rows.append(run_fdia_aware_screened_case(experiment, scenario_name, attack_name, detection))

            print("{:<8} | {:<19} | {}".format(scenario_name, attack_name, len(rows) - before_count))

    output_path = resolve_path(args.output)
    write_csv(rows, output_path)
    print("Saved CSV: {}".format(output_path))


if __name__ == "__main__":
    main()
