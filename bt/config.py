"""Config base del motor."""
ENGINE_VERSION = "0.2.0"
DATA_ROOT = "data/weltrade"
RESULTS_ROOT = "results"

TF_SECONDS = {
    "M1": 60, "M2": 120, "M3": 180, "M5": 300, "M15": 900,
    "M30": 1800, "H1": 3600, "H4": 14400, "D1": 86400,
}
SUPPORTED_TFS = list(TF_SECONDS.keys())
DEFAULT_WORKERS = 2
DEFAULT_MC_SIMS = 500
