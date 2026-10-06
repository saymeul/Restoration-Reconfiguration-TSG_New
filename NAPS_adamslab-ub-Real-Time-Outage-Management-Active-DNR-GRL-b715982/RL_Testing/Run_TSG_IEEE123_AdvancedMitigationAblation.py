"""IEEE 123 advanced mitigation ablation on hard residual FDIA cases.

The defense-stress audit showed that the damaging IEEE 123 cases completed so
far are detected, but a few detected cases keep nonzero residual restoration
loss after the current FDIA-aware mitigation. This runner reruns those hard
cases and compares the current one-step mitigation with stronger, explicitly
defined mitigation variants.

The trained restoration controller and attack definitions are not modified.
Attacks still corrupt only the observation supplied to the controller; every
candidate restoration action is evaluated on the same OpenDSS outage scenario.
"""

import argparse
import ast
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

import Run_TSG_IEEE34_BaselineAttackStudy as baseline
import Run_TSG_IEEE34_ActionMaskCriticality as actionmask34
import Run_TSG_IEEE34_MeasurementCriticality as measurement34
import Run_TSG_IEEE123_ActionMaskCriticality as actionmask123
import Run_TSG_IEEE123_MeasurementCriticality as measurement123
from FDIA_Common import (
    apply_attack,
    clone_observation,
    mitigate_observation,
    select_fdia_aware_grl_action,
)
from FDIA_DetectorSuite import load_learning_detectors, run_detector_suite
from FDIA_ExperimentCore import action_delta, resolve_path, safe_json, write_csv
from IEEE123_VulnerabilityRegistry import write_registry_outputs
from TSG_ControllerConfig import (
    add_controller_args,
    controller_metadata,
    controller_output_dir,
    make_controller_experiment,
)


SYSTEM_NAME = "123bus"
DEFAULT_OUTPUT_DIR = "paper_results/tsg_ieee123/advanced_mitigation_ablation"


VARIANT_FIELDS = [
    "source_study",
    "source_case_id",
    "source_attack_group",
    "source_attack",
    "target_observation_id",
    "subset_k",
    "scenario_seed",
    "variant",
    "variant_family",
    "selected_candidate",
    "candidate_pool",
    "fdia_detected",
    "detector_score",
    "detected_channels",
    "clean_restored_energy_kwh",
    "attacked_restored_energy_kwh",
    "variant_restored_energy_kwh",
    "attacked_physical_degradation_kwh",
    "variant_residual_degradation_kwh",
    "variant_degradation_recovered_kwh",
    "variant_recovery_ratio_clipped",
    "current_residual_degradation_kwh",
    "residual_reduction_vs_current_kwh",
    "residual_reduction_vs_current_ratio",
    "variant_action_changed_vs_clean",
    "variant_switch_changes_vs_clean",
    "variant_load_changes_vs_clean",
    "variant_action_changed_vs_attacked",
    "variant_switch_changes_vs_attacked",
    "variant_load_changes_vs_attacked",
    "variant_quality_rank_key",
    "source_physical_degradation_kwh",
    "source_residual_degradation_after_mitigation_kwh",
    "attack_metadata",
    "variant_action",
]

SUMMARY_FIELDS = [
    "variant",
    "variant_family",
    "case_count",
    "total_attacked_physical_degradation_kwh",
    "total_variant_residual_degradation_kwh",
    "mean_variant_residual_degradation_kwh",
    "max_variant_residual_degradation_kwh",
    "total_variant_degradation_recovered_kwh",
    "total_recovery_ratio_clipped",
    "mean_recovery_ratio_clipped",
    "cases_improved_vs_current",
    "cases_equal_vs_current",
    "cases_worse_vs_current",
    "total_residual_reduction_vs_current_kwh",
    "mean_residual_reduction_vs_current_kwh",
]

CASE_BEST_FIELDS = [
    "source_study",
    "source_case_id",
    "source_attack_group",
    "source_attack",
    "target_observation_id",
    "subset_k",
    "scenario_seed",
    "best_variant",
    "best_variant_family",
    "best_residual_degradation_kwh",
    "current_residual_degradation_kwh",
    "attacked_physical_degradation_kwh",
    "best_residual_reduction_vs_current_kwh",
    "best_recovery_ratio_clipped",
]

STEP_FIELDS = [
    "source_study",
    "source_case_id",
    "source_attack_group",
    "scenario_seed",
    "variant",
    "time_step",
    "hour",
    "energy_kw",
    "energy_ratio",
    "voltage_violation",
    "convergence_violation",
    "reward",
    "loads_served",
    "loads_shed",
]

EPS = 1.0e-9


