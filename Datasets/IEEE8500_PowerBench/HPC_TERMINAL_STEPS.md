# IEEE 8500 Complete Study HPC Terminal Runbook

This runbook is for your real goal: extend the IEEE 34-bus and IEEE 123-bus TSG restoration/FDIA study to the IEEE 8500-node feeder so all three systems can be compared.

PowerBench is used as the IEEE 8500 feeder/data source. The final goal is not only to run PowerBench detection examples. The final goal is to make IEEE 8500 a first-class case in your own pipeline:

- OpenDSS feeder import.
- Restoration outage cases.
- GRL controller training and frozen evaluation.
- MLP companion evidence if needed.
- BPSO scoped action-mask/status comparison if needed.
- Baseline FDIA attack-family study.
- Action-mask/status criticality.
- Voltage and branch-flow measurement criticality.
- Mitigation and advanced defense ablations.
- Paper-facing artifacts comparable with IEEE 34 and IEEE 123.

Status right now:

- IEEE 8500 PowerBench files are staged in `Datasets/IEEE8500_PowerBench`.
- Existing training code currently supports 13, 34, and 123, not 8500 yet.
- The terminal commands for staging, HPC upload, environment setup, and feeder compile tests are ready now.
- The full GRL/MLP/BPSO restoration-FDIA commands are the exact target workflow, but they must be run only after IEEE 8500 code integration is added.

## 0. Path Variables

Use these names throughout the HPC session.

Local Windows PowerShell:

```powershell
$LOCAL_REPO = "C:\Users\ISLAS2\OneDrive - Idaho National Laboratory\Desktop\TSG_Real-Time-Outage-Management-Active-DNR-GRL-v.1.0"
```

HPC bash:

```bash
export WORK=/scratch/$USER/tsg_ieee8500
export REPO_ROOT="$WORK/TSG_Real-Time-Outage-Management-Active-DNR-GRL-v.1.0"
export NAPS_ROOT="$REPO_ROOT/NAPS_adamslab-ub-Real-Time-Outage-Management-Active-DNR-GRL-b715982"
export IEEE8500_DATA="$REPO_ROOT/Datasets/IEEE8500_PowerBench"
export VENV="$WORK/.venv_ieee8500"
```

Change `/scratch/$USER/tsg_ieee8500` if your HPC project directory is different.

## 1. READY NOW: Package Local Files for HPC

Run in VS Code PowerShell.

```powershell
cd $LOCAL_REPO

Test-Path "Datasets\IEEE8500_PowerBench\source\PowerBench\Datasets\State Estimation\8500 Node\Master.dss"
Test-Path "Datasets\IEEE8500_PowerBench\powerbench_ieee8500_import_manifest.csv"
Test-Path "NAPS_adamslab-ub-Real-Time-Outage-Management-Active-DNR-GRL-b715982\RL_Training\train.py"
Test-Path "NAPS_adamslab-ub-Real-Time-Outage-Management-Active-DNR-GRL-b715982\RL_Testing\Run_TSG_IEEE123_BaselineAttackStudy.py"

$include = @(
  "Datasets\IEEE8500_PowerBench",
  "NAPS_adamslab-ub-Real-Time-Outage-Management-Active-DNR-GRL-b715982"
)

Compress-Archive -Path $include -DestinationPath ".\tsg_ieee8500_hpc_package.zip" -Force
Get-Item ".\tsg_ieee8500_hpc_package.zip"
```

All `Test-Path` commands should return `True`.

## 2. READY NOW: Upload to HPC

Run in VS Code PowerShell. Replace the placeholders.

```powershell
$HPC_USER = "<your_hpc_username>"
$HPC_HOST = "<hpc_login_host>"
$HPC_DIR = "/scratch/$HPC_USER/tsg_ieee8500"

ssh "$HPC_USER@$HPC_HOST" "mkdir -p $HPC_DIR"
scp ".\tsg_ieee8500_hpc_package.zip" "$HPC_USER@$HPC_HOST:$HPC_DIR/"
```

## 3. READY NOW: Unpack on HPC

Run after SSH into HPC.

