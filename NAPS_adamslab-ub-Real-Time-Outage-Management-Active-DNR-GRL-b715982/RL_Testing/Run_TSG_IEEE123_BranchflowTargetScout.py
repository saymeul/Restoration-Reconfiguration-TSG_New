"""Rank IEEE 123 branchflow observations for targeted criticality chunks.

This utility does not perform an attack. It evaluates the same deterministic
outage scenarios used by the IEEE 123 baseline study and ranks branchflow
observation channels by clean observed magnitude. The result helps prioritize
which branchflow targets to attack first.
"""

import argparse
import numpy as np

from FDIA_ExperimentCore import RestorationExperiment, resolve_path, safe_json, write_csv
from IEEE123_VulnerabilityRegistry import build_observation_registry
from Run_TSG_IEEE34_BaselineAttackStudy import generate_outage_scenario, scenario_observation


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scout active IEEE 123 branchflow observation targets."
    )
    parser.add_argument("--cases", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20260615)
    parser.add_argument(
        "--seed-schedule",
        choices=["baseline_attack", "criticality_sequential"],
        default="baseline_attack",
    )
    parser.add_argument("--baseline-case-seed-draws", type=int, default=5)
    parser.add_argument("--max-outage-fraction", type=float, default=0.50)
    parser.add_argument("--max-scenario-generation-attempts", type=int, default=100)
    parser.add_argument("--active-threshold", type=float, default=1.0e-9)
    parser.add_argument(
        "--output-dir",
        default="paper_results/tsg_ieee123/branchflow_target_scout",
    )
    return parser.parse_args()


def scenario_seeds(args):
    rng = np.random.default_rng(int(args.seed))
    for _case_index in range(int(args.cases)):
        scenario_seed = int(rng.integers(1, 2**31 - 1))
        yield scenario_seed
        if args.seed_schedule == "baseline_attack":
            for _draw_index in range(int(args.baseline_case_seed_draws)):
                rng.integers(1, 2**31 - 1)


def branchflow_targets(experiment):
    entries = [
        entry
        for entry in build_observation_registry(experiment)
        if entry.family == "branchflow" and entry.attackable and entry.current_grl_input
    ]
    return sorted(entries, key=lambda entry: str(entry.observation_id))


def main():
    args = parse_args()
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    experiment = RestorationExperiment(system="123bus", load_model=True)
    targets = branchflow_targets(experiment)
    values_by_target = {target.observation_id: [] for target in targets}
    scenario_rows = []

    for case_index, scenario_seed in enumerate(scenario_seeds(args)):
        scenario = generate_outage_scenario(experiment, scenario_seed, args)
        obs = scenario_observation(experiment, scenario)
        branchflows = np.asarray(obs["EdgeFeat(Branchflow)"], dtype=float).reshape(-1)
        finite_branchflows = np.nan_to_num(branchflows, nan=0.0, posinf=0.0, neginf=0.0)
        scenario_rows.append(
            {
                "case_index": case_index,
                "scenario_seed": int(scenario_seed),
                "root_node": scenario["root_node"],
                "radius": int(scenario["radius"]),
                "outage_edge_count": int(scenario["outage_edge_count"]),
                "max_abs_branchflow": float(np.max(np.abs(finite_branchflows))),
                "mean_abs_branchflow": float(np.mean(np.abs(finite_branchflows))),
            }
        )
        for target in targets:
            target_index = int(target.index[0])
            if target_index < len(finite_branchflows):
                value = float(finite_branchflows[target_index])
            else:
                value = 0.0
            values_by_target[target.observation_id].append(value)

    ranking_rows = []
    runner_index_by_observation = {
        target.observation_id: index for index, target in enumerate(targets)
    }

    for target in targets:
        values = np.asarray(values_by_target[target.observation_id], dtype=float)
        abs_values = np.abs(values)
        active_cases = int(np.sum(abs_values > float(args.active_threshold)))
        ranking_rows.append(
            {
                "target_observation_id": target.observation_id,
                "target_component_type": target.component_type,
                "target_component_name": target.component_name,
                "runner_target_index": int(runner_index_by_observation[target.observation_id]),
                "target_measurement_index": int(target.index[0]),
                "case_count": int(len(values)),
                "active_case_count": active_cases,
                "active_case_rate": float(active_cases / max(len(values), 1)),
                "mean_branchflow": float(np.mean(values)),
                "mean_abs_branchflow": float(np.mean(abs_values)),
                "max_abs_branchflow": float(np.max(abs_values)),
                "p95_abs_branchflow": float(np.percentile(abs_values, 95)),
            }
        )

    ranking_rows.sort(
        key=lambda row: (
            row["mean_abs_branchflow"],
            row["max_abs_branchflow"],
            row["active_case_rate"],
        ),
        reverse=True,
    )
    for rank, row in enumerate(ranking_rows, start=1):
        row["scout_rank"] = rank

    paths = {
        "ranking": output_dir / "tsg_ieee123_branchflow_target_scout_ranking.csv",
        "scenario_summary": output_dir / "tsg_ieee123_branchflow_target_scout_scenarios.csv",
        "manifest": output_dir / "tsg_ieee123_branchflow_target_scout_manifest.json",
    }
    write_csv(ranking_rows, paths["ranking"])
    write_csv(scenario_rows, paths["scenario_summary"])
    manifest = {
        "experiment": "IEEE 123 branchflow target scout",
        "system": "123bus",
        "cases": int(args.cases),
        "seed": int(args.seed),
        "seed_schedule": args.seed_schedule,
        "baseline_case_seed_draws": int(args.baseline_case_seed_draws),
        "target_count": len(targets),
        "active_threshold": float(args.active_threshold),
        "outputs": {key: str(value) for key, value in paths.items()},
        "notes": (
            "This utility ranks clean branchflow observation magnitudes only; "
            "it does not apply FDIA or measure restoration degradation."
        ),
    }
    paths["manifest"].write_text(safe_json(manifest) + "\n")
    print("wrote {}".format(paths["ranking"]), flush=True)
    print("wrote {}".format(paths["scenario_summary"]), flush=True)
    print("wrote {}".format(paths["manifest"]), flush=True)


if __name__ == "__main__":
    main()
