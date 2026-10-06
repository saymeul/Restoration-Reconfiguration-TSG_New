"""Generate an audited chunk plan for IEEE 8500 observation criticality runs.

The full IEEE 8500 criticality sweep is intentionally chunked because it is much
larger than IEEE 34. This utility writes a JSON manifest and PowerShell helper
scripts with exact commands for every branchflow and action-mask chunk.
"""

import argparse
from pathlib import Path

from FDIA_ExperimentCore import BASE_DIR, RestorationExperiment, resolve_path, safe_json
from IEEE8500_VulnerabilityRegistry import build_observation_registry


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create chunk and merge commands for IEEE 8500 criticality sweeps."
    )
    parser.add_argument("--cases", type=int, default=30)
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--seed", type=int, default=20260615)
    parser.add_argument(
        "--seed-schedule",
        choices=["baseline_attack", "criticality_sequential"],
        default="baseline_attack",
    )
    parser.add_argument("--baseline-case-seed-draws", type=int, default=5)
    parser.add_argument("--branchflow-chunk-size", type=int, default=1)
    parser.add_argument("--action-mask-chunk-size", type=int, default=1)
    parser.add_argument(
        "--output-root",
        default="paper_results/tsg_ieee8500/full_criticality_batches",
    )
    parser.add_argument(
        "--merged-output-root",
        default="paper_results/tsg_ieee8500/full_criticality_merged",
    )
    parser.add_argument("--conda-env", default="grl8500")
    parser.add_argument(
        "--omit-include-noop",
        action="store_true",
        help="Do not include no-op rows. Default keeps no-op rows for all-case accounting.",
    )
    return parser.parse_args()


def powershell_quote(value):
    text = str(value)
    if text and all(char not in text for char in " \t'\""):
        return text
    return "'" + text.replace("'", "''") + "'"


def powershell_command(parts):
    return " ".join(powershell_quote(part) for part in parts)


def chunk_ranges(total, chunk_size):
    if chunk_size <= 0:
        raise ValueError("Chunk size must be positive.")
    for start in range(0, total, chunk_size):
        end = min(start + chunk_size, total)
        yield start, end


def target_counts():
    experiment = RestorationExperiment(system="8500bus", load_model=False)
    entries = build_observation_registry(experiment)
    branchflow = sorted(
        [
            entry
            for entry in entries
            if entry.family == "branchflow" and entry.attackable and entry.current_grl_input
        ],
        key=lambda entry: str(entry.observation_id),
    )
    action_mask = sorted(
        [
            entry
            for entry in entries
            if entry.observation_key == "ActionMasking"
            and entry.component_type
            in ("sectionalizing_switch", "tie_switch", "dispatch_load")
        ],
        key=lambda entry: (int(entry.index[0]), str(entry.observation_id)),
    )
    return len(branchflow), len(action_mask)


def chunk_output(root, family, start, end):
    return Path(root) / family / "chunk_{:04d}_{:04d}".format(start, end - 1)


def build_branchflow_chunk(args, output_root, start, end):
    output_dir = chunk_output(output_root, "branchflow", start, end)
    command = [
        "conda",
        "run",
        "-n",
        args.conda_env,
        "python",
        "Run_TSG_IEEE8500_MeasurementCriticality.py",
        "--cases",
        str(args.cases),
        "--horizon",
        str(args.horizon),
        "--seed",
        str(args.seed),
        "--seed-schedule",
        args.seed_schedule,
        "--baseline-case-seed-draws",
        str(args.baseline_case_seed_draws),
        "--target-family",
        "branchflow",
        "--target-start-index",
        str(start),
        "--target-count",
        str(end - start),
        "--output-dir",
        str(output_dir),
    ]
    if not args.omit_include_noop:
        command.insert(-2, "--include-noop")
    return {
        "study": "branchflow",
        "target_start_index": start,
        "target_end_index_exclusive": end,
        "target_count": end - start,
        "output_dir": str(output_dir),
        "case_summary": str(output_dir / "tsg_ieee8500_measurement_criticality_cases.csv"),
        "ranking": str(output_dir / "tsg_ieee8500_measurement_criticality_ranking.csv"),
        "command": command,
        "powershell": powershell_command(command),
    }


def build_action_mask_chunk(args, output_root, start, end):
    output_dir = chunk_output(output_root, "action_mask", start, end)
    command = [
        "conda",
        "run",
        "-n",
        args.conda_env,
        "python",
        "Run_TSG_IEEE8500_ActionMaskCriticality.py",
        "--cases",
        str(args.cases),
        "--horizon",
        str(args.horizon),
        "--seed",
        str(args.seed),
        "--seed-schedule",
        args.seed_schedule,
        "--baseline-case-seed-draws",
        str(args.baseline_case_seed_draws),
        "--target-scope",
        "switch_and_load",
        "--target-start-index",
        str(start),
        "--target-count",
        str(end - start),
        "--output-dir",
        str(output_dir),
    ]
    if not args.omit_include_noop:
        command.insert(-2, "--include-noop")
    return {
        "study": "action_mask",
        "target_start_index": start,
        "target_end_index_exclusive": end,
        "target_count": end - start,
        "output_dir": str(output_dir),
        "case_summary": str(output_dir / "tsg_ieee8500_action_mask_criticality_cases.csv"),
        "ranking": str(output_dir / "tsg_ieee8500_action_mask_criticality_ranking.csv"),
        "command": command,
        "powershell": powershell_command(command),
    }