```bash
ssh <your_hpc_username>@<hpc_login_host>

export WORK=/scratch/$USER/tsg_ieee8500
cd "$WORK"

rm -rf TSG_Real-Time-Outage-Management-Active-DNR-GRL-v.1.0
mkdir -p TSG_Real-Time-Outage-Management-Active-DNR-GRL-v.1.0
unzip -o tsg_ieee8500_hpc_package.zip -d TSG_Real-Time-Outage-Management-Active-DNR-GRL-v.1.0

export REPO_ROOT="$WORK/TSG_Real-Time-Outage-Management-Active-DNR-GRL-v.1.0"
export NAPS_ROOT="$REPO_ROOT/NAPS_adamslab-ub-Real-Time-Outage-Management-Active-DNR-GRL-b715982"
export IEEE8500_DATA="$REPO_ROOT/Datasets/IEEE8500_PowerBench"
export VENV="$WORK/.venv_ieee8500"

test -f "$IEEE8500_DATA/source/PowerBench/Datasets/State Estimation/8500 Node/Master.dss"
test -f "$NAPS_ROOT/RL_Training/train.py"
test -f "$NAPS_ROOT/RL_Testing/Run_TSG_IEEE123_BaselineAttackStudy.py"
```

If `test -f` returns silently, the files exist.

## 4. READY NOW: Create Python Environment

Use your cluster's Python module name if different.

```bash
module purge
module avail python
module load python/3.10

cd "$WORK"
python -m venv "$VENV"
source "$VENV/bin/activate"

python -m pip install --upgrade pip setuptools wheel
python -m pip install opendssdirect.py numpy pandas scipy networkx matplotlib openpyxl
python -m pip install stable-baselines3 gymnasium tensorboard
```

For GPU training, install PyTorch using the CUDA command recommended by the HPC. CPU-only fallback:

```bash
python -m pip install torch
```

## 5. READY NOW: Compile-Smoke-Test IEEE 8500 OpenDSS

This confirms the imported PowerBench IEEE 8500 feeder compiles on HPC.

```bash
source "$VENV/bin/activate"
cd "$IEEE8500_DATA"

python - <<'PY'
import os
import opendssdirect as dss

master = os.path.abspath("source/PowerBench/Datasets/State Estimation/8500 Node/Master.dss")
print("Compiling:", master)
dss.Basic.ClearAll()
dss.Text.Command(f"compile [{master}]")

print("Circuit:", dss.Circuit.Name())
print("Buses:", len(dss.Circuit.AllBusNames()))
print("Lines:", len(dss.Lines.AllNames()))
print("Loads:", len(dss.Loads.AllNames()))
print("PDElements:", len(dss.PDElements.AllNames()))
print("IEEE 8500 feeder compile smoke test complete")
PY
```

Do not launch full IEEE 8500 jobs until this passes.

## 6. READY NOW: Confirm Current Integration Gap

This shows why IEEE 8500 code integration is still needed.

```bash
cd "$NAPS_ROOT"

rg -n "choices=\[13, 34, 123\]|env_size == 13|env_size == 34|env_size == 123" RL_Training
rg -n "Run_TSG_IEEE123|tsg_ieee123|123bus" RL_Testing | head -n 40
rg -n "8500|IEEE8500|tsg_ieee8500|DSSdirect_8500" RL_Training RL_Testing || true
```

Interpretation:

- If the first two commands find 13/34/123 references and the last command finds little or nothing, IEEE 8500 is not fully integrated yet.
- After integration, the last command should find IEEE 8500 environment files, result scripts, and config entries.

## 7. REQUIRED BEFORE COMPLETE RUN: IEEE 8500 Code Integration

Create/adapt these components so IEEE 8500 follows the same concept as IEEE 34 and IEEE 123.

```text
RL_Training/Environments/DSSdirect_8500bus_loadandswitching/
RL_Testing/8500bus/
RL_Testing/Run_TSG_IEEE8500_BaselineAttackStudy.py
RL_Testing/Run_TSG_IEEE8500_ActionMaskCriticality.py
RL_Testing/Run_TSG_IEEE8500_MeasurementCriticality.py
RL_Testing/Run_TSG_IEEE8500_AdvancedMitigationAblation.py
RL_Testing/Run_TSG_IEEE8500_CriticalityBatchPlan.py
RL_Testing/Run_TSG_IEEE8500_PaperArtifacts.py
RL_Testing/paper_results/tsg_ieee8500/
```

