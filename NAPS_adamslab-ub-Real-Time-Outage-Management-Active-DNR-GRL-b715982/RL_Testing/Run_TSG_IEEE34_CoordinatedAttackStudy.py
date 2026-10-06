"""IEEE 34-bus coordinated observation-FDIA vulnerability study.

This runner evaluates explicit multi-channel attacks against the GRL
restoration controller. It corrupts only the observations seen by the
controller; OpenDSS and the outage scenario remain the physical ground truth
for clean, attacked, and mitigated action evaluation.
"""

import argparse
import csv
import json

import numpy as np

from FDIA_Common import clone_observation, mitigate_observation, select_fdia_aware_grl_action
from FDIA_DetectorSuite import load_learning_detectors, run_detector_suite
from FDIA_ExperimentCore import (
    RestorationExperiment,
    action_delta,
    physical_impact,
    resolve_path,
    safe_json,
    write_csv,
)
from IEEE34_VulnerabilityRegistry import build_observation_registry, write_registry_outputs
from Run_TSG_IEEE34_BaselineAttackStudy import (
    EPS,
    evaluate_action_on_scenario,
    generate_outage_scenario,
    outage_edges_for_csv,
    scenario_observation,
    trajectory_after_action_on_scenario,
    trajectory_energy_summary,
)
from TSG_ControllerConfig import (
    add_controller_args,
    controller_metadata,
    controller_output_dir,
    experiment_controller_model_path,
    experiment_controller_name,
    make_controller_experiment,
)


DEFAULT_COORDINATED_ATTACK_SPECS = [
    {
        "coordinated_attack_id": "dispatch_s890_switch_swtie4",
        "description": "Most damaging dispatch-load action mask combined with most damaging switch action mask.",
        "components": [
            {
                "kind": "action_mask",
                "mode": "false_unavailable",
                "target_observation_id": "action_mask.Load_s890",
            },
            {
                "kind": "action_mask",
                "mode": "false_unavailable",
                "target_observation_id": "action_mask.swtie4",
            },
        ],
    },
    {
        "coordinated_attack_id": "dispatch_s844_switch_swtie1",
        "description": "Second damaging dispatch-load action mask combined with a high-ranked switch action mask.",
        "components": [
            {
                "kind": "action_mask",
                "mode": "false_unavailable",
                "target_observation_id": "action_mask.Load_s844",
            },
            {
                "kind": "action_mask",
                "mode": "false_unavailable",
                "target_observation_id": "action_mask.swtie1",
            },
        ],
    },
    {
        "coordinated_attack_id": "dispatch_s890_voltage_816",
        "description": "Most damaging dispatch-load action mask combined with the top false-low voltage bus.",
        "components": [
            {
                "kind": "action_mask",
                "mode": "false_unavailable",
                "target_observation_id": "action_mask.Load_s890",
            },
            {
                "kind": "voltage",
                "mode": "false_low",
                "target_observation_id": "bus_voltage.816",
                "reported_value": 0.80,
            },
        ],
    },
    {
        "coordinated_attack_id": "dispatch_s844_voltage_852",
        "description": "Second damaging dispatch-load action mask combined with a high-ranked false-low voltage bus.",
        "components": [
            {
                "kind": "action_mask",
                "mode": "false_unavailable",
                "target_observation_id": "action_mask.Load_s844",
            },
            {
                "kind": "voltage",
                "mode": "false_low",
                "target_observation_id": "bus_voltage.852",
                "reported_value": 0.80,
            },
        ],
    },
    {
        "coordinated_attack_id": "switch_swtie4_line_l8_voltage_816",
        "description": "High-impact switch mask with damaging false-open line status and false-low voltage.",
        "components": [
            {
                "kind": "action_mask",
                "mode": "false_unavailable",
                "target_observation_id": "action_mask.swtie4",
            },
            {
                "kind": "line_status",
                "mode": "false_open",
                "target_observation_id": "topology_edge.Line.l8",
            },
            {
                "kind": "voltage",
                "mode": "false_low",
                "target_observation_id": "bus_voltage.816",
                "reported_value": 0.80,
            },
        ],
    },
    {
        "coordinated_attack_id": "line_l8_line_824848_voltage_816",
        "description": "Two damaging false-open line-status observations combined with the top false-low voltage bus.",
        "components": [
            {
                "kind": "line_status",
                "mode": "false_open",
                "target_observation_id": "topology_edge.Line.l8",
            },
            {
                "kind": "line_status",
                "mode": "false_open",
                "target_observation_id": "topology_edge.Line.824848",
            },
            {
                "kind": "voltage",
                "mode": "false_low",
                "target_observation_id": "bus_voltage.816",
                "reported_value": 0.80,
            },
        ],
    },
    {
        "coordinated_attack_id": "dispatch_s890_line_l8_voltage_816",
        "description": "Strong dispatch-load mask combined with damaging false-open line status and false-low voltage.",
        "components": [
            {
                "kind": "action_mask",
                "mode": "false_unavailable",
                "target_observation_id": "action_mask.Load_s890",
            },
            {
                "kind": "line_status",
                "mode": "false_open",
                "target_observation_id": "topology_edge.Line.l8",
            },
            {
                "kind": "voltage",
                "mode": "false_low",
                "target_observation_id": "bus_voltage.816",
                "reported_value": 0.80,
            },
        ],
    },
    {
        "coordinated_attack_id": "hidden_l28_voltage_816_dispatch_s890",
        "description": "Hidden-outage false-closed line status combined with voltage and dispatch-load corruption.",
        "components": [
            {
                "kind": "line_status",
                "mode": "false_closed",
                "target_observation_id": "topology_edge.Line.l28",
            },
            {
                "kind": "voltage",
                "mode": "false_low",
                "target_observation_id": "bus_voltage.816",
                "reported_value": 0.80,
            },
            {
                "kind": "action_mask",
                "mode": "false_unavailable",
                "target_observation_id": "action_mask.Load_s890",
            },
        ],
    },
    {
        "coordinated_attack_id": "hidden_l30_switch_swtie4",
        "description": "Most damaging hidden-outage false-closed line status combined with high-impact switch masking.",
        "components": [
            {
                "kind": "line_status",
                "mode": "false_closed",
                "target_observation_id": "topology_edge.Line.l30",
            },
            {
                "kind": "action_mask",
                "mode": "false_unavailable",
                "target_observation_id": "action_mask.swtie4",
            },
        ],
    },
    {
        "coordinated_attack_id": "dispatch_s890_branchflow_l8_voltage_816",
        "description": "Strong dispatch-load mask with branchflow hiding and false-low voltage measurement corruption.",
        "components": [
            {
                "kind": "action_mask",
                "mode": "false_unavailable",
                "target_observation_id": "action_mask.Load_s890",
            },
            {
                "kind": "branchflow",
                "mode": "hide",
                "target_observation_id": "branchflow.Line.l8",
                "scale": 0.25,
            },
            {
                "kind": "voltage",
                "mode": "false_low",
                "target_observation_id": "bus_voltage.816",
                "reported_value": 0.80,
            },
        ],
    },
]


