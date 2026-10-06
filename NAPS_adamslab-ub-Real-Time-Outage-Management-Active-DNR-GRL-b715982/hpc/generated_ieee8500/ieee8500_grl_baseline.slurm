#!/bin/bash
#SBATCH --job-name=ieee8500_grl_baseline
#SBATCH --time=24:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --output=hpc_logs/ieee8500_grl_baseline_%j.out
#SBATCH --error=hpc_logs/ieee8500_grl_baseline_%j.err

set -euo pipefail
module purge
module load python/3.10
source "${VENV:?set VENV to your IEEE8500 Python environment}/bin/activate"
cd "C:\Users\ISLAS2\OneDrive - Idaho National Laboratory\Desktop\TSG_Real-Time-Outage-Management-Active-DNR-GRL-v.1.0\NAPS_adamslab-ub-Real-Time-Outage-Management-Active-DNR-GRL-b715982"
mkdir -p hpc_logs
export CASES="30"
export HORIZON="24"
export SEED="20260615"
export CHUNK_SIZE="1"
export CONTROLLER="GRL"
export TSG_IEEE8500_MAX_SWITCH_ACTIONS="0"
export TSG_IEEE8500_MAX_LOAD_ACTIONS="40"
export TSG_IEEE8500_SCENARIO_RADIUS="4"
export TSG_IEEE8500_MAX_OUTAGE_EDGES="25"
export TSG_IEEE8500_RESET_RADIUS="4"
export TSG_IEEE8500_RESET_MAX_OUTAGE_EDGES="25"

python RL_Testing/Run_TSG_IEEE8500_CompletePipeline.py --stage baseline_grl --controller GRL --cases 30 --horizon 24 --seed 20260615 --chunk-size 1 --voltage-array-count 0 --max-switch-actions 0 --max-load-actions 40 --scenario-radius 4 --max-outage-edges 25 --venv '' --python-module python/3.10
