"""Build IEEE 34 master evidence and observation-audit tables.

This script does not run new restoration simulations. It consolidates completed
deterministic IEEE 34 outputs and audits the observation registry so the next
attack runner is chosen from channels that the current GRL controller actually
sees.
"""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_RESULTS_DIR = BASE_DIR / "paper_results" / "tsg_ieee34"
RESULTS_DIR = DEFAULT_RESULTS_DIR


STUDIES = [
    {
        "study_id": "attack_family_baseline",
        "study_type": "attack_family",
        "file": RESULTS_DIR / "baseline_attack_full_deterministic" / "tsg_ieee34_attack_ranking.csv",
        "repeat_file": RESULTS_DIR
        / "baseline_attack_full_deterministic_repeat"
        / "tsg_ieee34_attack_ranking.csv",
        "attack_field": "attack",
        "rank_field": "damage_rank",
        "note": "Full deterministic IEEE 34 attack-family ranking.",
    },
    {
        "study_id": "attack_sensitivity",
        "study_type": "attack_sensitivity",
        "file": RESULTS_DIR / "attack_sensitivity_full" / "tsg_ieee34_attack_sensitivity_ranking.csv",
        "repeat_file": RESULTS_DIR
        / "attack_sensitivity_full_repeat"
        / "tsg_ieee34_attack_sensitivity_ranking.csv",
        "attack_field": "attack",
        "rank_field": "damage_rank",
        "note": "Severity sweep for topology, action-mask, voltage, branchflow, and energy attacks.",
    },
    {
        "study_id": "switch_action_mask_criticality",
        "study_type": "observation_criticality",
        "file": RESULTS_DIR
        / "action_mask_criticality_switch_full_deterministic"
        / "tsg_ieee34_action_mask_criticality_ranking.csv",
        "repeat_file": RESULTS_DIR
        / "action_mask_criticality_switch_full_deterministic_repeat"
        / "tsg_ieee34_action_mask_criticality_ranking.csv",
        "attack_field": None,
        "rank_field": "criticality_rank",
        "fixed_attack": "action_mask_false_unavailable_by_named_switch",
        "note": "Named switch/action-mask criticality ranking.",
    },
    {
        "study_id": "dispatch_load_false_unavailable_criticality",
        "study_type": "observation_criticality",
        "file": RESULTS_DIR
        / "action_mask_criticality_dispatch_load_false_unavailable_full_deterministic"
        / "tsg_ieee34_action_mask_criticality_ranking.csv",
        "repeat_file": RESULTS_DIR
        / "action_mask_criticality_dispatch_load_false_unavailable_full_deterministic_repeat"
        / "tsg_ieee34_action_mask_criticality_ranking.csv",
        "attack_field": None,
        "rank_field": "criticality_rank",
        "fixed_attack": "dispatch_load_action_mask_false_unavailable",
        "note": "Named dispatch-load action-mask false-unavailable criticality ranking.",
    },
    {
        "study_id": "line_status_false_open_criticality",
        "study_type": "topology_status_criticality",
        "file": RESULTS_DIR
        / "line_status_false_open_full_deterministic"
        / "tsg_ieee34_line_status_criticality_ranking.csv",
        "repeat_file": RESULTS_DIR
        / "line_status_false_open_full_deterministic_repeat"
        / "tsg_ieee34_line_status_criticality_ranking.csv",
        "attack_field": None,
        "rank_field": "criticality_rank",
        "fixed_attack": "line_status_false_open_adjacency",
        "note": "Named topology adjacency false-open line-status criticality ranking.",
    },
    {
        "study_id": "line_status_false_closed_criticality",
        "study_type": "topology_status_criticality",
        "file": RESULTS_DIR
        / "line_status_false_closed_full_deterministic"
        / "tsg_ieee34_line_status_criticality_ranking.csv",
        "repeat_file": RESULTS_DIR
        / "line_status_false_closed_full_deterministic_repeat"
        / "tsg_ieee34_line_status_criticality_ranking.csv",
        "attack_field": None,
        "rank_field": "criticality_rank",
        "fixed_attack": "line_status_false_closed_hidden_outage_adjacency",
        "note": "Named topology adjacency false-closed hidden-outage criticality ranking.",
    },
    {
        "study_id": "voltage_false_low_criticality",
        "study_type": "measurement_criticality",
        "file": RESULTS_DIR
        / "measurement_criticality_voltage_false_low_full"
        / "tsg_ieee34_measurement_criticality_ranking.csv",
        "repeat_file": RESULTS_DIR
        / "measurement_criticality_voltage_false_low_full_repeat"
        / "tsg_ieee34_measurement_criticality_ranking.csv",
        "attack_field": None,
        "rank_field": "criticality_rank",
        "fixed_attack": "voltage_false_low_0.80_pu",
        "note": "Named bus-voltage false-low criticality ranking.",
    },
    {
        "study_id": "branchflow_hide_criticality",
        "study_type": "measurement_criticality",
        "file": RESULTS_DIR
        / "measurement_criticality_branchflow_hide_full_chunked"
        / "tsg_ieee34_measurement_criticality_ranking.csv",
        "repeat_file": RESULTS_DIR
        / "measurement_criticality_branchflow_hide_full_chunked_repeat"
        / "tsg_ieee34_measurement_criticality_ranking.csv",
        "attack_field": None,
        "rank_field": "criticality_rank",
        "fixed_attack": "branchflow_hide_to_zero",
        "note": "Named branchflow hide-to-zero criticality ranking.",
    },
    {
        "study_id": "coordinated_attack_study",
        "study_type": "coordinated_attack",
        "file": RESULTS_DIR
        / "coordinated_attack_full_deterministic"
        / "tsg_ieee34_coordinated_attack_ranking.csv",
        "repeat_file": RESULTS_DIR
        / "coordinated_attack_full_deterministic_repeat"
        / "tsg_ieee34_coordinated_attack_ranking.csv",
        "attack_field": "coordinated_attack_id",
        "rank_field": "damage_rank",
        "note": "Curated coordinated attacks combining direct IEEE 34 action-mask, topology, voltage, and branchflow observation channels.",
    },
    {
        "study_id": "advanced_defense_stealth_stress",
        "study_type": "advanced_detection_mitigation",
        "file": RESULTS_DIR
        / "advanced_defense_stealth_full_deterministic"
        / "tsg_ieee34_advanced_defense_stealth_ranking.csv",
        "repeat_file": RESULTS_DIR
        / "advanced_defense_stealth_full_deterministic_repeat"
        / "tsg_ieee34_advanced_defense_stealth_ranking.csv",
        "attack_field": "stress_attack_id",
        "rank_field": "defense_rank",
        "note": "IEEE 34 detector-profile and mitigation-mode stress test using high-impact and stealth-constrained Load_s890-centered attacks.",
    },
    {
        "study_id": "advanced_defense_learning_stealth_stress",
        "study_type": "advanced_detection_mitigation_learning",
        "file": RESULTS_DIR
        / "advanced_defense_stealth_learning_full_deterministic"
        / "tsg_ieee34_advanced_defense_stealth_ranking.csv",
        "repeat_file": RESULTS_DIR
        / "advanced_defense_stealth_learning_full_deterministic_repeat"
        / "tsg_ieee34_advanced_defense_stealth_ranking.csv",
        "attack_field": "stress_attack_id",
        "rank_field": "defense_rank",
        "note": "IEEE 34 detector-profile and mitigation-mode stress test with existing trained learning detectors enabled.",
    },
]


