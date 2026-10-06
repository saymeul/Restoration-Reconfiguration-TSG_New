"""
Measure physical degradation caused by FDIA-induced restoration actions.

This runner does not train or detect attacks. It answers the first question:
when the same outage is controlled from a clean observation versus an attacked
observation, how much does the true OpenDSS physical result degrade?
"""

import argparse
from pathlib import Path

from FDIA_Common import ATTACK_NAMES
from FDIA_ExperimentCore import (
    ATTACK_TO_RL_LABEL,
    RestorationExperiment,
    resolve_path,
    run_dynamic_physical_impact,
    run_one_step_physical_impact,
    write_csv,
)


def parse_args():
    parser = argparse.ArgumentParser(description="FDIA physical-impact evaluation")
    parser.add_argument("--system", default="13bus", choices=["13bus", "34bus", "123bus"])
    parser.add_argument("--scenarios", nargs="+", default=["SC1", "SC2"], choices=["SC1", "SC2", "random"])
    parser.add_argument("--attacks", nargs="+", default=[name for name in ATTACK_NAMES if name != "clean"],
                        choices=ATTACK_NAMES)
    parser.add_argument("--model", default="", help="Optional path to a trained GCAPS restoration model")
    parser.add_argument("--dynamic", action="store_true", help="Record a loadshape trajectory after each action")
    parser.add_argument("--horizon", type=int, default=24, help="Number of dynamic trajectory samples")
    parser.add_argument("--step-hours", type=int, default=1, help="OpenDSS daily-mode step size in hours")
    parser.add_argument("--start-hour", type=int, default=0)
    parser.add_argument(
        "--output",
        default="paper_results/fdia_physical_impact.csv",
        help="Output CSV path. Relative paths are resolved from RL_Testing.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    model_path = args.model or None
    experiment = RestorationExperiment(args.system, model_path=model_path)
    rows = []

    print("FDIA physical-impact evaluation")
    print("System: {} | dynamic={} | model={}".format(args.system, args.dynamic, experiment.model_path))
    print("Scenario | Attack              | Mode       | Impact")
    print("-" * 86)

    for scenario_name in args.scenarios:
        for attack_name in args.attacks:
            if attack_name == "clean":
                continue
            if args.dynamic:
                dynamic_rows = run_dynamic_physical_impact(
                    experiment,
                    scenario_name,
                    attack_name,
                    horizon=args.horizon,
                    step_hours=args.step_hours,
                    start_hour=args.start_hour,
                )
                rows.extend(dynamic_rows)
                impact = max(row["physical_impact_score"] for row in dynamic_rows) if dynamic_rows else 0.0
                mode = "dynamic"
            else:
                row, _context = run_one_step_physical_impact(experiment, scenario_name, attack_name)
                row["attack_label_for_rl_detector"] = ATTACK_TO_RL_LABEL[attack_name]
                rows.append(row)
                impact = row["physical_impact_score"]
                mode = "one-step"
            print("{:<8} | {:<19} | {:<10} | {:.6f}".format(scenario_name, attack_name, mode, impact))

    output_path = resolve_path(args.output)
    if not output_path.is_absolute():
        output_path = Path(__file__).resolve().parent / args.output
    write_csv(rows, output_path)
    print("Saved CSV: {}".format(output_path))


if __name__ == "__main__":
    main()
