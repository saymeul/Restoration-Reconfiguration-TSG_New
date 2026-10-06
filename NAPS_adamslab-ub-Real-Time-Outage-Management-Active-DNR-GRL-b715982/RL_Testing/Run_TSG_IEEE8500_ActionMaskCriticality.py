"""IEEE 8500-node action-mask observation criticality study.

This is the IEEE 8500 counterpart to the frozen IEEE 34 action-mask study. It
attacks one named ActionMasking observation at a time and writes only under the
``tsg_ieee8500`` output namespace.
"""

import argparse
import csv
import numpy as np

import Run_TSG_IEEE34_ActionMaskCriticality as actionmask34
from FDIA_DetectorSuite import load_learning_detectors
from FDIA_ExperimentCore import RestorationExperiment, resolve_path, safe_json
from IEEE8500_VulnerabilityRegistry import build_observation_registry, write_registry_outputs
from Run_TSG_IEEE8500_Common import add_ieee8500_scenario_args, generate_outage_scenario
from TSG_ControllerConfig import (
    add_controller_args,
    controller_metadata,
    controller_output_dir,
    make_controller_experiment,
)


INT_CASE_FIELDS = {
    "scenario_seed",
    "scenario_generation_attempt",
    "scenario_radius",
    "scenario_subgraph_edge_count",
    "outage_edge_count",
    "target_action_index",
    "attack_applied",
    "damaging_case",
    "improvement_case",
    "fdia_detected",
    "bdd_detected",
    "learning_detected",
    "bypass_high_impact",
    "mitigation_detector_gate",
    "attacked_action_changed",
    "attacked_switch_changes_vs_clean",
    "attacked_load_changes_vs_clean",
    "mitigated_action_changed",
    "mitigated_switch_changes_vs_clean",
    "mitigated_load_changes_vs_clean",
}

FLOAT_CASE_FIELDS = {
    "scenario_outage_fraction",
    "clean_target_mask_value",
    "clean_target_action_value",
    "attacked_target_action_value",
    "mitigated_target_action_value",
    "clean_restored_energy_kwh",
    "attacked_restored_energy_kwh",
    "mitigated_restored_energy_kwh",
    "restored_energy_loss_kwh",
    "restored_energy_loss_ratio",
    "restored_energy_loss_percent",
    "physical_degradation_kwh",
    "physical_degradation_ratio",
    "physical_degradation_percent",
    "accidental_improvement_kwh",
    "residual_loss_after_mitigation_kwh",
    "residual_degradation_after_mitigation_kwh",
    "energy_recovered_kwh",
    "degradation_recovered_kwh",
    "mitigation_recovery_ratio",
    "mitigation_recovery_of_degradation_ratio",
    "mitigation_recovery_of_degradation_ratio_clipped",
    "detector_score",
    "learning_vote_fraction",
    "clean_policy_time_ms",
    "attacked_policy_time_ms",
    "mitigated_policy_time_ms",
    "clean_mean_energy_kw",
    "attacked_mean_energy_kw",
    "mitigated_mean_energy_kw",
    "clean_mean_voltage_violation",
    "attacked_mean_voltage_violation",
    "mitigated_mean_voltage_violation",
    "clean_mean_reward",
    "attacked_mean_reward",
    "mitigated_mean_reward",
}

SYSTEM_NAME = "8500bus"
DEFAULT_OUTPUT_DIR = "paper_results/tsg_ieee8500/action_mask_criticality"


def _csv_case_value(field, value):
    if value == "":
        return ""
    if field in INT_CASE_FIELDS:
        try:
            return int(float(value))
        except ValueError:
            return value
    if field in FLOAT_CASE_FIELDS:
        try:
            return float(value)
        except ValueError:
            return value
    return value


