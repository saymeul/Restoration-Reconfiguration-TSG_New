"""IEEE 34-bus advanced detector/mitigation and stealth stress study.

This runner starts from the completed IEEE 34 coordinated-attack evidence and
tests whether high-impact and low-residual variants are detected, whether they
bypass weaker detector profiles, and how much mitigation recovers. It corrupts
only controller observations; OpenDSS remains the physical ground truth.
"""

import argparse
import csv
import json
from time import perf_counter

import numpy as np

from FDIA_Common import (
    DEFAULT_THRESHOLDS,
    clone_observation,
    detect_fdia,
    mitigate_observation,
    restoration_action_quality,
    select_fdia_aware_grl_action,
)
from FDIA_DetectorSuite import (
    fuse_detector_reports,
    load_learning_detectors,
    run_learning_detectors,
)
from FDIA_ExperimentCore import (
    RestorationExperiment,
    action_delta,
    resolve_path,
    safe_json,
    write_csv,
)
from IEEE34_VulnerabilityRegistry import write_registry_outputs
from Run_TSG_IEEE34_BaselineAttackStudy import (
    EPS,
    evaluate_action_on_scenario,
    generate_outage_scenario,
    outage_edges_for_csv,
    scenario_observation,
    trajectory_after_action_on_scenario,
    trajectory_energy_summary,
)
from Run_TSG_IEEE34_CoordinatedAttackStudy import (
    DEFAULT_COORDINATED_ATTACK_SPECS,
    apply_component,
    observation_registry_by_id,
    safe_slug,
    same_action,
    semicolon_join,
)
from TSG_ControllerConfig import (
    add_controller_args,
    controller_metadata,
    controller_output_dir,
    experiment_controller_model_path,
    experiment_controller_name,
    make_controller_experiment,
)


RELAXED_STATUS_THRESHOLDS = dict(DEFAULT_THRESHOLDS)
RELAXED_STATUS_THRESHOLDS.update(
    {
        "action_mask_changed_fraction": 0.06,
        "topology_changed_edge_fraction": 0.04,
    }
)

STRICT_INTEGRITY_THRESHOLDS = dict(DEFAULT_THRESHOLDS)
STRICT_INTEGRITY_THRESHOLDS.update(
    {
        "voltage_max_abs": 0.02,
        "voltage_changed_fraction": 0.01,
        "branchflow_relative_mae": 0.03,
        "energy_abs": 0.02,
        "topology_changed_edge_fraction": 0.0,
        "action_mask_changed_fraction": 0.0,
    }
)


DETECTOR_PROFILES = [
    {
        "detector_profile": "current_residual",
        "description": "Current residual detector thresholds used in prior IEEE 34 studies.",
        "thresholds": dict(DEFAULT_THRESHOLDS),
    },
    {
        "detector_profile": "relaxed_status_tolerance",
        "description": "Stress profile that tolerates one action-mask/status change, exposing why status integrity checks matter.",
        "thresholds": RELAXED_STATUS_THRESHOLDS,
    },
    {
        "detector_profile": "strict_integrity",
        "description": "Advanced strict-integrity profile for binary status channels plus tighter measurement thresholds.",
        "thresholds": STRICT_INTEGRITY_THRESHOLDS,
    },
]


MITIGATION_MODES = [
    "gated_candidate_screening",
    "always_reference_screening",
]


STRESS_ATTACK_SPECS = [
    {
        "stress_attack_id": "stealth_load_s890_single_mask",
        "attack_class": "stealth_status",
        "stealth_intent": "single action-mask change; stealth only if detector tolerates one status/mask bit change",
        "description": "Single high-impact Load_s890 action-mask corruption.",
        "components": [
            {
                "kind": "action_mask",
                "mode": "false_unavailable",
                "target_observation_id": "action_mask.Load_s890",
            }
        ],
    },
    {
        "stress_attack_id": "stealth_load_s890_voltage_816_phase",
        "attack_class": "stealth_coordinated",
        "stealth_intent": "single action-mask change plus one below-threshold voltage phase bias",
        "description": "Load_s890 action-mask corruption plus one small voltage bias at bus 816.",
        "components": [
            {
                "kind": "action_mask",
                "mode": "false_unavailable",
                "target_observation_id": "action_mask.Load_s890",
            },
            {
                "kind": "voltage_phase_bias",
                "mode": "phase_bias",
                "target_observation_id": "bus_voltage.816",
                "phase_index": 0,
                "bias": -0.025,
            },
        ],
    },
    {
        "stress_attack_id": "stealth_load_s890_branchflow_l8_small",
        "attack_class": "stealth_coordinated",
        "stealth_intent": "single action-mask change plus small branchflow scaling",
        "description": "Load_s890 action-mask corruption plus a small branchflow reduction on Line.l8.",
        "components": [
            {
                "kind": "action_mask",
                "mode": "false_unavailable",
                "target_observation_id": "action_mask.Load_s890",
            },
            {
                "kind": "branchflow_scale",
                "mode": "scale",
                "target_observation_id": "branchflow.Line.l8",
                "scale": 0.98,
            },
        ],
    },
    {
        "stress_attack_id": "stealth_voltage_816_phase_only",
        "attack_class": "stealth_measurement",
        "stealth_intent": "one below-threshold voltage phase perturbation with no status corruption",
        "description": "Small one-phase voltage bias at bus 816.",
        "components": [
            {
                "kind": "voltage_phase_bias",
                "mode": "phase_bias",
                "target_observation_id": "bus_voltage.816",
                "phase_index": 0,
                "bias": -0.025,
            }
        ],
    },
    {
        "stress_attack_id": "stealth_branchflow_l8_small_only",
        "attack_class": "stealth_measurement",
        "stealth_intent": "small branchflow scaling with no status corruption",
        "description": "Small branchflow reduction on Line.l8.",
        "components": [
            {
                "kind": "branchflow_scale",
                "mode": "scale",
                "target_observation_id": "branchflow.Line.l8",
                "scale": 0.98,
            }
        ],
    },
    {
        "stress_attack_id": "highimpact_dispatch_s890_voltage_816",
        "attack_class": "high_impact_coordinated",
        "stealth_intent": "not stealth-constrained; included as high-impact mitigation stress case",
        "description": "Completed coordinated attack: Load_s890 false-unavailable plus bus 816 false-low voltage.",
        "source_coordinated_attack_id": "dispatch_s890_voltage_816",
    },
    {
        "stress_attack_id": "highimpact_dispatch_s890_line_l8_voltage_816",
        "attack_class": "high_impact_coordinated",
        "stealth_intent": "not stealth-constrained; included as high-impact mitigation stress case",
        "description": "Completed coordinated attack: Load_s890, Line.l8 false-open, and bus 816 false-low voltage.",
        "source_coordinated_attack_id": "dispatch_s890_line_l8_voltage_816",
    },
    {
        "stress_attack_id": "highimpact_dispatch_s890_switch_swtie4",
        "attack_class": "high_impact_coordinated",
        "stealth_intent": "not stealth-constrained; included as high-impact mitigation stress case",
        "description": "Completed coordinated attack: Load_s890 plus swtie4 action-mask false-unavailable.",
        "source_coordinated_attack_id": "dispatch_s890_switch_swtie4",
    },
]


