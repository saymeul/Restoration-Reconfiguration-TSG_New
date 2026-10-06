#!/bin/bash
#SBATCH --job-name=ieee8500_bflow
#SBATCH --array=0-999
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --output=hpc_logs/ieee8500_bflow_%A_%a.out
#SBATCH --error=hpc_logs/ieee8500_bflow_%A_%a.err

set -euo pipefail

module purge
module load python/3.10
source "${VENV:?set VENV to your IEEE8500 Python environment}/bin/activate"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAPS_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${NAPS_ROOT}"
mkdir -p hpc_logs
export CASES="${CASES:-30}"
export HORIZON="${HORIZON:-24}"
export CHUNK_SIZE="${CHUNK_SIZE:-1}"
export TARGET_START="${SLURM_ARRAY_TASK_ID}"
python RL_Testing/Run_TSG_IEEE8500_CompletePipeline.py --stage branchflow_chunk --controller GRL --cases "$CASES" --horizon "$HORIZON" --chunk-size "$CHUNK_SIZE" --target-start "$TARGET_START" --venv "$VENV"
