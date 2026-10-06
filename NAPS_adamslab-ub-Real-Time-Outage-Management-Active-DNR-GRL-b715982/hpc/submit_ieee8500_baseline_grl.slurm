#!/bin/bash
#SBATCH --job-name=ieee8500_base_grl
#SBATCH --time=24:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --output=hpc_logs/ieee8500_base_grl_%j.out
#SBATCH --error=hpc_logs/ieee8500_base_grl_%j.err

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
python RL_Testing/Run_TSG_IEEE8500_CompletePipeline.py --stage baseline_grl --controller GRL --cases "$CASES" --horizon "$HORIZON" --venv "$VENV"
