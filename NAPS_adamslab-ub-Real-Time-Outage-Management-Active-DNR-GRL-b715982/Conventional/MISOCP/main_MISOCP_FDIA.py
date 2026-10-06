"""Run IEEE 123-bus MISOCP clean/FDIA comparison cases.

This wrapper launches DecisionCtrl.py once per case because that script builds
and solves a Gurobi model at module scope. Each child solve writes one JSON row;
the wrapper adds clean-vs-attack action changes and writes the paper CSV.
"""

import argparse
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ATTACKS = ["clean", "voltage_masking", "branchflow_hiding", "energy_inflation", "topology_drop"]
SCENARIOS = ["SC1", "SC2"]
DEFENSE_MODES = ["unmitigated", "mitigated"]
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "RL_Testing" / "123bus" / "paper_results" / "misocp_fdia_123_results.csv"
DEFAULT_DEFENDED_OUTPUT = REPO_ROOT / "RL_Testing" / "123bus" / "paper_results" / "misocp_fdia_123_defended_results.csv"


FIELDS = [
    "method",
    "scenario",
    "case",
    "defense_mode",
    "energy_kw",
    "total_demand_kw",
    "energy_ratio",
    "voltage_violation",
    "convergence_violation",
    "reward",
    "fitness",
    "optimizer_best_fitness",
    "policy_time_ms",
    "runtime_sec",
    "loads_served",
    "loads_shed",
    "closed_switches",
    "open_switches",
    "action_changed",
    "switch_changes_vs_clean",
    "load_changes_vs_clean",
    "switch_vector",
    "load_status",
    "attack_metadata",
    "mitigation_metadata",
    "mitigation_applied",
    "mitigated_channels",
    "mitigated_keys",
    "fdia_detected",
    "detector_score",
    "detected_channels",
    "detector_residuals",
    "post_mitigation_fdia_detected",
    "post_mitigation_detector_score",
    "post_mitigation_detected_channels",
    "post_mitigation_detector_residuals",
    "optimizer_status",
    "optimizer_status_text",
]


def resolve_output_path(path):
    output_path = Path(path)
    if output_path.is_absolute():
        return output_path
    return (Path.cwd() / output_path).resolve()


def short_process_message(process):
    message = "\n".join(part for part in [process.stdout, process.stderr] if part).strip()
    lines = [line.strip() for line in message.splitlines() if line.strip()]
    if not lines:
        return "child process failed without an error message"
    return " | ".join(lines[-8:])


def classify_failure(message):
    lowered = message.lower()
    if "model too large for size-limited license" in lowered:
        return "license_blocked_size_limited"
    if "unable to open gurobi license file" in lowered:
        return "license_file_not_found"
    if "no gurobi license" in lowered or "license" in lowered:
        return "license_blocked"
    return "solve_failed"


def failed_row(scenario_name, attack_name, message, defense_mode="unmitigated"):
    status_text = f"{classify_failure(message)}: {message}"
    return {
        "method": "MISOCP",
        "scenario": scenario_name,
        "case": attack_name,
        "defense_mode": "clean" if attack_name == "clean" else defense_mode,
        "energy_kw": 0.0,
        "total_demand_kw": 0.0,
        "energy_ratio": 0.0,
        "voltage_violation": 0.0,
        "convergence_violation": 1.0,
        "reward": 0.0,
        "fitness": 0.0,
        "optimizer_best_fitness": 0.0,
        "policy_time_ms": 0.0,
        "runtime_sec": 0.0,
        "loads_served": 0,
        "loads_shed": 0,
        "closed_switches": 0,
        "open_switches": 0,
        "action_changed": 0,
        "switch_changes_vs_clean": 0,
        "load_changes_vs_clean": 0,
        "switch_vector": [],
        "load_status": {},
        "attack_metadata": {"target": "not_evaluated", "note": status_text},
        "mitigation_metadata": {
            "strategy": "not_evaluated",
            "mitigation_applied": False,
            "mitigated_channels": [],
            "mitigated_keys": [],
            "note": status_text,
        },
        "mitigation_applied": 0,
        "mitigated_channels": [],
        "mitigated_keys": [],
        "fdia_detected": 0,
        "detector_score": 0.0,
        "detected_channels": [],
        "detector_residuals": {"not_evaluated": 1.0},
        "post_mitigation_fdia_detected": 0,
        "post_mitigation_detector_score": 0.0,
        "post_mitigation_detected_channels": [],
        "post_mitigation_detector_residuals": {"not_evaluated": 1.0},
        "optimizer_status": -1,
        "optimizer_status_text": status_text,
        "action_array": [],
    }


