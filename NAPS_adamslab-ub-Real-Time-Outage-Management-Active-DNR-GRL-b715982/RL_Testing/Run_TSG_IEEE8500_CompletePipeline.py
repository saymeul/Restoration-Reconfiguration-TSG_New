"""One-file IEEE 8500 HPC orchestrator.

This is the main Python entry point for running the IEEE 8500 extension in the
same spirit as the frozen IEEE 34/123 studies.  It runs the study stages
directly and can also write/submit Slurm jobs for the long-running stages.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


RL_TESTING = Path(__file__).resolve().parent
NAPS_ROOT = RL_TESTING.parent
REPO_ROOT = NAPS_ROOT.parent
HPC_DIR = NAPS_ROOT / "hpc"
GENERATED_DIR = HPC_DIR / "generated_ieee8500"
RL_TRAINING = NAPS_ROOT / "RL_Training"
IEEE8500_DATA = REPO_ROOT / "Datasets" / "IEEE8500_PowerBench"

CONTROLLERS = ("GRL", "MLP", "BPSO")
DIRECT_STAGES = {
    "smoke_env",
    "train_grl",
    "train_mlp",
    "baseline_grl",
    "baseline_bpso",
    "batch_plan",
    "action_mask_chunk",
    "branchflow_chunk",
    "voltage_chunk",
    "merge_action_mask",
    "merge_branchflow",
    "merge_voltage",
    "branchflow_diagnosis",
    "branchflow_subset",
    "defense_summary",
    "advanced_mitigation",
    "paper_artifacts",
}


def norm_controller(value: str) -> str:
    value = str(value).upper()
    if value not in CONTROLLERS:
        raise argparse.ArgumentTypeError("controller must be one of {}".format(", ".join(CONTROLLERS)))
    return value


def result_root(controller: str) -> str:
    controller = norm_controller(controller)
    if controller == "MLP":
        return "paper_results/tsg_ieee8500_mlp"
    if controller == "BPSO":
        return "paper_results/tsg_ieee8500_bpso"
    return "paper_results/tsg_ieee8500"


def base_env(args: argparse.Namespace, controller: str | None = None) -> dict[str, str]:
    env = os.environ.copy()
    if args.venv:
        env["VENV"] = str(Path(args.venv).expanduser())
    env["CASES"] = str(args.cases)
    env["HORIZON"] = str(args.horizon)
    env["SEED"] = str(args.seed)
    env["CHUNK_SIZE"] = str(args.chunk_size)
    env["TSG_IEEE8500_MAX_SWITCH_ACTIONS"] = str(args.max_switch_actions)
    env["TSG_IEEE8500_MAX_LOAD_ACTIONS"] = str(args.max_load_actions)
    env["TSG_IEEE8500_SCENARIO_RADIUS"] = str(args.scenario_radius)
    env["TSG_IEEE8500_MAX_OUTAGE_EDGES"] = str(args.max_outage_edges)
    env["TSG_IEEE8500_RESET_RADIUS"] = str(args.scenario_radius)
    env["TSG_IEEE8500_RESET_MAX_OUTAGE_EDGES"] = str(args.max_outage_edges)
    if controller:
        env["CONTROLLER"] = norm_controller(controller)
    if args.no_cuda:
        env["NO_CUDA"] = "1"
    return env


def run_command(command: list[str], cwd: Path, env: dict[str, str], dry_run: bool = False) -> None:
    printable = " ".join(shlex.quote(part) for part in command)
    print("[cmd] {}  (cwd={})".format(printable, cwd), flush=True)
    if dry_run:
        return
    subprocess.run(command, cwd=str(cwd), env=env, check=True)


def run_python_code(code: str, cwd: Path, env: dict[str, str], dry_run: bool = False) -> None:
    run_command([sys.executable, "-c", code], cwd=cwd, env=env, dry_run=dry_run)


def copy_trained_model(src: Path, dst: Path, dry_run: bool = False) -> None:
    print("[copy] {} -> {}".format(src, dst), flush=True)
    if dry_run:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.copy2(src, dst)
    else:
        print("warning: trained model not found at {}".format(src), flush=True)


def target_start_from_env(env: dict[str, str]) -> str:
    return str(env.get("TARGET_START") or env.get("SLURM_ARRAY_TASK_ID") or "0")


def matched_case_files(pattern: Path, dry_run: bool = False) -> list[str]:
    matches = sorted(Path(match) for match in glob.glob(str(pattern)))
    if matches:
        return [str(path) for path in matches]
    if dry_run:
        return [str(pattern)]
    raise FileNotFoundError("No case files matched {}".format(pattern))


def run_stage_command(stage: str, args: argparse.Namespace, env: dict[str, str]) -> None:
    controller = norm_controller(env.get("CONTROLLER", args.controller))
    result_dir = result_root(controller)
    target_start = target_start_from_env(env)

    if stage == "smoke_env":
        run_python_code(
            "\n".join(
                [
                    "import os",
                    "import opendssdirect as dss",
                    "master = os.path.abspath('source/PowerBench/Datasets/State Estimation/8500 Node/Master.dss')",
                    "print('Compiling:', master)",
                    "dss.Basic.ClearAll()",
                    "dss.Text.Command(f'compile [{master}]')",
                    "print('Circuit:', dss.Circuit.Name())",
                    "print('Buses:', len(dss.Circuit.AllBusNames()))",
                    "print('Lines:', len(dss.Lines.AllNames()))",
                    "print('Loads:', len(dss.Loads.AllNames()))",
                    "print('PDElements:', len(dss.PDElements.AllNames()))",
                ]
            ),
            cwd=IEEE8500_DATA,
            env=env,
            dry_run=args.dry_run,
        )
        run_python_code(
            "\n".join(
                [
                    "from FDIA_ExperimentCore import RestorationExperiment",
                    "exp = RestorationExperiment(system='8500bus', load_model=False)",
                    "print('actions', exp.n_actions)",
                    "print('switches', exp.num_switches)",
                    "print('dispatch_loads', len(exp.dispatch_loads))",
                    "print('nodes', len(exp.init_module.node_list))",
                    "print('edges', len(exp.init_module.edge_list))",
                ]
            ),
            cwd=RL_TESTING,
            env=env,
            dry_run=args.dry_run,
        )
        return

    if stage in {"train_grl", "train_mlp"}:
        model_dir = RL_TRAINING / ("Trained_Models/IEEE8500_MLP" if stage == "train_mlp" else "Trained_Models/IEEE8500")
        tensorboard_dir = RL_TRAINING / "Tensorboard_logger"
        if not args.dry_run:
            model_dir.mkdir(parents=True, exist_ok=True)
            tensorboard_dir.mkdir(parents=True, exist_ok=True)
        encoder = "MLP" if stage == "train_mlp" else "GCAPS"
        train_cmd = [
            sys.executable,
            "train.py",
            "--env_size",
            "8500",
            "--node_encoder",
            encoder,
            "--num_cpu",
            env.get("NUM_CPU", "16"),
            "--total_steps",
            env.get("TOTAL_STEPS", "2000000"),
            "--n_steps",
            env.get("N_STEPS", "50000"),
            "--batch_size",
            env.get("BATCH_SIZE", "2000"),
            "--model_save",
            str(model_dir.relative_to(RL_TRAINING)) + "/",
        ]
        if env.get("NO_CUDA"):
            train_cmd.append("--no_cuda")
        run_command(train_cmd, cwd=RL_TRAINING, env=env, dry_run=args.dry_run)
        src_name = "{}_8500__final.zip".format(encoder)
        dst_name = "{}_8500.zip".format(encoder)
        copy_trained_model(model_dir / src_name, RL_TESTING / "8500bus" / "TrainedModels" / dst_name, dry_run=args.dry_run)
        return

    if stage in {"baseline_grl", "baseline_bpso"}:
        if stage == "baseline_bpso":
            controller = "BPSO"
            env["CONTROLLER"] = controller
            result_dir = result_root(controller)
        run_command(
            [
                sys.executable,
                "Run_TSG_IEEE8500_BaselineAttackStudy.py",
                "--controller",
                controller,
                "--cases",
                env["CASES"],
                "--seed",
                env["SEED"],
                "--attacks",
                "topology_drop",
                "action_mask_false_unavailable",
                "voltage_masking",
                "branchflow_hiding",
                "energy_inflation",
                "--horizon",
                env["HORIZON"],
                "--max-scenario-radius",
                env["TSG_IEEE8500_SCENARIO_RADIUS"],
                "--max-outage-edges",
                env["TSG_IEEE8500_MAX_OUTAGE_EDGES"],
                "--output-dir",
                "{}/baseline_attack_full_deterministic".format(result_dir),
            ],
            cwd=RL_TESTING,
            env=env,
            dry_run=args.dry_run,
        )
        return

    if stage == "batch_plan":
        run_command(
            [
                sys.executable,
                "Run_TSG_IEEE8500_CriticalityBatchPlan.py",
                "--cases",
                env["CASES"],
                "--horizon",
                env["HORIZON"],
                "--seed",
                env["SEED"],
                "--branchflow-chunk-size",
                env["CHUNK_SIZE"],
                "--action-mask-chunk-size",
                env["CHUNK_SIZE"],
                "--output-root",
                "{}/full_criticality_batches".format(result_dir),
                "--merged-output-root",
                "{}/full_criticality_merged".format(result_dir),
            ],
            cwd=RL_TESTING,
            env=env,
            dry_run=args.dry_run,
        )
        return

    if stage == "action_mask_chunk":
        run_command(
            [
                sys.executable,
                "Run_TSG_IEEE8500_ActionMaskCriticality.py",
                "--controller",
                controller,
                "--cases",
                env["CASES"],
                "--seed",
                env["SEED"],
                "--target-scope",
                "switch_and_load",
                "--target-start-index",
                target_start,
                "--target-count",
                env["CHUNK_SIZE"],
                "--horizon",
                env["HORIZON"],
                "--include-noop",
                "--max-scenario-radius",
                env["TSG_IEEE8500_SCENARIO_RADIUS"],
                "--max-outage-edges",
                env["TSG_IEEE8500_MAX_OUTAGE_EDGES"],
                "--output-dir",
                "{}/full_criticality_batches/action_mask/chunk_{}".format(result_dir, target_start),
            ],
            cwd=RL_TESTING,
            env=env,
            dry_run=args.dry_run,
        )
        return

    if stage in {"branchflow_chunk", "voltage_chunk"}:
        family = "voltage" if stage == "voltage_chunk" else "branchflow"
        run_command(
            [
                sys.executable,
                "Run_TSG_IEEE8500_MeasurementCriticality.py",
                "--controller",
                controller,
                "--cases",
                env["CASES"],
                "--seed",
                env["SEED"],
                "--target-family",
                family,
                "--target-start-index",
                target_start,
                "--target-count",
                env["CHUNK_SIZE"],
                "--horizon",
                env["HORIZON"],
                "--include-noop",
                "--max-scenario-radius",
                env["TSG_IEEE8500_SCENARIO_RADIUS"],
                "--max-outage-edges",
                env["TSG_IEEE8500_MAX_OUTAGE_EDGES"],
                "--output-dir",
                "{}/full_criticality_batches/{}/chunk_{}".format(result_dir, family, target_start),
            ],
            cwd=RL_TESTING,
            env=env,
            dry_run=args.dry_run,
        )
        return

    if stage == "merge_action_mask":
        case_files = matched_case_files(
            RL_TESTING / result_dir / "full_criticality_batches" / "action_mask" / "chunk_*" / "tsg_ieee8500_action_mask_criticality_cases.csv",
            dry_run=args.dry_run,
        )
        run_command(
            [
                sys.executable,
                "Run_TSG_IEEE8500_ActionMaskCriticality.py",
                "--merge-case-files",
                *case_files,
                "--output-dir",
                "{}/full_criticality_merged/action_mask".format(result_dir),
            ],
            cwd=RL_TESTING,
            env=env,
            dry_run=args.dry_run,
        )
        return

    if stage in {"merge_branchflow", "merge_voltage"}:
        family = "voltage" if stage == "merge_voltage" else "branchflow"
        case_files = matched_case_files(
            RL_TESTING / result_dir / "full_criticality_batches" / family / "chunk_*" / "tsg_ieee8500_measurement_criticality_cases.csv",
            dry_run=args.dry_run,
        )
        run_command(
            [
                sys.executable,
                "Run_TSG_IEEE8500_MeasurementCriticality.py",
                "--merge-case-files",
                *case_files,
                "--output-dir",
                "{}/full_criticality_merged/{}".format(result_dir, family),
            ],
            cwd=RL_TESTING,
            env=env,
            dry_run=args.dry_run,
        )
        return

    if stage == "branchflow_diagnosis":
        run_command(
            [
                sys.executable,
                "Run_TSG_IEEE8500_BranchflowBaselineDiagnosis.py",
                "--controller",
                controller,
                "--baseline-case-summary",
                "{}/baseline_attack_full_deterministic/tsg_ieee8500_case_summary.csv".format(result_dir),
                "--output-dir",
                "{}/branchflow_baseline_diagnosis".format(result_dir),
                "--max-scenario-radius",
                env["TSG_IEEE8500_SCENARIO_RADIUS"],
                "--max-outage-edges",
                env["TSG_IEEE8500_MAX_OUTAGE_EDGES"],
            ],
            cwd=RL_TESTING,
            env=env,
            dry_run=args.dry_run,
        )
        return

    if stage == "branchflow_subset":
        run_command(
            [
                sys.executable,
                "Run_TSG_IEEE8500_BranchflowSubsetAblation.py",
                "--controller",
                controller,
                "--damaging-cases",
                "{}/branchflow_baseline_diagnosis/tsg_ieee8500_branchflow_baseline_damaging_cases.csv".format(result_dir),
                "--output-dir",
                "{}/branchflow_subset_ablation".format(result_dir),
                "--horizon",
                env["HORIZON"],
                "--max-scenario-radius",
                env["TSG_IEEE8500_SCENARIO_RADIUS"],
                "--max-outage-edges",
                env["TSG_IEEE8500_MAX_OUTAGE_EDGES"],
            ],
            cwd=RL_TESTING,
            env=env,
            dry_run=args.dry_run,
        )
        return

    if stage == "defense_summary":
        run_command(
            [
                sys.executable,
                "Run_TSG_IEEE8500_DefenseStressSummary.py",
                "--baseline-cases",
                "{}/baseline_attack_full_deterministic/tsg_ieee8500_case_summary.csv".format(result_dir),
                "--action-mask-cases",
                "{}/full_criticality_merged/action_mask/tsg_ieee8500_action_mask_criticality_cases.csv".format(result_dir),
                "--branchflow-single-cases",
                "{}/full_criticality_merged/branchflow/tsg_ieee8500_measurement_criticality_cases.csv".format(result_dir),
                "--branchflow-subset-cases",
                "{}/branchflow_subset_ablation/tsg_ieee8500_branchflow_subset_ablation_cases.csv".format(result_dir),
                "--output-dir",
                "{}/defense_stress_summary".format(result_dir),
            ],
            cwd=RL_TESTING,
            env=env,
            dry_run=args.dry_run,
        )
        return

    if stage == "advanced_mitigation":
        run_command(
            [
                sys.executable,
                "Run_TSG_IEEE8500_AdvancedMitigationAblation.py",
                "--controller",
                controller,
                "--low-recovery-cases",
                "{}/defense_stress_summary/tsg_ieee8500_defense_stress_low_recovery_cases.csv".format(result_dir),
                "--baseline-cases",
                "{}/baseline_attack_full_deterministic/tsg_ieee8500_case_summary.csv".format(result_dir),
                "--branchflow-subset-cases",
                "{}/branchflow_subset_ablation/tsg_ieee8500_branchflow_subset_ablation_cases.csv".format(result_dir),
                "--branchflow-single-cases",
                "{}/full_criticality_merged/branchflow/tsg_ieee8500_measurement_criticality_cases.csv".format(result_dir),
                "--action-mask-cases",
                "{}/full_criticality_merged/action_mask/tsg_ieee8500_action_mask_criticality_cases.csv".format(result_dir),
                "--output-dir",
                "{}/advanced_mitigation_ablation".format(result_dir),
                "--max-cases",
                env.get("MAX_CASES", "60"),
                "--horizon",
                env["HORIZON"],
            ],
            cwd=RL_TESTING,
            env=env,
            dry_run=args.dry_run,
        )
        return

    if stage == "paper_artifacts":
        run_command(
            [
                sys.executable,
                "Run_TSG_IEEE8500_PaperArtifacts.py",
                "--results-dir",
                result_dir,
                "--output-dir",
                "{}/paper_artifacts".format(result_dir),
            ],
            cwd=RL_TESTING,
            env=env,
            dry_run=args.dry_run,
        )
        return

    raise ValueError("Unknown IEEE8500 stage: {}".format(stage))


def run_driver(stage: str, args: argparse.Namespace, controller: str | None = None) -> None:
    env = base_env(args, controller=controller)
    if args.target_start is not None:
        env["TARGET_START"] = str(args.target_start)
    run_stage_command(stage, args, env)


def batch_manifest_path(controller: str) -> Path:
    return RL_TESTING / result_root(controller) / "full_criticality_batches" / "IEEE8500_full_criticality_batch_manifest.json"


def read_batch_counts(controller: str, dry_run: bool = False) -> tuple[int, int]:
    path = batch_manifest_path(controller)
    if not path.exists():
        if dry_run:
            print(
                "[dry-run] Batch manifest not found: {}. Using one placeholder chunk per family.".format(path),
                flush=True,
            )
            return 1, 1
        raise FileNotFoundError(
            "Batch manifest not found: {}. Run --stage batch_plan first.".format(path)
        )
    manifest = json.loads(path.read_text())
    return int(manifest.get("action_mask_chunk_count", 0)), int(manifest.get("branchflow_chunk_count", 0))


def slurm_header(args: argparse.Namespace, name: str, array_count: int | None = None, gpu: bool = False) -> list[str]:
    lines = [
        "#!/bin/bash",
        "#SBATCH --job-name={}".format(name),
        "#SBATCH --time={}".format(args.slurm_time),
        "#SBATCH --cpus-per-task={}".format(args.slurm_cpus),
        "#SBATCH --mem={}".format(args.slurm_mem),
        "#SBATCH --output=hpc_logs/{}_%A_%a.out".format(name) if array_count else "#SBATCH --output=hpc_logs/{}_%j.out".format(name),
        "#SBATCH --error=hpc_logs/{}_%A_%a.err".format(name) if array_count else "#SBATCH --error=hpc_logs/{}_%j.err".format(name),
    ]
    if array_count:
        lines.insert(2, "#SBATCH --array=0-{}".format(max(0, array_count - 1)))
    if gpu:
        lines.append("#SBATCH --gres=gpu:1")
    if args.partition:
        lines.append("#SBATCH --partition={}".format(args.partition))
    if args.account:
        lines.append("#SBATCH --account={}".format(args.account))
    return lines


def write_slurm(
    args: argparse.Namespace,
    name: str,
    stage: str,
    controller: str,
    array_count: int | None = None,
    gpu: bool = False,
    extra_env: dict[str, str] | None = None,
) -> Path:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    path = GENERATED_DIR / "{}.slurm".format(name)
    lines = slurm_header(args, name, array_count=array_count, gpu=gpu)
    lines.extend(
        [
            "",
            "set -euo pipefail",
            "module purge",
            "module load {}".format(args.python_module),
            'source "{}"/bin/activate'.format(args.venv)
            if args.venv
            else 'source "${VENV:?set VENV to your IEEE8500 Python environment}/bin/activate"',
            'cd "{}"'.format(NAPS_ROOT),
            "mkdir -p hpc_logs",
            'export CASES="{}"'.format(args.cases),
            'export HORIZON="{}"'.format(args.horizon),
            'export SEED="{}"'.format(args.seed),
            'export CHUNK_SIZE="{}"'.format(args.chunk_size),
            'export CONTROLLER="{}"'.format(norm_controller(controller)),
            'export TSG_IEEE8500_MAX_SWITCH_ACTIONS="{}"'.format(args.max_switch_actions),
            'export TSG_IEEE8500_MAX_LOAD_ACTIONS="{}"'.format(args.max_load_actions),
            'export TSG_IEEE8500_SCENARIO_RADIUS="{}"'.format(args.scenario_radius),
            'export TSG_IEEE8500_MAX_OUTAGE_EDGES="{}"'.format(args.max_outage_edges),
            'export TSG_IEEE8500_RESET_RADIUS="{}"'.format(args.scenario_radius),
            'export TSG_IEEE8500_RESET_MAX_OUTAGE_EDGES="{}"'.format(args.max_outage_edges),
        ]
    )
    if array_count:
        lines.append('export TARGET_START="${SLURM_ARRAY_TASK_ID}"')
    if args.no_cuda:
        lines.append('export NO_CUDA="1"')
    for key, value in sorted((extra_env or {}).items()):
        lines.append('export {}="{}"'.format(key, value))
    lines.extend(
        [
            "",
            "python RL_Testing/Run_TSG_IEEE8500_CompletePipeline.py "
            "--stage {} --controller {} --cases {} --horizon {} --seed {} --chunk-size {} "
            "--voltage-array-count {} --max-switch-actions {} --max-load-actions {} "
            "--scenario-radius {} --max-outage-edges {} --venv {} --python-module {}{}".format(
                shlex.quote(stage),
                shlex.quote(norm_controller(controller)),
                args.cases,
                args.horizon,
                args.seed,
                args.chunk_size,
                args.voltage_array_count,
                args.max_switch_actions,
                args.max_load_actions,
                args.scenario_radius,
                args.max_outage_edges,
                shlex.quote(str(args.venv)),
                shlex.quote(str(args.python_module)),
                " --no-cuda" if args.no_cuda else "",
            ),
        ]
    )
    path.write_text("\n".join(lines) + "\n")
    print("[write] {}".format(path), flush=True)
    return path


def submit(path: Path, dependency: str | None, args: argparse.Namespace) -> str | None:
    command = ["sbatch", "--parsable"]
    if dependency:
        command.append("--dependency=afterok:{}".format(dependency))
    command.append(str(path))
    printable = " ".join(shlex.quote(part) for part in command)
    print("[submit] {}".format(printable), flush=True)
    if args.dry_run or not args.submit:
        return None
    if shutil.which("sbatch") is None:
        raise RuntimeError("sbatch not found. Run on the HPC login node or use --dry-run.")
    result = subprocess.run(command, cwd=str(NAPS_ROOT), check=True, capture_output=True, text=True)
    job_id = result.stdout.strip().split(";", 1)[0]
    print("[job] {} -> {}".format(path.name, job_id), flush=True)
    return job_id


def submit_grl_pipeline(args: argparse.Namespace) -> None:
    controller = norm_controller(args.controller)
    print("[pipeline] preparing batch plan for {}".format(controller), flush=True)
    run_driver("batch_plan", args, controller=controller)
    action_count, branchflow_count = read_batch_counts(controller, dry_run=args.dry_run)
    print(
        "[pipeline] batch counts: action_mask={}, branchflow={}".format(action_count, branchflow_count),
        flush=True,
    )

    train_stage = "train_mlp" if controller == "MLP" else "train_grl"
    train = write_slurm(args, "ieee8500_{}_train".format(controller.lower()), train_stage, controller, gpu=not args.no_cuda)
    baseline = write_slurm(args, "ieee8500_{}_baseline".format(controller.lower()), "baseline_grl", controller)
    action = write_slurm(args, "ieee8500_{}_amask".format(controller.lower()), "action_mask_chunk", controller, array_count=action_count)
    branch = write_slurm(args, "ieee8500_{}_bflow".format(controller.lower()), "branchflow_chunk", controller, array_count=branchflow_count)
    voltage = None
    if args.voltage_array_count > 0:
        voltage = write_slurm(
            args,
            "ieee8500_{}_voltage".format(controller.lower()),
            "voltage_chunk",
            controller,
            array_count=args.voltage_array_count,
        )
    merge = write_slurm(args, "ieee8500_{}_merge".format(controller.lower()), "merge_all", controller)
    post = write_slurm(args, "ieee8500_{}_post".format(controller.lower()), "postprocess", controller)
    paper = write_slurm(args, "ieee8500_{}_paper".format(controller.lower()), "paper_artifacts", controller)

    train_id = submit(train, None, args)
    baseline_id = submit(baseline, train_id, args)
    action_id = submit(action, baseline_id, args)
    branch_id = submit(branch, baseline_id, args)
    voltage_id = submit(voltage, baseline_id, args) if voltage else None
    merge_dependency = ":".join(job for job in [action_id, branch_id, voltage_id] if job)
    merge_id = submit(merge, merge_dependency or None, args)
    post_id = submit(post, merge_id, args)
    submit(paper, post_id, args)


def submit_bpso_pipeline(args: argparse.Namespace) -> None:
    controller = "BPSO"
    print("[pipeline] preparing BPSO scoped action-mask pipeline", flush=True)
    run_driver("batch_plan", args, controller=controller)
    action_count, _branchflow_count = read_batch_counts(controller, dry_run=args.dry_run)
    baseline = write_slurm(args, "ieee8500_bpso_baseline", "baseline_bpso", controller)
    action = write_slurm(args, "ieee8500_bpso_amask", "action_mask_chunk", controller, array_count=action_count)
    merge = write_slurm(args, "ieee8500_bpso_merge_amask", "merge_action_mask", controller)
    paper = write_slurm(args, "ieee8500_bpso_paper", "paper_artifacts", controller)

    baseline_id = submit(baseline, None, args)
    action_id = submit(action, baseline_id, args)
    merge_id = submit(merge, action_id, args)
    submit(paper, merge_id, args)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="IEEE 8500 complete HPC pipeline orchestrator.")
    parser.add_argument(
        "--stage",
        default="full_submit",
        choices=sorted(DIRECT_STAGES | {"full_submit", "merge_all", "postprocess"}),
        help="Stage to run. full_submit writes/submits dependent Slurm jobs.",
    )
    parser.add_argument("--controller", type=norm_controller, default="GRL")
    parser.add_argument("--include-bpso", action="store_true", help="Also write/submit the scoped BPSO action-mask pipeline.")
    parser.add_argument("--submit", action="store_true", help="Actually call sbatch. Without this, Slurm files are written only.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing them.")
    parser.add_argument("--cases", type=int, default=30)
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--seed", type=int, default=20260615)
    parser.add_argument("--chunk-size", type=int, default=1)
    parser.add_argument("--target-start", type=int, default=None)
    parser.add_argument(
        "--voltage-array-count",
        type=int,
        default=int(os.environ.get("VOLTAGE_ARRAY_COUNT", "0")),
        help="Optional number of voltage chunks to submit/merge. Set this when voltage criticality is required.",
    )
    parser.add_argument("--max-switch-actions", type=int, default=0)
    parser.add_argument("--max-load-actions", type=int, default=40)
    parser.add_argument("--scenario-radius", type=int, default=4)
    parser.add_argument("--max-outage-edges", type=int, default=25)
    parser.add_argument("--venv", default=os.environ.get("VENV", ""))
    parser.add_argument("--python-module", default=os.environ.get("PYTHON_MODULE", "python/3.10"))
    parser.add_argument("--partition", default=os.environ.get("SLURM_PARTITION", ""))
    parser.add_argument("--account", default=os.environ.get("SLURM_ACCOUNT", ""))
    parser.add_argument("--slurm-time", default="24:00:00")
    parser.add_argument("--slurm-cpus", default="8")
    parser.add_argument("--slurm-mem", default="64G")
    parser.add_argument("--no-cuda", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.stage == "full_submit":
        if norm_controller(args.controller) == "BPSO":
            submit_bpso_pipeline(args)
        else:
            submit_grl_pipeline(args)
            if args.include_bpso:
                submit_bpso_pipeline(args)
        return
    if args.stage == "merge_all":
        run_driver("merge_action_mask", args, controller=args.controller)
        run_driver("merge_branchflow", args, controller=args.controller)
        if args.voltage_array_count > 0:
            run_driver("merge_voltage", args, controller=args.controller)
        return
    if args.stage == "postprocess":
        run_driver("branchflow_diagnosis", args, controller=args.controller)
        run_driver("branchflow_subset", args, controller=args.controller)
        run_driver("defense_summary", args, controller=args.controller)
        run_driver("advanced_mitigation", args, controller=args.controller)
        return
    run_driver(args.stage, args, controller=args.controller)


if __name__ == "__main__":
    main()
