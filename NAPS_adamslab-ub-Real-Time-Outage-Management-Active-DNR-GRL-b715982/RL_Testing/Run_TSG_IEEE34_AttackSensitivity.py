"""IEEE 34-bus attack sensitivity study for TSG vulnerability assessment.

This runner sweeps attack severity settings while keeping the physical outage
scenario deterministic. Each case corrupts only the controller observation; the
clean, attacked, and mitigated actions are evaluated on the same explicit
OpenDSS outage-edge scenario.
"""

import argparse
from argparse import Namespace

import numpy as np

from FDIA_DetectorSuite import load_learning_detectors
from FDIA_ExperimentCore import (
    RestorationExperiment,
    resolve_path,
    safe_json,
    write_csv,
)
from IEEE34_VulnerabilityRegistry import write_registry_outputs
from Run_TSG_IEEE34_BaselineAttackStudy import (
    BASE_ATTACKS,
    case_summary,
    generate_outage_scenario,
    run_case,
    step_rows,
)
from TSG_ControllerConfig import (
    add_controller_args,
    controller_metadata,
    controller_output_dir,
    make_controller_experiment,
)


PARAMETER_COLUMNS = [
    "topology_drop_fraction",
    "action_mask_fraction",
    "action_mask_scope",
    "voltage_target_fraction",
    "voltage_reported",
    "branchflow_target_fraction",
    "branchflow_scale",
    "energy_bias",
    "energy_max_reported",
]

SYSTEM_NAME = "34bus"
DEFAULT_OUTPUT_DIR = "paper_results/tsg_ieee34/attack_sensitivity"


def parse_args():
    parser = argparse.ArgumentParser(
        description="IEEE 34-bus deterministic attack-severity sensitivity study."
    )
    parser.add_argument("--cases", type=int, default=30, help="Number of deterministic outage scenarios.")
    parser.add_argument("--seed", type=int, default=20260615)
    parser.add_argument("--attacks", nargs="+", default=BASE_ATTACKS)
    parser.add_argument("--levels", nargs="+", type=int, default=[1, 2, 3, 4, 5])
    parser.add_argument("--max-configs", type=int, default=0, help="Optional smoke-test limit on sweep configs.")
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--step-hours", type=float, default=1.0)
    parser.add_argument("--start-hour", type=int, default=0)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    add_controller_args(parser)
    parser.add_argument("--write-step-results", action="store_true")

    parser.add_argument("--max-outage-fraction", type=float, default=0.50)
    parser.add_argument("--max-scenario-generation-attempts", type=int, default=100)
    parser.add_argument("--bypass-loss-threshold-kwh", type=float, default=1.0e-6)

    parser.add_argument("--use-learning-detectors", action="store_true")
    parser.add_argument("--learning-detector-dir", default="34bus/paper_results/learning_detectors")
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