def load_case_rows(csv_paths):
    rows = []
    seen_case_ids = set()
    duplicate_case_ids = []
    for csv_path in csv_paths:
        path = resolve_path(csv_path)
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            for raw_row in reader:
                row = {field: _csv_case_value(field, value) for field, value in raw_row.items()}
                row["system"] = "8500bus"
                case_id = row.get("case_id")
                if case_id in seen_case_ids:
                    duplicate_case_ids.append(case_id)
                seen_case_ids.add(case_id)
                rows.append(row)
    if duplicate_case_ids:
        raise ValueError(
            "Duplicate case_id values found while merging chunks: {}".format(
                ", ".join(sorted(set(duplicate_case_ids))[:10])
            )
        )
    return rows


def parse_args():
    parser = argparse.ArgumentParser(
        description="IEEE 8500-node named ActionMasking observation criticality experiment."
    )
    parser.add_argument("--cases", type=int, default=3, help="Number of deterministic outage seeds.")
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
    parser.add_argument("--max-outage-fraction", type=float, default=0.50)
    parser.add_argument("--max-scenario-generation-attempts", type=int, default=100)
    add_ieee8500_scenario_args(parser)
    parser.add_argument(
        "--target-scope",
        choices=["switch", "load", "switch_and_load"],
        default="switch_and_load",
    )
    parser.add_argument(
        "--attack-mode",
        choices=["false_unavailable", "false_available"],
        default="false_unavailable",
    )
    parser.add_argument(
        "--include-noop",
        action="store_true",
        help="Keep rows where the requested corruption does not change the mask value.",
    )
    parser.add_argument("--max-targets", type=int, default=0)
    parser.add_argument("--target-start-index", type=int, default=0)
    parser.add_argument("--target-count", type=int, default=0)
    parser.add_argument("--merge-case-files", nargs="*")
    parser.add_argument("--write-step-results", action="store_true")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    add_controller_args(parser)
    parser.add_argument("--bypass-loss-threshold-kwh", type=float, default=1.0e-6)

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


def target_entries(experiment, scope):
    entries = [
        entry
        for entry in build_observation_registry(experiment)
        if entry.observation_key == "ActionMasking"
    ]
    if scope == "switch":
        entries = [
            entry
            for entry in entries
            if entry.component_type in ("sectionalizing_switch", "tie_switch")
        ]
    elif scope == "load":
        entries = [entry for entry in entries if entry.component_type == "dispatch_load"]
    else:
        entries = [
            entry
            for entry in entries
            if entry.component_type in ("sectionalizing_switch", "tie_switch", "dispatch_load")
        ]
    return sorted(entries, key=lambda entry: (int(entry.index[0]), str(entry.observation_id)))


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


def case_summary(case_id, scenario, target_entry, attack_mode, result, args):
    row = actionmask34.case_summary(case_id, scenario, target_entry, attack_mode, result, args)
    row["system"] = "8500bus"
    return row


def step_rows(case_id, scenario, target_entry, attack_mode, result):
    rows = actionmask34.step_rows(case_id, scenario, target_entry, attack_mode, result)
    for row in rows:
        row["system"] = "8500bus"
    return rows