DEFAULT_OUTPUT_DIR = "paper_results/tsg_ieee34/coordinated_attack_study"


CASE_SUMMARY_FIELDS = """system,controller,controller_model_path,case_id,scenario,scenario_seed,scenario_generation_attempt,scenario_root_node,scenario_radius,scenario_subgraph_edge_count,scenario_outage_fraction,outage_edge_count,outage_edges,attack,coordinated_attack_id,coordinated_attack_description,target_family,target_observation_id,target_component_names,component_count,component_applied_count,component_noop_count,attack_applied,changed_measurements,changed_action_mask_count,changed_topology_edge_count,changed_voltage_measurement_count,changed_branchflow_measurement_count,applied_observation_ids,component_attack_metadata,clean_restored_energy_kwh,attacked_restored_energy_kwh,mitigated_restored_energy_kwh,restored_energy_loss_kwh,restored_energy_loss_ratio,restored_energy_loss_percent,physical_degradation_kwh,physical_degradation_ratio,physical_degradation_percent,accidental_improvement_kwh,damaging_case,improvement_case,residual_loss_after_mitigation_kwh,residual_degradation_after_mitigation_kwh,energy_recovered_kwh,degradation_recovered_kwh,mitigation_recovery_ratio,mitigation_recovery_of_degradation_ratio,mitigation_recovery_of_degradation_ratio_clipped,fdia_detected,detector_score,detected_channels,bdd_detected,learning_detected,learning_vote_fraction,bypass_high_impact,mitigation_selected_candidate,mitigation_detector_gate,attack_metadata,clean_policy_time_ms,attacked_policy_time_ms,mitigated_policy_time_ms,clean_action,attacked_action,mitigated_action,attacked_action_changed,attacked_switch_changes_vs_clean,attacked_load_changes_vs_clean,mitigated_action_changed,mitigated_switch_changes_vs_clean,mitigated_load_changes_vs_clean,clean_mean_energy_kw,attacked_mean_energy_kw,mitigated_mean_energy_kw,clean_mean_voltage_violation,attacked_mean_voltage_violation,mitigated_mean_voltage_violation,clean_mean_reward,attacked_mean_reward,mitigated_mean_reward""".split(",")

STEP_RESULT_FIELDS = """system,controller,controller_model_path,case_id,scenario,scenario_seed,outage_edge_count,outage_edges,attack,coordinated_attack_id,mode,target_observation_id,target_component_names,time_step,hour,action_changed,switch_changes_vs_clean,load_changes_vs_clean,action,reward,energy_kw,total_demand_kw,energy_ratio,measured_energy_ratio,voltage_violation,convergence_violation,branchflow_mean,branchflow_max,voltage_min,voltage_max,loads_served,loads_shed,initial_reward,initial_energy_ratio,initial_voltage_violation,solve_warning,energy_ratio_delta_vs_clean,energy_kw_delta_vs_clean,voltage_violation_delta_vs_clean,reward_delta_vs_clean,convergence_delta_vs_clean,loads_served_delta_vs_clean,physical_impact_score""".split(",")

RANKING_FIELDS = """attack,coordinated_attack_id,coordinated_attack_description,target_family,target_observation_id,target_component_names,component_count,case_count,attack_applied_count,attack_applied_rate,mean_component_applied_count,mean_component_noop_count,mean_changed_measurements,mean_changed_action_mask_count,mean_changed_topology_edge_count,mean_changed_voltage_measurement_count,mean_changed_branchflow_measurement_count,mean_restored_energy_loss_kwh,max_restored_energy_loss_kwh,mean_restored_energy_loss_percent,mean_physical_degradation_kwh,total_physical_degradation_kwh,max_physical_degradation_kwh,mean_physical_degradation_percent,damaging_case_count,damaging_case_rate,mean_accidental_improvement_kwh,max_accidental_improvement_kwh,improvement_case_count,improvement_case_rate,mean_residual_degradation_after_mitigation_kwh,mean_mitigation_recovery_of_degradation_ratio,mean_mitigation_recovery_of_degradation_ratio_clipped,mean_mitigation_recovery_ratio,detection_rate,bypass_high_impact_rate,action_changed_rate,mean_attacked_switch_changes_vs_clean,mean_attacked_load_changes_vs_clean,damage_rank""".split(",")

COMPONENT_PRESENCE_FIELDS = """target_observation_id,target_family,target_component_type,target_component_name,component_kind,component_mode,case_count,coordinated_attack_count,coordinated_attack_ids,component_applied_count,component_applied_rate,mean_physical_degradation_kwh,max_physical_degradation_kwh,damaging_case_count,damaging_case_rate,detection_rate,bypass_high_impact_rate,component_presence_rank""".split(",")