DEFAULT_OUTPUT_DIR = "paper_results/tsg_ieee34/advanced_defense_stealth_study"


CASE_FIELDS = """system,controller,controller_model_path,case_id,scenario,scenario_seed,scenario_generation_attempt,scenario_root_node,scenario_radius,scenario_subgraph_edge_count,scenario_outage_fraction,outage_edge_count,outage_edges,attack,stress_attack_id,attack_class,stealth_intent,stress_attack_description,source_coordinated_attack_id,detector_profile,detector_profile_description,mitigation_mode,target_family,target_observation_id,target_component_names,component_count,component_applied_count,component_noop_count,attack_applied,changed_measurements,changed_action_mask_count,changed_topology_edge_count,changed_voltage_measurement_count,changed_branchflow_measurement_count,applied_observation_ids,component_attack_metadata,clean_restored_energy_kwh,attacked_restored_energy_kwh,mitigated_restored_energy_kwh,restored_energy_loss_kwh,restored_energy_loss_ratio,restored_energy_loss_percent,physical_degradation_kwh,physical_degradation_ratio,physical_degradation_percent,accidental_improvement_kwh,damaging_case,improvement_case,residual_loss_after_mitigation_kwh,residual_degradation_after_mitigation_kwh,energy_recovered_kwh,degradation_recovered_kwh,mitigation_recovery_ratio,mitigation_recovery_of_degradation_ratio,mitigation_recovery_of_degradation_ratio_clipped,fdia_detected,detector_score,detected_channels,bdd_detected,learning_detected,learning_vote_fraction,bypass_high_impact,stealth_success,mitigation_selected_candidate,mitigation_detector_gate,mitigation_candidate_count,detector_thresholds,detector_residuals,attack_metadata,clean_policy_time_ms,attacked_policy_time_ms,mitigated_policy_time_ms,clean_action,attacked_action,mitigated_action,attacked_action_changed,attacked_switch_changes_vs_clean,attacked_load_changes_vs_clean,mitigated_action_changed,mitigated_switch_changes_vs_clean,mitigated_load_changes_vs_clean,clean_mean_energy_kw,attacked_mean_energy_kw,mitigated_mean_energy_kw,clean_mean_voltage_violation,attacked_mean_voltage_violation,mitigated_mean_voltage_violation,clean_mean_reward,attacked_mean_reward,mitigated_mean_reward""".split(",")

RANKING_FIELDS = """attack,stress_attack_id,attack_class,stealth_intent,detector_profile,mitigation_mode,sensitivity_id,sensitivity_description,target_family,target_observation_id,target_component_names,case_count,attack_applied_count,attack_applied_rate,mean_component_applied_count,mean_component_noop_count,mean_changed_measurements,mean_changed_action_mask_count,mean_changed_topology_edge_count,mean_changed_voltage_measurement_count,mean_changed_branchflow_measurement_count,mean_restored_energy_loss_kwh,max_restored_energy_loss_kwh,mean_restored_energy_loss_percent,mean_physical_degradation_kwh,total_physical_degradation_kwh,max_physical_degradation_kwh,mean_physical_degradation_percent,damaging_case_count,damaging_case_rate,mean_accidental_improvement_kwh,max_accidental_improvement_kwh,improvement_case_count,improvement_case_rate,mean_residual_degradation_after_mitigation_kwh,max_residual_degradation_after_mitigation_kwh,mean_degradation_recovered_kwh,mean_mitigation_recovery_of_degradation_ratio,mean_mitigation_recovery_of_degradation_ratio_clipped,mean_mitigation_recovery_ratio,detection_rate,bypass_high_impact_rate,stealth_success_count,stealth_success_rate,action_changed_rate,mitigated_action_changed_rate,mean_attacked_switch_changes_vs_clean,mean_attacked_load_changes_vs_clean,mean_mitigated_switch_changes_vs_clean,mean_mitigated_load_changes_vs_clean,reference_candidate_selected_rate,defense_rank""".split(",")

PROFILE_FIELDS = """detector_profile,detector_profile_description,thresholds""".split(",")

SPEC_FIELDS = """stress_attack_id,attack_class,stealth_intent,stress_attack_description,source_coordinated_attack_id,component_count,target_observation_id,target_component_names,component_specs""".split(",")


def parse_args():
    parser = argparse.ArgumentParser(
        description="IEEE 34-bus advanced detection/mitigation and stealth stress study."
    )
    add_controller_args(parser)
    parser.add_argument("--cases", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20260615)
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--step-hours", type=float, default=1.0)
    parser.add_argument("--start-hour", type=int, default=0)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--attacks", nargs="+", default=None)
    parser.add_argument("--max-attacks", type=int, default=0)
    parser.add_argument("--profiles", nargs="+", default=None)
    parser.add_argument("--mitigation-modes", nargs="+", default=MITIGATION_MODES)
    parser.add_argument("--include-noop", action="store_true")
    parser.add_argument("--bypass-loss-threshold-kwh", type=float, default=1.0e-6)
    parser.add_argument("--max-outage-fraction", type=float, default=0.50)
    parser.add_argument("--max-scenario-generation-attempts", type=int, default=100)
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