REGISTRY_CANDIDATES = [
    RESULTS_DIR
    / "measurement_criticality_voltage_false_low_full"
    / "registries"
    / "ieee34_observation_registry.csv",
    RESULTS_DIR / "registries" / "ieee34_observation_registry.csv",
    RESULTS_DIR
    / "baseline_attack_full_deterministic"
    / "registries"
    / "ieee34_observation_registry.csv",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build IEEE 34 master evidence and observation-audit tables."
    )
    parser.add_argument(
        "--results-dir",
        default="paper_results/tsg_ieee34",
        help="Completed IEEE 34 result tree to audit, relative to RL_Testing unless absolute.",
    )
    parser.add_argument(
        "--output-dir",
        default="paper_results/tsg_ieee34/master_evidence_audit",
        help="Output directory, relative to RL_Testing unless absolute.",
    )
    return parser.parse_args()


def resolve_path(path_text):
    path = Path(path_text)
    if path.is_absolute():
        return path
    return BASE_DIR / path


def read_csv(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


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


def boolish(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def relative(path):
    try:
        return str(path.relative_to(BASE_DIR))
    except ValueError:
        return str(path)


def rebase_results_path(path, results_dir):
    try:
        suffix = Path(path).relative_to(DEFAULT_RESULTS_DIR)
    except ValueError:
        return Path(path)
    return Path(results_dir) / suffix


def source_path_with_fallback(path):
    path = Path(path)
    if path.exists():
        return path
    text = str(path)
    if "measurement_criticality_branchflow_hide_full_chunked" in text:
        candidate = Path(
            text.replace(
                "measurement_criticality_branchflow_hide_full_chunked",
                "measurement_criticality_branchflow_hide_full",
            )
        )
        if candidate.exists():
            return candidate
    return path


def studies_for_results_dir(results_dir):
    rebased = []
    for study in STUDIES:
        item = dict(study)
        item["file"] = source_path_with_fallback(rebase_results_path(study["file"], results_dir))
        item["repeat_file"] = rebase_results_path(study["repeat_file"], results_dir)
        rebased.append(item)
    return rebased


def registry_candidates_for_results_dir(results_dir):
    return [rebase_results_path(path, results_dir) for path in REGISTRY_CANDIDATES]


def line_diff_count(left_path, right_path):
    if not left_path.exists() or not right_path.exists():
        return ""
    left = left_path.read_text(encoding="utf-8").splitlines()
    right = right_path.read_text(encoding="utf-8").splitlines()
    count = abs(len(left) - len(right))
    count += sum(1 for left_line, right_line in zip(left, right) if left_line != right_line)
    return count


def observed_entity(row):
    for field in ("target_observation_id", "coordinated_attack_id", "sensitivity_id", "attack"):
        if row.get(field):
            return row[field]
    return ""


def paper_readiness_note(row):
    mean_deg = safe_float(row.get("mean_physical_degradation_kwh"))
    max_deg = safe_float(row.get("max_physical_degradation_kwh"))
    damaging_count = safe_int(row.get("damaging_case_count"))
    detection_rate = safe_float(row.get("detection_rate"), default=1.0)
    bypass_rate = safe_float(row.get("bypass_high_impact_rate"))
    if mean_deg > 0.0 or max_deg > 0.0 or damaging_count > 0:
        if bypass_rate > 0.0:
            return "Damaging and bypassing in at least one setting; high-priority paper evidence."
        return "Damaging physical impact observed; suitable for vulnerability ranking."
    if detection_rate < 1.0:
        return "No restored-energy degradation here, but useful for detection/bypass discussion."
    return "No positive restored-energy degradation under this tested setting."


def build_master_evidence(results_dir):
    rows = []
    missing_inputs = []
    repeat_diffs = {}
    for study in studies_for_results_dir(results_dir):
        source = study["file"]
        if not source.exists():
            missing_inputs.append(relative(source))
            continue
        repeat_diff = line_diff_count(source, study["repeat_file"])
        repeat_diffs[study["study_id"]] = repeat_diff
        for raw in read_csv(source):
            attack = study.get("fixed_attack") or raw.get(study.get("attack_field"), "")
            if raw.get("sensitivity_id"):
                attack = "{}: {}".format(attack, raw["sensitivity_id"])
            rank = safe_int(raw.get(study["rank_field"]), default=0)
            row = {
                "study_id": study["study_id"],
                "study_type": study["study_type"],
                "source_csv": relative(source),
                "repeat_csv": relative(study["repeat_file"]),
                "repeat_ranking_diff_count": repeat_diff,
                "source_rank": rank,
                "attack_or_corruption": attack,
                "sensitivity_description": raw.get("sensitivity_description", ""),
                "target_family": raw.get("target_family", ""),
                "target_observation_id": raw.get("target_observation_id", ""),
                "target_component_type": raw.get("target_component_type", ""),
                "target_component_name": raw.get("target_component_name", ""),
                "entity_id": observed_entity(raw),
                "case_count": safe_int(raw.get("case_count")),
                "attack_applied_count": safe_int(raw.get("attack_applied_count")),
                "mean_physical_degradation_kwh": safe_float(
                    raw.get("mean_physical_degradation_kwh")
                ),
                "total_physical_degradation_kwh": safe_float(
                    raw.get("total_physical_degradation_kwh")
                ),
                "max_physical_degradation_kwh": safe_float(
                    raw.get("max_physical_degradation_kwh")
                ),
                "damaging_case_count": safe_int(raw.get("damaging_case_count")),
                "damaging_case_rate": safe_float(raw.get("damaging_case_rate")),
                "mean_restored_energy_loss_kwh": safe_float(
                    raw.get("mean_restored_energy_loss_kwh")
                ),
                "mean_accidental_improvement_kwh": safe_float(
                    raw.get("mean_accidental_improvement_kwh")
                ),
                "detection_rate": safe_float(raw.get("detection_rate")),
                "bypass_high_impact_rate": safe_float(raw.get("bypass_high_impact_rate")),
                "mean_mitigation_recovery_of_degradation_ratio_clipped": safe_float(
                    raw.get("mean_mitigation_recovery_of_degradation_ratio_clipped")
                ),
                "action_changed_rate": safe_float(raw.get("action_changed_rate")),
                "mean_attacked_switch_changes_vs_clean": safe_float(
                    raw.get("mean_attacked_switch_changes_vs_clean")
                    or raw.get("mean_switch_changes_vs_clean")
                ),
                "mean_attacked_load_changes_vs_clean": safe_float(
                    raw.get("mean_attacked_load_changes_vs_clean")
                    or raw.get("mean_load_changes_vs_clean")
                ),
                "study_note": study["note"],
                "paper_readiness_note": paper_readiness_note(raw),
            }
            rows.append(row)

    rows.sort(
        key=lambda item: (
            item["mean_physical_degradation_kwh"],
            item["max_physical_degradation_kwh"],
            item["damaging_case_rate"],
        ),
        reverse=True,
    )
    for rank, row in enumerate(rows, start=1):
        row["global_damage_rank"] = rank
    return rows, missing_inputs, repeat_diffs


def select_registry_path(results_dir):
    candidates = registry_candidates_for_results_dir(results_dir)
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(
        "No IEEE 34 observation registry found in expected locations: {}".format(
            ", ".join(relative(path) for path in candidates)
        )
    )


def unique_join(values, limit=None):
    ordered = []
    seen = set()
    for value in values:
        if value in (None, "") or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    if limit is not None:
        ordered = ordered[:limit]
    return "; ".join(ordered)


def family_note(family, attackable_current, rows):
    if family == "load":
        return (
            "Load demand metadata exists, but load demand is not a current direct GRL "
            "observation. Load-control availability is attackable through ActionMasking "
            "dispatch_load entries."
        )
    if family == "der":
        return (
            "DER metadata exists for generator buses, but DER availability/capacity is "
            "not a current direct GRL observation. A DER-specific FDIA study needs a "
            "controller-input extension or a clearly separate physical-contingency study."
        )
    if family == "topology":
        return "Direct current GRL input through Adjacency; valid for line-status/topology attacks."
    if family == "action_mask":
        return "Direct current policy input; valid for switch and dispatch-load action-availability attacks."
    if family == "voltage":
        return "Direct current GRL measurement input; voltage FDIA is valid."
    if family == "branchflow":
        return "Direct current GRL measurement input; branchflow FDIA is valid."
    if family == "global":
        return "Direct scalar GRL inputs for energy supply, voltage violation, and convergence violation."
    if attackable_current:
        return "Direct current GRL input; valid attack surface."
    return "Not a current direct attackable GRL observation in this registry."


def build_observation_family_audit(registry_rows):
    families = {}
    for row in registry_rows:
        families.setdefault(row["family"], []).append(row)

    audit_rows = []
    for family, rows in sorted(families.items()):
        attackable = [row for row in rows if boolish(row.get("attackable"))]
        current = [row for row in rows if boolish(row.get("current_grl_input"))]
        attackable_current = [
            row
            for row in rows
            if boolish(row.get("attackable")) and boolish(row.get("current_grl_input"))
        ]
        audit_rows.append(
            {
                "family": family,
                "total_registry_count": len(rows),
                "attackable_count": len(attackable),
                "current_grl_input_count": len(current),
                "attackable_current_grl_input_count": len(attackable_current),
                "direct_current_grl_attack_surface": "yes" if attackable_current else "no",
                "observation_keys": unique_join(row.get("observation_key", "") for row in rows),
                "component_types": unique_join(row.get("component_type", "") for row in rows),
                "attack_modes": unique_join(row.get("attack_modes", "") for row in rows),
                "sample_observation_ids": unique_join(
                    (row.get("observation_id", "") for row in rows), limit=8
                ),
                "audit_note": family_note(family, len(attackable_current), rows),
            }
        )
    return audit_rows


def count_rows(registry_rows, family=None, component_type=None, current=None, attackable=None):
    rows = registry_rows
    if family is not None:
        rows = [row for row in rows if row.get("family") == family]
    if component_type is not None:
        rows = [row for row in rows if row.get("component_type") == component_type]
    if current is not None:
        rows = [row for row in rows if boolish(row.get("current_grl_input")) == current]
    if attackable is not None:
        rows = [row for row in rows if boolish(row.get("attackable")) == attackable]
    return len(rows)


def build_attack_surface_audit(registry_rows):
    switch_action_count = len(
        [
            row
            for row in registry_rows
            if row.get("family") == "action_mask"
            and row.get("component_type") in {"sectionalizing_switch", "tie_switch"}
            and boolish(row.get("current_grl_input"))
        ]
    )
    dispatch_load_action_count = count_rows(
        registry_rows,
        family="action_mask",
        component_type="dispatch_load",
        current=True,
        attackable=True,
    )
    fault_count = count_rows(registry_rows, family="fault")
    rows = [
        {
            "professor_requirement_area": "topology/status FDIA",
            "registry_evidence": "{} direct topology adjacency entries; {} switch action-mask entries".format(
                count_rows(registry_rows, family="topology", current=True, attackable=True),
                switch_action_count,
            ),
            "direct_current_grl_input": "yes",
            "valid_current_attack": "yes",
            "current_status": "Studied at family/sensitivity level; switch action-mask and named line-status criticality completed.",
            "recommended_next_step": "Use the completed coordinated results to select high-impact cases for advanced detector/mitigation stress tests.",
        },
        {
            "professor_requirement_area": "switch/breaker/line status corruption",
            "registry_evidence": "{} switch action-mask entries and {} topology line entries are direct inputs".format(
                switch_action_count,
                count_rows(registry_rows, family="topology", current=True, attackable=True),
            ),
            "direct_current_grl_input": "yes",
            "valid_current_attack": "yes",
            "current_status": "False-unavailable switch action-mask and named line-status false-open/false-closed adjacency attacks completed.",
            "recommended_next_step": "Stress-test high-impact switch/load/line combinations under stronger detector and stealth settings.",
        },
        {
            "professor_requirement_area": "load attack",
            "registry_evidence": "{} load-demand metadata entries are not direct inputs; {} dispatch-load action-mask entries are direct inputs".format(
                count_rows(registry_rows, family="load"),
                dispatch_load_action_count,
            ),
            "direct_current_grl_input": "partial",
            "valid_current_attack": "yes for load-control status via ActionMasking; no for pure load-demand observation FDIA",
            "current_status": "Dispatch-load false-unavailable action-mask criticality is completed; pure load-demand bias is not valid as observation FDIA for the current controller.",
            "recommended_next_step": "Use high-impact dispatch-load targets in coordinated attacks; treat load-demand bias as a future controller-input extension unless the model is changed.",
        },
        {
            "professor_requirement_area": "DER attack",
            "registry_evidence": "{} DER metadata entries; {} direct DER GRL inputs".format(
                count_rows(registry_rows, family="der"),
                count_rows(registry_rows, family="der", current=True, attackable=True),
            ),
            "direct_current_grl_input": "no",
            "valid_current_attack": "not as current observation FDIA",
            "current_status": "DER availability/capacity does not appear as a current controller observation channel.",
            "recommended_next_step": "Do not fake DER observation FDIA. Either extend controller observation/model or define a separate physical DER-contingency study.",
        },
        {
            "professor_requirement_area": "fault-status attack",
            "registry_evidence": "{} explicit fault-status registry entries".format(fault_count),
            "direct_current_grl_input": "no",
            "valid_current_attack": "not as named fault-status observation FDIA",
            "current_status": "Fault/outage information is represented through outage scenarios and topology/action state; hidden outage has been mapped to false-closed topology adjacency.",
            "recommended_next_step": "Do not claim explicit fault-status FDIA unless a formal fault-status observation channel is added.",
        },
        {
            "professor_requirement_area": "voltage measurement attack",
            "registry_evidence": "{} direct voltage entries".format(
                count_rows(registry_rows, family="voltage", current=True, attackable=True)
            ),
            "direct_current_grl_input": "yes",
            "valid_current_attack": "yes",
            "current_status": "False-low voltage criticality completed and damaging buses identified.",
            "recommended_next_step": "Use voltage false-low targets in advanced stealth and detector-threshold sensitivity tests.",
        },
        {
            "professor_requirement_area": "branchflow measurement attack",
            "registry_evidence": "{} direct branchflow entries".format(
                count_rows(registry_rows, family="branchflow", current=True, attackable=True)
            ),
            "direct_current_grl_input": "yes",
            "valid_current_attack": "yes",
            "current_status": "Hide-to-zero branchflow criticality completed; no physical degradation in this setting.",
            "recommended_next_step": "Treat branchflow as a coordinated/stealth channel unless a separate action-targeted branchflow perturbation is added.",
        },
        {
            "professor_requirement_area": "coordinated and stealthy attacks",
            "registry_evidence": "Direct channels exist for topology, action-mask, voltage, branchflow, and global EnergySupp.",
            "direct_current_grl_input": "yes",
            "valid_current_attack": "yes",
            "current_status": "Dedicated IEEE 34 deterministic coordinated attack runner and advanced defense/stealth stress runner completed.",
            "recommended_next_step": "Use the high-impact relaxed-detector bypass cases to motivate strict status-integrity detection, robust mitigation, and cross-system replication on IEEE 123.",
        },
    ]
    return rows


def build_study_summary(master_rows):
    groups = {}
    for row in master_rows:
        groups.setdefault(row["study_id"], []).append(row)
    summary = []
    for study_id, rows in sorted(groups.items()):
        top = max(
            rows,
            key=lambda item: (
                item["mean_physical_degradation_kwh"],
                item["max_physical_degradation_kwh"],
            ),
        )
        summary.append(
            {
                "study_id": study_id,
                "row_count": len(rows),
                "repeat_ranking_diff_count": top["repeat_ranking_diff_count"],
                "damaging_rows": sum(1 for row in rows if row["damaging_case_count"] > 0),
                "top_entity": top["entity_id"],
                "top_attack_or_corruption": top["attack_or_corruption"],
                "top_mean_physical_degradation_kwh": top["mean_physical_degradation_kwh"],
                "top_max_physical_degradation_kwh": top["max_physical_degradation_kwh"],
                "top_detection_rate": top["detection_rate"],
                "top_bypass_high_impact_rate": top["bypass_high_impact_rate"],
            }
        )
    return summary


def markdown_table(rows, columns, limit=None):
    selected = rows[:limit] if limit is not None else rows
    lines = []
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("| " + " | ".join(["---"] * len(columns)) + " |")
    for row in selected:
        values = []
        for column in columns:
            value = row.get(column, "")
            if isinstance(value, float):
                value = "{:.3f}".format(value)
            values.append(str(value).replace("|", "/"))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def build_markdown(master_rows, family_rows, surface_rows, output_paths):
    top_columns = [
        "global_damage_rank",
        "study_id",
        "attack_or_corruption",
        "entity_id",
        "mean_physical_degradation_kwh",
        "max_physical_degradation_kwh",
        "damaging_case_count",
        "detection_rate",
        "bypass_high_impact_rate",
    ]
    family_columns = [
        "family",
        "total_registry_count",
        "attackable_current_grl_input_count",
        "direct_current_grl_attack_surface",
        "audit_note",
    ]
    surface_columns = [
        "professor_requirement_area",
        "direct_current_grl_input",
        "valid_current_attack",
        "recommended_next_step",
    ]
    lines = [
        "# IEEE 34 Master Evidence and Observation Audit",
        "",
        "Generated: {} local time".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "",
        "This file summarizes completed deterministic IEEE 34 evidence and audits which",
        "observation families are true current GRL inputs. It is intended to prevent",
        "paper claims from drifting beyond what the controller actually observes.",
        "",
        "## Output Files",
        "",
    ]
    for label, path in output_paths.items():
        lines.append("- {}: `{}`".format(label, relative(path)))
    lines.extend(
        [
            "",
            "## Top Evidence Rows",
            "",
            markdown_table(master_rows, top_columns, limit=12),
            "",
            "## Observation Family Audit",
            "",
            markdown_table(family_rows, family_columns),
            "",
            "## Professor Requirement Audit",
            "",
            markdown_table(surface_rows, surface_columns),
            "",
            "## Main Next Implementation Recommendation",
            "",
            "Next convert the IEEE 34 evidence into paper-ready figures/tables",
            "and then replicate the same audited workflow on IEEE 123. The IEEE",
            "34 advanced stress study shows that strict status-integrity",
            "detection is essential for Load_s890-centered attacks: relaxed",
            "status thresholds create high-impact bypass cases under gated",
            "mitigation. Do not claim load-demand, DER-availability, or",
            "fault-status observation FDIA unless the controller observation is",
            "extended or the attack is explicitly defined as a separate",
            "physical-contingency study.",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    args = parse_args()
    results_dir = resolve_path(args.results_dir)
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    master_rows, missing_inputs, repeat_diffs = build_master_evidence(results_dir)
    registry_path = select_registry_path(results_dir)
    registry_rows = read_csv(registry_path)
    family_rows = build_observation_family_audit(registry_rows)
    surface_rows = build_attack_surface_audit(registry_rows)
    study_summary_rows = build_study_summary(master_rows)

    paths = {
        "master_evidence": output_dir / "ieee34_master_evidence_table.csv",
        "study_summary": output_dir / "ieee34_study_summary.csv",
        "observation_family_audit": output_dir / "ieee34_observation_family_audit.csv",
        "attack_surface_audit": output_dir / "ieee34_attack_surface_audit.csv",
        "markdown_summary": output_dir / "IEEE34_Master_Evidence_Audit.md",
        "manifest": output_dir / "ieee34_master_evidence_manifest.json",
    }
    write_csv(master_rows, paths["master_evidence"])
    write_csv(study_summary_rows, paths["study_summary"])
    write_csv(family_rows, paths["observation_family_audit"])
    write_csv(surface_rows, paths["attack_surface_audit"])
    markdown = build_markdown(master_rows, family_rows, surface_rows, paths)
    paths["markdown_summary"].write_text(markdown + "\n", encoding="utf-8")

    manifest = {
        "experiment": "IEEE 34 master evidence and observation audit",
        "generated_at_local": datetime.now().isoformat(timespec="seconds"),
        "results_dir": relative(results_dir),
        "registry_source": relative(registry_path),
        "completed_study_count": len(study_summary_rows),
        "master_evidence_row_count": len(master_rows),
        "observation_family_count": len(family_rows),
        "attack_surface_row_count": len(surface_rows),
        "repeat_ranking_diff_counts": repeat_diffs,
        "missing_inputs": missing_inputs,
        "outputs": {key: relative(path) for key, path in paths.items()},
        "notes": (
            "The audit distinguishes direct current GRL observations from candidate "
            "metadata. Load-demand, DER, and fault-status claims should follow this "
            "distinction unless the controller observation is changed."
        ),
    }
    paths["manifest"].write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for key, path in paths.items():
        print("wrote {}: {}".format(key, path), flush=True)


if __name__ == "__main__":
    main()
