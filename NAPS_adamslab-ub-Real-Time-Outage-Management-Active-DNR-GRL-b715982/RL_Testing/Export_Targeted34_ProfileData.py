"""Export voltage-profile and energy-served data for targeted 34-bus FDIA cases.

The targeted dynamic experiment stores compact impact/detection summaries. This
script replays the selected cases and exports the profile-level data needed for
original-paper-style plots:

* per-bus, per-phase voltage at every time step
* hourly energy served in kWh for GCAPS/MLP/BPSO
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

import numpy as np

from FDIA_ExperimentCore import physical_impact, resolve_path, safe_json, write_csv
from Run_FDIA_TargetedDynamicImpact34_NoMitigation import (
    build_policy_observation,
    case_from_search_row,
    decide,
    make_controller,
)


METHOD_LABELS = {"GRL": "GCAPS", "MLP": "MLP", "BPSO": "BPSO"}
PHASE_LABELS = {1: "A", 2: "B", 3: "C"}
MAX_PLOT_VOLTAGE_PU = 2.0
MAX_ENERGY_FACTOR = 1.50


def parse_args():
    parser = argparse.ArgumentParser(
        description="Export per-bus voltages and energy-served profiles for targeted 34-bus FDIA cases."
    )
    parser.add_argument(
        "--result-dir",
        default="paper_results/naps_34bus/targeted_dynamic_no_mitigation",
        help="Directory containing targeted_selected_cases_34bus.csv and manifest.",
    )
    parser.add_argument("--selected-file", default="targeted_selected_cases_34bus.csv")
    parser.add_argument("--horizon", type=int, default=0, help="Override manifest horizon; 0 uses manifest.")
    parser.add_argument("--step-hours", type=int, default=0, help="Override manifest step size; 0 uses manifest.")
    parser.add_argument("--start-hour", type=int, default=-1, help="Override manifest start hour; -1 uses manifest.")
    parser.add_argument("--methods", nargs="+", default=None, choices=["GRL", "MLP", "BPSO"])
    parser.add_argument("--bpso-particles", type=int, default=0)
    parser.add_argument("--bpso-iterations", type=int, default=0)
    parser.add_argument("--bpso-seed", type=int, default=5157)
    parser.add_argument("--bpso-load-weight-gain", type=float, default=0.20)
    parser.add_argument("--decision-mask-scope", default="switch_and_load")
    parser.add_argument("--decision-mask-min-fraction", type=float, default=0.20)
    parser.add_argument("--decision-mask-max-fraction", type=float, default=0.70)
    parser.add_argument("--no-decision-channel-projection", action="store_true")
    parser.add_argument("--no-figures", action="store_true")
    return parser.parse_args()


def load_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def read_csv_rows(path):
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def parse_json_field(value, default):
    if value is None or value == "":
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def set_scenario_seed(seed):
    random.seed(int(seed))
    np.random.seed(int(seed) % (2**32 - 1))


def apply_manifest_defaults(args, manifest):
    if args.horizon <= 0:
        args.horizon = int(manifest.get("horizon", 24))
    if args.step_hours <= 0:
        args.step_hours = int(manifest.get("step_hours", 1))
    if args.start_hour < 0:
        args.start_hour = int(manifest.get("start_hour", 0))
    if args.bpso_particles <= 0:
        args.bpso_particles = int(manifest.get("bpso_particles", 8))
    if args.bpso_iterations <= 0:
        args.bpso_iterations = int(manifest.get("bpso_iterations", 8))
    return args


def profile_after_action(experiment, scenario_seed, action, args):
    action = np.asarray(action, dtype=int)
    set_scenario_seed(scenario_seed)
    first_metrics, first_obs = experiment.evaluate_action("random", action)
    try:
        experiment._configure_daily_mode(args.step_hours)
    except Exception as exc:
        first_metrics["time_command_warning"] = str(exc)

    trajectory = []
    observations = []
    for step in range(int(args.horizon)):
        hour = int(args.start_hour + step * args.step_hours)
        solve_warning = ""
        try:
            experiment._advance_time(hour)
        except Exception as exc:
            solve_warning = str(exc)
        obs = experiment.current_observation()
        metrics = experiment.metrics_from_observation(obs, action=action)
        if step == 0:
            metrics.update(
                {
                    "initial_reward": first_metrics["reward"],
                    "initial_energy_ratio": first_metrics["energy_ratio"],
                    "initial_voltage_violation": first_metrics["voltage_violation"],
                }
            )
        metrics.update({"time_step": step, "hour": hour, "solve_warning": solve_warning})
        trajectory.append(metrics)
        observations.append(obs)

    if not trajectory:
        first_metrics.update({"time_step": 0, "hour": args.start_hour, "solve_warning": ""})
        trajectory.append(first_metrics)
        observations.append(first_obs)
    return trajectory, observations


def run_profile_case(controller, case, args):
    set_scenario_seed(case.scenario_seed)
    true_obs = controller.experiment.get_observation("random")
    clean_action, clean_policy_ms, clean_controller_metadata = decide(controller, true_obs, case, "clean")
    policy_obs, attack_metadata = build_policy_observation(true_obs, clean_action, case, controller, args)
    attacked_action, attacked_policy_ms, attacked_controller_metadata = decide(
        controller,
        policy_obs,
        case,
        "attacked_dynamic",
    )
    clean_trajectory, clean_observations = profile_after_action(
        controller.experiment,
        case.scenario_seed,
        clean_action,
        args,
    )
    attacked_trajectory, attacked_observations = profile_after_action(
        controller.experiment,
        case.scenario_seed,
        attacked_action,
        args,
    )
    return {
        "clean_action": clean_action,
        "attacked_action": attacked_action,
        "clean_policy_ms": clean_policy_ms,
        "attacked_policy_ms": attacked_policy_ms,
        "clean_controller_metadata": clean_controller_metadata,
        "attacked_controller_metadata": attacked_controller_metadata,
        "attack_metadata": attack_metadata,
        "clean_trajectory": clean_trajectory,
        "attacked_trajectory": attacked_trajectory,
        "clean_observations": clean_observations,
        "attacked_observations": attacked_observations,
    }


def run_profile_case_from_actions(controller, case, clean_action, attacked_action, args):
    clean_action = np.asarray(clean_action, dtype=int)
    attacked_action = np.asarray(attacked_action, dtype=int)
    clean_trajectory, clean_observations = profile_after_action(
        controller.experiment,
        case.scenario_seed,
        clean_action,
        args,
    )
    attacked_trajectory, attacked_observations = profile_after_action(
        controller.experiment,
        case.scenario_seed,
        attacked_action,
        args,
    )
    return {
        "clean_action": clean_action,
        "attacked_action": attacked_action,
        "clean_policy_ms": 0.0,
        "attacked_policy_ms": 0.0,
        "clean_controller_metadata": {},
        "attacked_controller_metadata": {},
        "attack_metadata": {"source": "targeted_method_comparison_34bus.csv"},
        "clean_trajectory": clean_trajectory,
        "attacked_trajectory": attacked_trajectory,
        "clean_observations": clean_observations,
        "attacked_observations": attacked_observations,
    }


def comparison_actions(comparison_rows):
    actions = {}
    for row in comparison_rows:
        if row.get("time_step") != "0":
            continue
        key = (row.get("case_id"), row.get("mode"))
        actions[key] = parse_json_field(row.get("action"), [])
    return actions


def bus_phase_rows(case, controller, result):
    node_list = list(getattr(controller.experiment.state_module, "node_list", []))
    nodes_conn = list(getattr(controller.experiment.state_module, "nodes_conn", []))
    rows = []
    for mode, observations in [
        ("clean_dynamic", result["clean_observations"]),
        ("attacked_dynamic", result["attacked_observations"]),
    ]:
        other_observations = result["clean_observations"]
        for step, obs in enumerate(observations):
            voltages = np.asarray(obs["NodeFeat(BusVoltage)"], dtype=float)
            clean_voltages = np.asarray(other_observations[step]["NodeFeat(BusVoltage)"], dtype=float)
            hour = int(result["clean_trajectory"][step]["hour"])
            if mode == "attacked_dynamic":
                hour = int(result["attacked_trajectory"][step]["hour"])
            for bus_index, bus in enumerate(node_list):
                present_phases = set()
                if bus_index < len(nodes_conn):
                    present_phases = {int(value) for value in np.asarray(nodes_conn[bus_index]).reshape(-1)}
                for phase_index in (1, 2, 3):
                    array_phase = phase_index - 1
                    voltage = float(voltages[bus_index, array_phase])
                    clean_voltage = float(clean_voltages[bus_index, array_phase])
                    voltage_valid = int(np.isfinite(voltage) and 0.0 <= voltage <= MAX_PLOT_VOLTAGE_PU)
                    clean_voltage_valid = int(
                        np.isfinite(clean_voltage) and 0.0 <= clean_voltage <= MAX_PLOT_VOLTAGE_PU
                    )
                    voltage_for_plot = voltage if voltage_valid else ""
                    clean_voltage_for_plot = clean_voltage if clean_voltage_valid else ""
                    voltage_delta = (
                        voltage - clean_voltage
                        if voltage_valid and clean_voltage_valid
                        else ""
                    )
                    rows.append(
                        {
                            "case_id": case.case_id,
                            "target_method": case.target_method,
                            "method": case.target_method,
                            "paper_method_label": METHOD_LABELS.get(case.target_method, case.target_method),
                            "scenario_seed": case.scenario_seed,
                            "attack": case.attack,
                            "mode": mode,
                            "time_step": step,
                            "hour": hour,
                            "bus_index": bus_index,
                            "bus": bus,
                            "phase": PHASE_LABELS[phase_index],
                            "phase_index": phase_index,
                            "phase_present_base": int(phase_index in present_phases),
                            "phase_active": int(voltage_valid and voltage > 0.01),
                            "voltage_valid": voltage_valid,
                            "clean_voltage_valid": clean_voltage_valid,
                            "voltage_pu": voltage_for_plot,
                            "clean_voltage_pu": clean_voltage_for_plot,
                            "voltage_delta_vs_clean": voltage_delta,
                        }
                    )
    return rows


def parse_float(value, default=0.0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if np.isfinite(number) else default


def parse_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def energy_valid(energy_kw, total_demand_kw):
    if not np.isfinite(energy_kw):
        return False
    if total_demand_kw <= 0:
        return 0.0 <= energy_kw <= 1.0e6
    return 0.0 <= energy_kw <= MAX_ENERGY_FACTOR * total_demand_kw


def energy_rows_from_comparison(comparison_rows, selected_cases, args):
    selected = {case.case_id for case in selected_cases}
    rows = []
    for source in comparison_rows:
        if source.get("case_id") not in selected:
            continue
        if source.get("mode") not in ("clean_dynamic", "attacked_dynamic"):
            continue
        energy_kw = parse_float(source.get("energy_kw"), default=float("nan"))
        total_demand_kw = parse_float(source.get("total_demand_kw"), default=0.0)
        valid = energy_valid(energy_kw, total_demand_kw)
        energy_kwh = energy_kw * float(args.step_hours) if valid else ""
        rows.append(
            {
                "case_id": source.get("case_id"),
                "target_method": source.get("target_method", source.get("method")),
                "method": source.get("method"),
                "paper_method_label": METHOD_LABELS.get(source.get("method"), source.get("method")),
                "scenario_seed": parse_int(source.get("scenario_seed")),
                "attack": source.get("attack"),
                "mode": source.get("mode"),
                "time_step": parse_int(source.get("time_step")),
                "hour": parse_int(source.get("hour")),
                "step_hours": int(args.step_hours),
                "energy_valid": int(valid),
                "energy_kw": energy_kw if valid else "",
                "energy_served_kwh": energy_kwh,
                "total_demand_kw": total_demand_kw,
                "energy_ratio": parse_float(source.get("energy_ratio")),
                "voltage_violation": parse_float(source.get("voltage_violation")),
                "convergence_violation": parse_float(source.get("convergence_violation")),
                "reward": parse_float(source.get("reward")),
                "loads_served": parse_int(source.get("loads_served")),
                "loads_shed": parse_int(source.get("loads_shed")),
                "energy_ratio_delta_vs_clean": parse_float(source.get("energy_ratio_delta_vs_clean")),
                "energy_kw_delta_vs_clean": parse_float(source.get("energy_kw_delta_vs_clean")),
                "voltage_violation_delta_vs_clean": parse_float(source.get("voltage_violation_delta_vs_clean")),
                "reward_delta_vs_clean": parse_float(source.get("reward_delta_vs_clean")),
                "convergence_delta_vs_clean": parse_float(source.get("convergence_delta_vs_clean")),
                "loads_served_delta_vs_clean": parse_int(source.get("loads_served_delta_vs_clean")),
                "physical_impact_score": parse_float(source.get("physical_impact_score")),
                "source": "targeted_method_comparison_34bus.csv",
            }
        )
    return rows


def energy_rows(case, result, args):
    rows = []
    clean = result["clean_trajectory"]
    attacked = result["attacked_trajectory"]
    impact_by_step = [physical_impact(c, a) for c, a in zip(clean, attacked)]
    for mode, trajectory in [("clean_dynamic", clean), ("attacked_dynamic", attacked)]:
        for step, metrics in enumerate(trajectory):
            impact = (
                {
                    "energy_ratio_delta_vs_clean": 0.0,
                    "energy_kw_delta_vs_clean": 0.0,
                    "voltage_violation_delta_vs_clean": 0.0,
                    "reward_delta_vs_clean": 0.0,
                    "convergence_delta_vs_clean": 0.0,
                    "loads_served_delta_vs_clean": 0,
                    "physical_impact_score": 0.0,
                }
                if mode == "clean_dynamic"
                else impact_by_step[step]
            )
            energy_kw = float(metrics.get("energy_kw", 0.0))
            rows.append(
                {
                    "case_id": case.case_id,
                    "target_method": case.target_method,
                    "method": case.target_method,
                    "paper_method_label": METHOD_LABELS.get(case.target_method, case.target_method),
                    "scenario_seed": case.scenario_seed,
                    "attack": case.attack,
                    "mode": mode,
                    "time_step": int(metrics["time_step"]),
                    "hour": int(metrics["hour"]),
                    "step_hours": int(args.step_hours),
                    "energy_kw": energy_kw,
                    "energy_served_kwh": energy_kw * float(args.step_hours),
                    "total_demand_kw": float(metrics.get("total_demand_kw", 0.0)),
                    "energy_ratio": float(metrics.get("energy_ratio", 0.0)),
                    "voltage_violation": float(metrics.get("voltage_violation", 0.0)),
                    "convergence_violation": float(metrics.get("convergence_violation", 0.0)),
                    "reward": float(metrics.get("reward", 0.0)),
                    "loads_served": int(metrics.get("loads_served", 0)),
                    "loads_shed": int(metrics.get("loads_shed", 0)),
                    **impact,
                }
            )
    return rows


def finite_float(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def mean(values):
    numbers = [finite_float(value) for value in values]
    numbers = [value for value in numbers if value is not None]
    return float(np.mean(numbers)) if numbers else 0.0


def min_value(values):
    numbers = [finite_float(value) for value in values]
    numbers = [value for value in numbers if value is not None]
    return float(np.min(numbers)) if numbers else 0.0


def max_value(values):
    numbers = [finite_float(value) for value in values]
    numbers = [value for value in numbers if value is not None]
    return float(np.max(numbers)) if numbers else 0.0


def summarize_energy(rows):
    groups = {}
    for row in rows:
        key = (row["target_method"], row["paper_method_label"], row["mode"], row["time_step"], row["hour"])
        groups.setdefault(key, []).append(row)
    summary = []
    for (method, label, mode, time_step, hour), items in sorted(groups.items()):
        summary.append(
            {
                "target_method": method,
                "paper_method_label": label,
                "mode": mode,
                "time_step": time_step,
                "hour": hour,
                "case_count": len({item["case_id"] for item in items}),
                "valid_energy_case_count": int(
                    sum(1 for item in items if str(item.get("energy_valid", "1")) == "1")
                ),
                "mean_energy_served_kwh": mean(
                    item["energy_served_kwh"] for item in items if str(item.get("energy_valid", "1")) == "1"
                ),
                "min_energy_served_kwh": min_value(
                    item["energy_served_kwh"] for item in items if str(item.get("energy_valid", "1")) == "1"
                ),
                "max_energy_served_kwh": max_value(
                    item["energy_served_kwh"] for item in items if str(item.get("energy_valid", "1")) == "1"
                ),
                "mean_energy_kw": mean(
                    item["energy_kw"] for item in items if str(item.get("energy_valid", "1")) == "1"
                ),
                "mean_energy_ratio": mean(item["energy_ratio"] for item in items),
                "mean_voltage_violation": mean(item["voltage_violation"] for item in items),
                "mean_physical_impact_score": mean(item["physical_impact_score"] for item in items),
            }
        )
    return summary


def summarize_voltages(rows):
    groups = {}
    for row in rows:
        key = (
            row["target_method"],
            row["paper_method_label"],
            row["mode"],
            row["time_step"],
            row["hour"],
            row["bus_index"],
            row["bus"],
            row["phase"],
            row["phase_index"],
        )
        groups.setdefault(key, []).append(row)
    summary = []
    for (method, label, mode, time_step, hour, bus_index, bus, phase, phase_index), items in sorted(groups.items()):
        summary.append(
            {
                "target_method": method,
                "paper_method_label": label,
                "mode": mode,
                "time_step": time_step,
                "hour": hour,
                "bus_index": bus_index,
                "bus": bus,
                "phase": phase,
                "phase_index": phase_index,
                "phase_present_base": max(int(item["phase_present_base"]) for item in items),
                "active_case_fraction": mean(item["phase_active"] for item in items),
                "valid_voltage_case_fraction": mean(item["voltage_valid"] for item in items),
                "mean_voltage_pu": mean(item["voltage_pu"] for item in items),
                "min_voltage_pu": min_value(item["voltage_pu"] for item in items),
                "max_voltage_pu": max_value(item["voltage_pu"] for item in items),
                "mean_voltage_delta_vs_clean": mean(item["voltage_delta_vs_clean"] for item in items),
            }
        )
    return summary


def write_energy_figure(summary_rows, output_path):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        return "matplotlib unavailable: {}".format(exc)

    attacked = [row for row in summary_rows if row["mode"] == "attacked_dynamic"]
    methods = ["GCAPS", "MLP", "BPSO"]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    colors = {"GCAPS": "#2f6f8f", "MLP": "#b85750", "BPSO": "#6f8f3f"}
    for label in methods:
        items = [row for row in attacked if row["paper_method_label"] == label]
        items.sort(key=lambda row: int(row["hour"]))
        if not items:
            continue
        ax.plot(
            [int(row["hour"]) for row in items],
            [float(row["mean_energy_served_kwh"]) for row in items],
            marker="o",
            linewidth=1.8,
            markersize=3.2,
            color=colors.get(label),
            label=label,
        )
    ax.set_xlabel("Hour")
    ax.set_ylabel("Mean Energy Served (kWh)")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return str(output_path)


def write_manifest(output_dir, args, selected_cases, voltage_rows, energy_rows_written, figure_note):
    manifest = {
        "experiment": "IEEE 34-bus targeted FDIA profile export",
        "source_selected_file": str(resolve_path(args.result_dir) / args.selected_file),
        "selected_cases": len(selected_cases),
        "horizon": args.horizon,
        "step_hours": args.step_hours,
        "start_hour": args.start_hour,
        "voltage_rows": len(voltage_rows),
        "energy_rows": len(energy_rows_written),
        "voltage_csv": "profile_voltage_bus_phase_34bus.csv",
        "energy_csv": "profile_energy_served_34bus.csv",
        "energy_summary_csv": "table_energy_served_by_method_34bus.csv",
        "voltage_summary_csv": "table_voltage_profile_summary_34bus.csv",
        "figure_output": figure_note,
        "note": (
            "Energy served in kWh is computed from the accepted targeted_method_comparison_34bus.csv "
            "values as OpenDSS supplied kW multiplied by the simulation step size in hours. "
            "Voltage rows include every bus and phases A/B/C; phase_present_base, phase_active, "
            "and voltage_valid identify absent, inactive, or numerically invalid replay points."
        ),
    }
    path = output_dir / "profile_export_manifest.json"
    path.write_text(safe_json(manifest) + "\n")
    return path


def main():
    args = parse_args()
    result_dir = resolve_path(args.result_dir)
    manifest = load_json(result_dir / "targeted_dynamic_no_mitigation_manifest.json")
    args = apply_manifest_defaults(args, manifest)
    selected_path = result_dir / args.selected_file
    comparison_path = result_dir / "targeted_method_comparison_34bus.csv"
    selected_rows = read_csv_rows(selected_path)
    comparison_rows = read_csv_rows(comparison_path)
    accepted_actions = comparison_actions(comparison_rows)
    if args.methods:
        selected_rows = [row for row in selected_rows if row["target_method"] in set(args.methods)]
    selected_cases = [case_from_search_row(row) for row in selected_rows]
    if not selected_cases:
        raise RuntimeError("No selected cases were found in {}".format(selected_path))

    controllers = {method: make_controller(method, args) for method in sorted({case.target_method for case in selected_cases})}
    voltage_rows = []
    served_rows = energy_rows_from_comparison(comparison_rows, selected_cases, args)
    for index, case in enumerate(selected_cases, start=1):
        print(
            "profile export {}/{} {} target={} attack={}".format(
                index,
                len(selected_cases),
                case.case_id,
                case.target_method,
                case.attack,
            ),
            flush=True,
        )
        clean_action = accepted_actions.get((case.case_id, "clean_dynamic"))
        attacked_action = accepted_actions.get((case.case_id, "attacked_dynamic"))
        if clean_action and attacked_action:
            result = run_profile_case_from_actions(
                controllers[case.target_method],
                case,
                clean_action,
                attacked_action,
                args,
            )
        else:
            result = run_profile_case(controllers[case.target_method], case, args)
        voltage_rows.extend(bus_phase_rows(case, controllers[case.target_method], result))

    energy_summary = summarize_energy(served_rows)
    voltage_summary = summarize_voltages(voltage_rows)

    voltage_path = result_dir / "profile_voltage_bus_phase_34bus.csv"
    energy_path = result_dir / "profile_energy_served_34bus.csv"
    energy_summary_path = result_dir / "table_energy_served_by_method_34bus.csv"
    voltage_summary_path = result_dir / "table_voltage_profile_summary_34bus.csv"
    write_csv(voltage_rows, voltage_path)
    write_csv(served_rows, energy_path)
    write_csv(energy_summary, energy_summary_path)
    write_csv(voltage_summary, voltage_summary_path)

    figure_note = "figures skipped"
    if not args.no_figures:
        figure_note = write_energy_figure(energy_summary, result_dir / "fig_energy_served_kwh_attacked_34bus.png")
    manifest_path = write_manifest(result_dir, args, selected_cases, voltage_rows, served_rows, figure_note)

    print("wrote {}".format(voltage_path), flush=True)
    print("wrote {}".format(energy_path), flush=True)
    print("wrote {}".format(energy_summary_path), flush=True)
    print("wrote {}".format(voltage_summary_path), flush=True)
    print("figure {}".format(figure_note), flush=True)
    print("wrote {}".format(manifest_path), flush=True)


if __name__ == "__main__":
    main()