def sensitivity_specs():
    specs = []

    for level, fraction in enumerate([0.01, 0.03, 0.05, 0.10, 0.15], start=1):
        specs.append(
            {
                "attack": "topology_drop",
                "sensitivity_level": level,
                "sensitivity_id": "topology_drop_L{}".format(level),
                "sensitivity_description": "drop_fraction={:.2f}".format(fraction),
                "severity_score": float(level) / 5.0,
                "parameters": {"topology_drop_fraction": fraction},
            }
        )

    for level, fraction in enumerate([0.10, 0.25, 0.50, 0.75, 1.00], start=1):
        specs.append(
            {
                "attack": "action_mask_false_unavailable",
                "sensitivity_level": level,
                "sensitivity_id": "action_mask_false_unavailable_L{}".format(level),
                "sensitivity_description": "mask_fraction={:.2f},scope=switch".format(fraction),
                "severity_score": float(level) / 5.0,
                "parameters": {
                    "action_mask_fraction": fraction,
                    "action_mask_scope": "switch",
                },
            }
        )

    for level, fraction in enumerate([0.05, 0.10, 0.20, 0.40, 0.60], start=1):
        specs.append(
            {
                "attack": "voltage_masking",
                "sensitivity_level": level,
                "sensitivity_id": "voltage_masking_L{}".format(level),
                "sensitivity_description": "target_fraction={:.2f},reported_voltage=1.00".format(fraction),
                "severity_score": float(level) / 5.0,
                "parameters": {
                    "voltage_target_fraction": fraction,
                    "voltage_reported": 1.0,
                },
            }
        )

    branchflow_levels = [
        (0.05, 0.75),
        (0.10, 0.50),
        (0.20, 0.25),
        (0.40, 0.10),
        (0.60, 0.00),
    ]
    for level, (fraction, scale) in enumerate(branchflow_levels, start=1):
        specs.append(
            {
                "attack": "branchflow_hiding",
                "sensitivity_level": level,
                "sensitivity_id": "branchflow_hiding_L{}".format(level),
                "sensitivity_description": "target_fraction={:.2f},scale={:.2f}".format(fraction, scale),
                "severity_score": float(level) / 5.0,
                "parameters": {
                    "branchflow_target_fraction": fraction,
                    "branchflow_scale": scale,
                },
            }
        )

    for level, bias in enumerate([0.05, 0.10, 0.25, 0.40, 0.60], start=1):
        specs.append(
            {
                "attack": "energy_inflation",
                "sensitivity_level": level,
                "sensitivity_id": "energy_inflation_L{}".format(level),
                "sensitivity_description": "bias={:.2f},max_reported={:.2f}".format(bias, 1.0 + bias),
                "severity_score": float(level) / 5.0,
                "parameters": {
                    "energy_bias": bias,
                    "energy_max_reported": 1.0 + bias,
                },
            }
        )

    return specs


def selected_specs(args):
    attacks = set(args.attacks)
    levels = set(int(level) for level in args.levels)
    specs = [
        spec
        for spec in sensitivity_specs()
        if spec["attack"] in attacks and int(spec["sensitivity_level"]) in levels
    ]
    specs.sort(key=lambda spec: (BASE_ATTACKS.index(spec["attack"]), spec["sensitivity_level"]))
    if int(args.max_configs) > 0:
        specs = specs[: int(args.max_configs)]
    return specs


def args_for_spec(base_args, spec):
    case_args = Namespace(**vars(base_args))

    # Defaults match Run_TSG_IEEE34_BaselineAttackStudy.py.
    case_args.topology_drop_fraction = 0.05
    case_args.action_mask_fraction = 0.25
    case_args.action_mask_scope = "switch"
    case_args.voltage_target_fraction = 0.20
    case_args.voltage_reported = 1.0
    case_args.branchflow_target_fraction = 0.20
    case_args.branchflow_scale = 0.25
    case_args.energy_bias = 0.25
    case_args.energy_max_reported = 1.25

    for key, value in spec["parameters"].items():
        setattr(case_args, key, value)
    return case_args


def empty_parameter_row():
    return {column: "" for column in PARAMETER_COLUMNS}


def parameter_row(spec, case_args):
    row = empty_parameter_row()
    for column in PARAMETER_COLUMNS:
        if hasattr(case_args, column):
            row[column] = getattr(case_args, column)
    row["attack_parameters"] = dict(spec["parameters"])
    return row


def add_sensitivity_metadata(row, spec, case_args):
    row.update(
        {
            "sensitivity_id": spec["sensitivity_id"],
            "sensitivity_level": int(spec["sensitivity_level"]),
            "severity_score": float(spec["severity_score"]),
            "sensitivity_description": spec["sensitivity_description"],
        }
    )
    row.update(parameter_row(spec, case_args))
    return row