def main():
    args = parse_args()
    output_dir = resolve_path(
        controller_output_dir(args.output_dir, DEFAULT_OUTPUT_DIR, SYSTEM_NAME, args.controller)
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "case_summary": output_dir / "tsg_ieee8500_action_mask_criticality_cases.csv",
        "criticality_ranking": output_dir / "tsg_ieee8500_action_mask_criticality_ranking.csv",
        "manifest": output_dir / "tsg_ieee8500_action_mask_criticality_manifest.json",
    }
    if args.write_step_results:
        paths["step_results"] = output_dir / "tsg_ieee8500_action_mask_criticality_steps.csv"

    if args.merge_case_files is not None:
        case_rows = load_case_rows(args.merge_case_files)
        if not case_rows:
            raise ValueError("No case rows were found in --merge-case-files inputs.")
        criticality_rows = actionmask34.aggregate_criticality(case_rows)
        actionmask34.write_csv_or_header(
            case_rows,
            paths["case_summary"],
            actionmask34.CASE_SUMMARY_FIELDS,
        )
        actionmask34.write_csv_or_header(
            criticality_rows,
            paths["criticality_ranking"],
            actionmask34.CRITICALITY_FIELDS,
        )
        manifest = {
            "experiment": "IEEE 8500-node named ActionMasking observation criticality study",
            "system": "8500bus",
            **controller_metadata(SYSTEM_NAME, args),
            "merge_case_files": [str(resolve_path(path)) for path in args.merge_case_files],
            "case_row_count": len(case_rows),
            "criticality_row_count": len(criticality_rows),
            "outputs": {key: str(value) for key, value in paths.items()},
            "ieee34_freeze_boundary": "IEEE 34 is frozen; this runner writes only under tsg_ieee8500.",
        }
        paths["manifest"].write_text(safe_json(manifest) + "\n")
        print("wrote {}".format(paths["case_summary"]), flush=True)
        print("wrote {}".format(paths["criticality_ranking"]), flush=True)
        print("wrote {}".format(paths["manifest"]), flush=True)
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
    all_targets = target_entries(experiment, args.target_scope)
    target_start, target_end, targets = selected_targets(all_targets, args)

    case_rows = []
    all_step_rows = []
    skipped_noop_count = 0

    for case_index, scenario_seed in enumerate(scenario_seeds(args)):
        scenario = generate_outage_scenario(experiment, scenario_seed, args)
        for target_index, target_entry in enumerate(targets):
            case_id = "AM{:04d}_T{:04d}_{}_seed{}".format(
                case_index,
                target_start + target_index,
                target_entry.observation_id.replace(".", "_"),
                scenario_seed,
            )
            print(
                "running {} target={}".format(case_id, target_entry.observation_id),
                flush=True,
            )
            result = actionmask34.run_target_case(
                experiment,
                scenario,
                target_entry,
                args.attack_mode,
                learning_detectors,
                args,
            )
            if result is None:
                skipped_noop_count += 1
                continue
            case_rows.append(case_summary(case_id, scenario, target_entry, args.attack_mode, result, args))
            if args.write_step_results:
                all_step_rows.extend(step_rows(case_id, scenario, target_entry, args.attack_mode, result))

    criticality_rows = actionmask34.aggregate_criticality(case_rows)
    actionmask34.write_csv_or_header(
        case_rows,
        paths["case_summary"],
        actionmask34.CASE_SUMMARY_FIELDS,
    )
    actionmask34.write_csv_or_header(
        criticality_rows,
        paths["criticality_ranking"],
        actionmask34.CRITICALITY_FIELDS,
    )
    if args.write_step_results:
        actionmask34.write_csv_or_header(
            all_step_rows,
            paths["step_results"],
            actionmask34.STEP_RESULT_FIELDS,
        )

    manifest = {
        "experiment": "IEEE 8500-node named ActionMasking observation criticality study",
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
        "target_scope": args.target_scope,
        "attack_mode": args.attack_mode,
        "full_target_count": len(all_targets),
        "target_start_index": int(target_start),
        "target_end_index_exclusive": int(target_end),
        "target_count": len(targets),
        "case_row_count": len(case_rows),
        "executed_case_count": len(case_rows),
        "skipped_noop_count": int(skipped_noop_count),
        "criticality_row_count": len(criticality_rows),
        "learning_detectors_enabled": bool(args.use_learning_detectors),
        "learning_detector_count": len(learning_detectors),
        "registry_outputs": {key: str(value) for key, value in registry_outputs.items()},
        "outputs": {key: str(value) for key, value in paths.items()},
        "ieee34_freeze_boundary": "IEEE 34 is frozen; this runner writes only under tsg_ieee8500.",
    }
    paths["manifest"].write_text(safe_json(manifest) + "\n")

    print("wrote {}".format(paths["case_summary"]), flush=True)
    print("wrote {}".format(paths["criticality_ranking"]), flush=True)
    print("wrote {}".format(paths["manifest"]), flush=True)


if __name__ == "__main__":
    main()
