"""IEEE 8500-node voltage and branchflow observation criticality study.

This runner attacks one named voltage or branchflow observation at a time. It
is chunk-friendly because IEEE 8500 has many more measurement targets than IEEE
34, and full measurement criticality should be accumulated in audited chunks.
"""

import argparse
import numpy as np

import Run_TSG_IEEE34_MeasurementCriticality as measurement34
from FDIA_DetectorSuite import load_learning_detectors
from FDIA_ExperimentCore import RestorationExperiment, resolve_path, safe_json, write_csv
from IEEE8500_VulnerabilityRegistry import build_observation_registry, write_registry_outputs
from Run_TSG_IEEE8500_Common import add_ieee8500_scenario_args, generate_outage_scenario
from TSG_ControllerConfig import (
    add_controller_args,
    controller_metadata,
    controller_output_dir,
    make_controller_experiment,
)


SYSTEM_NAME = "8500bus"
DEFAULT_OUTPUT_DIR = "paper_results/tsg_ieee8500/measurement_criticality"


def parse_args():
    parser = argparse.ArgumentParser(
        description="IEEE 8500-node named voltage/branchflow observation criticality experiment."
    )
    parser.add_argument("--cases", type=int, default=30, help="Number of deterministic outage scenarios.")
    parser.add_argument("--seed", type=int, default=20260615)
    parser.add_argument(
        "--seed-schedule",
        choices=["baseline_attack", "criticality_sequential"],
        default="baseline_attack",
        help="baseline_attack matches the completed IEEE 8500 baseline outage-seed schedule.",
    )
    parser.add_argument(
        "--baseline-case-seed-draws",
        type=int,
        default=5,
        help="Number of per-attack RNG draws consumed after each baseline scenario seed.",
    )
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--step-hours", type=float, default=1.0)
    parser.add_argument("--start-hour", type=int, default=0)
    parser.add_argument(
        "--target-family",
        choices=["voltage", "branchflow", "both"],
        default="branchflow",
    )
    parser.add_argument(
        "--voltage-attack-mode",
        choices=["mask_to_nominal", "false_low", "false_high", "scale", "bias"],
        default="false_low",
    )
    parser.add_argument("--voltage-reported", type=float, default=1.0)
    parser.add_argument("--voltage-false-low", type=float, default=0.80)
    parser.add_argument("--voltage-false-high", type=float, default=1.20)
    parser.add_argument("--voltage-scale", type=float, default=0.90)
    parser.add_argument("--voltage-bias", type=float, default=-0.05)
    parser.add_argument(
        "--branchflow-attack-mode",
        choices=["hide", "inflate"],
        default="hide",
    )
    parser.add_argument("--branchflow-hide-scale", type=float, default=0.0)
    parser.add_argument("--branchflow-inflate-scale", type=float, default=2.0)
    parser.add_argument(
        "--include-noop",
        action="store_true",
        help="Keep rows where the requested corruption does not change the observation value.",
    )
    parser.add_argument("--max-targets", type=int, default=0)
    parser.add_argument("--target-start-index", type=int, default=0)
    parser.add_argument("--target-count", type=int, default=0)
    parser.add_argument("--merge-case-files", nargs="*")
    parser.add_argument("--write-step-results", action="store_true")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    add_controller_args(parser)
    parser.add_argument("--bypass-loss-threshold-kwh", type=float, default=1.0e-6)
    parser.add_argument("--max-outage-fraction", type=float, default=0.50)
    parser.add_argument("--max-scenario-generation-attempts", type=int, default=100)
    add_ieee8500_scenario_args(parser)

    parser.add_argument("--use-learning-detectors", action="store_true")
    parser.add_argument("--learning-detector-dir", default="8500bus/paper_results/learning_detectors")
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