def aggregate_sensitivity(case_rows):
    groups = {}
    for row in case_rows:
        key = (row["attack"], row["sensitivity_id"])
        groups.setdefault(key, []).append(row)

    aggregates = []
    for (attack, sensitivity_id), rows in sorted(groups.items()):
        damaging_rows = [row for row in rows if int(row["damaging_case"]) == 1]
        improvement_rows = [row for row in rows if int(row["improvement_case"]) == 1]
        degradation_recovery_values = [
            row["mitigation_recovery_of_degradation_ratio"] for row in damaging_rows
        ]
        degradation_recovery_clipped_values = [
            row["mitigation_recovery_of_degradation_ratio_clipped"] for row in damaging_rows
        ]
        representative = rows[0]
        aggregate = {
            "attack": attack,
            "sensitivity_id": sensitivity_id,
            "sensitivity_level": int(representative["sensitivity_level"]),
            "severity_score": float(representative["severity_score"]),
            "sensitivity_description": representative["sensitivity_description"],
            "case_count": len(rows),
            "mean_physical_degradation_kwh": float(
                np.mean([row["physical_degradation_kwh"] for row in rows])
            ),
            "total_physical_degradation_kwh": float(
                np.sum([row["physical_degradation_kwh"] for row in rows])
            ),
            "max_physical_degradation_kwh": float(
                np.max([row["physical_degradation_kwh"] for row in rows])
            ),
            "mean_physical_degradation_percent": float(
                np.mean([row["physical_degradation_percent"] for row in rows])
            ),
            "damaging_case_count": len(damaging_rows),
            "damaging_case_rate": float(len(damaging_rows) / len(rows)) if rows else 0.0,
            "mean_restored_energy_loss_kwh": float(
                np.mean([row["restored_energy_loss_kwh"] for row in rows])
            ),
            "max_restored_energy_loss_kwh": float(
                np.max([row["restored_energy_loss_kwh"] for row in rows])
            ),
            "mean_accidental_improvement_kwh": float(
                np.mean([row["accidental_improvement_kwh"] for row in rows])
            ),
            "max_accidental_improvement_kwh": float(
                np.max([row["accidental_improvement_kwh"] for row in rows])
            ),
            "improvement_case_count": len(improvement_rows),
            "improvement_case_rate": float(len(improvement_rows) / len(rows)) if rows else 0.0,
            "mean_residual_degradation_after_mitigation_kwh": float(
                np.mean([row["residual_degradation_after_mitigation_kwh"] for row in rows])
            ),
            "mean_mitigation_recovery_of_degradation_ratio": float(
                np.mean(degradation_recovery_values)
                if degradation_recovery_values
                else 0.0
            ),
            "mean_mitigation_recovery_of_degradation_ratio_clipped": float(
                np.mean(degradation_recovery_clipped_values)
                if degradation_recovery_clipped_values
                else 0.0
            ),
            "mean_mitigation_recovery_ratio": float(
                np.mean([row["mitigation_recovery_ratio"] for row in rows])
            ),
            "detection_rate": float(np.mean([row["fdia_detected"] for row in rows])),
            "bypass_high_impact_rate": float(np.mean([row["bypass_high_impact"] for row in rows])),
            "mean_attacked_switch_changes_vs_clean": float(
                np.mean([row["attacked_switch_changes_vs_clean"] for row in rows])
            ),
            "mean_attacked_load_changes_vs_clean": float(
                np.mean([row["attacked_load_changes_vs_clean"] for row in rows])
            ),
        }
        for column in PARAMETER_COLUMNS:
            aggregate[column] = representative.get(column, "")
        aggregate["attack_parameters"] = representative.get("attack_parameters", {})
        aggregates.append(aggregate)

    curve_rows = sorted(
        aggregates,
        key=lambda row: (BASE_ATTACKS.index(row["attack"]), row["sensitivity_level"]),
    )
    ranking_rows = sorted(
        aggregates,
        key=lambda row: (
            row["mean_physical_degradation_kwh"],
            row["max_physical_degradation_kwh"],
            row["damaging_case_rate"],
        ),
        reverse=True,
    )
    for index, row in enumerate(ranking_rows, start=1):
        row["damage_rank"] = index
    return curve_rows, ranking_rows


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
    specs = selected_specs(args)
    if not specs:
        raise RuntimeError("No sensitivity configurations selected.")

    rng = np.random.default_rng(int(args.seed))
    scenarios = []
    for case_index in range(int(args.cases)):
        scenario_seed = int(rng.integers(1, 2**31 - 1))
        scenarios.append((case_index, generate_outage_scenario(experiment, scenario_seed, args)))

    case_rows = []
    all_step_rows = []
    for spec_index, spec in enumerate(specs):
        case_args = args_for_spec(args, spec)
        for case_index, scenario in scenarios:
            case_seed = int(rng.integers(1, 2**31 - 1))
            case_id = "S{:02d}_C{:04d}_{}_seed{}".format(
                spec_index,
                case_index,
                spec["sensitivity_id"],
                scenario["scenario_seed"],
            )
            print(
                "running {} attack={} {}".format(
                    case_id,
                    spec["attack"],
                    spec["sensitivity_description"],
                ),
                flush=True,
            )
            result = run_case(
                experiment,
                scenario,
                spec["attack"],
                case_seed + spec_index,
                learning_detectors,
                case_args,
            )
            summary = case_summary(case_id, scenario, spec["attack"], result, case_args)
            case_rows.append(add_sensitivity_metadata(summary, spec, case_args))
            if args.write_step_results:
                for step_row in step_rows(case_id, scenario, spec["attack"], result):
                    all_step_rows.append(add_sensitivity_metadata(step_row, spec, case_args))

    curve_rows, ranking_rows = aggregate_sensitivity(case_rows)

    paths = {
        "case_summary": output_dir / "tsg_ieee34_attack_sensitivity_cases.csv",
        "sensitivity_curve": output_dir / "tsg_ieee34_attack_sensitivity_curve.csv",
        "sensitivity_ranking": output_dir / "tsg_ieee34_attack_sensitivity_ranking.csv",
        "manifest": output_dir / "tsg_ieee34_attack_sensitivity_manifest.json",
    }
    if args.write_step_results:
        paths["step_results"] = output_dir / "tsg_ieee34_attack_sensitivity_steps.csv"

    write_csv(case_rows, paths["case_summary"])
    write_csv(curve_rows, paths["sensitivity_curve"])
    write_csv(ranking_rows, paths["sensitivity_ranking"])
    if args.write_step_results:
        write_csv(all_step_rows, paths["step_results"])

    manifest = {
        "experiment": "IEEE 34-bus deterministic attack sensitivity study",
        "system": "34bus",
        **controller_metadata(SYSTEM_NAME, args),
        "cases": int(args.cases),
        "horizon": int(args.horizon),
        "step_hours": float(args.step_hours),
        "start_hour": int(args.start_hour),
        "seed": int(args.seed),
        "scenario_mode": "deterministic_outage_edges",
        "max_outage_fraction": float(args.max_outage_fraction),
        "selected_attacks": args.attacks,
        "selected_levels": [int(level) for level in args.levels],
        "sensitivity_config_count": len(specs),
        "sensitivity_configs": specs,
        "executed_case_count": len(case_rows),
        "write_step_results": bool(args.write_step_results),
        "learning_detectors_enabled": bool(args.use_learning_detectors),
        "learning_detector_count": len(learning_detectors),
        "registry_outputs": {key: str(value) for key, value in registry_outputs.items()},
        "outputs": {key: str(value) for key, value in paths.items()},
        "notes": (
            "Attacks corrupt only controller observations. Clean, attacked, and mitigated "
            "actions are evaluated on the same explicit OpenDSS outage-edge scenarios. "
            "Damage ranking uses positive restored-energy degradation; signed restored-energy "
            "loss and accidental improvement are reported separately."
        ),
    }
    paths["manifest"].write_text(safe_json(manifest) + "\n")

    print("wrote {}".format(paths["case_summary"]), flush=True)
    print("wrote {}".format(paths["sensitivity_curve"]), flush=True)
    print("wrote {}".format(paths["sensitivity_ranking"]), flush=True)
    print("wrote {}".format(paths["manifest"]), flush=True)


if __name__ == "__main__":
    main()
