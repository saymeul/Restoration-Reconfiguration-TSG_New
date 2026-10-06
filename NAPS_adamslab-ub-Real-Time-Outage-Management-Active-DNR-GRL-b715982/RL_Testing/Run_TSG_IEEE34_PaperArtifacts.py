"""Build paper-facing IEEE 34 TSG vulnerability artifacts.

This script reads the audited IEEE 34 simulation outputs and creates
tables, figures, a concise results narrative, and a manifest. It does not
rerun restoration simulations.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import textwrap
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_RESULTS_DIR = BASE_DIR / "paper_results" / "tsg_ieee34"
RESULTS_DIR = DEFAULT_RESULTS_DIR
LEARNING_DETECTOR_DIR = BASE_DIR / "34bus" / "paper_results" / "learning_detectors"


INPUTS = {
    "master_evidence": RESULTS_DIR
    / "master_evidence_audit"
    / "ieee34_master_evidence_table.csv",
    "study_summary": RESULTS_DIR / "master_evidence_audit" / "ieee34_study_summary.csv",
    "attack_surface_audit": RESULTS_DIR
    / "master_evidence_audit"
    / "ieee34_attack_surface_audit.csv",
    "baseline_attack": RESULTS_DIR
    / "baseline_attack_full_deterministic"
    / "tsg_ieee34_attack_ranking.csv",
    "switch_action_mask": RESULTS_DIR
    / "action_mask_criticality_switch_full_deterministic"
    / "tsg_ieee34_action_mask_criticality_ranking.csv",
    "dispatch_load_action_mask": RESULTS_DIR
    / "action_mask_criticality_dispatch_load_false_unavailable_full_deterministic"
    / "tsg_ieee34_action_mask_criticality_ranking.csv",
    "line_status_false_open": RESULTS_DIR
    / "line_status_false_open_full_deterministic"
    / "tsg_ieee34_line_status_criticality_ranking.csv",
    "line_status_false_closed": RESULTS_DIR
    / "line_status_false_closed_full_deterministic"
    / "tsg_ieee34_line_status_criticality_ranking.csv",
    "voltage_false_low": RESULTS_DIR
    / "measurement_criticality_voltage_false_low_full"
    / "tsg_ieee34_measurement_criticality_ranking.csv",
    "branchflow_hide": RESULTS_DIR
    / "measurement_criticality_branchflow_hide_full_chunked"
    / "tsg_ieee34_measurement_criticality_ranking.csv",
    "coordinated_attack": RESULTS_DIR
    / "coordinated_attack_full_deterministic"
    / "tsg_ieee34_coordinated_attack_ranking.csv",
    "advanced_defense": RESULTS_DIR
    / "advanced_defense_stealth_full_deterministic"
    / "tsg_ieee34_advanced_defense_stealth_ranking.csv",
    "advanced_defense_learning": RESULTS_DIR
    / "advanced_defense_stealth_learning_full_deterministic"
    / "tsg_ieee34_advanced_defense_stealth_ranking.csv",
    "learning_model_summary": LEARNING_DETECTOR_DIR / "model_summary.csv",
}


def rebase_results_path(path: Path, results_dir: Path) -> Path:
    try:
        suffix = Path(path).relative_to(DEFAULT_RESULTS_DIR)
    except ValueError:
        return Path(path)
    return Path(results_dir) / suffix


def source_path_with_fallback(path: Path) -> Path:
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


def inputs_for_results_dir(results_dir: Path) -> dict[str, Path]:
    return {
        name: source_path_with_fallback(rebase_results_path(path, results_dir))
        for name, path in INPUTS.items()
    }


def resolve_path(path_text: str | None, default: Path) -> Path:
    if not path_text:
        return default
    path = Path(path_text)
    if path.is_absolute():
        return path
    return (BASE_DIR / path).resolve()


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(BASE_DIR))
    except ValueError:
        return str(path)


def read_csv(path: Path, missing: list[str]) -> list[dict[str, str]]:
    if not path.exists():
        missing.append(relative(path))
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def safe_float(value, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return number


def safe_int(value, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def pct(value) -> float:
    return 100.0 * safe_float(value)


def round_row(row: dict, fields: list[str]) -> dict:
    rounded = {}
    for field in fields:
        value = row.get(field, "")
        if isinstance(value, float):
            rounded[field] = round(value, 6)
        else:
            rounded[field] = value
    return rounded


def fmt(value) -> str:
    if isinstance(value, float):
        return "{:.3f}".format(value)
    if isinstance(value, int):
        return str(value)
    text = "" if value is None else str(value)
    try:
        number = float(text)
    except (TypeError, ValueError):
        return text
    if not math.isfinite(number):
        return text
    if abs(number - round(number)) < 1e-9 and abs(number) < 1000000:
        return str(int(round(number)))
    return "{:.3f}".format(number)


def markdown_table(rows: list[dict], columns: list[str], limit: int | None = None) -> str:
    rows = rows[:limit] if limit is not None else rows
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    lines = [header, sep]
    for row in rows:
        cells = []
        for column in columns:
            cell = fmt(row.get(column, ""))
            cell = cell.replace("|", "/")
            cells.append(cell)
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_table_bundle(
    table_dir: Path,
    name: str,
    rows: list[dict],
    columns: list[str],
    title: str,
    md_limit: int = 20,
) -> list[str]:
    csv_path = table_dir / "{}.csv".format(name)
    md_path = table_dir / "{}.md".format(name)
    clipped_rows = [round_row(row, columns) for row in rows]
    write_csv(csv_path, clipped_rows, columns)
    body = ["# {}".format(title), "", markdown_table(clipped_rows, columns, md_limit), ""]
    if len(clipped_rows) > md_limit:
        body.append("Markdown preview shows first {} of {} rows.".format(md_limit, len(clipped_rows)))
        body.append("")
    write_text(md_path, "\n".join(body))
    return [relative(csv_path), relative(md_path)]


def sort_rows(rows: list[dict], field: str, reverse: bool = True) -> list[dict]:
    return sorted(rows, key=lambda row: safe_float(row.get(field)), reverse=reverse)


def normalize_master(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        out.append(
            {
                "rank": safe_int(row.get("global_damage_rank")),
                "study_id": row.get("study_id", ""),
                "study_type": row.get("study_type", ""),
                "attack_or_corruption": row.get("attack_or_corruption", ""),
                "target_observation_id": row.get("target_observation_id", ""),
                "case_count": safe_int(row.get("case_count")),
                "mean_degradation_kwh": safe_float(row.get("mean_physical_degradation_kwh")),
                "max_degradation_kwh": safe_float(row.get("max_physical_degradation_kwh")),
                "damaging_cases": safe_int(row.get("damaging_case_count")),
                "detection_rate_pct": pct(row.get("detection_rate")),
                "bypass_rate_pct": pct(row.get("bypass_high_impact_rate")),
                "mitigation_recovery_pct": pct(
                    row.get("mean_mitigation_recovery_of_degradation_ratio_clipped")
                ),
                "paper_readiness_note": row.get("paper_readiness_note", ""),
            }
        )
    return sort_rows(out, "mean_degradation_kwh")


def normalize_attack_family(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        out.append(
            {
                "damage_rank": safe_int(row.get("damage_rank")),
                "attack": row.get("attack", ""),
                "case_count": safe_int(row.get("case_count")),
                "mean_degradation_kwh": safe_float(row.get("mean_physical_degradation_kwh")),
                "max_degradation_kwh": safe_float(row.get("max_physical_degradation_kwh")),
                "damaging_cases": safe_int(row.get("damaging_case_count")),
                "damaging_case_rate_pct": pct(row.get("damaging_case_rate")),
                "mean_accidental_improvement_kwh": safe_float(
                    row.get("mean_accidental_improvement_kwh")
                ),
                "detection_rate_pct": pct(row.get("detection_rate")),
                "mitigation_recovery_pct": pct(
                    row.get("mean_mitigation_recovery_of_degradation_ratio_clipped")
                ),
            }
        )
    return sorted(out, key=lambda row: row["damage_rank"] or 999999)


def normalize_observation_rows(
    rows: list[dict],
    source_family: str,
    attack_definition: str,
    note: str,
    limit_per_family: int = 10,
) -> list[dict]:
    normalized = []
    sorted_rows = sort_rows(rows, "mean_physical_degradation_kwh")[:limit_per_family]
    for row in sorted_rows:
        normalized.append(
            {
                "evidence_family": source_family,
                "attack_definition": attack_definition,
                "target_observation_id": row.get("target_observation_id", ""),
                "target_component_type": row.get("target_component_type", ""),
                "target_component_name": row.get("target_component_name", ""),
                "case_count": safe_int(row.get("case_count")),
                "attack_applied_count": safe_int(row.get("attack_applied_count")),
                "mean_degradation_kwh": safe_float(row.get("mean_physical_degradation_kwh")),
                "max_degradation_kwh": safe_float(row.get("max_physical_degradation_kwh")),
                "damaging_cases": safe_int(row.get("damaging_case_count")),
                "detection_rate_pct": pct(row.get("detection_rate")),
                "action_changed_rate_pct": pct(row.get("action_changed_rate")),
                "mitigation_recovery_pct": pct(
                    row.get("mean_mitigation_recovery_of_degradation_ratio_clipped")
                ),
                "paper_note": note,
            }
        )
    return normalized


def build_observation_criticality(inputs: dict[str, list[dict]]) -> list[dict]:
    rows = []
    rows.extend(
        normalize_observation_rows(
            inputs["dispatch_load_action_mask"],
            "load-control action mask",
            "false unavailable dispatch-load action",
            "Direct current-GRL load-status/control observation.",
        )
    )
    rows.extend(
        normalize_observation_rows(
            inputs["switch_action_mask"],
            "switch action mask",
            "false unavailable switch action",
            "Direct current-GRL switch-status/action availability observation.",
        )
    )
    rows.extend(
        normalize_observation_rows(
            inputs["line_status_false_open"],
            "line status/topology",
            "false open line-status adjacency",
            "Direct topology/status observation.",
        )
    )
    rows.extend(
        normalize_observation_rows(
            inputs["line_status_false_closed"],
            "line status/topology",
            "false closed hidden-outage adjacency",
            "Direct topology/status observation; executable cases are sparse.",
        )
    )
    rows.extend(
        normalize_observation_rows(
            inputs["voltage_false_low"],
            "bus voltage",
            "false low voltage measurement",
            "Direct measurement observation.",
        )
    )
    rows.extend(
        normalize_observation_rows(
            inputs["branchflow_hide"],
            "branch flow",
            "hide branchflow to zero",
            "Standalone branchflow hiding was not physically damaging in this grid.",
        )
    )
    return sort_rows(rows, "mean_degradation_kwh")


def normalize_coordinated(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        attack_id = (
            row.get("coordinated_attack_id")
            or row.get("attack")
            or row.get("stress_attack_id")
            or row.get("sensitivity_id")
            or ""
        )
        out.append(
            {
                "damage_rank": safe_int(row.get("damage_rank") or row.get("defense_rank")),
                "attack_id": attack_id,
                "target_observation_id": row.get("target_observation_id", ""),
                "target_component_names": row.get("target_component_names", ""),
                "case_count": safe_int(row.get("case_count")),
                "mean_degradation_kwh": safe_float(row.get("mean_physical_degradation_kwh")),
                "max_degradation_kwh": safe_float(row.get("max_physical_degradation_kwh")),
                "damaging_cases": safe_int(row.get("damaging_case_count")),
                "detection_rate_pct": pct(row.get("detection_rate")),
                "bypass_rate_pct": pct(row.get("bypass_high_impact_rate")),
                "mitigation_recovery_pct": pct(
                    row.get("mean_mitigation_recovery_of_degradation_ratio_clipped")
                ),
                "mean_load_changes": safe_float(row.get("mean_attacked_load_changes_vs_clean")),
                "mean_switch_changes": safe_float(row.get("mean_attacked_switch_changes_vs_clean")),
            }
        )
    return sort_rows(out, "mean_degradation_kwh")


def normalize_advanced(rows: list[dict], source: str) -> list[dict]:
    out = []
    for row in rows:
        out.append(
            {
                "source": source,
                "defense_rank": safe_int(row.get("defense_rank")),
                "attack_id": row.get("stress_attack_id") or row.get("attack", ""),
                "attack_class": row.get("attack_class", ""),
                "detector_profile": row.get("detector_profile", ""),
                "mitigation_mode": row.get("mitigation_mode", ""),
                "target_observation_id": row.get("target_observation_id", ""),
                "case_count": safe_int(row.get("case_count")),
                "mean_degradation_kwh": safe_float(row.get("mean_physical_degradation_kwh")),
                "max_degradation_kwh": safe_float(row.get("max_physical_degradation_kwh")),
                "damaging_cases": safe_int(row.get("damaging_case_count")),
                "mean_residual_degradation_kwh": safe_float(
                    row.get("mean_residual_degradation_after_mitigation_kwh")
                ),
                "mitigation_recovery_pct": pct(
                    row.get("mean_mitigation_recovery_of_degradation_ratio_clipped")
                ),
                "detection_rate_pct": pct(row.get("detection_rate")),
                "bypass_rate_pct": pct(row.get("bypass_high_impact_rate")),
                "stealth_success_rate_pct": pct(row.get("stealth_success_rate")),
                "reference_candidate_selected_pct": pct(row.get("reference_candidate_selected_rate")),
            }
        )
    return sort_rows(out, "mean_degradation_kwh")


def build_learning_ablation(
    base_rows: list[dict], learning_rows: list[dict]
) -> list[dict]:
    base_by_key = {
        (row["attack_id"], row["detector_profile"], row["mitigation_mode"]): row
        for row in base_rows
    }
    out = []
    for learned in learning_rows:
        key = (learned["attack_id"], learned["detector_profile"], learned["mitigation_mode"])
        base = base_by_key.get(key)
        if not base:
            continue
        out.append(
            {
                "attack_id": learned["attack_id"],
                "detector_profile": learned["detector_profile"],
                "mitigation_mode": learned["mitigation_mode"],
                "base_detection_rate_pct": base["detection_rate_pct"],
                "learning_detection_rate_pct": learned["detection_rate_pct"],
                "detection_delta_pct": learned["detection_rate_pct"] - base["detection_rate_pct"],
                "base_bypass_rate_pct": base["bypass_rate_pct"],
                "learning_bypass_rate_pct": learned["bypass_rate_pct"],
                "bypass_delta_pct": learned["bypass_rate_pct"] - base["bypass_rate_pct"],
                "base_residual_degradation_kwh": base["mean_residual_degradation_kwh"],
                "learning_residual_degradation_kwh": learned["mean_residual_degradation_kwh"],
                "residual_delta_kwh": learned["mean_residual_degradation_kwh"]
                - base["mean_residual_degradation_kwh"],
                "base_recovery_pct": base["mitigation_recovery_pct"],
                "learning_recovery_pct": learned["mitigation_recovery_pct"],
                "recovery_delta_pct": learned["mitigation_recovery_pct"]
                - base["mitigation_recovery_pct"],
            }
        )
    return sort_rows(out, "detection_delta_pct")


def normalize_model_summary(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        out.append(
            {
                "task": row.get("task", ""),
                "model": row.get("model", ""),
                "accuracy_pct": pct(row.get("accuracy")),
                "macro_f1_pct": pct(row.get("macro_f1")),
                "weighted_f1_pct": pct(row.get("weighted_f1")),
            }
        )
    return sorted(out, key=lambda row: (row["task"], -row["macro_f1_pct"], row["model"]))


def import_matplotlib(manifest: dict):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        return plt
    except Exception as exc:  # pragma: no cover - environment dependent
        manifest.setdefault("figure_notes", []).append(
            "Matplotlib unavailable; figures were not generated: {}".format(exc)
        )
        return None


def short_label(text: str, width: int = 44) -> str:
    text = text.replace("_", " ")
    return textwrap.shorten(text, width=width, placeholder="...")


def plot_horizontal_bar(
    plt,
    rows: list[dict],
    label_field: str,
    value_field: str,
    path: Path,
    title: str,
    xlabel: str,
    limit: int = 12,
) -> None:
    selected = sort_rows(rows, value_field)[:limit]
    selected = list(reversed(selected))
    labels = [short_label(row.get(label_field, "")) for row in selected]
    values = [safe_float(row.get(value_field)) for row in selected]
    height = max(4.5, 0.42 * len(selected) + 1.6)
    fig, ax = plt.subplots(figsize=(9.0, height))
    ax.barh(labels, values, color="#2f6f8f")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.grid(axis="x", alpha=0.25)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def plot_grouped_degradation(
    plt, rows: list[dict], path: Path, title: str, limit: int = 10
) -> None:
    selected = sort_rows(rows, "mean_degradation_kwh")[:limit]
    labels = [short_label(row.get("attack_id", ""), 36) for row in selected]
    mean_values = [row["mean_degradation_kwh"] for row in selected]
    max_values = [row["max_degradation_kwh"] for row in selected]
    x_positions = list(range(len(selected)))
    fig, ax = plt.subplots(figsize=(10.5, 5.3))
    width = 0.38
    ax.bar([x - width / 2 for x in x_positions], mean_values, width, label="Mean", color="#2f6f8f")
    ax.bar([x + width / 2 for x in x_positions], max_values, width, label="Max", color="#c66b3d")
    ax.set_title(title)
    ax.set_ylabel("Physical degradation (kWh)")
    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def plot_advanced_residual(plt, rows: list[dict], path: Path) -> None:
    priority_attacks = {
        "stealth_load_s890_single_mask",
        "stealth_load_s890_branchflow_l8_small",
        "highimpact_dispatch_s890_voltage_816",
        "highimpact_dispatch_s890_line_l8_voltage_816",
    }
    selected = [
        row
        for row in rows
        if row["attack_id"] in priority_attacks
        and row["detector_profile"] in {"relaxed_status_tolerance", "current_residual"}
        and row["mitigation_mode"] in {"gated_candidate_screening", "always_reference_screening"}
    ]
    selected = sort_rows(selected, "mean_degradation_kwh")[:12]
    labels = [
        "{}\n{}\n{}".format(
            short_label(row["attack_id"], 28),
            short_label(row["detector_profile"], 24),
            short_label(row["mitigation_mode"], 26),
        )
        for row in selected
    ]
    x_positions = list(range(len(selected)))
    fig, ax = plt.subplots(figsize=(11.5, 6.0))
    width = 0.38
    ax.bar(
        [x - width / 2 for x in x_positions],
        [row["mean_degradation_kwh"] for row in selected],
        width,
        label="Attacked degradation",
        color="#2f6f8f",
    )
    ax.bar(
        [x + width / 2 for x in x_positions],
        [row["mean_residual_degradation_kwh"] for row in selected],
        width,
        label="Residual after mitigation",
        color="#c66b3d",
    )
    ax.set_title("Advanced Defense Residual Degradation")
    ax.set_ylabel("Mean physical degradation (kWh)")
    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def plot_detection_rates(plt, rows: list[dict], path: Path) -> None:
    selected = sort_rows(rows, "mean_degradation_kwh")[:12]
    labels = [
        "{}\n{}".format(short_label(row["attack_id"], 30), short_label(row["detector_profile"], 24))
        for row in selected
    ]
    x_positions = list(range(len(selected)))
    fig, ax = plt.subplots(figsize=(11.5, 5.6))
    width = 0.38
    ax.bar(
        [x - width / 2 for x in x_positions],
        [row["detection_rate_pct"] for row in selected],
        width,
        label="Detection",
        color="#2f6f8f",
    )
    ax.bar(
        [x + width / 2 for x in x_positions],
        [row["bypass_rate_pct"] for row in selected],
        width,
        label="High-impact bypass",
        color="#c66b3d",
    )
    ax.set_title("Detection and Bypass Rates")
    ax.set_ylabel("Rate (%)")
    ax.set_ylim(0, 105)
    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def plot_learning_ablation(plt, rows: list[dict], path: Path) -> None:
    selected = sorted(
        rows,
        key=lambda row: (
            row["attack_id"],
            row["detector_profile"],
            row["mitigation_mode"],
        ),
    )[:14]
    labels = [
        "{}\n{}\n{}".format(
            short_label(row["attack_id"], 24),
            short_label(row["detector_profile"], 20),
            short_label(row["mitigation_mode"], 22),
        )
        for row in selected
    ]
    x_positions = list(range(len(selected)))
    fig, ax = plt.subplots(figsize=(12.0, 5.8))
    width = 0.38
    ax.bar(
        [x - width / 2 for x in x_positions],
        [row["base_detection_rate_pct"] for row in selected],
        width,
        label="Residual detector only",
        color="#2f6f8f",
    )
    ax.bar(
        [x + width / 2 for x in x_positions],
        [row["learning_detection_rate_pct"] for row in selected],
        width,
        label="Residual plus learning",
        color="#5a8f4c",
    )
    ax.set_title("Learning Detector Ablation")
    ax.set_ylabel("Detection rate (%)")
    ax.set_ylim(0, 105)
    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def generate_figures(
    figure_dir: Path,
    manifest: dict,
    master_rows: list[dict],
    observation_rows: list[dict],
    coordinated_rows: list[dict],
    advanced_rows: list[dict],
    learning_ablation_rows: list[dict],
) -> list[str]:
    plt = import_matplotlib(manifest)
    if plt is None:
        return []
    figure_paths = {
        "top_master_degradation": figure_dir / "fig_01_top_master_degradation.png",
        "observation_criticality": figure_dir / "fig_02_observation_criticality.png",
        "coordinated_degradation": figure_dir / "fig_03_coordinated_attack_degradation.png",
        "advanced_residual": figure_dir / "fig_04_advanced_defense_residual.png",
        "detection_bypass": figure_dir / "fig_05_detection_bypass_rates.png",
    }
    plot_horizontal_bar(
        plt,
        master_rows,
        "attack_or_corruption",
        "mean_degradation_kwh",
        figure_paths["top_master_degradation"],
        "Top IEEE 34 Vulnerability Evidence",
        "Mean physical degradation (kWh)",
        limit=12,
    )
    plot_horizontal_bar(
        plt,
        observation_rows,
        "target_observation_id",
        "mean_degradation_kwh",
        figure_paths["observation_criticality"],
        "Critical IEEE 34 Observations",
        "Mean physical degradation (kWh)",
        limit=12,
    )
    plot_grouped_degradation(
        plt,
        coordinated_rows,
        figure_paths["coordinated_degradation"],
        "Coordinated Attack Degradation",
        limit=10,
    )
    plot_advanced_residual(plt, advanced_rows, figure_paths["advanced_residual"])
    plot_detection_rates(plt, advanced_rows, figure_paths["detection_bypass"])
    created = [relative(path) for path in figure_paths.values() if path.exists()]
    if learning_ablation_rows:
        learning_path = figure_dir / "fig_06_learning_detector_ablation.png"
        plot_learning_ablation(plt, learning_ablation_rows, learning_path)
        created.append(relative(learning_path))
    return created


def best_row(rows: list[dict], field: str = "mean_degradation_kwh") -> dict:
    if not rows:
        return {}
    return sort_rows(rows, field)[0]


def build_narrative(
    master_rows: list[dict],
    attack_rows: list[dict],
    observation_rows: list[dict],
    coordinated_rows: list[dict],
    advanced_rows: list[dict],
    learning_rows: list[dict],
    learning_ablation_rows: list[dict],
    model_rows: list[dict],
    missing_inputs: list[str],
) -> str:
    top_master = best_row(master_rows)
    top_attack = best_row(attack_rows)
    top_observation = best_row(observation_rows)
    top_coordinated = best_row(coordinated_rows)
    top_advanced = best_row(advanced_rows)
    relaxed_rows = [
        row
        for row in advanced_rows
        if row["detector_profile"] == "relaxed_status_tolerance"
        and row["mitigation_mode"] == "gated_candidate_screening"
    ]
    relaxed_top = best_row(relaxed_rows)
    reference_rows = [
        row for row in advanced_rows if row["mitigation_mode"] == "always_reference_screening"
    ]
    reference_top = best_row(reference_rows, "mitigation_recovery_pct")
    lines = [
        "# IEEE 34 TSG Vulnerability Assessment Results Narrative",
        "",
        "Generated: {}".format(datetime.now().isoformat(timespec="seconds")),
        "",
        "## Evidence Boundary",
        "",
        "The IEEE 34 evidence base is now organized around direct observations available to the current GRL restoration controller: action-mask/status inputs, topology adjacency/status, bus-voltage measurements, branch-flow measurements, and global restoration scalars. Load-demand, DER-availability, and explicit fault-status FDIA should not be claimed as direct current-controller observation attacks unless the controller observation model is extended.",
        "",
        "All reported degradation is physical restored-energy degradation, computed as positive loss relative to the clean baseline. Accidental improvements are kept separate so the paper does not overstate attack damage.",
        "",
        "## Which Attacks Are Most Damaging?",
        "",
    ]
    if top_attack:
        lines.append(
            "At the attack-family level, the strongest direct family is `{}` with mean degradation {:.3f} kWh, maximum degradation {:.3f} kWh, and {} damaging cases out of {}.".format(
                top_attack["attack"],
                top_attack["mean_degradation_kwh"],
                top_attack["max_degradation_kwh"],
                top_attack["damaging_cases"],
                top_attack["case_count"],
            )
        )
    if top_coordinated:
        lines.append(
            "The strongest coordinated IEEE 34 attack is `{}` with mean degradation {:.3f} kWh and maximum degradation {:.3f} kWh. This result is dominated by the dispatch-load status/control observation `Load_s890`; branchflow and voltage components should be interpreted as coordinated context unless they are shown damaging as standalone attacks.".format(
                top_coordinated["attack_id"],
                top_coordinated["mean_degradation_kwh"],
                top_coordinated["max_degradation_kwh"],
            )
        )
    if top_master:
        lines.append(
            "Across the master evidence table, the top ranked row is `{}` from `{}` with mean degradation {:.3f} kWh.".format(
                top_master["attack_or_corruption"],
                top_master["study_id"],
                top_master["mean_degradation_kwh"],
            )
        )
    lines.extend(
        [
            "",
            "## Which Observations Are Most Critical?",
            "",
        ]
    )
    if top_observation:
        lines.append(
            "The most critical individual observation is `{}` under `{}` with mean degradation {:.3f} kWh and maximum degradation {:.3f} kWh. This is a direct current-controller observation and is therefore suitable for the IEEE 34 paper claim.".format(
                top_observation["target_observation_id"],
                top_observation["attack_definition"],
                top_observation["mean_degradation_kwh"],
                top_observation["max_degradation_kwh"],
            )
        )
    lines.append(
        "The ranked criticality table separates dispatch-load action-mask observations, switch action-mask observations, line-status/topology observations, voltage measurements, and branchflow measurements. Standalone branchflow hiding is retained in the table even when it produces zero positive restored-energy degradation, because that negative result is scientifically useful."
    )
    lines.extend(
        [
            "",
            "## How Much Restored Energy Is Lost?",
            "",
            "Use the manuscript tables to report both mean and maximum physical degradation. The main restored-energy-loss claim for IEEE 34 should emphasize `mean_physical_degradation_kwh`, `max_physical_degradation_kwh`, and `damaging_case_count`; `mean_restored_energy_loss_kwh` can be negative when some attack realizations accidentally improve restoration, so it is not the cleanest damage metric by itself.",
            "",
            "## Detection and Mitigation",
            "",
        ]
    )
    if relaxed_top:
        lines.append(
            "The relaxed status-tolerance detector exposes the clearest bypass story: `{}` with gated candidate screening has mean degradation {:.3f} kWh, detection rate {:.1f}%, bypass rate {:.1f}%, and residual degradation after mitigation {:.3f} kWh.".format(
                relaxed_top["attack_id"],
                relaxed_top["mean_degradation_kwh"],
                relaxed_top["detection_rate_pct"],
                relaxed_top["bypass_rate_pct"],
                relaxed_top["mean_residual_degradation_kwh"],
            )
        )
    if reference_top:
        lines.append(
            "Always-reference screening is the strongest robust-mitigation benchmark in the current IEEE 34 evidence, reaching up to {:.1f}% mean degradation recovery in the selected stress rows. This should be described as a stronger trusted-reference screening mode, not as a free detector replacement.".format(
                reference_top["mitigation_recovery_pct"]
            )
        )
    lines.extend(
        [
            "Strict status-integrity checks remain central for high-impact action-mask/status attacks. Relaxing binary status assumptions can let damaging Load_s890-centered attacks pass the gate, while robust candidate screening can recover much of the lost performance when a trusted/reference candidate is considered.",
            "",
            "## Learning Detector Ablation",
            "",
        ]
    )
    if learning_rows and learning_ablation_rows:
        best_delta = best_row(learning_ablation_rows, "detection_delta_pct")
        lines.append(
            "A learning-detector ablation has been generated using the existing IEEE 34 trained detector artifacts. The largest detection-rate increase in the ablation table is for `{}` / `{}` / `{}`, with a detection change of {:.1f} percentage points.".format(
                best_delta["attack_id"],
                best_delta["detector_profile"],
                best_delta["mitigation_mode"],
                best_delta["detection_delta_pct"],
            )
        )
        lines.append(
            "The learning-model summary table should be used carefully: it reports held-out model metrics, while the ablation table reports downstream restoration-defense behavior."
        )
    elif model_rows:
        lines.append(
            "Trained IEEE 34 learning-detector model artifacts are present and summarized, but the restoration-defense ablation output was not found yet. Treat the model summary as detector-readiness evidence, not downstream mitigation evidence."
        )
    else:
        lines.append(
            "No IEEE 34 learning-detector model summary was available in the expected path, so the paper artifacts do not claim a learning-detector ablation."
        )
    lines.extend(
        [
            "",
            "## Recommended Manuscript Use",
            "",
            "Use Table 1 for the global damage ranking, Table 2 for attack-family comparisons, Table 3 for critical observations, Table 4 for coordinated attacks, Table 5 for advanced detection/mitigation stress testing, and the learning-ablation/model-summary tables only if their generated outputs are included in the final evidence package.",
            "",
            "For figures, use the top-master-degradation and observation-criticality plots in the vulnerability section, the coordinated-degradation plot in the attack-scenario section, and the advanced-residual plus detection-bypass plots in the defense section.",
        ]
    )
    if missing_inputs:
        lines.extend(
            [
                "",
                "## Missing Inputs",
                "",
            ]
        )
        lines.extend(["- {}".format(item) for item in missing_inputs])
    return "\n".join(lines) + "\n"


def build_readme(created_tables: list[str], created_figures: list[str], narrative_path: Path) -> str:
    return "\n".join(
        [
            "# IEEE 34 Paper Artifacts",
            "",
            "This folder contains paper-facing outputs generated from the completed IEEE 34 vulnerability simulations. The source simulations are not rerun by this artifact builder.",
            "",
            "## Key Files",
            "",
            "- Narrative: `{}`".format(relative(narrative_path)),
            "- Manifest: `{}`".format(
                relative(narrative_path.parent / "ieee34_paper_artifacts_manifest.json")
            ),
            "",
            "## Tables",
            "",
            *["- `{}`".format(path) for path in created_tables],
            "",
            "## Figures",
            "",
            *["- `{}`".format(path) for path in created_figures],
            "",
            "## Claim Boundary",
            "",
            "Only direct current-GRL observations are included as current IEEE 34 FDIA claims. Load-demand, DER-availability, and explicit fault-status FDIA require a controller-observation extension before they should be claimed as direct attacks.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate IEEE 34 TSG paper tables, figures, narrative, and manifest."
    )
    parser.add_argument(
        "--results-dir",
        default="paper_results/tsg_ieee34",
        help="Completed IEEE 34 result tree to package, relative to RL_Testing unless absolute.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory relative to RL_Testing unless absolute.",
    )
    args = parser.parse_args()

    results_dir = resolve_path(args.results_dir, DEFAULT_RESULTS_DIR)
    inputs = inputs_for_results_dir(results_dir)
    output_dir = resolve_path(args.output_dir, results_dir / "paper_artifacts")
    table_dir = output_dir / "tables"
    figure_dir = output_dir / "figures"
    missing_inputs: list[str] = []
    raw_inputs = {name: read_csv(path, missing_inputs) for name, path in inputs.items()}

    master_rows = normalize_master(raw_inputs["master_evidence"])
    attack_rows = normalize_attack_family(raw_inputs["baseline_attack"])
    observation_rows = build_observation_criticality(raw_inputs)
    coordinated_rows = normalize_coordinated(raw_inputs["coordinated_attack"])
    advanced_rows = normalize_advanced(raw_inputs["advanced_defense"], "residual_only")
    learning_rows = normalize_advanced(raw_inputs["advanced_defense_learning"], "residual_plus_learning")
    advanced_combined_rows = sort_rows(advanced_rows + learning_rows, "mean_degradation_kwh")
    learning_ablation_rows = build_learning_ablation(advanced_rows, learning_rows)
    model_rows = normalize_model_summary(raw_inputs["learning_model_summary"])
    study_rows = raw_inputs["study_summary"]
    attack_surface_rows = raw_inputs["attack_surface_audit"]

    created_tables: list[str] = []
    created_tables.extend(
        write_table_bundle(
            table_dir,
            "table_01_master_top_evidence",
            master_rows[:30],
            [
                "rank",
                "study_id",
                "attack_or_corruption",
                "target_observation_id",
                "case_count",
                "mean_degradation_kwh",
                "max_degradation_kwh",
                "damaging_cases",
                "detection_rate_pct",
                "bypass_rate_pct",
                "mitigation_recovery_pct",
            ],
            "Table 1. IEEE 34 Master Evidence Ranking",
        )
    )
    created_tables.extend(
        write_table_bundle(
            table_dir,
            "table_02_attack_family_ranking",
            attack_rows,
            [
                "damage_rank",
                "attack",
                "case_count",
                "mean_degradation_kwh",
                "max_degradation_kwh",
                "damaging_cases",
                "damaging_case_rate_pct",
                "mean_accidental_improvement_kwh",
                "detection_rate_pct",
                "mitigation_recovery_pct",
            ],
            "Table 2. IEEE 34 Attack-Family Ranking",
        )
    )
    created_tables.extend(
        write_table_bundle(
            table_dir,
            "table_03_observation_criticality",
            observation_rows,
            [
                "evidence_family",
                "attack_definition",
                "target_observation_id",
                "target_component_name",
                "case_count",
                "attack_applied_count",
                "mean_degradation_kwh",
                "max_degradation_kwh",
                "damaging_cases",
                "detection_rate_pct",
                "action_changed_rate_pct",
                "mitigation_recovery_pct",
                "paper_note",
            ],
            "Table 3. IEEE 34 Critical Observations",
            md_limit=30,
        )
    )
    created_tables.extend(
        write_table_bundle(
            table_dir,
            "table_04_coordinated_attack_ranking",
            coordinated_rows,
            [
                "damage_rank",
                "attack_id",
                "target_observation_id",
                "case_count",
                "mean_degradation_kwh",
                "max_degradation_kwh",
                "damaging_cases",
                "detection_rate_pct",
                "bypass_rate_pct",
                "mitigation_recovery_pct",
                "mean_load_changes",
                "mean_switch_changes",
            ],
            "Table 4. IEEE 34 Coordinated Attack Ranking",
        )
    )
    created_tables.extend(
        write_table_bundle(
            table_dir,
            "table_05_advanced_defense_stealth",
            advanced_combined_rows,
            [
                "source",
                "defense_rank",
                "attack_id",
                "attack_class",
                "detector_profile",
                "mitigation_mode",
                "case_count",
                "mean_degradation_kwh",
                "mean_residual_degradation_kwh",
                "mitigation_recovery_pct",
                "detection_rate_pct",
                "bypass_rate_pct",
                "stealth_success_rate_pct",
            ],
            "Table 5. IEEE 34 Advanced Defense and Stealth Stress Results",
            md_limit=30,
        )
    )
    created_tables.extend(
        write_table_bundle(
            table_dir,
            "table_06_learning_detector_ablation",
            learning_ablation_rows,
            [
                "attack_id",
                "detector_profile",
                "mitigation_mode",
                "base_detection_rate_pct",
                "learning_detection_rate_pct",
                "detection_delta_pct",
                "base_bypass_rate_pct",
                "learning_bypass_rate_pct",
                "bypass_delta_pct",
                "base_residual_degradation_kwh",
                "learning_residual_degradation_kwh",
                "residual_delta_kwh",
                "base_recovery_pct",
                "learning_recovery_pct",
                "recovery_delta_pct",
            ],
            "Table 6. IEEE 34 Learning Detector Ablation",
            md_limit=30,
        )
    )
    created_tables.extend(
        write_table_bundle(
            table_dir,
            "table_07_learning_detector_model_summary",
            model_rows,
            ["task", "model", "accuracy_pct", "macro_f1_pct", "weighted_f1_pct"],
            "Table 7. IEEE 34 Learning Detector Model Summary",
        )
    )
    created_tables.extend(
        write_table_bundle(
            table_dir,
            "table_08_attack_surface_audit",
            attack_surface_rows,
            list(attack_surface_rows[0].keys()) if attack_surface_rows else [],
            "Table 8. IEEE 34 Attack Surface Audit",
            md_limit=20,
        )
    )
    created_tables.extend(
        write_table_bundle(
            table_dir,
            "table_09_study_summary",
            study_rows,
            list(study_rows[0].keys()) if study_rows else [],
            "Table 9. IEEE 34 Study Summary",
            md_limit=20,
        )
    )

    manifest = {
        "experiment": "IEEE 34 TSG paper artifact generation",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "results_dir": relative(results_dir),
        "output_dir": relative(output_dir),
        "missing_inputs": sorted(set(missing_inputs)),
        "source_inputs": {name: relative(path) for name, path in inputs.items()},
        "row_counts": {
            "master_evidence": len(master_rows),
            "attack_family": len(attack_rows),
            "observation_criticality": len(observation_rows),
            "coordinated_attack": len(coordinated_rows),
            "advanced_defense": len(advanced_rows),
            "advanced_defense_learning": len(learning_rows),
            "learning_ablation": len(learning_ablation_rows),
            "learning_model_summary": len(model_rows),
        },
    }
    created_figures = generate_figures(
        figure_dir,
        manifest,
        master_rows,
        observation_rows,
        coordinated_rows,
        advanced_rows,
        learning_ablation_rows,
    )

    narrative_path = output_dir / "IEEE34_TSG_Paper_Results_Narrative.md"
    write_text(
        narrative_path,
        build_narrative(
            master_rows,
            attack_rows,
            observation_rows,
            coordinated_rows,
            advanced_rows,
            learning_rows,
            learning_ablation_rows,
            model_rows,
            manifest["missing_inputs"],
        ),
    )
    readme_path = output_dir / "README_IEEE34_PaperArtifacts.md"
    write_text(readme_path, build_readme(created_tables, created_figures, narrative_path))

    manifest["tables"] = created_tables
    manifest["figures"] = created_figures
    manifest["narrative"] = relative(narrative_path)
    manifest["readme"] = relative(readme_path)
    manifest_path = output_dir / "ieee34_paper_artifacts_manifest.json"
    write_text(manifest_path, json.dumps(manifest, indent=2, sort_keys=True))

    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
