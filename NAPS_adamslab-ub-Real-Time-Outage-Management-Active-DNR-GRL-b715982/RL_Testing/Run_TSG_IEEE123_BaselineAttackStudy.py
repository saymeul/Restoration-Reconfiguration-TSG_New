"""IEEE 123-bus baseline-vs-attack vulnerability study for TSG work.

This runner starts the IEEE 123 replication without touching the frozen IEEE 34
evidence package. It reuses the validated baseline attack/evaluation functions
from the IEEE 34 runner, but writes all outputs under ``tsg_ieee123`` and uses
the IEEE 123 restoration model/environment.
"""

import argparse
import numpy as np

import Run_TSG_IEEE34_BaselineAttackStudy as baseline
from FDIA_DetectorSuite import load_learning_detectors
from FDIA_ExperimentCore import RestorationExperiment, resolve_path, safe_json, write_csv
from IEEE123_VulnerabilityRegistry import write_registry_outputs
from TSG_ControllerConfig import (
    add_controller_args,
    controller_metadata,
    controller_output_dir,
    make_controller_experiment,
)


BASE_ATTACKS = list(baseline.BASE_ATTACKS)
SYSTEM_NAME = "123bus"
DEFAULT_OUTPUT_DIR = "paper_results/tsg_ieee123/baseline_attack_study"


def parse_args():
    parser = argparse.ArgumentParser(
        description="IEEE 123-bus restored-energy vulnerability baseline for GRL observation FDIA."
    )
    parser.add_argument("--cases", type=int, default=1, help="Number of deterministic outage seeds.")
    parser.add_argument("--seed", type=int, default=20260615)
    parser.add_argument("--attacks", nargs="+", default=BASE_ATTACKS)
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--step-hours", type=float, default=1.0)
    parser.add_argument("--start-hour", type=int, default=0)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    add_controller_args(parser)
    parser.add_argument("--max-outage-fraction", type=float, default=0.50)
    parser.add_argument("--max-scenario-generation-attempts", type=int, default=100)

    parser.add_argument("--topology-drop-fraction", type=float, default=0.05)
    parser.add_argument("--action-mask-fraction", type=float, default=0.25)
    parser.add_argument(
        "--action-mask-scope",
        choices=["switch", "load", "switch_and_load"],
        default="switch",
    )
    parser.add_argument("--voltage-target-fraction", type=float, default=0.20)
    parser.add_argument("--voltage-reported", type=float, default=1.0)
    parser.add_argument("--branchflow-target-fraction", type=float, default=0.20)
    parser.add_argument("--branchflow-scale", type=float, default=0.25)
    parser.add_argument("--energy-bias", type=float, default=0.25)
    parser.add_argument("--energy-max-reported", type=float, default=1.25)
    parser.add_argument("--bypass-loss-threshold-kwh", type=float, default=1.0e-6)

    parser.add_argument("--use-learning-detectors", action="store_true")
    parser.add_argument("--learning-detector-dir", default="123bus/paper_results/learning_detectors")
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
    return parser.parse_args()


def case_summary(case_id, scenario, attack_name, result, args):
    row = baseline.case_summary(case_id, scenario, attack_name, result, args)
    row["system"] = "123bus"
    return row


def step_rows(case_id, scenario, attack_name, result):
    rows = baseline.step_rows(case_id, scenario, attack_name, result)
    for row in rows:
        row["system"] = "123bus"
    return rows


def main():
    args = parse_args()
    output_dir = resolve_path(
        controller_output_dir(args.output_dir, DEFAULT_OUTPUT_DIR, SYSTEM_NAME, args.controller)
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    registry_outputs = write_registry_outputs(
        make_controller_experiment(SYSTEM_NAME, args, load_model=False),
        output_dir / "registries",
    )

    learning_detectors = []
    if args.use_learning_detectors:
        learning_detectors = load_learning_detectors(
            resolve_path(args.learning_detector_dir),
            tasks=args.learning_tasks,
            model_names=args.learning_models,
        )

    experiment = make_controller_experiment(SYSTEM_NAME, args, load_model=True)
    rng = np.random.default_rng(int(args.seed))
    summary_rows = []
    all_step_rows = []

    for case_index in range(int(args.cases)):
        scenario_seed = int(rng.integers(1, 2**31 - 1))
        scenario = baseline.generate_outage_scenario(experiment, scenario_seed, args)
        for attack_index, attack_name in enumerate(args.attacks):
            case_seed = int(rng.integers(1, 2**31 - 1))
            case_id = "B{:04d}_{}_seed{}".format(case_index, attack_name, scenario_seed)
            print("running {} attack={}".format(case_id, attack_name), flush=True)
            result = baseline.run_case(
                experiment,
                scenario,
                attack_name,
                case_seed + attack_index,
                learning_detectors,
                args,
            )
            summary_rows.append(case_summary(case_id, scenario, attack_name, result, args))
            all_step_rows.extend(step_rows(case_id, scenario, attack_name, result))

    ranking_rows = baseline.aggregate_attack_ranking(summary_rows)
    paths = {
        "case_summary": output_dir / "tsg_ieee123_case_summary.csv",
        "step_results": output_dir / "tsg_ieee123_step_results.csv",
        "attack_ranking": output_dir / "tsg_ieee123_attack_ranking.csv",
        "manifest": output_dir / "tsg_ieee123_manifest.json",
    }
    write_csv(summary_rows, paths["case_summary"])
    write_csv(all_step_rows, paths["step_results"])
    write_csv(ranking_rows, paths["attack_ranking"])

    manifest = {
        "experiment": "IEEE 123-bus TSG baseline-vs-attack restored-energy vulnerability study",
        "system": "123bus",
        **controller_metadata(SYSTEM_NAME, args),
        "cases": int(args.cases),
        "attacks": args.attacks,
        "horizon": int(args.horizon),
        "step_hours": float(args.step_hours),
        "start_hour": int(args.start_hour),
        "seed": int(args.seed),
        "scenario_mode": "deterministic_outage_edges",
        "max_outage_fraction": float(args.max_outage_fraction),
        "max_scenario_generation_attempts": int(args.max_scenario_generation_attempts),
        "learning_detectors_enabled": bool(args.use_learning_detectors),
        "learning_detector_count": len(learning_detectors),
        "registry_outputs": {key: str(value) for key, value in registry_outputs.items()},
        "outputs": {key: str(value) for key, value in paths.items()},
        "ieee34_freeze_boundary": "IEEE 34 results are read-only prior evidence; this runner writes only under tsg_ieee123.",
        "notes": (
            "Attacks corrupt only controller observations. Clean, attacked, and mitigated "
            "actions are evaluated on the same explicit OpenDSS outage-edge scenario."
        ),
    }
    paths["manifest"].write_text(safe_json(manifest) + "\n")

    print("wrote {}".format(paths["case_summary"]), flush=True)
    print("wrote {}".format(paths["attack_ranking"]), flush=True)
    print("wrote {}".format(paths["manifest"]), flush=True)


if __name__ == "__main__":
    main()