def run_child_case(scenario_name, attack_name, defense_mode, seed, row_path, verbose=False):
    script_path = Path(__file__).with_name("DecisionCtrl.py")
    command = [
        sys.executable,
        str(script_path),
        "--scenario",
        scenario_name,
        "--attack",
        attack_name,
        "--defense-mode",
        defense_mode,
        "--seed",
        str(seed),
        "--row-output",
        str(row_path),
    ]
    if verbose:
        command.append("--verbose")

    process = subprocess.run(
        command,
        cwd=str(Path(__file__).parent),
        capture_output=True,
        text=True,
    )
    if verbose and process.stdout:
        print(process.stdout)
    if process.returncode != 0 or not row_path.exists():
        return failed_row(scenario_name, attack_name, short_process_message(process), defense_mode)
    with row_path.open() as handle:
        return json.load(handle)


def attach_clean_comparison(row, clean_action):
    if clean_action is None:
        row["action_changed"] = 0
        row["switch_changes_vs_clean"] = 0
        row["load_changes_vs_clean"] = 0
        return row

    action = row["action_array"]
    num_switches = len(row["switch_vector"])
    row["action_changed"] = int(any(int(a) != int(b) for a, b in zip(action, clean_action)))
    row["switch_changes_vs_clean"] = int(
        sum(int(action[i]) != int(clean_action[i]) for i in range(num_switches))
    )
    row["load_changes_vs_clean"] = int(
        sum(int(action[i]) != int(clean_action[i]) for i in range(num_switches, len(action)))
    )
    return row


def is_blocked(row):
    return int(row.get("optimizer_status", 0)) == -1


def write_csv(rows, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            csv_row = {field: row[field] for field in FIELDS}
            for field in [
                "switch_vector",
                "load_status",
                "attack_metadata",
                "mitigation_metadata",
                "mitigated_channels",
                "mitigated_keys",
                "detected_channels",
                "detector_residuals",
                "post_mitigation_detected_channels",
                "post_mitigation_detector_residuals",
            ]:
                csv_row[field] = json.dumps(csv_row[field])
            writer.writerow(csv_row)


def parse_args():
    parser = argparse.ArgumentParser(description="Run MISOCP IEEE 123-bus clean/FDIA comparison cases")
    parser.add_argument("--scenarios", nargs="+", default=SCENARIOS, choices=SCENARIOS)
    parser.add_argument("--attacks", nargs="+", default=ATTACKS, choices=ATTACKS)
    parser.add_argument("--defense-modes", nargs="+", default=DEFENSE_MODES, choices=DEFENSE_MODES)
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--output", default=str(DEFAULT_DEFENDED_OUTPUT))
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    rows = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        for scenario_name in args.scenarios:
            clean_path = tmp_path / f"{scenario_name}_clean.json"
            clean_row = run_child_case(scenario_name, "clean", "unmitigated", args.seed, clean_path, args.verbose)
            attach_clean_comparison(clean_row, None)
            rows.append(clean_row)
            clean_action = clean_row["action_array"]
            print(
                f"MISOCP {scenario_name} clean | energy_ratio={clean_row['energy_ratio']:.6f} | "
                f"fitness={clean_row['fitness']:.6f} | runtime_sec={clean_row['runtime_sec']:.2f}"
            )
            if is_blocked(clean_row):
                print(f"MISOCP {scenario_name} blocked | {clean_row['optimizer_status_text']}")
                for attack_name in args.attacks:
                    if attack_name == "clean":
                        continue
                    for defense_mode in args.defense_modes:
                        row = failed_row(
                            scenario_name,
                            attack_name,
                            "not_run_because_clean_misocp_case_was_blocked",
                            defense_mode=defense_mode,
                        )
                        rows.append(row)
                continue

            for attack_name in args.attacks:
                if attack_name == "clean":
                    continue
                for defense_mode in args.defense_modes:
                    row_path = tmp_path / f"{scenario_name}_{attack_name}_{defense_mode}.json"
                    row = run_child_case(scenario_name, attack_name, defense_mode, args.seed, row_path, args.verbose)
                    attach_clean_comparison(row, clean_action)
                    rows.append(row)
                    print(
                        f"MISOCP {scenario_name} {attack_name} {defense_mode} | "
                        f"energy_ratio={row['energy_ratio']:.6f} | "
                        f"fitness={row['fitness']:.6f} | action_changed={row['action_changed']} | "
                        f"mitigated={row['mitigation_applied']} | runtime_sec={row['runtime_sec']:.2f}"
                    )

    output_path = resolve_output_path(args.output)
    write_csv(rows, output_path)
    print(f"Saved MISOCP paper CSV: {output_path}")


if __name__ == "__main__":
    main()
