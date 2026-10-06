"""
Shared configuration for 123-bus FDIA experiments.
"""

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PAPER_RESULTS_DIR = BASE_DIR / "paper_results"

ATTACK_NAMES = ["clean", "voltage_masking", "branchflow_hiding", "energy_inflation", "topology_drop"]
FIXED_SCENARIOS = {
    "SC1": "test_func1",
    "SC2": "test_func2",
}
DATASET_SCENARIOS = {
    **FIXED_SCENARIOS,
    "random": "reset",
}

DEFAULT_GCAPS_MODEL = BASE_DIR / "TrainedModels" / "GCAPS_123.zip"
DEFAULT_FDIA_RESULTS = PAPER_RESULTS_DIR / "fdia_123_results.csv"
DEFAULT_DEFENDED_FDIA_RESULTS = PAPER_RESULTS_DIR / "fdia_123_defended_results.csv"
DEFAULT_FDIA_DATASET = PAPER_RESULTS_DIR / "fdia_learning_dataset_123.npz"
DEFAULT_DETECTOR_DIR = PAPER_RESULTS_DIR / "learning_detectors"
DEFAULT_LEARNING_MODEL = DEFAULT_DETECTOR_DIR / "multiclass" / "mlp_torch.pkl"


def resolve_local_path(path):
    """Resolve relative paths from this 123-bus folder instead of the launch directory."""
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return BASE_DIR / candidate