def target_entries(experiment, family):
    families = {"voltage", "branchflow"} if family == "both" else {family}
    entries = [
        entry
        for entry in build_observation_registry(experiment)
        if entry.family in families and entry.attackable and entry.current_grl_input
    ]
    family_order = {"voltage": 0, "branchflow": 1}
    return sorted(
        entries,
        key=lambda entry: (family_order.get(entry.family, 99), str(entry.observation_id)),
    )


def selected_targets(all_targets, args):
    start = max(0, int(args.target_start_index))
    if start > len(all_targets):
        raise ValueError(
            "target_start_index {} exceeds target count {}.".format(start, len(all_targets))
        )
    if int(args.target_count) > 0:
        end = min(start + int(args.target_count), len(all_targets))
    elif int(args.max_targets) > 0:
        end = min(start + int(args.max_targets), len(all_targets))
    else:
        end = len(all_targets)
    return start, end, all_targets[start:end]


def scenario_seeds(args):
    rng = np.random.default_rng(int(args.seed))
    for _case_index in range(int(args.cases)):
        scenario_seed = int(rng.integers(1, 2**31 - 1))
        yield scenario_seed
        if args.seed_schedule == "baseline_attack":
            for _draw_index in range(int(args.baseline_case_seed_draws)):
                rng.integers(1, 2**31 - 1)


def normalize_system(rows):
    for row in rows:
        row["system"] = "8500bus"
    return rows


def case_summary(case_id, scenario, target_entry, result, args):
    row = measurement34.case_summary(case_id, scenario, target_entry, result, args)
    row["system"] = "8500bus"
    return row


def step_rows(case_id, scenario, target_entry, result):
    return normalize_system(measurement34.step_rows(case_id, scenario, target_entry, result))


def output_paths(output_dir, write_step_results):
    paths = {
        "case_summary": output_dir / "tsg_ieee8500_measurement_criticality_cases.csv",
        "criticality_ranking": output_dir / "tsg_ieee8500_measurement_criticality_ranking.csv",
        "family_summary": output_dir / "tsg_ieee8500_measurement_criticality_family_summary.csv",
        "manifest": output_dir / "tsg_ieee8500_measurement_criticality_manifest.json",
    }
    if write_step_results:
        paths["step_results"] = output_dir / "tsg_ieee8500_measurement_criticality_steps.csv"
    return paths