Update these existing files or their IEEE 8500 equivalents:

```text
RL_Training/Configs/training_config.py
RL_Training/train.py
RL_Testing/TSG_ControllerConfig.py
RL_Testing/FDIA_ExperimentCore.py
RL_Testing/FDIA_Common.py
RL_Testing/FDIA_DetectorSuite.py
```

IEEE 8500 must expose the same study surface as IEEE 34/123:

```text
Observation channels:
  bus voltage
  branch flow
  topology/status
  restored energy/load
  action mask

Action space:
  controllable switches
  controllable load restoration actions
  optional DER/PV/EVCS actions only if included in scope

Scenario support:
  deterministic outage seeds
  outage edge lists
  clean trajectory
  attacked trajectory
  mitigated trajectory

Result fields:
  clean restored energy
  attacked restored energy
  mitigated restored energy
  physical degradation
  detection rate
  mitigation recovery
  action changes
  target observation ID
```

## 8. AFTER INTEGRATION: Verify New IEEE 8500 Code

Run before submitting big jobs.

```bash
cd "$NAPS_ROOT"
source "$VENV/bin/activate"

rg -n "8500|IEEE8500|tsg_ieee8500|DSSdirect_8500" RL_Training RL_Testing

python -m py_compile \
  RL_Training/train.py \
  RL_Training/Configs/training_config.py \
  RL_Testing/Run_TSG_IEEE8500_BaselineAttackStudy.py \
  RL_Testing/Run_TSG_IEEE8500_ActionMaskCriticality.py \
  RL_Testing/Run_TSG_IEEE8500_MeasurementCriticality.py \
  RL_Testing/Run_TSG_IEEE8500_AdvancedMitigationAblation.py \
  RL_Testing/Run_TSG_IEEE8500_PaperArtifacts.py
```

Tiny smoke tests:

```bash
cd "$NAPS_ROOT/RL_Testing"

python Run_TSG_IEEE8500_BaselineAttackStudy.py \
  --cases 1 \
  --attacks clean voltage_masking branchflow_hiding energy_inflation topology_drop action_mask_false_unavailable \
  --horizon 2 \
  --output-dir paper_results/tsg_ieee8500/smoke_baseline

python Run_TSG_IEEE8500_ActionMaskCriticality.py \
  --cases 1 \
  --target-count 1 \
  --horizon 2 \
  --output-dir paper_results/tsg_ieee8500/smoke_action_mask

python Run_TSG_IEEE8500_MeasurementCriticality.py \
  --cases 1 \
  --target-family branchflow \
  --target-count 1 \
  --horizon 2 \
  --output-dir paper_results/tsg_ieee8500/smoke_branchflow
```

Continue only when the smoke tests write valid CSV and JSON manifest files.

## 9. AFTER INTEGRATION: Train IEEE 8500 GRL

```bash
cd "$NAPS_ROOT"
mkdir -p hpc_logs

cat > submit_ieee8500_train_grl.slurm <<'EOF'
#!/bin/bash
#SBATCH --job-name=ieee8500_grl_train
#SBATCH --time=72:00:00
#SBATCH --cpus-per-task=16
#SBATCH --mem=96G
#SBATCH --gres=gpu:1
#SBATCH --output=hpc_logs/ieee8500_grl_train_%j.out
#SBATCH --error=hpc_logs/ieee8500_grl_train_%j.err

set -euo pipefail

module purge
module load python/3.10
source "$VENV/bin/activate"

cd "$NAPS_ROOT/RL_Training"
mkdir -p Trained_Models/IEEE8500 Tensorboard_logger

python train.py \
  --env_size 8500 \
  --node_encoder GCAPS \
  --num_cpu 16 \
  --total_steps 2000000 \
  --n_steps 50000 \
  --batch_size 2000 \
  --model_save Trained_Models/IEEE8500/
EOF

sbatch submit_ieee8500_train_grl.slurm
squeue -u "$USER"
```

If no GPU is available, remove `#SBATCH --gres=gpu:1` and add `--no_cuda` to the `python train.py` command.