def parse_args():
    parser = argparse.ArgumentParser(
        description="IEEE 123 advanced mitigation ablation for hard residual FDIA cases."
    )
    parser.add_argument(
        "--low-recovery-cases",
        default=(
            "paper_results/tsg_ieee123/defense_stress_summary/"
            "tsg_ieee123_defense_stress_low_recovery_cases.csv"
        ),
    )
    parser.add_argument(
        "--baseline-cases",
        default=(
            "paper_results/tsg_ieee123/baseline_attack_full_deterministic/"
            "tsg_ieee123_case_summary.csv"
        ),
    )
    parser.add_argument(
        "--branchflow-subset-cases",
        default=(
            "paper_results/tsg_ieee123/branchflow_subset_ablation/"
            "tsg_ieee123_branchflow_subset_ablation_cases.csv"
        ),
    )
    parser.add_argument(
        "--branchflow-single-cases",
        default=(
            "paper_results/tsg_ieee123/full_criticality_merged_partial/branchflow/"
            "tsg_ieee123_measurement_criticality_cases.csv"
        ),
    )
    parser.add_argument(
        "--action-mask-cases",
        default=(
            "paper_results/tsg_ieee123/full_criticality_merged_partial/action_mask/"
            "tsg_ieee123_action_mask_criticality_cases.csv"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
    )
    parser.add_argument("--max-cases", type=int, default=0)
    parser.add_argument("--min-source-residual-kwh", type=float, default=0.0)
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--step-hours", type=float, default=1.0)
    parser.add_argument("--start-hour", type=int, default=0)
    parser.add_argument("--max-outage-fraction", type=float, default=0.50)
    parser.add_argument("--max-scenario-generation-attempts", type=int, default=100)
    parser.add_argument("--bypass-loss-threshold-kwh", type=float, default=1.0e-6)
    parser.add_argument("--no-step-results", action="store_true")
    add_controller_args(parser)

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


def _float(row, field, default=0.0):
    try:
        value = row.get(field, default)
        if value == "":
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _int(row, field, default=0):
    try:
        value = row.get(field, default)
        if value == "":
            return int(default)
        return int(float(value))
    except (TypeError, ValueError):
        return int(default)


def _jsonish(value):
    if value in (None, ""):
        return {}
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        try:
            parsed = ast.literal_eval(value)
            return parsed if isinstance(parsed, dict) else {}
        except (SyntaxError, ValueError):
            return {}


def read_csv_rows(path):
    resolved = resolve_path(path)
    if not resolved.exists():
        return []
    with resolved.open(newline="") as handle:
        return list(csv.DictReader(handle))


def load_case_map(path):
    return {row["case_id"]: row for row in read_csv_rows(path)}


def load_hard_cases(args):
    rows = read_csv_rows(args.low_recovery_cases)
    rows = [
        row
        for row in rows
        if _float(row, "residual_degradation_after_mitigation_kwh")
        > float(args.min_source_residual_kwh)
    ]
    rows.sort(
        key=lambda row: (
            _float(row, "residual_degradation_after_mitigation_kwh"),
            _float(row, "physical_degradation_kwh"),
        ),
        reverse=True,
    )
    if int(args.max_cases) > 0:
        rows = rows[: int(args.max_cases)]
    return rows


def source_row_for_hard_case(hard_case, source_maps):
    case_id = hard_case["case_id"]
    source_study = hard_case["source_study"]
    if source_study == "baseline_attack_family":
        source_row = source_maps["baseline"].get(case_id)
    elif source_study == "branchflow_coordinated_subset_ablation":
        source_row = source_maps["branchflow_subset"].get(case_id)
    elif source_study == "branchflow_single_criticality_partial":
        source_row = source_maps["branchflow_single"].get(case_id)
    elif source_study == "action_mask_single_criticality_partial":
        source_row = source_maps["action_mask"].get(case_id)
    else:
        source_row = None
    if source_row is None:
        raise ValueError("No source row found for hard case {}".format(case_id))
    return source_row


def corrupt_action_mask_from_metadata(true_obs, metadata):
    attacked = clone_observation(true_obs)
    mask = np.asarray(attacked["ActionMasking"], dtype=float).reshape(-1).copy()
    selected = metadata.get("selected_action_indices", [])
    for action_index in selected:
        mask[int(action_index)] = 1.0
    attacked["ActionMasking"] = mask
    replay_metadata = dict(metadata)
    replay_metadata["replayed_from_metadata"] = True
    return attacked, replay_metadata


def corrupt_branchflow_subset_from_metadata(true_obs, metadata):
    attacked = clone_observation(true_obs)
    flows = np.asarray(attacked["EdgeFeat(Branchflow)"], dtype=float).reshape(-1)
    selected = np.asarray(metadata.get("selected_measurement_indices", []), dtype=int)
    scale = float(metadata.get("scale", 0.25))
    original = flows[selected].copy() if selected.size else np.asarray([])
    flows[selected] = flows[selected] * scale
    replay_metadata = dict(metadata)
    replay_metadata["replayed_from_metadata"] = True
    replay_metadata["mean_abs_change_replayed"] = (
        float(np.mean(np.abs(original - flows[selected]))) if selected.size else 0.0
    )
    return attacked, replay_metadata


def corrupt_action_mask_target(true_obs, source_row, target_by_id):
    target_id = source_row.get("target_observation_id", "")
    attack_mode = source_row.get("attack_mode", "false_unavailable")
    target_entry = target_by_id.get(target_id)
    if target_entry is None:
        raise ValueError("Unknown action-mask target {}".format(target_id))
    return actionmask34.corrupt_action_mask_entry(true_obs, target_entry, attack_mode)


def corrupt_branchflow_single_target(true_obs, source_row, target_by_id):
    target_id = source_row.get("target_observation_id", "")
    target_entry = target_by_id.get(target_id)
    if target_entry is None:
        raise ValueError("Unknown branchflow target {}".format(target_id))

    attacked = clone_observation(true_obs)
    flows = np.asarray(attacked["EdgeFeat(Branchflow)"], dtype=float).copy()
    branch_index = int(target_entry.index[0])
    original = float(np.nan_to_num(flows[branch_index], nan=0.0, posinf=0.0, neginf=0.0))
    source_metadata = _jsonish(source_row.get("attack_metadata", ""))

    attacked_value = source_row.get("attacked_value", "")
    if attacked_value not in ("", None):
        corrupted = _float(source_row, "attacked_value", original)
    elif "attacked_value" in source_metadata:
        try:
            corrupted = float(source_metadata["attacked_value"])
        except (TypeError, ValueError):
            corrupted = original
    else:
        attack_name = source_row.get("attack", source_metadata.get("attack", "branchflow_hide"))
        if attack_name == "branchflow_inflate":
            corrupted = original * float(source_metadata.get("branchflow_inflate_scale", 2.0))
        else:
            corrupted = original * float(source_metadata.get("branchflow_hide_scale", 0.0))

    flows[branch_index] = corrupted
    attacked["EdgeFeat(Branchflow)"] = flows
    changed = abs(float(corrupted) - original) > EPS
    replay_metadata = {
        "target": "EdgeFeat(Branchflow)",
        "attack": source_row.get("attack", source_metadata.get("attack", "branchflow_hide")),
        "target_observation_id": target_entry.observation_id,
        "target_component_type": target_entry.component_type,
        "target_component_name": target_entry.component_name,
        "target_index": branch_index,
        "changed_measurements": int(changed),
        "attack_applied": int(changed),
        "original_value": original,
        "attacked_value": float(corrupted),
        "mean_abs_change": abs(float(corrupted) - original),
        "max_abs_change": abs(float(corrupted) - original),
        "replayed_from_source_case_id": source_row.get("case_id", ""),
    }
    if source_metadata:
        replay_metadata["source_attack_metadata"] = source_metadata
    return attacked, replay_metadata


def replay_attack(true_obs, hard_case, source_row, target_maps):
    source_study = hard_case["source_study"]
    metadata = _jsonish(source_row.get("attack_metadata", ""))
    if source_study == "baseline_attack_family":
        attack_name = source_row.get("attack", hard_case.get("attack", ""))
        if attack_name == "action_mask_false_unavailable":
            return corrupt_action_mask_from_metadata(true_obs, metadata)
        kwargs = metadata.get("attack_kwargs", {})
        attacked, attack_metadata = apply_attack(clone_observation(true_obs), attack_name, **kwargs)
        attack_metadata["attack_kwargs"] = kwargs
        attack_metadata["replayed_from_metadata"] = True
        return attacked, attack_metadata
    if source_study == "branchflow_coordinated_subset_ablation":
        return corrupt_branchflow_subset_from_metadata(true_obs, metadata)
    if source_study == "branchflow_single_criticality_partial":
        attacked, attack_metadata = corrupt_branchflow_single_target(
            true_obs,
            source_row,
            target_maps["branchflow"],
        )
        return attacked, attack_metadata
    if source_study == "action_mask_single_criticality_partial":
        attacked, attack_metadata = corrupt_action_mask_target(
            true_obs,
            source_row,
            target_maps["action_mask"],
        )
        attack_metadata["replayed_from_source_case_id"] = source_row.get("case_id", "")
        return attacked, attack_metadata
    raise ValueError("Unsupported source study {}".format(source_study))


def energy_summary(trajectory, step_hours):
    return baseline.trajectory_energy_summary(trajectory, step_hours)


def trajectory_sort_key(summary):
    return (
        int(summary["valid_step_count"]),
        float(summary["restored_energy_kwh"]),
        -float(summary["mean_voltage_violation"]),
        float(summary["mean_reward"]),
    )


def trajectory_sort_key_text(summary):
    key = trajectory_sort_key(summary)
    return "{}/{:.9f}/{:.9f}/{:.9f}".format(key[0], key[1], key[2], key[3])


def add_unique_candidate(candidates, seen_actions, name, action, policy_time_ms):
    action = np.asarray(action, dtype=int)
    key = tuple(int(value) for value in action.reshape(-1))
    if key in seen_actions:
        candidates[seen_actions[key]]["aliases"].append(name)
        return
    seen_actions[key] = len(candidates)
    candidates.append(
        {
            "name": name,
            "aliases": [name],
            "action": action,
            "policy_time_ms": float(policy_time_ms),
        }
    )


def candidate_by_name(candidates, name):
    for candidate in candidates:
        if name in candidate["aliases"] or candidate["name"] == name:
            return candidate
    raise ValueError("Missing candidate {}".format(name))


def select_best_candidate(candidate_names, candidates, trajectory_cache, step_hours):
    selected = None
    for name in candidate_names:
        candidate = candidate_by_name(candidates, name)
        action_key = tuple(int(value) for value in candidate["action"].reshape(-1))
        summary = energy_summary(trajectory_cache[action_key], step_hours)
        if selected is None or trajectory_sort_key(summary) > trajectory_sort_key(selected["summary"]):
            selected = {"candidate": candidate, "summary": summary}
    return selected["candidate"], selected["summary"]


def one_step_current_decision(experiment, scenario, policy_obs, mitigated_obs, detection):
    def predict_action_fn(obs):
        return experiment.predict_action(obs)

    def evaluate_action_fn(action):
        metrics, _obs = baseline.evaluate_action_on_scenario(experiment, scenario, action)
        return metrics

    return select_fdia_aware_grl_action(
        predict_action_fn,
        evaluate_action_fn,
        policy_obs,
        mitigated_obs,
        detection,
        experiment.num_switches,
    )


def run_hard_case(experiment, hard_case, source_row, target_maps, learning_detectors, args):
    scenario_seed = _int(hard_case, "scenario_seed")
    scenario = baseline.generate_outage_scenario(experiment, scenario_seed, args)
    true_obs = baseline.scenario_observation(experiment, scenario)
    clean_action, clean_policy_ms = experiment.predict_action(true_obs)
    clean_trajectory, _clean_first_obs = baseline.trajectory_after_action_on_scenario(
        experiment,
        scenario,
        clean_action,
        args,
    )
    clean_summary = energy_summary(clean_trajectory, args.step_hours)

    policy_obs, attack_metadata = replay_attack(true_obs, hard_case, source_row, target_maps)
    detection = run_detector_suite(true_obs, policy_obs, learning_detectors=learning_detectors)
    attacked_action, attacked_policy_ms = experiment.predict_action(policy_obs)
    attacked_trajectory, _attacked_first_obs = baseline.trajectory_after_action_on_scenario(
        experiment,
        scenario,
        attacked_action,
        args,
    )
    attacked_summary = energy_summary(attacked_trajectory, args.step_hours)
    attacked_physical_degradation = max(
        0.0,
        clean_summary["restored_energy_kwh"] - attacked_summary["restored_energy_kwh"],
    )

    mitigated_obs, observation_mitigation = mitigate_observation(true_obs, policy_obs, detection)
    mitigated_action, mitigated_policy_ms = experiment.predict_action(mitigated_obs)
    reference_action, reference_policy_ms = clean_action, clean_policy_ms

    current_decision = one_step_current_decision(
        experiment,
        scenario,
        policy_obs,
        mitigated_obs,
        detection,
    )
    current_action = np.asarray(current_decision["action"], dtype=int)

    candidates = []
    seen_actions = {}
    add_unique_candidate(
        candidates,
        seen_actions,
        "attacked_observation_grl",
        attacked_action,
        attacked_policy_ms,
    )
    if detection.get("detected", False):
        add_unique_candidate(
            candidates,
            seen_actions,
            "detector_mitigated_observation_grl",
            mitigated_action,
            mitigated_policy_ms,
        )
        add_unique_candidate(
            candidates,
            seen_actions,
            "all_channel_reference_observation_grl",
            reference_action,
            reference_policy_ms,
        )
    add_unique_candidate(
        candidates,
        seen_actions,
        "current_one_step_fdia_aware",
        current_action,
        float(current_decision.get("policy_time_ms", 0.0)),
    )

    trajectory_cache = {}
    trajectory_cache[tuple(int(value) for value in clean_action.reshape(-1))] = clean_trajectory
    trajectory_cache[tuple(int(value) for value in attacked_action.reshape(-1))] = attacked_trajectory
    for candidate in candidates:
        action_key = tuple(int(value) for value in candidate["action"].reshape(-1))
        if action_key not in trajectory_cache:
            trajectory, _first_obs = baseline.trajectory_after_action_on_scenario(
                experiment,
                scenario,
                candidate["action"],
                args,
            )
            trajectory_cache[action_key] = trajectory

    raw_names = ["attacked_observation_grl"]
    mitigated_names = ["detector_mitigated_observation_grl"] if detection.get("detected", False) else raw_names
    reference_names = (
        ["all_channel_reference_observation_grl"] if detection.get("detected", False) else raw_names
    )
    raw_mitigated_names = raw_names + mitigated_names
    raw_mitigated_reference_names = raw_names + mitigated_names + reference_names

    horizon_raw_mitigated, horizon_raw_mitigated_summary = select_best_candidate(
        raw_mitigated_names,
        candidates,
        trajectory_cache,
        args.step_hours,
    )
    horizon_reference, horizon_reference_summary = select_best_candidate(
        raw_mitigated_reference_names,
        candidates,
        trajectory_cache,
        args.step_hours,
    )

    variant_specs = [
        {
            "variant": "attacked_no_defense",
            "variant_family": "baseline",
            "candidate": candidate_by_name(candidates, "attacked_observation_grl"),
            "candidate_pool": "attacked_observation_grl",
            "quality_summary": energy_summary(attacked_trajectory, args.step_hours),
        },
        {
            "variant": "current_one_step_fdia_aware",
            "variant_family": "current_mitigation",
            "candidate": candidate_by_name(candidates, "current_one_step_fdia_aware"),
            "candidate_pool": "attacked_observation_grl;detector_mitigated_observation_grl",
            "quality_summary": energy_summary(
                trajectory_cache[tuple(int(value) for value in current_action.reshape(-1))],
                args.step_hours,
            ),
        },
        {
            "variant": "detector_mitigated_only",
            "variant_family": "advanced_candidate",
            "candidate": candidate_by_name(candidates, mitigated_names[0]),
            "candidate_pool": ";".join(mitigated_names),
            "quality_summary": energy_summary(
                trajectory_cache[
                    tuple(
                        int(value)
                        for value in candidate_by_name(candidates, mitigated_names[0])[
                            "action"
                        ].reshape(-1)
                    )
                ],
                args.step_hours,
            ),
        },
        {
            "variant": "all_channel_reference_only",
            "variant_family": "advanced_candidate",
            "candidate": candidate_by_name(candidates, reference_names[0]),
            "candidate_pool": ";".join(reference_names),
            "quality_summary": energy_summary(
                trajectory_cache[
                    tuple(
                        int(value)
                        for value in candidate_by_name(candidates, reference_names[0])[
                            "action"
                        ].reshape(-1)
                    )
                ],
                args.step_hours,
            ),
        },
        {
            "variant": "horizon_screen_raw_mitigated",
            "variant_family": "advanced_horizon_screening",
            "candidate": horizon_raw_mitigated,
            "candidate_pool": ";".join(raw_mitigated_names),
            "quality_summary": horizon_raw_mitigated_summary,
        },
        {
            "variant": "horizon_screen_raw_mitigated_reference",
            "variant_family": "advanced_horizon_screening",
            "candidate": horizon_reference,
            "candidate_pool": ";".join(raw_mitigated_reference_names),
            "quality_summary": horizon_reference_summary,
        },
    ]

    current_summary = variant_specs[1]["quality_summary"]
    current_residual = max(
        0.0,
        clean_summary["restored_energy_kwh"] - current_summary["restored_energy_kwh"],
    )

    variant_rows = []
    step_rows = []
    source_physical_degradation = _float(hard_case, "physical_degradation_kwh")
    source_residual = _float(hard_case, "residual_degradation_after_mitigation_kwh")
    detected_channels = detection.get("detected_channels", [])

    for spec in variant_specs:
        candidate = spec["candidate"]
        action = np.asarray(candidate["action"], dtype=int)
        action_key = tuple(int(value) for value in action.reshape(-1))
        trajectory = trajectory_cache[action_key]
        summary = energy_summary(trajectory, args.step_hours)
        residual = max(0.0, clean_summary["restored_energy_kwh"] - summary["restored_energy_kwh"])
        recovered = attacked_physical_degradation - residual
        recovery_ratio = (
            min(1.0, max(0.0, recovered / attacked_physical_degradation))
            if attacked_physical_degradation > EPS
            else 0.0
        )
        residual_reduction = current_residual - residual
        residual_reduction_ratio = (
            residual_reduction / current_residual if current_residual > EPS else 0.0
        )
        delta_clean = action_delta(clean_action, action, experiment.num_switches)
        delta_attacked = action_delta(attacked_action, action, experiment.num_switches)
        variant_rows.append(
            {
                "source_study": hard_case["source_study"],
                "source_case_id": hard_case["case_id"],
                "source_attack_group": hard_case["attack_group"],
                "source_attack": hard_case["attack"],
                "target_observation_id": hard_case.get("target_observation_id", ""),
                "subset_k": hard_case.get("subset_k", ""),
                "scenario_seed": scenario_seed,
                "variant": spec["variant"],
                "variant_family": spec["variant_family"],
                "selected_candidate": candidate["name"],
                "candidate_pool": spec["candidate_pool"],
                "fdia_detected": int(bool(detection.get("detected", False))),
                "detector_score": float(detection.get("score", 0.0)),
                "detected_channels": detected_channels,
                "clean_restored_energy_kwh": clean_summary["restored_energy_kwh"],
                "attacked_restored_energy_kwh": attacked_summary["restored_energy_kwh"],
                "variant_restored_energy_kwh": summary["restored_energy_kwh"],
                "attacked_physical_degradation_kwh": attacked_physical_degradation,
                "variant_residual_degradation_kwh": residual,
                "variant_degradation_recovered_kwh": recovered,
                "variant_recovery_ratio_clipped": recovery_ratio,
                "current_residual_degradation_kwh": current_residual,
                "residual_reduction_vs_current_kwh": residual_reduction,
                "residual_reduction_vs_current_ratio": residual_reduction_ratio,
                "variant_action_changed_vs_clean": delta_clean["action_changed"],
                "variant_switch_changes_vs_clean": delta_clean["switch_changes_vs_clean"],
                "variant_load_changes_vs_clean": delta_clean["load_changes_vs_clean"],
                "variant_action_changed_vs_attacked": delta_attacked["action_changed"],
                "variant_switch_changes_vs_attacked": delta_attacked["switch_changes_vs_clean"],
                "variant_load_changes_vs_attacked": delta_attacked["load_changes_vs_clean"],
                "variant_quality_rank_key": trajectory_sort_key_text(summary),
                "source_physical_degradation_kwh": source_physical_degradation,
                "source_residual_degradation_after_mitigation_kwh": source_residual,
                "attack_metadata": attack_metadata,
                "variant_action": action.tolist(),
            }
        )
        for metrics in trajectory:
            step_rows.append(
                {
                    "source_study": hard_case["source_study"],
                    "source_case_id": hard_case["case_id"],
                    "source_attack_group": hard_case["attack_group"],
                    "scenario_seed": scenario_seed,
                    "variant": spec["variant"],
                    "time_step": metrics.get("time_step", ""),
                    "hour": metrics.get("hour", ""),
                    "energy_kw": metrics.get("energy_kw", ""),
                    "energy_ratio": metrics.get("energy_ratio", ""),
                    "voltage_violation": metrics.get("voltage_violation", ""),
                    "convergence_violation": metrics.get("convergence_violation", ""),
                    "reward": metrics.get("reward", ""),
                    "loads_served": metrics.get("loads_served", ""),
                    "loads_shed": metrics.get("loads_shed", ""),
                }
            )

    return {
        "scenario": scenario,
        "observation_mitigation": observation_mitigation,
        "current_decision": current_decision,
        "variant_rows": variant_rows,
        "step_rows": step_rows,
    }


def summarize_variants(variant_rows):
    groups = defaultdict(list)
    for row in variant_rows:
        groups[(row["variant"], row["variant_family"])].append(row)

    summary_rows = []
    for (variant, variant_family), rows in sorted(groups.items()):
        residuals = np.asarray([row["variant_residual_degradation_kwh"] for row in rows], dtype=float)
        degradations = np.asarray([row["attacked_physical_degradation_kwh"] for row in rows], dtype=float)
        recovered = np.asarray([row["variant_degradation_recovered_kwh"] for row in rows], dtype=float)
        recovery = np.asarray([row["variant_recovery_ratio_clipped"] for row in rows], dtype=float)
        reductions = np.asarray([row["residual_reduction_vs_current_kwh"] for row in rows], dtype=float)
        summary_rows.append(
            {
                "variant": variant,
                "variant_family": variant_family,
                "case_count": len(rows),
                "total_attacked_physical_degradation_kwh": float(np.sum(degradations)),
                "total_variant_residual_degradation_kwh": float(np.sum(residuals)),
                "mean_variant_residual_degradation_kwh": float(np.mean(residuals))
                if residuals.size
                else 0.0,
                "max_variant_residual_degradation_kwh": float(np.max(residuals))
                if residuals.size
                else 0.0,
                "total_variant_degradation_recovered_kwh": float(np.sum(recovered)),
                "total_recovery_ratio_clipped": float(
                    np.sum(recovered) / np.sum(degradations)
                )
                if np.sum(degradations) > EPS
                else 0.0,
                "mean_recovery_ratio_clipped": float(np.mean(recovery)) if recovery.size else 0.0,
                "cases_improved_vs_current": int(np.sum(reductions > EPS)),
                "cases_equal_vs_current": int(np.sum(np.abs(reductions) <= EPS)),
                "cases_worse_vs_current": int(np.sum(reductions < -EPS)),
                "total_residual_reduction_vs_current_kwh": float(np.sum(reductions)),
                "mean_residual_reduction_vs_current_kwh": float(np.mean(reductions))
                if reductions.size
                else 0.0,
            }
        )

    summary_rows.sort(
        key=lambda row: (
            row["total_variant_residual_degradation_kwh"],
            -row["total_residual_reduction_vs_current_kwh"],
        )
    )
    return summary_rows


def best_by_case(variant_rows):
    groups = defaultdict(list)
    for row in variant_rows:
        groups[row["source_case_id"]].append(row)

    best_rows = []
    for _case_id, rows in sorted(groups.items()):
        best = min(
            rows,
            key=lambda row: (
                row["variant_residual_degradation_kwh"],
                -row["variant_recovery_ratio_clipped"],
            ),
        )
        best_rows.append(
            {
                "source_study": best["source_study"],
                "source_case_id": best["source_case_id"],
                "source_attack_group": best["source_attack_group"],
                "source_attack": best["source_attack"],
                "target_observation_id": best["target_observation_id"],
                "subset_k": best["subset_k"],
                "scenario_seed": best["scenario_seed"],
                "best_variant": best["variant"],
                "best_variant_family": best["variant_family"],
                "best_residual_degradation_kwh": best["variant_residual_degradation_kwh"],
                "current_residual_degradation_kwh": best["current_residual_degradation_kwh"],
                "attacked_physical_degradation_kwh": best["attacked_physical_degradation_kwh"],
                "best_residual_reduction_vs_current_kwh": best[
                    "residual_reduction_vs_current_kwh"
                ],
                "best_recovery_ratio_clipped": best["variant_recovery_ratio_clipped"],
            }
        )
    best_rows.sort(
        key=lambda row: (
            row["best_residual_reduction_vs_current_kwh"],
            row["attacked_physical_degradation_kwh"],
        ),
        reverse=True,
    )
    return best_rows


def write_csv_or_header(rows, path, fieldnames):
    if rows:
        write_csv(rows, path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(",".join(fieldnames) + "\n")


def markdown_summary(summary_rows, best_rows):
    lines = [
        "# IEEE 123 Advanced Mitigation Ablation",
        "",
        "This ablation reruns the detected hard residual IEEE 123 FDIA cases and compares mitigation variants.",
        "",
        "## Variant Summary",
        "",
        "| Variant | Cases | Residual kWh | Recovered kWh | Recovery | Improved vs current | Worse vs current |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            "| {variant} | {cases} | {resid:.6f} | {recovered:.6f} | {recovery:.6f} | {improved} | {worse} |".format(
                variant=row["variant"],
                cases=row["case_count"],
                resid=row["total_variant_residual_degradation_kwh"],
                recovered=row["total_variant_degradation_recovered_kwh"],
                recovery=row["total_recovery_ratio_clipped"],
                improved=row["cases_improved_vs_current"],
                worse=row["cases_worse_vs_current"],
            )
        )

    lines.extend(
        [
            "",
            "## Best Variant By Case",
            "",
            "| Source case | Group | Best variant | Current residual kWh | Best residual kWh | Reduction kWh |",
            "|---|---|---|---:|---:|---:|",
        ]
    )
    for row in best_rows:
        lines.append(
            "| {case} | {group} | {variant} | {current:.6f} | {best:.6f} | {reduction:.6f} |".format(
                case=row["source_case_id"],
                group=row["source_attack_group"],
                variant=row["best_variant"],
                current=row["current_residual_degradation_kwh"],
                best=row["best_residual_degradation_kwh"],
                reduction=row["best_residual_reduction_vs_current_kwh"],
            )
        )
    lines.append("")
    return "\n".join(lines)


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

    hard_cases = load_hard_cases(args)
    source_maps = {
        "baseline": load_case_map(args.baseline_cases),
        "branchflow_subset": load_case_map(args.branchflow_subset_cases),
        "branchflow_single": load_case_map(args.branchflow_single_cases),
        "action_mask": load_case_map(args.action_mask_cases),
    }

    experiment = make_controller_experiment(SYSTEM_NAME, args, load_model=True)
    action_targets = actionmask123.target_entries(experiment, "switch_and_load")
    branchflow_targets = measurement123.target_entries(experiment, "branchflow")
    target_maps = {
        "action_mask": {entry.observation_id: entry for entry in action_targets},
        "branchflow": {entry.observation_id: entry for entry in branchflow_targets},
    }

    variant_rows = []
    step_rows = []
    for case_index, hard_case in enumerate(hard_cases):
        source_row = source_row_for_hard_case(hard_case, source_maps)
        print(
            "running mitigation ablation case {}/{} {} group={}".format(
                case_index + 1,
                len(hard_cases),
                hard_case["case_id"],
                hard_case["attack_group"],
            ),
            flush=True,
        )
        result = run_hard_case(
            experiment,
            hard_case,
            source_row,
            target_maps,
            learning_detectors,
            args,
        )
        variant_rows.extend(result["variant_rows"])
        if not args.no_step_results:
            step_rows.extend(result["step_rows"])

    summary_rows = summarize_variants(variant_rows)
    best_rows = best_by_case(variant_rows)

    paths = {
        "variant_cases": output_dir / "tsg_ieee123_advanced_mitigation_variant_cases.csv",
        "variant_summary": output_dir / "tsg_ieee123_advanced_mitigation_variant_summary.csv",
        "best_by_case": output_dir / "tsg_ieee123_advanced_mitigation_best_by_case.csv",
        "markdown_summary": output_dir / "tsg_ieee123_advanced_mitigation_summary.md",
        "manifest": output_dir / "tsg_ieee123_advanced_mitigation_manifest.json",
    }
    if not args.no_step_results:
        paths["step_results"] = output_dir / "tsg_ieee123_advanced_mitigation_step_results.csv"

    write_csv_or_header(variant_rows, paths["variant_cases"], VARIANT_FIELDS)
    write_csv_or_header(summary_rows, paths["variant_summary"], SUMMARY_FIELDS)
    write_csv_or_header(best_rows, paths["best_by_case"], CASE_BEST_FIELDS)
    if not args.no_step_results:
        write_csv_or_header(step_rows, paths["step_results"], STEP_FIELDS)
    paths["markdown_summary"].write_text(markdown_summary(summary_rows, best_rows) + "\n")

    manifest = {
        "experiment": "IEEE 123 advanced mitigation ablation on detected residual FDIA cases",
        "system": "123bus",
        **controller_metadata(SYSTEM_NAME, args),
        "hard_case_input": str(resolve_path(args.low_recovery_cases)),
        "baseline_cases_input": str(resolve_path(args.baseline_cases)),
        "branchflow_subset_cases_input": str(resolve_path(args.branchflow_subset_cases)),
        "branchflow_single_cases_input": str(resolve_path(args.branchflow_single_cases)),
        "action_mask_cases_input": str(resolve_path(args.action_mask_cases)),
        "hard_case_count": len(hard_cases),
        "variant_row_count": len(variant_rows),
        "summary_row_count": len(summary_rows),
        "best_by_case_row_count": len(best_rows),
        "horizon": int(args.horizon),
        "step_hours": float(args.step_hours),
        "start_hour": int(args.start_hour),
        "learning_detectors_enabled": bool(args.use_learning_detectors),
        "learning_detector_count": len(learning_detectors),
        "registry_outputs": {key: str(value) for key, value in registry_outputs.items()},
        "outputs": {key: str(value) for key, value in paths.items()},
        "mitigation_variants": [
            "attacked_no_defense",
            "current_one_step_fdia_aware",
            "detector_mitigated_only",
            "all_channel_reference_only",
            "horizon_screen_raw_mitigated",
            "horizon_screen_raw_mitigated_reference",
        ],
        "notes": (
            "This runner reruns only detected low-recovery residual cases from "
            "the IEEE 123 defense-stress audit. The all-channel reference and "
            "horizon-screened variants are advanced-defense ablations, not "
            "changes to the trained restoration controller policy."
        ),
    }
    paths["manifest"].write_text(safe_json(manifest) + "\n")

    for key, path in paths.items():
        print("wrote {} {}".format(key, path), flush=True)


if __name__ == "__main__":
    main()