def merge_command(args, merged_output_root, study, case_files):
    if study == "branchflow":
        runner = "Run_TSG_IEEE8500_MeasurementCriticality.py"
        output_dir = Path(merged_output_root) / "branchflow"
    elif study == "action_mask":
        runner = "Run_TSG_IEEE8500_ActionMaskCriticality.py"
        output_dir = Path(merged_output_root) / "action_mask"
    else:
        raise ValueError("Unsupported merge study: {}".format(study))

    command = [
        "conda",
        "run",
        "-n",
        args.conda_env,
        "python",
        runner,
        "--merge-case-files",
    ]
    command.extend(str(path) for path in case_files)
    command.extend(["--output-dir", str(output_dir)])
    return {
        "study": study,
        "output_dir": str(output_dir),
        "case_files": [str(path) for path in case_files],
        "command": command,
        "powershell": powershell_command(command),
    }


def write_script(path, commands, title):
    lines = [
        "$ErrorActionPreference = 'Stop'",
        "Set-Location -LiteralPath {}".format(powershell_quote(BASE_DIR)),
        "",
        "# {}".format(title),
    ]
    for index, command in enumerate(commands, start=1):
        lines.append("")
        lines.append("# Command {} of {}".format(index, len(commands)))
        lines.append(command["powershell"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def main():
    args = parse_args()
    output_root = resolve_path(args.output_root)
    merged_output_root = resolve_path(args.merged_output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    merged_output_root.mkdir(parents=True, exist_ok=True)

    branchflow_count, action_mask_count = target_counts()
    branchflow_chunks = [
        build_branchflow_chunk(args, args.output_root, start, end)
        for start, end in chunk_ranges(branchflow_count, int(args.branchflow_chunk_size))
    ]
    action_mask_chunks = [
        build_action_mask_chunk(args, args.output_root, start, end)
        for start, end in chunk_ranges(action_mask_count, int(args.action_mask_chunk_size))
    ]

    branchflow_merge = merge_command(
        args,
        args.merged_output_root,
        "branchflow",
        [chunk["case_summary"] for chunk in branchflow_chunks],
    )
    action_mask_merge = merge_command(
        args,
        args.merged_output_root,
        "action_mask",
        [chunk["case_summary"] for chunk in action_mask_chunks],
    )

    manifest = {
        "experiment": "IEEE 8500-node full observation-criticality batch plan",
        "system": "8500bus",
        "cases": int(args.cases),
        "horizon": int(args.horizon),
        "seed": int(args.seed),
        "seed_schedule": args.seed_schedule,
        "baseline_case_seed_draws": int(args.baseline_case_seed_draws),
        "include_noop": not bool(args.omit_include_noop),
        "output_root": str(output_root),
        "merged_output_root": str(merged_output_root),
        "branchflow_target_count": branchflow_count,
        "branchflow_chunk_size": int(args.branchflow_chunk_size),
        "branchflow_chunk_count": len(branchflow_chunks),
        "action_mask_target_count": action_mask_count,
        "action_mask_chunk_size": int(args.action_mask_chunk_size),
        "action_mask_chunk_count": len(action_mask_chunks),
        "branchflow_chunks": branchflow_chunks,
        "action_mask_chunks": action_mask_chunks,
        "merge_commands": [branchflow_merge, action_mask_merge],
        "ieee34_freeze_boundary": "IEEE 34 is frozen; this plan writes only under tsg_ieee8500.",
    }

    manifest_path = output_root / "IEEE8500_full_criticality_batch_manifest.json"
    run_script_path = output_root / "run_all_IEEE8500_criticality_chunks.ps1"
    merge_script_path = output_root / "merge_IEEE8500_criticality_chunks.ps1"
    manifest["outputs"] = {
        "manifest": str(manifest_path),
        "run_all_script": str(run_script_path),
        "merge_script": str(merge_script_path),
    }

    manifest_path.write_text(safe_json(manifest) + "\n")
    write_script(
        run_script_path,
        branchflow_chunks + action_mask_chunks,
        "Run all IEEE 8500 full criticality chunks.",
    )
    write_script(
        merge_script_path,
        [branchflow_merge, action_mask_merge],
        "Merge completed IEEE 8500 full criticality chunks.",
    )

    print("wrote {}".format(manifest_path), flush=True)
    print("wrote {}".format(run_script_path), flush=True)
    print("wrote {}".format(merge_script_path), flush=True)
    print(
        "planned {} branchflow chunks and {} action-mask chunks".format(
            len(branchflow_chunks),
            len(action_mask_chunks),
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