## 10. AFTER INTEGRATION: Train IEEE 8500 MLP Companion

Use only if you need MLP companion evidence.

```bash
cd "$NAPS_ROOT"
mkdir -p hpc_logs

cat > submit_ieee8500_train_mlp.slurm <<'EOF'
#!/bin/bash
#SBATCH --job-name=ieee8500_mlp_train
#SBATCH --time=72:00:00
#SBATCH --cpus-per-task=16
#SBATCH --mem=96G
#SBATCH --gres=gpu:1
#SBATCH --output=hpc_logs/ieee8500_mlp_train_%j.out
#SBATCH --error=hpc_logs/ieee8500_mlp_train_%j.err

set -euo pipefail

module purge
module load python/3.10
source "$VENV/bin/activate"

cd "$NAPS_ROOT/RL_Training"
mkdir -p Trained_Models/IEEE8500_MLP Tensorboard_logger

python train.py \
  --env_size 8500 \
  --node_encoder MLP \
  --num_cpu 16 \
  --total_steps 2000000 \
  --n_steps 50000 \
  --batch_size 2000 \
  --model_save Trained_Models/IEEE8500_MLP/
EOF

sbatch submit_ieee8500_train_mlp.slurm
squeue -u "$USER"
```

## 11. AFTER INTEGRATION: Baseline Attack-Family Study

```bash
cd "$NAPS_ROOT"
mkdir -p hpc_logs

cat > submit_ieee8500_baseline_grl.slurm <<'EOF'
#!/bin/bash
#SBATCH --job-name=ieee8500_base_grl
#SBATCH --time=24:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --output=hpc_logs/ieee8500_base_grl_%j.out
#SBATCH --error=hpc_logs/ieee8500_base_grl_%j.err

set -euo pipefail

module purge
module load python/3.10
source "$VENV/bin/activate"

cd "$NAPS_ROOT/RL_Testing"

python Run_TSG_IEEE8500_BaselineAttackStudy.py \
  --cases 30 \
  --seed 20260615 \
  --attacks topology_drop action_mask_false_unavailable voltage_masking branchflow_hiding energy_inflation \
  --horizon 24 \
  --step-hours 1.0 \
  --output-dir paper_results/tsg_ieee8500/baseline_attack_full_deterministic
EOF

sbatch submit_ieee8500_baseline_grl.slurm
squeue -u "$USER"
```

## 12. AFTER INTEGRATION: Action-Mask Criticality

Create a batch plan first if the IEEE 8500 runner supports it.

```bash
cd "$NAPS_ROOT/RL_Testing"
source "$VENV/bin/activate"

python Run_TSG_IEEE8500_CriticalityBatchPlan.py \
  --cases 30 \
  --horizon 24 \
  --seed 20260615 \
  --action-mask-chunk-size 1 \
  --output-dir paper_results/tsg_ieee8500/action_mask_criticality_batches
```

Submit chunks. Adjust `--array=0-999` to match the generated plan.

```bash
cd "$NAPS_ROOT"
mkdir -p hpc_logs

cat > submit_ieee8500_action_mask_chunks.slurm <<'EOF'
#!/bin/bash
#SBATCH --job-name=ieee8500_amask
#SBATCH --array=0-999
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --output=hpc_logs/ieee8500_amask_%A_%a.out
#SBATCH --error=hpc_logs/ieee8500_amask_%A_%a.err

set -euo pipefail

module purge
module load python/3.10
source "$VENV/bin/activate"

cd "$NAPS_ROOT/RL_Testing"

python Run_TSG_IEEE8500_ActionMaskCriticality.py \
  --cases 30 \
  --seed 20260615 \
  --target-start-index "$SLURM_ARRAY_TASK_ID" \
  --target-count 1 \
  --horizon 24 \
  --output-dir "paper_results/tsg_ieee8500/action_mask_criticality_batches/chunk_${SLURM_ARRAY_TASK_ID}"
EOF

sbatch submit_ieee8500_action_mask_chunks.slurm
squeue -u "$USER"
```

Merge after completion:

```bash
cd "$NAPS_ROOT/RL_Testing"
source "$VENV/bin/activate"

python Run_TSG_IEEE8500_ActionMaskCriticality.py \
  --merge-case-files paper_results/tsg_ieee8500/action_mask_criticality_batches/chunk_*/tsg_ieee8500_action_mask_criticality_cases.csv \
  --output-dir paper_results/tsg_ieee8500/full_criticality_merged/action_mask
```

## 13. AFTER INTEGRATION: Measurement Criticality

Branch-flow chunks:

```bash
cd "$NAPS_ROOT"
mkdir -p hpc_logs

cat > submit_ieee8500_branchflow_chunks.slurm <<'EOF'
#!/bin/bash
#SBATCH --job-name=ieee8500_bflow
#SBATCH --array=0-999
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --output=hpc_logs/ieee8500_bflow_%A_%a.out
#SBATCH --error=hpc_logs/ieee8500_bflow_%A_%a.err

set -euo pipefail

module purge
module load python/3.10
source "$VENV/bin/activate"

cd "$NAPS_ROOT/RL_Testing"

python Run_TSG_IEEE8500_MeasurementCriticality.py \
  --cases 30 \
  --seed 20260615 \
  --target-family branchflow \
  --target-start-index "$SLURM_ARRAY_TASK_ID" \
  --target-count 1 \
  --horizon 24 \
  --output-dir "paper_results/tsg_ieee8500/branchflow_criticality_batches/chunk_${SLURM_ARRAY_TASK_ID}"
EOF

sbatch submit_ieee8500_branchflow_chunks.slurm
squeue -u "$USER"
```

Voltage chunks:

```bash
cd "$NAPS_ROOT"
mkdir -p hpc_logs

cat > submit_ieee8500_voltage_chunks.slurm <<'EOF'
#!/bin/bash
#SBATCH --job-name=ieee8500_voltage
#SBATCH --array=0-999
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --output=hpc_logs/ieee8500_voltage_%A_%a.out
#SBATCH --error=hpc_logs/ieee8500_voltage_%A_%a.err

set -euo pipefail

module purge
module load python/3.10
source "$VENV/bin/activate"

cd "$NAPS_ROOT/RL_Testing"

python Run_TSG_IEEE8500_MeasurementCriticality.py \
  --cases 30 \
  --seed 20260615 \
  --target-family voltage \
  --target-start-index "$SLURM_ARRAY_TASK_ID" \
  --target-count 1 \
  --horizon 24 \
  --output-dir "paper_results/tsg_ieee8500/voltage_criticality_batches/chunk_${SLURM_ARRAY_TASK_ID}"
EOF

sbatch submit_ieee8500_voltage_chunks.slurm
squeue -u "$USER"
```

Merge after completion:

```bash
cd "$NAPS_ROOT/RL_Testing"
source "$VENV/bin/activate"

python Run_TSG_IEEE8500_MeasurementCriticality.py \
  --merge-case-files paper_results/tsg_ieee8500/branchflow_criticality_batches/chunk_*/tsg_ieee8500_measurement_criticality_cases.csv \
  --output-dir paper_results/tsg_ieee8500/full_criticality_merged/branchflow

python Run_TSG_IEEE8500_MeasurementCriticality.py \
  --merge-case-files paper_results/tsg_ieee8500/voltage_criticality_batches/chunk_*/tsg_ieee8500_measurement_criticality_cases.csv \
  --output-dir paper_results/tsg_ieee8500/full_criticality_merged/voltage
```

## 14. AFTER INTEGRATION: Advanced Mitigation Ablation

```bash
cd "$NAPS_ROOT"
mkdir -p hpc_logs

cat > submit_ieee8500_advanced_mitigation.slurm <<'EOF'
#!/bin/bash
#SBATCH --job-name=ieee8500_advmit
#SBATCH --time=24:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --output=hpc_logs/ieee8500_advmit_%j.out
#SBATCH --error=hpc_logs/ieee8500_advmit_%j.err

set -euo pipefail

module purge
module load python/3.10
source "$VENV/bin/activate"

cd "$NAPS_ROOT/RL_Testing"

python Run_TSG_IEEE8500_AdvancedMitigationAblation.py \
  --source-case-file paper_results/tsg_ieee8500/full_criticality_merged/action_mask/tsg_ieee8500_action_mask_criticality_cases.csv \
  --max-cases 60 \
  --horizon 24 \
  --output-dir paper_results/tsg_ieee8500/advanced_mitigation_ablation
EOF

sbatch submit_ieee8500_advanced_mitigation.slurm
squeue -u "$USER"
```