SPEC_FIELDS = """coordinated_attack_id,coordinated_attack_description,component_count,target_observation_id,target_component_names,component_specs""".split(",")


INT_CASE_FIELDS = {
    "scenario_seed",
    "scenario_generation_attempt",
    "scenario_radius",
    "scenario_subgraph_edge_count",
    "outage_edge_count",
    "component_count",
    "component_applied_count",
    "component_noop_count",
    "attack_applied",
    "changed_measurements",
    "changed_action_mask_count",
    "changed_topology_edge_count",
    "changed_voltage_measurement_count",
    "changed_branchflow_measurement_count",
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


def parse_args():
    parser = argparse.ArgumentParser(
        description="IEEE 34-bus coordinated multi-observation FDIA experiment."
    )
    add_controller_args(parser)
    parser.add_argument("--cases", type=int, default=30, help="Number of deterministic outage scenarios.")
    parser.add_argument("--seed", type=int, default=20260615)
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--step-hours", type=float, default=1.0)
    parser.add_argument("--start-hour", type=int, default=0)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--specs",
        nargs="+",
        default=None,
        help="Optional coordinated attack IDs to run. Defaults to all curated IEEE 34 specs.",
    )
    parser.add_argument("--max-specs", type=int, default=0, help="Optional smoke-test limit on specs.")
    parser.add_argument("--spec-start-index", type=int, default=0, help="Zero-based start index into selected specs.")
    parser.add_argument("--spec-count", type=int, default=0, help="Optional number of specs after --spec-start-index.")
    parser.add_argument(
        "--include-noop",
        action="store_true",
        help="Keep cases where no coordinated component changed the controller observation.",
    )
    parser.add_argument(
        "--merge-case-files",
        nargs="+",
        default=None,
        help="Merge completed chunk case CSVs and recompute coordinated rankings without running simulations.",
    )
    parser.add_argument("--write-step-results", action="store_true")
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


def semicolon_join(values):
    return ";".join(str(value) for value in values if value not in (None, ""))


def unique_join(values):
    ordered = []
    seen = set()
    for value in values:
        if value in (None, "") or value in seen:
            continue
        seen.add(value)
        ordered.append(str(value))
    return ";".join(ordered)


def safe_slug(value):
    return (
        str(value)
        .replace(".", "_")
        .replace("-", "_")
        .replace(" ", "_")
        .replace("/", "_")
        .replace(";", "_")
    )


