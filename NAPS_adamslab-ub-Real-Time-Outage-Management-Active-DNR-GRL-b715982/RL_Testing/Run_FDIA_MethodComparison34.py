"""Run 34-bus FDIA method comparison experiments.

This runner replays rows from the NAPS 34-bus FDIA attack-search CSV. Each
available method receives the same clean and attacked observations, selects an
action, and the selected action is evaluated on the true 34-bus OpenDSS
scenario.

MISOCP is recorded as unavailable unless a real 34-bus implementation exists.
The existing repository implementation targets IEEE 123-bus, so this script
does not copy or reinterpret it as a 34-bus baseline.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import numpy as np

from FDIA_Common import apply_attack, restoration_action_quality
from FDIA_ExperimentCore import (
    BASE_DIR,
    RestorationExperiment,
    action_delta,
    detector_observation_from_reports,
    physical_impact,
    resolve_path,
    safe_json,
    write_csv,
)


DEFAULT_CASES = "paper_results/naps_34bus/fdia_attack_search_34bus_all.csv"
DEFAULT_OUTPUT = "paper_results/naps_34bus/fdia_method_comparison_34bus.csv"
DEFAULT_ARTIFACT_DIR = "paper_results/naps_34bus/method_comparison_artifacts"
DEFAULT_METHODS = ("GRL", "MLP", "BPSO", "MISOCP")
MISOCP_34BUS_UNAVAILABLE_REASON = (
    "No 34-bus MISOCP solver is present in this repository. "
    "Conventional/MISOCP targets IEEE 123-bus and requires gurobipy/Gurobi."
)
SUMMARY_ABS_LIMITS = {
    "reward": 1.0e6,
    "energy_kw": 1.0e6,
    "energy_ratio": 10.0,
    "voltage_violation": 100.0,
    "convergence_violation": 100.0,
    "physical_impact_score": 100.0,
    "action_changed": 1.0,
    "policy_time_ms": 1.0e8,
}


@dataclass(frozen=True)
class AttackCase:
    source_index: int
    system: str
    scenario: str
    scenario_seed: int
    attack: str
    attack_kwargs: dict
    source_physical_impact_score: float


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compare real 34-bus restoration methods under FDIA attacks."
    )
    parser.add_argument("--cases", default=DEFAULT_CASES, help="Input attack-search CSV.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output comparison CSV.")
    parser.add_argument(
        "--artifact-dir",
        default=DEFAULT_ARTIFACT_DIR,
        help="Directory for method summary tables and figures.",
    )
    parser.add_argument(
        "--methods",
        nargs="+",
        default=list(DEFAULT_METHODS),
        choices=list(DEFAULT_METHODS),
        help="Methods to evaluate.",
    )
    parser.add_argument(
        "--max-cases",
        type=int,
        default=0,
        help="Maximum attack cases to replay. Use 0 for all cases.",
    )
    parser.add_argument(
        "--case-order",
        choices=("csv", "impact"),
        default="impact",
        help="Replay order. impact sorts by source physical impact descending.",
    )
    parser.add_argument(
        "--attacks",
        nargs="*",
        default=None,
        help="Optional attack-name filter, for example voltage_masking topology_drop.",
    )
    parser.add_argument(
        "--bpso-particles",
        type=int,
        default=8,
        help="BPSO particle count.",
    )
    parser.add_argument(
        "--bpso-iterations",
        type=int,
        default=8,
        help="BPSO iteration count.",
    )
    parser.add_argument(
        "--bpso-seed",
        type=int,
        default=5157,
        help="Base seed for deterministic BPSO runs.",
    )
    parser.add_argument(
        "--allow-masked-switch-actions",
        action="store_true",
        help="Allow BPSO to close switches marked unavailable by ActionMasking.",
    )
    parser.add_argument(
        "--skip-unavailable",
        action="store_true",
        help="Skip methods that are unavailable instead of writing unavailable rows.",
    )
    parser.add_argument(
        "--no-figures",
        action="store_true",
        help="Skip matplotlib figures. Summary CSV is still written.",
    )
    return parser.parse_args()


def parse_json_field(value, default):
    if value is None or value == "":
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def parse_float(value, default=0.0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return number


def parse_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_attack_cases(input_path, attacks=None, max_cases=0, case_order="impact"):
    path = resolve_path(input_path)
    attack_filter = set(attacks or [])
    cases = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader):
            attack = row.get("attack", "")
            if attack_filter and attack not in attack_filter:
                continue
            system = row.get("system", "34bus")
            if system != "34bus":
                continue
            cases.append(
                AttackCase(
                    source_index=index,
                    system=system,
                    scenario=row.get("scenario", "random"),
                    scenario_seed=parse_int(row.get("scenario_seed")),
                    attack=attack,
                    attack_kwargs=parse_json_field(row.get("attack_kwargs"), {}),
                    source_physical_impact_score=parse_float(
                        row.get("physical_impact_score"), default=0.0
                    ),
                )
            )

    if case_order == "impact":
        cases.sort(key=lambda item: item.source_physical_impact_score, reverse=True)
    if max_cases and max_cases > 0:
        cases = cases[:max_cases]
    return cases


def stable_seed(*parts):
    value = 2166136261
    for part in parts:
        for char in str(part):
            value ^= ord(char)
            value = (value * 16777619) % (2**32 - 1)
    return int(value or 1)


def set_scenario_seed(seed):
    random.seed(int(seed))
    np.random.seed(int(seed) % (2**32 - 1))


def reset_same_random_scenario(experiment, scenario_seed):
    set_scenario_seed(scenario_seed)
    return experiment.get_observation("random")


def clone_observation(obs):
    cloned = {}
    for key, value in obs.items():
        if isinstance(value, np.ndarray):
            cloned[key] = np.array(value, copy=True)
        elif isinstance(value, dict):
            cloned[key] = value.copy()
        elif isinstance(value, list):
            cloned[key] = list(value)
        else:
            cloned[key] = value
    return cloned


def evaluate_on_seed(experiment, scenario_seed, action):
    reset_same_random_scenario(experiment, scenario_seed)
    obs_post, reward, done, _ = experiment.env.step(np.asarray(action, dtype=int))
    metrics = experiment.metrics_from_observation(obs_post, reward=reward, action=action)
    metrics["done"] = bool(done)
    return metrics, obs_post


class PPOController:
    def __init__(self, method, model_path):
        self.method = method
        self.method_status = "ok"
        self.method_notes = "PPO policy evaluated on 34-bus OpenDSS environment."
        self.experiment = RestorationExperiment(
            system="34bus",
            model_path=model_path,
            load_model=True,
        )

    def decide(self, obs, case, mode):
        action, policy_time_ms = self.experiment.predict_action(obs)
        return np.asarray(action, dtype=int), float(policy_time_ms), {}


class BPSOController:
    def __init__(self, particles, iterations, seed, enforce_action_mask=True):
        self.method = "BPSO"
        self.method_status = "ok"
        self.method_notes = (
            "Binary PSO over the real 34-bus action vector, scored with the "
            "same OpenDSS physical evaluator used for GRL/MLP."
        )
        self.experiment = RestorationExperiment(system="34bus", load_model=False)
        self.particles = max(1, int(particles))
        self.iterations = max(1, int(iterations))
        self.seed = int(seed)
        self.enforce_action_mask = bool(enforce_action_mask)

    def decide(self, obs, case, mode):
        rng = np.random.default_rng(stable_seed(self.seed, case.scenario_seed))
        n_actions = int(self.experiment.n_actions)
        action_mask = np.asarray(obs.get("ActionMasking", []), dtype=float).reshape(-1)
        if action_mask.size != n_actions:
            action_mask = np.zeros(n_actions, dtype=float)

        def repair(position):
            action = np.asarray(position, dtype=int).reshape(-1).copy()
            if action.size != n_actions:
                repaired = np.zeros(n_actions, dtype=int)
                repaired[: min(action.size, n_actions)] = action[: min(action.size, n_actions)]
                action = repaired
            action = np.where(action > 0, 1, 0).astype(int)
            if self.enforce_action_mask:
                action[action_mask > 0.5] = 0
            return action

        def score(position):
            action = repair(position)
            metrics, _ = evaluate_on_seed(self.experiment, case.scenario_seed, action)
            return restoration_action_quality(metrics), metrics, action

        start = perf_counter()
        positions = rng.integers(0, 2, size=(self.particles, n_actions), dtype=int)
        positions = np.asarray([repair(item) for item in positions], dtype=int)
        velocities = rng.normal(0.0, 0.25, size=(self.particles, n_actions))
        personal_best_positions = positions.copy()
        personal_best_scores = np.full(self.particles, -np.inf, dtype=float)
        global_best_position = positions[0].copy()
        global_best_score = -np.inf
        global_best_metrics = None
        best_iteration = 0
        candidate_evaluations = 0

        for iteration in range(self.iterations):
            for particle_index in range(self.particles):
                value, metrics, action = score(positions[particle_index])
                candidate_evaluations += 1
                if value > personal_best_scores[particle_index]:
                    personal_best_scores[particle_index] = value
                    personal_best_positions[particle_index] = action
                if value > global_best_score:
                    global_best_score = value
                    global_best_position = action
                    global_best_metrics = metrics
                    best_iteration = iteration

            inertia = 0.72
            cognitive = 1.49
            social = 1.49
            r1 = rng.random(size=(self.particles, n_actions))
            r2 = rng.random(size=(self.particles, n_actions))
            velocities = (
                inertia * velocities
                + cognitive * r1 * (personal_best_positions - positions)
                + social * r2 * (global_best_position - positions)
            )
            probabilities = 1.0 / (1.0 + np.exp(-np.clip(velocities, -20.0, 20.0)))
            positions = (rng.random(size=(self.particles, n_actions)) < probabilities).astype(int)
            positions = np.asarray([repair(item) for item in positions], dtype=int)

        elapsed_ms = (perf_counter() - start) * 1000.0
        metadata = {
            "bpso_particles": self.particles,
            "bpso_iterations": self.iterations,
            "bpso_candidate_evaluations": candidate_evaluations,
            "bpso_best_iteration": int(best_iteration),
            "bpso_best_quality": float(global_best_score),
            "bpso_best_metrics": global_best_metrics or {},
            "bpso_enforced_action_mask": int(self.enforce_action_mask),
        }
        return repair(global_best_position), float(elapsed_ms), metadata


class UnavailableController:
    def __init__(self, method, reason):
        self.method = method
        self.method_status = "unavailable"
        self.method_notes = reason
        self.experiment = None


def make_controller(method, args):
    method = method.upper()
    if method == "GRL":
        return PPOController(
            method="GRL",
            model_path=BASE_DIR / "34bus" / "TrainedModels" / "GCAPS_34.zip",
        )
    if method == "MLP":
        return PPOController(
            method="MLP",
            model_path=BASE_DIR / "34bus" / "TrainedModels" / "MLP_34.zip",
        )
    if method == "BPSO":
        return BPSOController(
            particles=args.bpso_particles,
            iterations=args.bpso_iterations,
            seed=args.bpso_seed,
            enforce_action_mask=not args.allow_masked_switch_actions,
        )
    if method == "MISOCP":
        return UnavailableController(method="MISOCP", reason=MISOCP_34BUS_UNAVAILABLE_REASON)
    raise ValueError("Unknown method: {}".format(method))


def action_to_list(action):
    return [int(value) for value in np.asarray(action, dtype=int).reshape(-1)]


def make_result_row(
    controller,
    case,
    mode,
    action,
    metrics,
    clean_action,
    clean_metrics,
    clean_policy_time_ms,
    policy_time_ms,
    attack_metadata,
    detector_features,
    bdd_report,
    controller_metadata,
):
    experiment = controller.experiment
    action_list = action_to_list(action)
    clean_action_list = action_to_list(clean_action)
    switch_vector, load_status = experiment.split_action(action_list)
    row = {
        "system": "34bus",
        "method": controller.method,
        "method_status": controller.method_status,
        "method_notes": controller.method_notes,
        "source_case_index": case.source_index,
        "source_physical_impact_score": case.source_physical_impact_score,
        "scenario": case.scenario,
        "scenario_seed": case.scenario_seed,
        "attack": "clean" if mode == "clean" else case.attack,
        "mode": mode,
        "attack_kwargs": {} if mode == "clean" else case.attack_kwargs,
        "clean_action": clean_action_list,
        "action": action_list,
        "switch_vector": action_to_list(switch_vector),
        "load_status": load_status,
        "attack_metadata": attack_metadata,
        "bdd_detected": bool(bdd_report.get("detected", False)),
        "bdd_score": float(bdd_report.get("score", 0.0)),
        "bdd_detected_channels": bdd_report.get("detected_channels", []),
        "detector_feature_vector": detector_features,
        "controller_metadata": controller_metadata,
        "clean_policy_time_ms": float(clean_policy_time_ms),
        "policy_time_ms": float(policy_time_ms),
    }
    row.update(metrics)
    row.update(physical_impact(clean_metrics, metrics))
    row.update(action_delta(clean_action_list, action_list, experiment.num_switches))
    return row


def make_unavailable_row(controller, case):
    return {
        "system": "34bus",
        "method": controller.method,
        "method_status": controller.method_status,
        "method_notes": controller.method_notes,
        "source_case_index": case.source_index,
        "source_physical_impact_score": case.source_physical_impact_score,
        "scenario": case.scenario,
        "scenario_seed": case.scenario_seed,
        "attack": case.attack,
        "mode": "not_evaluated",
        "attack_kwargs": case.attack_kwargs,
        "attack_metadata": {},
        "bdd_detected": "",
        "bdd_score": "",
        "bdd_detected_channels": [],
        "detector_feature_vector": [],
        "controller_metadata": {"reason": controller.method_notes},
    }


def run_case(controller, case):
    experiment = controller.experiment
    true_obs = clone_observation(reset_same_random_scenario(experiment, case.scenario_seed))
    clean_action, clean_policy_time_ms, clean_controller_metadata = controller.decide(
        clone_observation(true_obs), case, "clean"
    )
    clean_metrics, _ = evaluate_on_seed(experiment, case.scenario_seed, clean_action)

    clean_row = make_result_row(
        controller=controller,
        case=case,
        mode="clean",
        action=clean_action,
        metrics=clean_metrics,
        clean_action=clean_action,
        clean_metrics=clean_metrics,
        clean_policy_time_ms=clean_policy_time_ms,
        policy_time_ms=clean_policy_time_ms,
        attack_metadata={"target": "none"},
        detector_features=[],
        bdd_report={"detected": False, "score": 0.0, "detected_channels": []},
        controller_metadata=clean_controller_metadata,
    )

    policy_obs, attack_metadata = apply_attack(
        clone_observation(true_obs), case.attack, **case.attack_kwargs
    )
    detector_features, bdd_report = detector_observation_from_reports(true_obs, policy_obs)
    attacked_action, policy_time_ms, controller_metadata = controller.decide(
        clone_observation(policy_obs), case, "attacked_unmitigated"
    )
    attacked_metrics, _ = evaluate_on_seed(experiment, case.scenario_seed, attacked_action)

    attacked_row = make_result_row(
        controller=controller,
        case=case,
        mode="attacked_unmitigated",
        action=attacked_action,
        metrics=attacked_metrics,
        clean_action=clean_action,
        clean_metrics=clean_metrics,
        clean_policy_time_ms=clean_policy_time_ms,
        policy_time_ms=policy_time_ms,
        attack_metadata=attack_metadata,
        detector_features=detector_features,
        bdd_report=bdd_report,
        controller_metadata=controller_metadata,
    )
    return [clean_row, attacked_row]


def finite_values(rows, method, mode, column):
    values = []
    abs_limit = SUMMARY_ABS_LIMITS.get(column)
    for row in rows:
        if row.get("method") != method or row.get("mode") != mode:
            continue
        if row.get("method_status") != "ok":
            continue
        value = parse_float(row.get(column), default=float("nan"))
        if math.isfinite(value):
            if abs_limit is not None and abs(value) > abs_limit:
                continue
            values.append(value)
    return values


def summarize_rows(rows):
    methods = sorted({row.get("method") for row in rows if row.get("method")})
    modes = sorted({row.get("mode") for row in rows if row.get("mode")})
    summary = []
    columns = (
        "reward",
        "energy_kw",
        "energy_ratio",
        "voltage_violation",
        "convergence_violation",
        "physical_impact_score",
        "action_changed",
        "policy_time_ms",
    )
    for method in methods:
        for mode in modes:
            subset = [
                row
                for row in rows
                if row.get("method") == method
                and row.get("mode") == mode
                and row.get("method_status") == "ok"
            ]
            if not subset:
                continue
            item = {"method": method, "mode": mode, "n": len(subset)}
            for column in columns:
                values = finite_values(rows, method, mode, column)
                item[column + "_n"] = len(values)
                if values:
                    item[column + "_mean"] = float(np.mean(values))
                    item[column + "_median"] = float(np.median(values))
            summary.append(item)
    return summary


def write_method_figures(rows, artifact_dir):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        return ["matplotlib figures skipped: {}".format(exc)]

    artifact_dir = Path(artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    attacked = [
        row
        for row in rows
        if row.get("mode") == "attacked_unmitigated" and row.get("method_status") == "ok"
    ]
    methods = sorted({row["method"] for row in attacked})
    if not methods:
        return ["matplotlib figures skipped: no evaluated attacked rows"]

    figure_specs = [
        ("energy_ratio", "Mean Energy Ratio", "fig_method_energy_ratio.png"),
        ("voltage_violation", "Mean Voltage Violation", "fig_method_voltage_violation.png"),
        ("physical_impact_score", "Mean Physical Impact Score", "fig_method_fdia_impact.png"),
        ("policy_time_ms", "Mean Decision Time (ms)", "fig_method_runtime.png"),
    ]
    written = []
    for column, ylabel, filename in figure_specs:
        means = []
        labels = []
        for method in methods:
            values = finite_values(rows, method, "attacked_unmitigated", column)
            if values:
                labels.append(method)
                means.append(float(np.mean(values)))
        if not labels:
            continue
        fig, ax = plt.subplots(figsize=(7.0, 4.0))
        ax.bar(labels, means, color=["#2f6f8f", "#b85750", "#6f8f3f", "#7a6aa8"][: len(labels)])
        ax.set_ylabel(ylabel)
        ax.set_xlabel("Method")
        ax.grid(axis="y", alpha=0.25)
        fig.tight_layout()
        output_path = artifact_dir / filename
        fig.savefig(output_path, dpi=180)
        plt.close(fig)
        written.append(str(output_path))
    return written


def write_manifest(output_path, artifact_dir, args, cases, rows, figure_notes):
    manifest_path = Path(artifact_dir) / "method_comparison_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "output_csv": str(output_path),
        "input_cases": str(resolve_path(args.cases)),
        "methods_requested": args.methods,
        "cases_replayed": len(cases),
        "rows_written": len(rows),
        "bpso_particles": args.bpso_particles,
        "bpso_iterations": args.bpso_iterations,
        "skip_unavailable": bool(args.skip_unavailable),
        "figure_outputs": figure_notes,
        "misocp_34bus_status": MISOCP_34BUS_UNAVAILABLE_REASON,
    }
    manifest_path.write_text(safe_json(manifest) + "\n")
    return manifest_path


def main():
    args = parse_args()
    cases = load_attack_cases(
        args.cases,
        attacks=args.attacks,
        max_cases=args.max_cases,
        case_order=args.case_order,
    )
    if not cases:
        raise RuntimeError("No 34-bus attack cases were found.")

    output_path = resolve_path(args.output)
    artifact_dir = resolve_path(args.artifact_dir)
    rows = []

    for method in args.methods:
        controller = make_controller(method, args)
        if controller.method_status != "ok":
            if not args.skip_unavailable:
                rows.extend(make_unavailable_row(controller, case) for case in cases)
            continue
        for case in cases:
            rows.extend(run_case(controller, case))

    write_csv(rows, output_path)
    summary_rows = summarize_rows(rows)
    summary_path = artifact_dir / "table_method_summary.csv"
    write_csv(summary_rows, summary_path)
    figure_notes = []
    if not args.no_figures:
        figure_notes = write_method_figures(rows, artifact_dir)
    manifest_path = write_manifest(output_path, artifact_dir, args, cases, rows, figure_notes)

    print("wrote {}".format(output_path))
    print("wrote {}".format(summary_path))
    print("wrote {}".format(manifest_path))
    if figure_notes:
        for note in figure_notes:
            print("figure {}".format(note))


if __name__ == "__main__":
    main()