## 15. AFTER INTEGRATION: BPSO Scoped Comparison

BPSO does not need neural training, but IEEE 8500 needs a BPSO action-mask mapping, feasible action set, and objective scoring first.

```bash
cd "$NAPS_ROOT"
mkdir -p hpc_logs

cat > submit_ieee8500_bpso_action_mask.slurm <<'EOF'
#!/bin/bash
#SBATCH --job-name=ieee8500_bpso_am
#SBATCH --time=24:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --output=hpc_logs/ieee8500_bpso_am_%j.out
#SBATCH --error=hpc_logs/ieee8500_bpso_am_%j.err

set -euo pipefail

module purge
module load python/3.10
source "$VENV/bin/activate"

cd "$NAPS_ROOT/RL_Testing"

python Run_TSG_IEEE8500_BPSO_ActionMaskCriticality.py \
  --cases 30 \
  --seed 20260615 \
  --horizon 24 \
  --output-dir paper_results/tsg_ieee8500_bpso/action_mask_criticality
EOF

sbatch submit_ieee8500_bpso_action_mask.slurm
squeue -u "$USER"
```

Keep the same scope language as IEEE 123 BPSO: action-mask/status FDIA is directly comparable; voltage, branch-flow, topology, and energy-channel claims require a richer perceived-objective BPSO model.

## 16. AFTER INTEGRATION: Paper Artifacts

```bash
cd "$NAPS_ROOT/RL_Testing"
source "$VENV/bin/activate"

python Run_TSG_IEEE8500_PaperArtifacts.py \
  --input-root paper_results/tsg_ieee8500 \
  --output-root paper_results/tsg_ieee8500/paper_artifacts
```

If MLP and BPSO companion packages are included:

```bash
python Run_TSG_IEEE8500_PaperArtifacts.py \
  --input-root paper_results/tsg_ieee8500_mlp \
  --output-root paper_results/tsg_ieee8500_mlp/paper_artifacts

python Run_TSG_IEEE8500_PaperArtifacts.py \
  --input-root paper_results/tsg_ieee8500_bpso \
  --output-root paper_results/tsg_ieee8500_bpso/paper_artifacts
```

## 17. READY NOW: Optional PowerBench Supporting Jobs

These are not the final TSG restoration/FDIA study. They are only supporting data-generation checks from the imported PowerBench source.

Sensor attack data:

```bash
cd "$IEEE8500_DATA"
mkdir -p logs

cat > submit_powerbench_ieee8500_sensor.slurm <<'EOF'
#!/bin/bash
#SBATCH --job-name=pb8500_sensor
#SBATCH --array=0-3
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --output=logs/pb8500_sensor_%A_%a.out
#SBATCH --error=logs/pb8500_sensor_%A_%a.err

set -euo pipefail

module purge
module load python/3.10
source "$VENV/bin/activate"

cd "$IEEE8500_DATA/source/PowerBench/Datasets/Cyber Attack Detection/Sensor Attacks/8500-Node"
python DataGeneration_Multi.py
EOF

sbatch submit_powerbench_ieee8500_sensor.slurm
squeue -u "$USER"
```

PV attack data:

```bash
cd "$IEEE8500_DATA"
mkdir -p logs

cat > submit_powerbench_ieee8500_pv.slurm <<'EOF'
#!/bin/bash
#SBATCH --job-name=pb8500_pv
#SBATCH --array=0-3
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --output=logs/pb8500_pv_%A_%a.out
#SBATCH --error=logs/pb8500_pv_%A_%a.err

set -euo pipefail

module purge
module load python/3.10
source "$VENV/bin/activate"

cd "$IEEE8500_DATA/source/PowerBench/Datasets/Cyber Attack Detection/PV Attacks/8500-Node"
python DataGeneration_Multi.py
EOF

sbatch submit_powerbench_ieee8500_pv.slurm
squeue -u "$USER"
```