def write_csv_or_header(rows, path, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        write_csv(rows, path)
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.DictWriter(handle, fieldnames=fieldnames).writeheader()


def coordinated_spec_map():
    return {spec["coordinated_attack_id"]: spec for spec in DEFAULT_COORDINATED_ATTACK_SPECS}


def expanded_stress_specs():
    source_specs = coordinated_spec_map()
    specs = []
    for spec in STRESS_ATTACK_SPECS:
        expanded = dict(spec)
        if "source_coordinated_attack_id" in spec:
            source = source_specs[spec["source_coordinated_attack_id"]]
            expanded["components"] = [dict(component) for component in source["components"]]
        else:
            expanded["components"] = [dict(component) for component in spec["components"]]
        specs.append(expanded)
    return specs


def selected_specs(args):
    specs = expanded_stress_specs()
    if args.attacks:
        requested = set(args.attacks)
        available = {spec["stress_attack_id"] for spec in specs}
        missing = sorted(requested - available)
        if missing:
            raise ValueError(
                "Unknown stress attack spec(s): {}. Available: {}".format(
                    ", ".join(missing),
                    ", ".join(sorted(available)),
                )
            )
        specs = [spec for spec in specs if spec["stress_attack_id"] in requested]
    if int(args.max_attacks) > 0:
        specs = specs[: int(args.max_attacks)]
    return specs


def selected_profiles(args):
    profiles = list(DETECTOR_PROFILES)
    if args.profiles:
        requested = set(args.profiles)
        available = {profile["detector_profile"] for profile in profiles}
        missing = sorted(requested - available)
        if missing:
            raise ValueError(
                "Unknown detector profile(s): {}. Available: {}".format(
                    ", ".join(missing),
                    ", ".join(sorted(available)),
                )
            )
        profiles = [profile for profile in profiles if profile["detector_profile"] in requested]
    return profiles


def validate_mitigation_modes(args):
    unknown = sorted(set(args.mitigation_modes) - set(MITIGATION_MODES))
    if unknown:
        raise ValueError(
            "Unknown mitigation mode(s): {}. Available: {}".format(
                ", ".join(unknown),
                ", ".join(MITIGATION_MODES),
            )
        )


def validate_targets(specs, registry_by_id):
    missing = []
    for spec in specs:
        for component in spec["components"]:
            observation_id = component["target_observation_id"]
            if observation_id not in registry_by_id:
                missing.append((spec["stress_attack_id"], observation_id))
    if missing:
        raise ValueError(
            "Stress attack target(s) missing from registry: {}".format(
                ", ".join("{} -> {}".format(spec_id, obs_id) for spec_id, obs_id in missing)
            )
        )


def _finite_vector(values):
    return np.nan_to_num(np.asarray(values, dtype=float), nan=0.0, posinf=0.0, neginf=0.0)


def apply_voltage_phase_bias_component(attacked, true_obs, entry, component):
    voltages = np.asarray(attacked["NodeFeat(BusVoltage)"], dtype=float).copy()
    true_voltages = np.asarray(true_obs["NodeFeat(BusVoltage)"], dtype=float)
    bus_index = int(entry.index[0])
    phase_index = int(component.get("phase_index", 0))
    original = _finite_vector(true_voltages[bus_index, :])
    prior = _finite_vector(voltages[bus_index, :])
    corrupted = prior.copy()
    active_mask = np.isfinite(original) & (original > 0.01)
    attack_applied = 0
    changed_measurements = 0
    if 0 <= phase_index < corrupted.size and bool(active_mask[phase_index]):
        corrupted[phase_index] = corrupted[phase_index] + float(component.get("bias", 0.0))
        attack_applied = int(abs(corrupted[phase_index] - original[phase_index]) > EPS)
        changed_measurements = attack_applied
    voltages[bus_index, :] = corrupted
    attacked["NodeFeat(BusVoltage)"] = voltages
    return {
        "kind": "voltage",
        "target": "NodeFeat(BusVoltage)",
        "mode": "phase_bias",
        "attack": "voltage_phase_bias",
        "target_observation_id": entry.observation_id,
        "target_family": entry.family,
        "target_component_type": entry.component_type,
        "target_component_name": entry.component_name,
        "target_index": bus_index,
        "target_phase_index": phase_index,
        "active_phase_count": int(np.sum(active_mask)),
        "bias": float(component.get("bias", 0.0)),
        "original_value": original.tolist(),
        "prior_attacked_value": prior.tolist(),
        "attacked_value": corrupted.tolist(),
        "changed_measurements": int(changed_measurements),
        "attack_applied": int(attack_applied),
        "mean_abs_change": float(np.mean(np.abs(corrupted - original))) if original.size else 0.0,
        "max_abs_change": float(np.max(np.abs(corrupted - original))) if original.size else 0.0,
    }


def apply_branchflow_scale_component(attacked, true_obs, entry, component):
    flows = np.asarray(attacked["EdgeFeat(Branchflow)"], dtype=float).copy()
    true_flows = np.asarray(true_obs["EdgeFeat(Branchflow)"], dtype=float)
    branch_index = int(entry.index[0])
    original_array = _finite_vector(true_flows[branch_index]).reshape(-1)
    prior_array = _finite_vector(flows[branch_index]).reshape(-1)
    original = float(original_array[0]) if original_array.size else 0.0
    prior = float(prior_array[0]) if prior_array.size else 0.0
    scale = float(component.get("scale", 1.0))
    attacked_value = original * scale
    flows[branch_index] = attacked_value
    attacked["EdgeFeat(Branchflow)"] = flows
    changed = abs(attacked_value - original) > EPS
    return {
        "kind": "branchflow",
        "target": "EdgeFeat(Branchflow)",
        "mode": "scale",
        "attack": "branchflow_scale",
        "target_observation_id": entry.observation_id,
        "target_family": entry.family,
        "target_component_type": entry.component_type,
        "target_component_name": entry.component_name,
        "target_index": branch_index,
        "scale": scale,
        "original_value": original,
        "prior_attacked_value": prior,
        "attacked_value": attacked_value,
        "changed_measurements": int(changed),
        "attack_applied": int(changed),
        "mean_abs_change": abs(attacked_value - original),
        "max_abs_change": abs(attacked_value - original),
    }


def apply_stress_component(attacked, true_obs, entry, component):
    kind = component.get("kind")
    if kind == "voltage_phase_bias":
        return apply_voltage_phase_bias_component(attacked, true_obs, entry, component)
    if kind == "branchflow_scale":
        return apply_branchflow_scale_component(attacked, true_obs, entry, component)
    return apply_component(attacked, true_obs, entry, component)


def summarize_attack(spec, component_metadata, entries):
    applied = [item for item in component_metadata if int(item.get("attack_applied", 0)) == 1]
    return {
        "attack": spec["stress_attack_id"],
        "stress_attack_id": spec["stress_attack_id"],
        "attack_class": spec["attack_class"],
        "stealth_intent": spec["stealth_intent"],
        "stress_attack_description": spec["description"],
        "source_coordinated_attack_id": spec.get("source_coordinated_attack_id", ""),
        "target_family": "advanced_defense_stealth",
        "target_observation_id": semicolon_join(item["target_observation_id"] for item in component_metadata),
        "target_component_names": semicolon_join(entry.component_name for entry in entries),
        "component_count": len(component_metadata),
        "component_applied_count": len(applied),
        "component_noop_count": len(component_metadata) - len(applied),
        "attack_applied": int(bool(applied)),
        "changed_measurements": sum(int(item.get("changed_measurements", 0)) for item in component_metadata),
        "changed_action_mask_count": sum(
            int(item.get("changed_measurements", 0))
            for item in component_metadata
            if item.get("kind") == "action_mask"
        ),
        "changed_topology_edge_count": sum(
            int(item.get("changed_measurements", 0))
            for item in component_metadata
            if item.get("kind") == "line_status"
        ),
        "changed_voltage_measurement_count": sum(
            int(item.get("changed_measurements", 0))
            for item in component_metadata
            if item.get("kind") == "voltage"
        ),
        "changed_branchflow_measurement_count": sum(
            int(item.get("changed_measurements", 0))
            for item in component_metadata
            if item.get("kind") == "branchflow"
        ),
        "applied_observation_ids": semicolon_join(item["target_observation_id"] for item in applied),
        "component_attack_metadata": component_metadata,
    }


def apply_stress_attack(true_obs, spec, registry_by_id):
    attacked = clone_observation(true_obs)
    entries = []
    component_metadata = []
    for component in spec["components"]:
        entry = registry_by_id[component["target_observation_id"]]
        metadata = apply_stress_component(attacked, true_obs, entry, component)
        entries.append(entry)
        component_metadata.append(metadata)
    return attacked, summarize_attack(spec, component_metadata, entries)


def run_detector_profile(true_obs, policy_obs, profile, learning_detectors, args):
    bdd_report = detect_fdia(true_obs, policy_obs, thresholds=profile["thresholds"])
    learning_reports = run_learning_detectors(
        policy_obs,
        learning_detectors or [],
        bdd_report=bdd_report,
    )
    detection = fuse_detector_reports(
        bdd_report,
        learning_reports,
        min_learning_vote_fraction=0.50,
    )
    detection["detector_profile"] = profile["detector_profile"]
    detection["detector_profile_description"] = profile["description"]
    return detection


def prepare_scenario_context(experiment, scenario, args):
    true_obs = scenario_observation(experiment, scenario)
    clean_action, clean_policy_ms = experiment.predict_action(true_obs)
    clean_trajectory, _clean_first_obs = trajectory_after_action_on_scenario(
        experiment,
        scenario,
        clean_action,
        args,
    )
    return {
        "true_obs": true_obs,
        "clean_action": clean_action,
        "clean_policy_ms": clean_policy_ms,
        "clean_trajectory": clean_trajectory,
    }


def select_always_reference_action(experiment, scenario, policy_obs, true_obs, attacked_action, clean_action, args):
    start = perf_counter()
    candidates = []

    def candidate_metrics(action):
        metrics, _obs = evaluate_action_on_scenario(experiment, scenario, action)
        return metrics

    candidates.append(
        {
            "name": "attacked_observation_grl",
            "action": np.asarray(attacked_action, dtype=int),
            "metrics": candidate_metrics(attacked_action),
        }
    )
    if same_action(attacked_action, clean_action):
        reference_metrics = candidates[0]["metrics"]
    else:
        reference_metrics = candidate_metrics(clean_action)
    candidates.append(
        {
            "name": "reference_observation_grl",
            "action": np.asarray(clean_action, dtype=int),
            "metrics": reference_metrics,
        }
    )
    selected = max(candidates, key=lambda candidate: restoration_action_quality(candidate["metrics"]))
    return {
        "action": np.asarray(selected["action"], dtype=int),
        "selected_candidate": selected["name"],
        "policy_time_ms": 0.0,
        "decision_time_ms": (perf_counter() - start) * 1000.0,
        "candidate_count": len(candidates),
        "fdia_aware_metadata": {
            "strategy": "always_reference_candidate_screening",
            "detector_gate": False,
            "candidate_count": len(candidates),
            "candidate_names": [candidate["name"] for candidate in candidates],
            "screening_model": "OpenDSS/digital-twin physical validation",
        },
    }


def run_mitigation_mode(
    experiment,
    scenario,
    scenario_context,
    policy_obs,
    attacked_action,
    attacked_trajectory,
    detection,
    mitigation_mode,
    args,
):
    true_obs = scenario_context["true_obs"]
    clean_action = scenario_context["clean_action"]
    clean_trajectory = scenario_context["clean_trajectory"]

    if mitigation_mode == "gated_candidate_screening":
        mitigated_obs, observation_mitigation = mitigate_observation(true_obs, policy_obs, detection)

        def predict_action_fn(obs):
            return experiment.predict_action(obs)

        def evaluate_action_fn(action):
            metrics, _obs = evaluate_action_on_scenario(experiment, scenario, action)
            return metrics

        fdia_aware = select_fdia_aware_grl_action(
            predict_action_fn,
            evaluate_action_fn,
            policy_obs,
            mitigated_obs,
            detection,
            experiment.num_switches,
        )
        fdia_aware["observation_mitigation"] = observation_mitigation
        mitigated_action = np.asarray(fdia_aware["action"], dtype=int)
    elif mitigation_mode == "always_reference_screening":
        fdia_aware = select_always_reference_action(
            experiment,
            scenario,
            policy_obs,
            true_obs,
            attacked_action,
            clean_action,
            args,
        )
        fdia_aware["observation_mitigation"] = {
            "strategy": "always_compare_attacked_and_reference_actions",
            "mitigation_applied": True,
            "reference_source": "OpenDSS/state-estimator observation",
        }
        mitigated_action = np.asarray(fdia_aware["action"], dtype=int)
    else:
        raise ValueError("Unsupported mitigation mode: {}".format(mitigation_mode))

    if same_action(mitigated_action, clean_action):
        mitigated_trajectory = clean_trajectory
    elif same_action(mitigated_action, attacked_action):
        mitigated_trajectory = attacked_trajectory
    else:
        mitigated_trajectory, _mitigated_first_obs = trajectory_after_action_on_scenario(
            experiment,
            scenario,
            mitigated_action,
            args,
        )
    return fdia_aware, mitigated_action, mitigated_trajectory


def trajectory_summaries(result, args):
    clean = trajectory_energy_summary(result["clean_trajectory"], args.step_hours)
    attacked = trajectory_energy_summary(result["attacked_trajectory"], args.step_hours)
    mitigated = trajectory_energy_summary(result["mitigated_trajectory"], args.step_hours)
    return clean, attacked, mitigated


def case_summary(case_id, scenario, result, args):
    clean, attacked, mitigated = trajectory_summaries(result, args)
    clean_energy = clean["restored_energy_kwh"]
    energy_loss = clean_energy - attacked["restored_energy_kwh"]
    recovered = mitigated["restored_energy_kwh"] - attacked["restored_energy_kwh"]
    residual_loss = clean_energy - mitigated["restored_energy_kwh"]
    physical_degradation = max(0.0, energy_loss)
    accidental_improvement = max(0.0, -energy_loss)
    residual_degradation = max(0.0, residual_loss)
    degradation_recovered = physical_degradation - residual_degradation
    loss_ratio = energy_loss / clean_energy if clean_energy > EPS else 0.0
    physical_degradation_ratio = physical_degradation / clean_energy if clean_energy > EPS else 0.0
    recovery_ratio = recovered / energy_loss if abs(energy_loss) > EPS else 0.0
    degradation_recovery_ratio = (
        degradation_recovered / physical_degradation
        if physical_degradation > EPS
        else 0.0
    )
    degradation_recovery_ratio_clipped = min(1.0, max(0.0, degradation_recovery_ratio))
    detection = result["detection"]
    attack_summary = result["attack_summary"]
    fdia_aware = result["fdia_aware"]
    mitigation_metadata = fdia_aware.get("fdia_aware_metadata", {})
    delta_attacked = action_delta(
        result["clean_action"],
        result["attacked_action"],
        result["experiment"].num_switches,
    )
    delta_mitigated = action_delta(
        result["clean_action"],
        result["mitigated_action"],
        result["experiment"].num_switches,
    )
    bypass_high_impact = int(
        (not bool(detection.get("detected", False)))
        and energy_loss > float(args.bypass_loss_threshold_kwh)
    )
    stealth_success = int(
        bypass_high_impact == 1
        and int(delta_attacked["action_changed"]) == 1
        and str(attack_summary.get("attack_class", "")).startswith("stealth")
    )
    row = {
        "system": "34bus",
        "controller": experiment_controller_name(result["experiment"]),
        "controller_model_path": experiment_controller_model_path(result["experiment"]),
        "case_id": case_id,
        "scenario": scenario["scenario"],
        "scenario_seed": int(scenario["scenario_seed"]),
        "scenario_generation_attempt": int(scenario["generation_attempt"]),
        "scenario_root_node": scenario["root_node"],
        "scenario_radius": int(scenario["radius"]),
        "scenario_subgraph_edge_count": int(scenario["subgraph_edge_count"]),
        "scenario_outage_fraction": float(scenario["outage_fraction"]),
        "outage_edge_count": int(scenario["outage_edge_count"]),
        "outage_edges": outage_edges_for_csv(scenario["outage_edges"]),
        "detector_profile": result["detector_profile"]["detector_profile"],
        "detector_profile_description": result["detector_profile"]["description"],
        "mitigation_mode": result["mitigation_mode"],
        "clean_restored_energy_kwh": clean_energy,
        "attacked_restored_energy_kwh": attacked["restored_energy_kwh"],
        "mitigated_restored_energy_kwh": mitigated["restored_energy_kwh"],
        "restored_energy_loss_kwh": energy_loss,
        "restored_energy_loss_ratio": loss_ratio,
        "restored_energy_loss_percent": 100.0 * loss_ratio,
        "physical_degradation_kwh": physical_degradation,
        "physical_degradation_ratio": physical_degradation_ratio,
        "physical_degradation_percent": 100.0 * physical_degradation_ratio,
        "accidental_improvement_kwh": accidental_improvement,
        "damaging_case": int(physical_degradation > EPS),
        "improvement_case": int(accidental_improvement > EPS),
        "residual_loss_after_mitigation_kwh": residual_loss,
        "residual_degradation_after_mitigation_kwh": residual_degradation,
        "energy_recovered_kwh": recovered,
        "degradation_recovered_kwh": degradation_recovered,
        "mitigation_recovery_ratio": recovery_ratio,
        "mitigation_recovery_of_degradation_ratio": degradation_recovery_ratio,
        "mitigation_recovery_of_degradation_ratio_clipped": degradation_recovery_ratio_clipped,
        "fdia_detected": int(bool(detection.get("detected", False))),
        "detector_score": float(detection.get("score", 0.0)),
        "detected_channels": detection.get("detected_channels", []),
        "bdd_detected": int(bool(detection.get("bdd_report", {}).get("detected", False))),
        "learning_detected": int(bool(detection.get("learning_detected", False))),
        "learning_vote_fraction": float(detection.get("learning_vote_fraction", 0.0)),
        "bypass_high_impact": bypass_high_impact,
        "stealth_success": stealth_success,
        "mitigation_selected_candidate": fdia_aware.get("selected_candidate", ""),
        "mitigation_detector_gate": int(bool(mitigation_metadata.get("detector_gate", False))),
        "mitigation_candidate_count": int(mitigation_metadata.get("candidate_count", fdia_aware.get("candidate_count", 0))),
        "detector_thresholds": result["detector_profile"]["thresholds"],
        "detector_residuals": detection.get("bdd_report", {}).get("residuals", {}),
        "attack_metadata": attack_summary,
        "clean_policy_time_ms": result["clean_policy_ms"],
        "attacked_policy_time_ms": result["attacked_policy_ms"],
        "mitigated_policy_time_ms": fdia_aware.get("policy_time_ms", 0.0),
        "clean_action": np.asarray(result["clean_action"], dtype=int).tolist(),
        "attacked_action": np.asarray(result["attacked_action"], dtype=int).tolist(),
        "mitigated_action": np.asarray(result["mitigated_action"], dtype=int).tolist(),
        "attacked_action_changed": delta_attacked["action_changed"],
        "attacked_switch_changes_vs_clean": delta_attacked["switch_changes_vs_clean"],
        "attacked_load_changes_vs_clean": delta_attacked["load_changes_vs_clean"],
        "mitigated_action_changed": delta_mitigated["action_changed"],
        "mitigated_switch_changes_vs_clean": delta_mitigated["switch_changes_vs_clean"],
        "mitigated_load_changes_vs_clean": delta_mitigated["load_changes_vs_clean"],
        "clean_mean_energy_kw": clean["mean_energy_kw"],
        "attacked_mean_energy_kw": attacked["mean_energy_kw"],
        "mitigated_mean_energy_kw": mitigated["mean_energy_kw"],
        "clean_mean_voltage_violation": clean["mean_voltage_violation"],
        "attacked_mean_voltage_violation": attacked["mean_voltage_violation"],
        "mitigated_mean_voltage_violation": mitigated["mean_voltage_violation"],
        "clean_mean_reward": clean["mean_reward"],
        "attacked_mean_reward": attacked["mean_reward"],
        "mitigated_mean_reward": mitigated["mean_reward"],
    }
    row.update(attack_summary)
    return row


def run_stress_case(experiment, scenario, scenario_context, spec, registry_by_id, profiles, mitigation_modes, learning_detectors, args):
    true_obs = scenario_context["true_obs"]
    clean_action = scenario_context["clean_action"]
    clean_policy_ms = scenario_context["clean_policy_ms"]
    clean_trajectory = scenario_context["clean_trajectory"]
    policy_obs, attack_summary = apply_stress_attack(true_obs, spec, registry_by_id)
    if not args.include_noop and int(attack_summary["attack_applied"]) == 0:
        return []

    attacked_action, attacked_policy_ms = experiment.predict_action(policy_obs)
    if same_action(attacked_action, clean_action):
        attacked_trajectory = clean_trajectory
    else:
        attacked_trajectory, _attacked_first_obs = trajectory_after_action_on_scenario(
            experiment,
            scenario,
            attacked_action,
            args,
        )

    rows = []
    for profile in profiles:
        detection = run_detector_profile(true_obs, policy_obs, profile, learning_detectors, args)
        for mitigation_mode in mitigation_modes:
            fdia_aware, mitigated_action, mitigated_trajectory = run_mitigation_mode(
                experiment,
                scenario,
                scenario_context,
                policy_obs,
                attacked_action,
                attacked_trajectory,
                detection,
                mitigation_mode,
                args,
            )
            rows.append(
                {
                    "experiment": experiment,
                    "scenario": scenario,
                    "true_obs": true_obs,
                    "policy_obs": policy_obs,
                    "clean_action": clean_action,
                    "attacked_action": attacked_action,
                    "mitigated_action": mitigated_action,
                    "clean_policy_ms": clean_policy_ms,
                    "attacked_policy_ms": attacked_policy_ms,
                    "attack_summary": attack_summary,
                    "detector_profile": profile,
                    "detection": detection,
                    "mitigation_mode": mitigation_mode,
                    "fdia_aware": fdia_aware,
                    "clean_trajectory": clean_trajectory,
                    "attacked_trajectory": attacked_trajectory,
                    "mitigated_trajectory": mitigated_trajectory,
                }
            )
    return rows


def safe_float(value, default=0.0):
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    if value in (None, ""):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def aggregate_ranking(case_rows):
    groups = {}
    for row in case_rows:
        key = (row["stress_attack_id"], row["detector_profile"], row["mitigation_mode"])
        groups.setdefault(key, []).append(row)

    ranking = []
    for (attack_id, detector_profile, mitigation_mode), rows in sorted(groups.items()):
        first = rows[0]
        damaging_rows = [row for row in rows if safe_int(row.get("damaging_case")) == 1]
        improvement_rows = [row for row in rows if safe_int(row.get("improvement_case")) == 1]
        stealth_rows = [row for row in rows if safe_int(row.get("stealth_success")) == 1]
        reference_selected = [
            row for row in rows if row.get("mitigation_selected_candidate") == "reference_observation_grl"
        ]
        degradation_recovery_values = [
            safe_float(row.get("mitigation_recovery_of_degradation_ratio")) for row in damaging_rows
        ]
        degradation_recovery_clipped_values = [
            safe_float(row.get("mitigation_recovery_of_degradation_ratio_clipped")) for row in damaging_rows
        ]
        ranking.append(
            {
                "attack": attack_id,
                "stress_attack_id": attack_id,
                "attack_class": first.get("attack_class", ""),
                "stealth_intent": first.get("stealth_intent", ""),
                "detector_profile": detector_profile,
                "mitigation_mode": mitigation_mode,
                "sensitivity_id": "{}:{}".format(detector_profile, mitigation_mode),
                "sensitivity_description": "{} with {}".format(detector_profile, mitigation_mode),
                "target_family": first.get("target_family", ""),
                "target_observation_id": first.get("target_observation_id", ""),
                "target_component_names": first.get("target_component_names", ""),
                "case_count": len(rows),
                "attack_applied_count": sum(safe_int(row.get("attack_applied")) for row in rows),
                "attack_applied_rate": float(np.mean([safe_int(row.get("attack_applied")) for row in rows])),
                "mean_component_applied_count": float(
                    np.mean([safe_float(row.get("component_applied_count")) for row in rows])
                ),
                "mean_component_noop_count": float(
                    np.mean([safe_float(row.get("component_noop_count")) for row in rows])
                ),
                "mean_changed_measurements": float(
                    np.mean([safe_float(row.get("changed_measurements")) for row in rows])
                ),
                "mean_changed_action_mask_count": float(
                    np.mean([safe_float(row.get("changed_action_mask_count")) for row in rows])
                ),
                "mean_changed_topology_edge_count": float(
                    np.mean([safe_float(row.get("changed_topology_edge_count")) for row in rows])
                ),
                "mean_changed_voltage_measurement_count": float(
                    np.mean([safe_float(row.get("changed_voltage_measurement_count")) for row in rows])
                ),
                "mean_changed_branchflow_measurement_count": float(
                    np.mean([safe_float(row.get("changed_branchflow_measurement_count")) for row in rows])
                ),
                "mean_restored_energy_loss_kwh": float(
                    np.mean([safe_float(row.get("restored_energy_loss_kwh")) for row in rows])
                ),
                "max_restored_energy_loss_kwh": float(
                    np.max([safe_float(row.get("restored_energy_loss_kwh")) for row in rows])
                ),
                "mean_restored_energy_loss_percent": float(
                    np.mean([safe_float(row.get("restored_energy_loss_percent")) for row in rows])
                ),
                "mean_physical_degradation_kwh": float(
                    np.mean([safe_float(row.get("physical_degradation_kwh")) for row in rows])
                ),
                "total_physical_degradation_kwh": float(
                    np.sum([safe_float(row.get("physical_degradation_kwh")) for row in rows])
                ),
                "max_physical_degradation_kwh": float(
                    np.max([safe_float(row.get("physical_degradation_kwh")) for row in rows])
                ),
                "mean_physical_degradation_percent": float(
                    np.mean([safe_float(row.get("physical_degradation_percent")) for row in rows])
                ),
                "damaging_case_count": len(damaging_rows),
                "damaging_case_rate": float(len(damaging_rows) / len(rows)) if rows else 0.0,
                "mean_accidental_improvement_kwh": float(
                    np.mean([safe_float(row.get("accidental_improvement_kwh")) for row in rows])
                ),
                "max_accidental_improvement_kwh": float(
                    np.max([safe_float(row.get("accidental_improvement_kwh")) for row in rows])
                ),
                "improvement_case_count": len(improvement_rows),
                "improvement_case_rate": float(len(improvement_rows) / len(rows)) if rows else 0.0,
                "mean_residual_degradation_after_mitigation_kwh": float(
                    np.mean([safe_float(row.get("residual_degradation_after_mitigation_kwh")) for row in rows])
                ),
                "max_residual_degradation_after_mitigation_kwh": float(
                    np.max([safe_float(row.get("residual_degradation_after_mitigation_kwh")) for row in rows])
                ),
                "mean_degradation_recovered_kwh": float(
                    np.mean([safe_float(row.get("degradation_recovered_kwh")) for row in rows])
                ),
                "mean_mitigation_recovery_of_degradation_ratio": float(
                    np.mean(degradation_recovery_values) if degradation_recovery_values else 0.0
                ),
                "mean_mitigation_recovery_of_degradation_ratio_clipped": float(
                    np.mean(degradation_recovery_clipped_values)
                    if degradation_recovery_clipped_values
                    else 0.0
                ),
                "mean_mitigation_recovery_ratio": float(
                    np.mean([safe_float(row.get("mitigation_recovery_ratio")) for row in rows])
                ),
                "detection_rate": float(np.mean([safe_int(row.get("fdia_detected")) for row in rows])),
                "bypass_high_impact_rate": float(
                    np.mean([safe_int(row.get("bypass_high_impact")) for row in rows])
                ),
                "stealth_success_count": len(stealth_rows),
                "stealth_success_rate": float(len(stealth_rows) / len(rows)) if rows else 0.0,
                "action_changed_rate": float(
                    np.mean([safe_int(row.get("attacked_action_changed")) for row in rows])
                ),
                "mitigated_action_changed_rate": float(
                    np.mean([safe_int(row.get("mitigated_action_changed")) for row in rows])
                ),
                "mean_attacked_switch_changes_vs_clean": float(
                    np.mean([safe_float(row.get("attacked_switch_changes_vs_clean")) for row in rows])
                ),
                "mean_attacked_load_changes_vs_clean": float(
                    np.mean([safe_float(row.get("attacked_load_changes_vs_clean")) for row in rows])
                ),
                "mean_mitigated_switch_changes_vs_clean": float(
                    np.mean([safe_float(row.get("mitigated_switch_changes_vs_clean")) for row in rows])
                ),
                "mean_mitigated_load_changes_vs_clean": float(
                    np.mean([safe_float(row.get("mitigated_load_changes_vs_clean")) for row in rows])
                ),
                "reference_candidate_selected_rate": float(len(reference_selected) / len(rows)) if rows else 0.0,
            }
        )

    ranking.sort(
        key=lambda row: (
            row["mean_residual_degradation_after_mitigation_kwh"],
            row["mean_physical_degradation_kwh"],
            row["bypass_high_impact_rate"],
        ),
        reverse=True,
    )
    for index, row in enumerate(ranking, start=1):
        row["defense_rank"] = index
    return ranking


def profile_rows(profiles):
    return [
        {
            "detector_profile": profile["detector_profile"],
            "detector_profile_description": profile["description"],
            "thresholds": profile["thresholds"],
        }
        for profile in profiles
    ]


def spec_rows(specs, registry_by_id):
    rows = []
    for spec in specs:
        entries = [registry_by_id[component["target_observation_id"]] for component in spec["components"]]
        rows.append(
            {
                "stress_attack_id": spec["stress_attack_id"],
                "attack_class": spec["attack_class"],
                "stealth_intent": spec["stealth_intent"],
                "stress_attack_description": spec["description"],
                "source_coordinated_attack_id": spec.get("source_coordinated_attack_id", ""),
                "component_count": len(spec["components"]),
                "target_observation_id": semicolon_join(component["target_observation_id"] for component in spec["components"]),
                "target_component_names": semicolon_join(entry.component_name for entry in entries),
                "component_specs": spec["components"],
            }
        )
    return rows


def output_paths(output_dir):
    return {
        "case_summary": output_dir / "tsg_ieee34_advanced_defense_stealth_cases.csv",
        "defense_ranking": output_dir / "tsg_ieee34_advanced_defense_stealth_ranking.csv",
        "attack_specs": output_dir / "tsg_ieee34_advanced_defense_stealth_specs.csv",
        "detector_profiles": output_dir / "tsg_ieee34_advanced_defense_detector_profiles.csv",
        "manifest": output_dir / "tsg_ieee34_advanced_defense_stealth_manifest.json",
    }


def main():
    args = parse_args()
    args.output_dir = controller_output_dir(
        args.output_dir,
        DEFAULT_OUTPUT_DIR,
        "34bus",
        args.controller,
    )
    validate_mitigation_modes(args)
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = output_paths(output_dir)

    registry_experiment = make_controller_experiment("34bus", args, load_model=False)
    registry_outputs = write_registry_outputs(registry_experiment, output_dir / "registries")
    registry_by_id = observation_registry_by_id(registry_experiment)
    specs = selected_specs(args)
    profiles = selected_profiles(args)
    validate_targets(specs, registry_by_id)

    learning_detectors = []
    if args.use_learning_detectors:
        learning_detectors = load_learning_detectors(
            resolve_path(args.learning_detector_dir),
            tasks=args.learning_tasks,
            model_names=args.learning_models,
        )

    experiment = make_controller_experiment("34bus", args, load_model=True)
    rng = np.random.default_rng(int(args.seed))
    case_rows = []
    skipped_noop_count = 0

    for case_index in range(int(args.cases)):
        scenario_seed = int(rng.integers(1, 2**31 - 1))
        scenario = generate_outage_scenario(experiment, scenario_seed, args)
        scenario_context = prepare_scenario_context(experiment, scenario, args)
        for spec in specs:
            print(
                "running S{:04d}_{} seed={}".format(
                    case_index,
                    spec["stress_attack_id"],
                    scenario_seed,
                ),
                flush=True,
            )
            results = run_stress_case(
                experiment,
                scenario,
                scenario_context,
                spec,
                registry_by_id,
                profiles,
                args.mitigation_modes,
                learning_detectors,
                args,
            )
            if not results:
                skipped_noop_count += 1
                continue
            for result in results:
                case_id = "S{:04d}_{}_{}_{}_seed{}".format(
                    case_index,
                    safe_slug(spec["stress_attack_id"]),
                    safe_slug(result["detector_profile"]["detector_profile"]),
                    safe_slug(result["mitigation_mode"]),
                    scenario_seed,
                )
                case_rows.append(case_summary(case_id, scenario, result, args))

    ranking_rows = aggregate_ranking(case_rows) if case_rows else []
    write_csv_or_header(case_rows, paths["case_summary"], CASE_FIELDS)
    write_csv_or_header(ranking_rows, paths["defense_ranking"], RANKING_FIELDS)
    write_csv_or_header(spec_rows(specs, registry_by_id), paths["attack_specs"], SPEC_FIELDS)
    write_csv_or_header(profile_rows(profiles), paths["detector_profiles"], PROFILE_FIELDS)

    manifest = {
        "experiment": "IEEE 34-bus advanced detection/mitigation and stealth stress study",
        "system": "34bus",
        **controller_metadata("34bus", args),
        "cases": int(args.cases),
        "horizon": int(args.horizon),
        "step_hours": float(args.step_hours),
        "start_hour": int(args.start_hour),
        "seed": int(args.seed),
        "scenario_mode": "deterministic_outage_edges",
        "attack_count": len(specs),
        "stress_attack_ids": [spec["stress_attack_id"] for spec in specs],
        "detector_profiles": [profile["detector_profile"] for profile in profiles],
        "mitigation_modes": list(args.mitigation_modes),
        "executed_case_rows": len(case_rows),
        "skipped_noop_count": skipped_noop_count,
        "learning_detectors_enabled": bool(args.use_learning_detectors),
        "learning_detector_count": len(learning_detectors),
        "registry_outputs": {key: str(value) for key, value in registry_outputs.items()},
        "outputs": {key: str(value) for key, value in paths.items()},
        "notes": (
            "Rows are indexed by stress attack, detector profile, and mitigation mode. "
            "always_reference_screening is an upper-bound robust mitigation that assumes "
            "a trusted reference/state-estimator observation is available for candidate screening."
        ),
    }
    paths["manifest"].write_text(safe_json(manifest) + "\n")

    for key, path in paths.items():
        print("wrote {}: {}".format(key, path), flush=True)


if __name__ == "__main__":
    main()
