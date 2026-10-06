#!/bin/bash
#SBATCH --job-name=ieee8500_grl_train
#SBATCH --time=72:00:00
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --gres=gpu:1
#SBATCH --output=hpc_logs/ieee8500_grl_train_%j.out
#SBATCH --error=hpc_logs/ieee8500_grl_train_%j.err

set -euo pipefail

module purge
module load python/3.10
source "${VENV:?set VENV to your IEEE8500 Python environment}/bin/activate"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAPS_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${NAPS_ROOT}"
mkdir -p hpc_logs
export NUM_CPU="${SLURM_CPUS_PER_TASK:-16}"
python RL_Testing/Run_TSG_IEEE8500_CompletePipeline.py --stage train_grl --controller GRL --venv "$VENV"