EVCS attack data:

```bash
cd "$IEEE8500_DATA"
mkdir -p logs

cat > submit_powerbench_ieee8500_evcs.slurm <<'EOF'
#!/bin/bash
#SBATCH --job-name=pb8500_evcs
#SBATCH --array=0-3
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --output=logs/pb8500_evcs_%A_%a.out
#SBATCH --error=logs/pb8500_evcs_%A_%a.err

set -euo pipefail

module purge
module load python/3.10
source "$VENV/bin/activate"

cd "$IEEE8500_DATA/source/PowerBench/Datasets/Cyber Attack Detection/EVCS Attacks/8500-bus"
python DataGeneration_Multi.py
EOF

sbatch submit_powerbench_ieee8500_evcs.slurm
squeue -u "$USER"
```

Line-failure data:

```bash
cd "$IEEE8500_DATA"
mkdir -p logs

cat > submit_powerbench_ieee8500_line_failure.slurm <<'EOF'
#!/bin/bash
#SBATCH --job-name=pb8500_linefail
#SBATCH --time=24:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --output=logs/pb8500_linefail_%j.out
#SBATCH --error=logs/pb8500_linefail_%j.err

set -euo pipefail

module purge
module load python/3.10
source "$VENV/bin/activate"

cd "$IEEE8500_DATA/source/PowerBench/Datasets/Line Failure Detection/8500-bus"
python DataGeneration.py
python PostProcess.py
EOF

sbatch submit_powerbench_ieee8500_line_failure.slurm
squeue -u "$USER"
```

## 18. Monitor Jobs and Inspect Results

```bash
squeue -u "$USER"

cd "$NAPS_ROOT"
ls hpc_logs 2>/dev/null || true
tail -n 80 hpc_logs/<log_file_name>.out
tail -n 80 hpc_logs/<log_file_name>.err

cd "$NAPS_ROOT/RL_Testing"
find paper_results -maxdepth 3 -type f -name "*.csv" | sort | head -n 40
find paper_results -maxdepth 3 -type f -name "*.json" | sort | head -n 40
```

PowerBench supporting outputs:

```bash
cd "$IEEE8500_DATA"
find source/PowerBench/Datasets -type d -name results
find source/PowerBench/Datasets -type f -name "*.csv" | head
find source/PowerBench/Datasets -type f -name "*.pkl" | head
```

## 19. Copy Results Back to Windows

Run from local VS Code PowerShell.

```powershell
cd $LOCAL_REPO

$HPC_USER = "<your_hpc_username>"
$HPC_HOST = "<hpc_login_host>"
$HPC_DIR = "/scratch/$HPC_USER/tsg_ieee8500"

mkdir ".\hpc_results_ieee8500" -Force
scp -r "$HPC_USER@$HPC_HOST:$HPC_DIR/TSG_Real-Time-Outage-Management-Active-DNR-GRL-v.1.0/NAPS_adamslab-ub-Real-Time-Outage-Management-Active-DNR-GRL-b715982/RL_Testing/paper_results/tsg_ieee8500*" ".\hpc_results_ieee8500\"
scp -r "$HPC_USER@$HPC_HOST:$HPC_DIR/TSG_Real-Time-Outage-Management-Active-DNR-GRL-v.1.0/NAPS_adamslab-ub-Real-Time-Outage-Management-Active-DNR-GRL-b715982/hpc_logs" ".\hpc_results_ieee8500\"
```

## 20. Completion Criteria

The IEEE 8500 comparison package is complete when these exist:

```text
paper_results/tsg_ieee8500/baseline_attack_full_deterministic/
paper_results/tsg_ieee8500/full_criticality_merged/action_mask/
paper_results/tsg_ieee8500/full_criticality_merged/branchflow/
paper_results/tsg_ieee8500/full_criticality_merged/voltage/
paper_results/tsg_ieee8500/advanced_mitigation_ablation/
paper_results/tsg_ieee8500/paper_artifacts/
```

If included:

```text
paper_results/tsg_ieee8500_mlp/
paper_results/tsg_ieee8500_bpso/
```

At that point, IEEE 8500 can be compared directly with IEEE 34 and IEEE 123 in the manuscript.