def write_csv_or_header(rows, path, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        write_csv(rows, path)
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.DictWriter(handle, fieldnames=fieldnames).writeheader()


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


def selected_attack_specs(args):
    specs = list(DEFAULT_COORDINATED_ATTACK_SPECS)
    if args.specs:
        requested = set(args.specs)
        available = {spec["coordinated_attack_id"] for spec in specs}
        missing = sorted(requested - available)
        if missing:
            raise ValueError(
                "Unknown coordinated attack spec(s): {}. Available: {}".format(
                    ", ".join(missing),
                    ", ".join(sorted(available)),
                )
            )
        specs = [spec for spec in specs if spec["coordinated_attack_id"] in requested]

    start = max(0, int(args.spec_start_index))
    if start > len(specs):
        raise ValueError(
            "--spec-start-index {} is beyond the selected spec count {}".format(start, len(specs))
        )
    if int(args.spec_count) > 0:
        end = min(start + int(args.spec_count), len(specs))
    elif int(args.max_specs) > 0:
        end = min(start + int(args.max_specs), len(specs))
    else:
        end = len(specs)
    return specs[start:end], len(specs), start, end


def observation_registry_by_id(experiment):
    entries = build_observation_registry(experiment)
    return {entry.observation_id: entry for entry in entries}


def validate_specs(specs, registry_by_id):
    missing = []
    for spec in specs:
        for component in spec["components"]:
            observation_id = component["target_observation_id"]
            if observation_id not in registry_by_id:
                missing.append((spec["coordinated_attack_id"], observation_id))
    if missing:
        formatted = ", ".join("{} -> {}".format(spec_id, obs_id) for spec_id, obs_id in missing)
        raise ValueError("Coordinated attack target(s) missing from IEEE 34 observation registry: {}".format(formatted))


def component_target_entries(spec, registry_by_id):
    return [registry_by_id[component["target_observation_id"]] for component in spec["components"]]


def spec_target_observation_ids(spec):
    return semicolon_join(component["target_observation_id"] for component in spec["components"])


def spec_rows(specs, registry_by_id):
    rows = []
    for spec in specs:
        entries = component_target_entries(spec, registry_by_id)
        rows.append(
            {
                "coordinated_attack_id": spec["coordinated_attack_id"],
                "coordinated_attack_description": spec["description"],
                "component_count": len(spec["components"]),
                "target_observation_id": spec_target_observation_ids(spec),
                "target_component_names": semicolon_join(entry.component_name for entry in entries),
                "component_specs": spec["components"],
            }
        )
    return rows


def _finite_vector(values):
    return np.nan_to_num(np.asarray(values, dtype=float), nan=0.0, posinf=0.0, neginf=0.0)


def apply_action_mask_component(attacked, true_obs, entry, component):
    mask = np.asarray(attacked["ActionMasking"], dtype=float).reshape(-1).copy()
    true_mask = np.asarray(true_obs["ActionMasking"], dtype=float).reshape(-1)
    target_index = int(entry.index[0])
    original_value = float(true_mask[target_index])
    prior_attacked_value = float(mask[target_index])
    mode = component.get("mode", "false_unavailable")
    if mode == "false_unavailable":
        attacked_value = 1.0
    elif mode == "false_available":
        attacked_value = 0.0
    else:
        raise ValueError("Unsupported action-mask component mode: {}".format(mode))
    mask[target_index] = attacked_value
    attacked["ActionMasking"] = mask
    changed = abs(attacked_value - original_value) > EPS
    return {
        "kind": "action_mask",
        "target": "ActionMasking",
        "mode": mode,
        "attack": "action_mask_{}".format(mode),
        "target_observation_id": entry.observation_id,
        "target_family": entry.family,
        "target_component_type": entry.component_type,
        "target_component_name": entry.component_name,
        "target_action_index": target_index,
        "original_value": original_value,
        "prior_attacked_value": prior_attacked_value,
        "attacked_value": attacked_value,
        "changed_measurements": int(changed),
        "attack_applied": int(changed),
        "mean_abs_change": abs(attacked_value - original_value),
        "max_abs_change": abs(attacked_value - original_value),
    }


def apply_line_status_component(attacked, true_obs, entry, component):
    adjacency = np.asarray(attacked["Adjacency"], dtype=float).copy()
    true_adjacency = np.asarray(true_obs["Adjacency"], dtype=float)
    node_i = int(entry.index[0])
    node_j = int(entry.index[1])
    if node_i < 0 or node_j < 0:
        raise ValueError("Target {} has invalid adjacency index {}.".format(entry.observation_id, entry.index))
    original = float(true_adjacency[node_i, node_j])
    prior_attacked_value = float(adjacency[node_i, node_j])
    mode = component.get("mode", "false_open")
    if mode == "false_open":
        attacked_value = 0.0
    elif mode == "false_closed":
        attacked_value = 1.0
    elif mode == "flip":
        attacked_value = 0.0 if original > 0.5 else 1.0
    else:
        raise ValueError("Unsupported line-status component mode: {}".format(mode))
    adjacency[node_i, node_j] = attacked_value
    adjacency[node_j, node_i] = attacked_value
    attacked["Adjacency"] = adjacency
    changed = abs(attacked_value - original) > EPS
    return {
        "kind": "line_status",
        "target": "Adjacency",
        "mode": mode,
        "attack": "line_status_{}".format(mode),
        "target_observation_id": entry.observation_id,
        "target_family": entry.family,
        "target_component_type": entry.component_type,
        "target_component_name": entry.component_name,
        "target_node_i": node_i,
        "target_node_j": node_j,
        "original_value": original,
        "prior_attacked_value": prior_attacked_value,
        "attacked_value": attacked_value,
        "changed_measurements": int(changed),
        "attack_applied": int(changed),
        "mean_abs_change": abs(attacked_value - original),
        "max_abs_change": abs(attacked_value - original),
    }


def apply_voltage_component(attacked, true_obs, entry, component):
    voltages = np.asarray(attacked["NodeFeat(BusVoltage)"], dtype=float).copy()
    true_voltages = np.asarray(true_obs["NodeFeat(BusVoltage)"], dtype=float)
    bus_index = int(entry.index[0])
    original = _finite_vector(true_voltages[bus_index, :])
    prior_attacked_value = _finite_vector(voltages[bus_index, :])
    active_mask = np.isfinite(original) & (original > 0.01)
    corrupted = prior_attacked_value.copy()
    mode = component.get("mode", "false_low")
    if mode == "false_low":
        reported_value = float(component.get("reported_value", 0.80))
        corrupted[active_mask] = reported_value
    elif mode == "false_high":
        reported_value = float(component.get("reported_value", 1.10))
        corrupted[active_mask] = reported_value
    elif mode == "mask_to_nominal":
        reported_value = float(component.get("reported_value", 1.00))
        corrupted[active_mask] = reported_value
    elif mode == "scale":
        reported_value = float(component.get("scale", 1.0))
        corrupted[active_mask] = corrupted[active_mask] * reported_value
    elif mode == "bias":
        reported_value = float(component.get("bias", 0.0))
        corrupted[active_mask] = corrupted[active_mask] + reported_value
    else:
        raise ValueError("Unsupported voltage component mode: {}".format(mode))
    voltages[bus_index, :] = corrupted
    attacked["NodeFeat(BusVoltage)"] = voltages
    changed = np.abs(corrupted - original) > EPS
    return {
        "kind": "voltage",
        "target": "NodeFeat(BusVoltage)",
        "mode": mode,
        "attack": "voltage_{}".format(mode),
        "target_observation_id": entry.observation_id,
        "target_family": entry.family,
        "target_component_type": entry.component_type,
        "target_component_name": entry.component_name,
        "target_index": bus_index,
        "active_phase_count": int(np.sum(active_mask)),
        "original_value": original.tolist(),
        "prior_attacked_value": prior_attacked_value.tolist(),
        "attacked_value": corrupted.tolist(),
        "changed_measurements": int(np.sum(changed)),
        "attack_applied": int(np.any(changed)),
        "mean_abs_change": float(np.mean(np.abs(corrupted - original))) if original.size else 0.0,
        "max_abs_change": float(np.max(np.abs(corrupted - original))) if original.size else 0.0,
    }


def apply_branchflow_component(attacked, true_obs, entry, component):
    flows = np.asarray(attacked["EdgeFeat(Branchflow)"], dtype=float).copy()
    true_flows = np.asarray(true_obs["EdgeFeat(Branchflow)"], dtype=float)
    branch_index = int(entry.index[0])
    original_array = _finite_vector(true_flows[branch_index]).reshape(-1)
    prior_array = _finite_vector(flows[branch_index]).reshape(-1)
    original = float(original_array[0]) if original_array.size else 0.0
    prior_attacked_value = float(prior_array[0]) if prior_array.size else 0.0
    mode = component.get("mode", "hide")
    if mode == "hide":
        attacked_value = original * float(component.get("scale", 0.25))
    elif mode == "inflate":
        attacked_value = original * float(component.get("scale", 1.50))
    else:
        raise ValueError("Unsupported branchflow component mode: {}".format(mode))
    flows[branch_index] = attacked_value
    attacked["EdgeFeat(Branchflow)"] = flows
    changed = abs(attacked_value - original) > EPS
    return {
        "kind": "branchflow",
        "target": "EdgeFeat(Branchflow)",
        "mode": mode,
        "attack": "branchflow_{}".format(mode),
        "target_observation_id": entry.observation_id,
        "target_family": entry.family,
        "target_component_type": entry.component_type,
        "target_component_name": entry.component_name,
        "target_index": branch_index,
        "original_value": original,
        "prior_attacked_value": prior_attacked_value,
        "attacked_value": attacked_value,
        "changed_measurements": int(changed),
        "attack_applied": int(changed),
        "mean_abs_change": abs(attacked_value - original),
        "max_abs_change": abs(attacked_value - original),
    }


def apply_component(attacked, true_obs, entry, component):
    kind = component.get("kind")
    if kind == "action_mask":
        return apply_action_mask_component(attacked, true_obs, entry, component)
    if kind == "line_status":
        return apply_line_status_component(attacked, true_obs, entry, component)
    if kind == "voltage":
        return apply_voltage_component(attacked, true_obs, entry, component)
    if kind == "branchflow":
        return apply_branchflow_component(attacked, true_obs, entry, component)
    raise ValueError("Unsupported coordinated component kind: {}".format(kind))


def summarize_components(spec, component_metadata, entries):
    applied = [item for item in component_metadata if int(item.get("attack_applied", 0)) == 1]
    changed_action_mask = sum(
        int(item.get("changed_measurements", 0))
        for item in component_metadata
        if item.get("kind") == "action_mask"
    )
    changed_topology = sum(
        int(item.get("changed_measurements", 0))
        for item in component_metadata
        if item.get("kind") == "line_status"
    )
    changed_voltage = sum(
        int(item.get("changed_measurements", 0))
        for item in component_metadata
        if item.get("kind") == "voltage"
    )
    changed_branchflow = sum(
        int(item.get("changed_measurements", 0))
        for item in component_metadata
        if item.get("kind") == "branchflow"
    )
    return {
        "attack": spec["coordinated_attack_id"],
        "coordinated_attack_id": spec["coordinated_attack_id"],
        "coordinated_attack_description": spec["description"],
        "target_family": "coordinated",
        "target_observation_id": semicolon_join(item["target_observation_id"] for item in component_metadata),
        "target_component_names": semicolon_join(entry.component_name for entry in entries),
        "component_count": len(component_metadata),
        "component_applied_count": len(applied),
        "component_noop_count": len(component_metadata) - len(applied),
        "attack_applied": int(bool(applied)),
        "changed_measurements": sum(int(item.get("changed_measurements", 0)) for item in component_metadata),
        "changed_action_mask_count": int(changed_action_mask),
        "changed_topology_edge_count": int(changed_topology),
        "changed_voltage_measurement_count": int(changed_voltage),
        "changed_branchflow_measurement_count": int(changed_branchflow),
        "applied_observation_ids": semicolon_join(item["target_observation_id"] for item in applied),
        "component_attack_metadata": component_metadata,
    }


def apply_coordinated_attack(true_obs, spec, registry_by_id):
    attacked = clone_observation(true_obs)
    entries = component_target_entries(spec, registry_by_id)
    component_metadata = []
    for component, entry in zip(spec["components"], entries):
        metadata = apply_component(attacked, true_obs, entry, component)
        component_metadata.append(metadata)
    attack_summary = summarize_components(spec, component_metadata, entries)
    return attacked, attack_summary


def case_energy_summary(result, args):
    clean = trajectory_energy_summary(result["clean_trajectory"], args.step_hours)
    attacked = trajectory_energy_summary(result["attacked_trajectory"], args.step_hours)
    mitigated = trajectory_energy_summary(result["mitigated_trajectory"], args.step_hours)
    energy_loss = clean["restored_energy_kwh"] - attacked["restored_energy_kwh"]
    recovered = mitigated["restored_energy_kwh"] - attacked["restored_energy_kwh"]
    residual_loss = clean["restored_energy_kwh"] - mitigated["restored_energy_kwh"]
    return clean, attacked, mitigated, energy_loss, recovered, residual_loss


def case_summary(case_id, scenario, result, args):
    clean, attacked, mitigated, energy_loss, recovered, residual_loss = case_energy_summary(result, args)
    clean_energy = clean["restored_energy_kwh"]
    loss_ratio = energy_loss / clean_energy if clean_energy > EPS else 0.0
    recovery_ratio = recovered / energy_loss if abs(energy_loss) > EPS else 0.0
    physical_degradation = max(0.0, energy_loss)
    accidental_improvement = max(0.0, -energy_loss)
    physical_degradation_ratio = physical_degradation / clean_energy if clean_energy > EPS else 0.0
    residual_degradation = max(0.0, residual_loss)
    degradation_recovered = physical_degradation - residual_degradation
    degradation_recovery_ratio = (
        degradation_recovered / physical_degradation
        if physical_degradation > EPS
        else 0.0
    )
    degradation_recovery_ratio_clipped = min(1.0, max(0.0, degradation_recovery_ratio))
    detection = result["detection"]
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
    mitigation_metadata = result["fdia_aware"].get("fdia_aware_metadata", {})
    attack_summary = result["attack_summary"]
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
        "clean_restored_energy_kwh": clean["restored_energy_kwh"],
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
        "bypass_high_impact": int(
            (not bool(detection.get("detected", False)))
            and energy_loss > float(args.bypass_loss_threshold_kwh)
        ),
        "mitigation_selected_candidate": result["fdia_aware"].get("selected_candidate", ""),
        "mitigation_detector_gate": int(bool(mitigation_metadata.get("detector_gate", False))),
        "attack_metadata": attack_summary,
        "clean_policy_time_ms": result["clean_policy_ms"],
        "attacked_policy_time_ms": result["attacked_policy_ms"],
        "mitigated_policy_time_ms": result["fdia_aware"].get("policy_time_ms", 0.0),
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


def step_rows(case_id, scenario, result):
    rows = []
    clean_trajectory = result["clean_trajectory"]
    attack_summary = result["attack_summary"]
    modes = [
        ("clean_baseline", result["clean_action"], result["clean_trajectory"]),
        ("attacked_no_defense", result["attacked_action"], result["attacked_trajectory"]),
        ("mitigated", result["mitigated_action"], result["mitigated_trajectory"]),
    ]
    for mode, action, trajectory in modes:
        for clean_metrics, metrics in zip(clean_trajectory, trajectory):
            if mode == "clean_baseline":
                impact = {
                    "energy_ratio_delta_vs_clean": 0.0,
                    "energy_kw_delta_vs_clean": 0.0,
                    "voltage_violation_delta_vs_clean": 0.0,
                    "reward_delta_vs_clean": 0.0,
                    "convergence_delta_vs_clean": 0.0,
                    "loads_served_delta_vs_clean": 0,
                    "physical_impact_score": 0.0,
                }
            else:
                impact = physical_impact(clean_metrics, metrics)
            delta = action_delta(result["clean_action"], action, result["experiment"].num_switches)
            row = {
                "system": "34bus",
                "controller": experiment_controller_name(result["experiment"]),
                "controller_model_path": experiment_controller_model_path(result["experiment"]),
                "case_id": case_id,
                "scenario": scenario["scenario"],
                "scenario_seed": int(scenario["scenario_seed"]),
                "outage_edge_count": int(scenario["outage_edge_count"]),
                "outage_edges": outage_edges_for_csv(scenario["outage_edges"]),
                "attack": attack_summary["attack"],
                "coordinated_attack_id": attack_summary["coordinated_attack_id"],
                "mode": mode,
                "target_observation_id": attack_summary["target_observation_id"],
                "target_component_names": attack_summary["target_component_names"],
                "time_step": metrics.get("time_step", ""),
                "hour": metrics.get("hour", ""),
                "action_changed": delta["action_changed"],
                "switch_changes_vs_clean": delta["switch_changes_vs_clean"],
                "load_changes_vs_clean": delta["load_changes_vs_clean"],
                "action": np.asarray(action, dtype=int).tolist(),
            }
            row.update(metrics)
            row.update(impact)
            rows.append(row)
    return rows


def same_action(left, right):
    return np.array_equal(np.asarray(left, dtype=int), np.asarray(right, dtype=int))


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


def run_coordinated_case(experiment, scenario, scenario_context, spec, registry_by_id, learning_detectors, args):
    true_obs = scenario_context["true_obs"]
    clean_action = scenario_context["clean_action"]
    clean_policy_ms = scenario_context["clean_policy_ms"]
    clean_trajectory = scenario_context["clean_trajectory"]

    policy_obs, attack_summary = apply_coordinated_attack(true_obs, spec, registry_by_id)
    if not args.include_noop and int(attack_summary["attack_applied"]) == 0:
        return None

    detection = run_detector_suite(true_obs, policy_obs, learning_detectors=learning_detectors)
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

    return {
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
        "detection": detection,
        "fdia_aware": fdia_aware,
        "clean_trajectory": clean_trajectory,
        "attacked_trajectory": attacked_trajectory,
        "mitigated_trajectory": mitigated_trajectory,
    }


def aggregate_attack_ranking(case_rows):
    groups = {}
    for row in case_rows:
        groups.setdefault(row["coordinated_attack_id"], []).append(row)

    ranking = []
    for attack_id, rows in sorted(groups.items()):
        applied_rows = [row for row in rows if int(row.get("attack_applied", 0)) == 1]
        metric_rows = applied_rows or rows
        damaging_rows = [row for row in metric_rows if int(row["damaging_case"]) == 1]
        improvement_rows = [row for row in metric_rows if int(row["improvement_case"]) == 1]
        degradation_recovery_values = [
            row["mitigation_recovery_of_degradation_ratio"] for row in damaging_rows
        ]
        degradation_recovery_clipped_values = [
            row["mitigation_recovery_of_degradation_ratio_clipped"] for row in damaging_rows
        ]
        first = rows[0]
        ranking.append(
            {
                "attack": attack_id,
                "coordinated_attack_id": attack_id,
                "coordinated_attack_description": first.get("coordinated_attack_description", ""),
                "target_family": "coordinated",
                "target_observation_id": first.get("target_observation_id", ""),
                "target_component_names": first.get("target_component_names", ""),
                "component_count": safe_int(first.get("component_count")),
                "case_count": len(rows),
                "attack_applied_count": len(applied_rows),
                "attack_applied_rate": float(len(applied_rows) / len(rows)) if rows else 0.0,
                "mean_component_applied_count": float(
                    np.mean([row["component_applied_count"] for row in metric_rows])
                ),
                "mean_component_noop_count": float(
                    np.mean([row["component_noop_count"] for row in metric_rows])
                ),
                "mean_changed_measurements": float(
                    np.mean([row["changed_measurements"] for row in metric_rows])
                ),
                "mean_changed_action_mask_count": float(
                    np.mean([row["changed_action_mask_count"] for row in metric_rows])
                ),
                "mean_changed_topology_edge_count": float(
                    np.mean([row["changed_topology_edge_count"] for row in metric_rows])
                ),
                "mean_changed_voltage_measurement_count": float(
                    np.mean([row["changed_voltage_measurement_count"] for row in metric_rows])
                ),
                "mean_changed_branchflow_measurement_count": float(
                    np.mean([row["changed_branchflow_measurement_count"] for row in metric_rows])
                ),
                "mean_restored_energy_loss_kwh": float(
                    np.mean([row["restored_energy_loss_kwh"] for row in metric_rows])
                ),
                "max_restored_energy_loss_kwh": float(
                    np.max([row["restored_energy_loss_kwh"] for row in metric_rows])
                ),
                "mean_restored_energy_loss_percent": float(
                    np.mean([row["restored_energy_loss_percent"] for row in metric_rows])
                ),
                "mean_physical_degradation_kwh": float(
                    np.mean([row["physical_degradation_kwh"] for row in metric_rows])
                ),
                "total_physical_degradation_kwh": float(
                    np.sum([row["physical_degradation_kwh"] for row in metric_rows])
                ),
                "max_physical_degradation_kwh": float(
                    np.max([row["physical_degradation_kwh"] for row in metric_rows])
                ),
                "mean_physical_degradation_percent": float(
                    np.mean([row["physical_degradation_percent"] for row in metric_rows])
                ),
                "damaging_case_count": len(damaging_rows),
                "damaging_case_rate": float(len(damaging_rows) / len(metric_rows)) if metric_rows else 0.0,
                "mean_accidental_improvement_kwh": float(
                    np.mean([row["accidental_improvement_kwh"] for row in metric_rows])
                ),
                "max_accidental_improvement_kwh": float(
                    np.max([row["accidental_improvement_kwh"] for row in metric_rows])
                ),
                "improvement_case_count": len(improvement_rows),
                "improvement_case_rate": float(len(improvement_rows) / len(metric_rows)) if metric_rows else 0.0,
                "mean_residual_degradation_after_mitigation_kwh": float(
                    np.mean([row["residual_degradation_after_mitigation_kwh"] for row in metric_rows])
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
                    np.mean([row["mitigation_recovery_ratio"] for row in metric_rows])
                ),
                "detection_rate": float(np.mean([row["fdia_detected"] for row in metric_rows])),
                "bypass_high_impact_rate": float(
                    np.mean([row["bypass_high_impact"] for row in metric_rows])
                ),
                "action_changed_rate": float(
                    np.mean([row["attacked_action_changed"] for row in metric_rows])
                ),
                "mean_attacked_switch_changes_vs_clean": float(
                    np.mean([row["attacked_switch_changes_vs_clean"] for row in metric_rows])
                ),
                "mean_attacked_load_changes_vs_clean": float(
                    np.mean([row["attacked_load_changes_vs_clean"] for row in metric_rows])
                ),
            }
        )

    ranking.sort(
        key=lambda row: (
            row["mean_physical_degradation_kwh"],
            row["max_physical_degradation_kwh"],
            row["damaging_case_rate"],
        ),
        reverse=True,
    )
    for index, row in enumerate(ranking, start=1):
        row["damage_rank"] = index
    return ranking


def parse_component_metadata(row):
    metadata = row.get("component_attack_metadata", [])
    if isinstance(metadata, list):
        return metadata
    if metadata in (None, ""):
        return []
    try:
        parsed = json.loads(metadata)
    except (TypeError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []


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


def aggregate_component_presence(case_rows):
    groups = {}
    for row in case_rows:
        for component in parse_component_metadata(row):
            key = (
                component.get("target_observation_id", ""),
                component.get("target_family", ""),
                component.get("target_component_type", ""),
                component.get("target_component_name", ""),
                component.get("kind", ""),
                component.get("mode", ""),
            )
            groups.setdefault(key, []).append((row, component))

    rows = []
    for (
        observation_id,
        family,
        component_type,
        component_name,
        kind,
        mode,
    ), pairs in sorted(groups.items()):
        case_values = [pair[0] for pair in pairs]
        component_values = [pair[1] for pair in pairs]
        damaging = [row for row in case_values if safe_int(row.get("damaging_case")) == 1]
        rows.append(
            {
                "target_observation_id": observation_id,
                "target_family": family,
                "target_component_type": component_type,
                "target_component_name": component_name,
                "component_kind": kind,
                "component_mode": mode,
                "case_count": len(case_values),
                "coordinated_attack_count": len(
                    set(row.get("coordinated_attack_id", "") for row in case_values)
                ),
                "coordinated_attack_ids": unique_join(
                    row.get("coordinated_attack_id", "") for row in case_values
                ),
                "component_applied_count": sum(
                    safe_int(component.get("attack_applied")) for component in component_values
                ),
                "component_applied_rate": float(
                    np.mean([safe_int(component.get("attack_applied")) for component in component_values])
                )
                if component_values
                else 0.0,
                "mean_physical_degradation_kwh": float(
                    np.mean([safe_float(row.get("physical_degradation_kwh")) for row in case_values])
                )
                if case_values
                else 0.0,
                "max_physical_degradation_kwh": float(
                    np.max([safe_float(row.get("physical_degradation_kwh")) for row in case_values])
                )
                if case_values
                else 0.0,
                "damaging_case_count": len(damaging),
                "damaging_case_rate": float(len(damaging) / len(case_values)) if case_values else 0.0,
                "detection_rate": float(
                    np.mean([safe_int(row.get("fdia_detected")) for row in case_values])
                )
                if case_values
                else 0.0,
                "bypass_high_impact_rate": float(
                    np.mean([safe_int(row.get("bypass_high_impact")) for row in case_values])
                )
                if case_values
                else 0.0,
            }
        )

    rows.sort(
        key=lambda row: (
            row["mean_physical_degradation_kwh"],
            row["max_physical_degradation_kwh"],
            row["damaging_case_rate"],
        ),
        reverse=True,
    )
    for index, row in enumerate(rows, start=1):
        row["component_presence_rank"] = index
    return rows


def output_paths(output_dir, args):
    paths = {
        "case_summary": output_dir / "tsg_ieee34_coordinated_attack_cases.csv",
        "attack_ranking": output_dir / "tsg_ieee34_coordinated_attack_ranking.csv",
        "component_presence": output_dir / "tsg_ieee34_coordinated_component_presence.csv",
        "attack_specs": output_dir / "tsg_ieee34_coordinated_attack_specs.csv",
        "manifest": output_dir / "tsg_ieee34_coordinated_attack_manifest.json",
    }
    if args.write_step_results:
        paths["step_results"] = output_dir / "tsg_ieee34_coordinated_attack_steps.csv"
    return paths


def main():
    args = parse_args()
    args.output_dir = controller_output_dir(
        args.output_dir,
        DEFAULT_OUTPUT_DIR,
        "34bus",
        args.controller,
    )
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = output_paths(output_dir, args)

    if args.merge_case_files is not None:
        registry_experiment = make_controller_experiment("34bus", args, load_model=False)
        registry_by_id = observation_registry_by_id(registry_experiment)
        selected_specs, full_selected_count, spec_start, spec_end = selected_attack_specs(args)
        validate_specs(selected_specs, registry_by_id)
        case_rows = load_case_rows(args.merge_case_files)
        ranking_rows = aggregate_attack_ranking(case_rows)
        component_rows = aggregate_component_presence(case_rows)
        write_csv_or_header(case_rows, paths["case_summary"], CASE_SUMMARY_FIELDS)
        write_csv_or_header(ranking_rows, paths["attack_ranking"], RANKING_FIELDS)
        write_csv_or_header(component_rows, paths["component_presence"], COMPONENT_PRESENCE_FIELDS)
        write_csv_or_header(spec_rows(selected_specs, registry_by_id), paths["attack_specs"], SPEC_FIELDS)
        manifest = {
            "experiment": "IEEE 34-bus coordinated observation-FDIA vulnerability study",
            "system": "34bus",
            **controller_metadata("34bus", args),
            "merge_mode": True,
            "input_case_files": [str(resolve_path(path)) for path in args.merge_case_files],
            "merged_case_count": len(case_rows),
            "coordinated_attack_count": len(set(row["coordinated_attack_id"] for row in case_rows)),
            "selected_spec_count_before_window": full_selected_count,
            "spec_start_index": spec_start,
            "spec_end_index_exclusive": spec_end,
            "outputs": {key: str(value) for key, value in paths.items()},
            "notes": "Merged deterministic coordinated attack chunks and recomputed ranking/component summaries.",
        }
        paths["manifest"].write_text(safe_json(manifest) + "\n")
        for key, path in paths.items():
            print("wrote {}: {}".format(key, path), flush=True)
        return

    registry_experiment = make_controller_experiment("34bus", args, load_model=False)
    registry_outputs = write_registry_outputs(registry_experiment, output_dir / "registries")
    registry_by_id = observation_registry_by_id(registry_experiment)
    selected_specs, full_selected_count, spec_start, spec_end = selected_attack_specs(args)
    validate_specs(selected_specs, registry_by_id)

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
    all_step_rows = []
    skipped_noop_count = 0

    for case_index in range(int(args.cases)):
        scenario_seed = int(rng.integers(1, 2**31 - 1))
        scenario = generate_outage_scenario(experiment, scenario_seed, args)
        scenario_context = prepare_scenario_context(experiment, scenario, args)
        for spec in selected_specs:
            attack_id = spec["coordinated_attack_id"]
            case_id = "C{:04d}_{}_seed{}".format(case_index, safe_slug(attack_id), scenario_seed)
            print("running {} attack={}".format(case_id, attack_id), flush=True)
            result = run_coordinated_case(
                experiment,
                scenario,
                scenario_context,
                spec,
                registry_by_id,
                learning_detectors,
                args,
            )
            if result is None:
                skipped_noop_count += 1
                continue
            case_rows.append(case_summary(case_id, scenario, result, args))
            if args.write_step_results:
                all_step_rows.extend(step_rows(case_id, scenario, result))

    ranking_rows = aggregate_attack_ranking(case_rows) if case_rows else []
    component_rows = aggregate_component_presence(case_rows) if case_rows else []
    spec_table_rows = spec_rows(selected_specs, registry_by_id)

    write_csv_or_header(case_rows, paths["case_summary"], CASE_SUMMARY_FIELDS)
    write_csv_or_header(ranking_rows, paths["attack_ranking"], RANKING_FIELDS)
    write_csv_or_header(component_rows, paths["component_presence"], COMPONENT_PRESENCE_FIELDS)
    write_csv_or_header(spec_table_rows, paths["attack_specs"], SPEC_FIELDS)
    if args.write_step_results:
        write_csv_or_header(all_step_rows, paths["step_results"], STEP_RESULT_FIELDS)

    manifest = {
        "experiment": "IEEE 34-bus coordinated observation-FDIA vulnerability study",
        "system": "34bus",
        **controller_metadata("34bus", args),
        "cases": int(args.cases),
        "horizon": int(args.horizon),
        "step_hours": float(args.step_hours),
        "start_hour": int(args.start_hour),
        "seed": int(args.seed),
        "scenario_mode": "deterministic_outage_edges",
        "max_outage_fraction": float(args.max_outage_fraction),
        "max_scenario_generation_attempts": int(args.max_scenario_generation_attempts),
        "selected_spec_count_before_window": full_selected_count,
        "spec_start_index": spec_start,
        "spec_end_index_exclusive": spec_end,
        "spec_count": len(selected_specs),
        "coordinated_attack_ids": [spec["coordinated_attack_id"] for spec in selected_specs],
        "executed_case_count": len(case_rows),
        "skipped_noop_count": skipped_noop_count,
        "write_step_results": bool(args.write_step_results),
        "learning_detectors_enabled": bool(args.use_learning_detectors),
        "learning_detector_count": len(learning_detectors),
        "registry_outputs": {key: str(value) for key, value in registry_outputs.items()},
        "outputs": {key: str(value) for key, value in paths.items()},
        "notes": (
            "Each case corrupts a curated combination of direct current GRL observations. "
            "Component metadata records whether each sub-attack actually changed the observed value. "
            "OpenDSS remains the physical ground truth for all clean, attacked, and mitigated action evaluations."
        ),
    }
    paths["manifest"].write_text(safe_json(manifest) + "\n")

    for key, path in paths.items():
        print("wrote {}: {}".format(key, path), flush=True)


if __name__ == "__main__":
    main()