def main():
    args = parse_args()
    output_dir = resolve_path(
        controller_output_dir(args.output_dir, DEFAULT_OUTPUT_DIR, SYSTEM_NAME, args.controller)
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = output_paths(output_dir, args.write_step_results)

    if args.merge_case_files is not None:
        case_rows = measurement34.load_case_rows(args.merge_case_files)
        if not case_rows:
            raise ValueError("No case rows were found in --merge-case-files inputs.")
        normalize_system(case_rows)
        criticality_rows = measurement34.aggregate_criticality(case_rows)
        family_rows = measurement34.aggregate_by_family(case_rows)
        write_csv(case_rows, paths["case_summary"])
        write_csv(criticality_rows, paths["criticality_ranking"])
        write_csv(family_rows, paths["family_summary"])
        manifest = {
            "experiment": "IEEE 8500-node named voltage/branchflow observation criticality study",
            "system": "8500bus",
            **controller_metadata(SYSTEM_NAME, args),
            "merge_case_files": [str(path) for path in args.merge_case_files],
            "case_row_count": len(case_rows),
            "criticality_row_count": len(criticality_rows),
            "family_summary_row_count": len(family_rows),
            "outputs": {key: str(value) for key, value in paths.items()},
            "ieee34_freeze_boundary": "IEEE 34 is frozen; this runner writes only under tsg_ieee8500.",
        }
        paths["manifest"].write_text(safe_json(manifest) + "\n")
        print("wrote {}".format(paths["criticality_ranking"]), flush=True)
        return

    registry_experiment = make_controller_experiment(SYSTEM_NAME, args, load_model=False)
    registry_outputs = write_registry_outputs(registry_experiment, output_dir / "registries")

    learning_detectors = []
    if args.use_learning_detectors:
        learning_detectors = load_learning_detectors(
            resolve_path(args.learning_detector_dir),
            tasks=args.learning_tasks,
            model_names=args.learning_models,
        )

    experiment = make_controller_experiment(SYSTEM_NAME, args, load_model=True)
    all_targets = target_entries(experiment, args.target_family)
    target_start, target_end, targets = selected_targets(all_targets, args)

    case_rows = []
    all_step_rows = []
    skipped_noop_count = 0

    for case_index, scenario_seed in enumerate(scenario_seeds(args)):
        scenario = generate_outage_scenario(experiment, scenario_seed, args)
        for target_index, target_entry in enumerate(targets):
            case_id = "ME{:04d}_T{:04d}_{}_seed{}".format(
                case_index,
                target_start + target_index,
                target_entry.observation_id.replace(".", "_"),
                scenario_seed,
            )
            print(
                "running {} target={}".format(case_id, target_entry.observation_id),
                flush=True,
            )
            result = measurement34.run_target_case(
                experiment,
                scenario,
                target_entry,
                learning_detectors,
                args,
            )
            if result is None:
                skipped_noop_count += 1
                continue
            case_rows.append(case_summary(case_id, scenario, target_entry, result, args))
            if args.write_step_results:
                all_step_rows.extend(step_rows(case_id, scenario, target_entry, result))

    criticality_rows = measurement34.aggregate_criticality(case_rows)
    family_rows = measurement34.aggregate_by_family(case_rows)

    write_csv(case_rows, paths["case_summary"])
    write_csv(criticality_rows, paths["criticality_ranking"])
    write_csv(family_rows, paths["family_summary"])
    if args.write_step_results:
        write_csv(all_step_rows, paths["step_results"])

    manifest = {
        "experiment": "IEEE 8500-node named voltage/branchflow observation criticality study",
        "system": "8500bus",
        **controller_metadata(SYSTEM_NAME, args),
        "cases": int(args.cases),
        "horizon": int(args.horizon),
        "step_hours": float(args.step_hours),
        "start_hour": int(args.start_hour),
        "seed": int(args.seed),
        "seed_schedule": args.seed_schedule,
        "baseline_case_seed_draws": int(args.baseline_case_seed_draws),
        "scenario_mode": "deterministic_outage_edges",
        "target_family": args.target_family,
        "voltage_attack_mode": args.voltage_attack_mode,
        "voltage_false_low": float(args.voltage_false_low),
        "voltage_false_high": float(args.voltage_false_high),
        "voltage_reported": float(args.voltage_reported),
        "branchflow_attack_mode": args.branchflow_attack_mode,
        "branchflow_hide_scale": float(args.branchflow_hide_scale),
        "branchflow_inflate_scale": float(args.branchflow_inflate_scale),
        "full_target_count": len(all_targets),
        "target_start_index": target_start,
        "target_end_index_exclusive": target_end,
        "target_count": len(targets),
        "case_row_count": len(case_rows),
        "executed_case_count": len(case_rows),
        "skipped_noop_count": int(skipped_noop_count),
        "criticality_row_count": len(criticality_rows),
        "family_summary_row_count": len(family_rows),
        "learning_detectors_enabled": bool(args.use_learning_detectors),
        "learning_detector_count": len(learning_detectors),
        "registry_outputs": {key: str(value) for key, value in registry_outputs.items()},
        "outputs": {key: str(value) for key, value in paths.items()},
        "ieee34_freeze_boundary": "IEEE 34 is frozen; this runner writes only under tsg_ieee8500.",
    }
    paths["manifest"].write_text(safe_json(manifest) + "\n")

    print("wrote {}".format(paths["case_summary"]), flush=True)
    print("wrote {}".format(paths["criticality_ranking"]), flush=True)
    print("wrote {}".format(paths["family_summary"]), flush=True)
    print("wrote {}".format(paths["manifest"]), flush=True)


if __name__ == "__main__":
    main()
