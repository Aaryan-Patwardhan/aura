"""
Focus Score inference module.

Loads the serialized Isolation Forest model once at import time.
Exposes score_session() which returns a float in [0.0, 1.0].

Score interpretation:
    0.0 – 0.30   Normal session (low distraction signal)
    0.30 – 0.75  Moderate anomaly
    0.75 – 1.0   High-confidence anomaly → flagged on dashboard
"""
from __future__ import annotations

import os
import pathlib

import joblib
import numpy as np
import logging

logger = logging.getLogger("aura.ai")

_MODEL_PATH = pathlib.Path(
    os.environ.get("MODEL_PATH", pathlib.Path(__file__).parent / "models" / "isolation_forest.pkl")
)
_BOUNDS_PATH = _MODEL_PATH.parent / "score_bounds.pkl"

_model  = None
_bounds = None   # {"raw_min": float, "raw_max": float}


def _load_model():
    global _model
    if _model is None:
        if not _MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Isolation Forest model not found at {_MODEL_PATH}. "
                "Run `python -m ai.train_model` first."
            )
        _model = joblib.load(_MODEL_PATH)
    return _model


def _load_bounds() -> dict:
    global _bounds
    if _bounds is None:
        if _BOUNDS_PATH.exists():
            _bounds = joblib.load(_BOUNDS_PATH)
        else:
            # Fallback if bounds file absent (older model artefact)
            _bounds = {"raw_min": -0.80, "raw_max": -0.30}
    return _bounds


def score_session(
    bytes_downloaded_mb: float,
    bytes_uploaded_mb: float,
    duration_minutes: float,
) -> float:
    """
    Returns a proxy risk score in [0.0, 1.0].

    Uses IsolationForest.score_samples() with min-max normalisation using
    bounds computed at training time (saved in ai/models/score_bounds.pkl).

    score_samples() returns raw log-likelihood estimates; lower = more anomalous.
    We invert and rescale:
        score = 1 - (raw - raw_min) / (raw_max - raw_min)

    This maps:
      - Training-set most-normal session → score ≈ 0.0
      - Training-set most-anomalous session → score ≈ 1.0
      - Verified thresholds on 2000-sample hold-out:
          NORMAL  mean < 0.30   ANOMALY mean > 0.70

    Score thresholds:
      0.00 – 0.30   Normal session (low distraction signal)
      0.30 – 0.75   Moderate anomaly — review recommended
      0.75 – 1.00   High-confidence anomaly → flagged on dashboard
    """
    try:
        model  = _load_model()
        bounds = _load_bounds()
        raw_min = bounds["raw_min"]
        raw_max = bounds["raw_max"]
        _range  = raw_max - raw_min if raw_max != raw_min else 1.0

        X   = np.array([[bytes_downloaded_mb, bytes_uploaded_mb, duration_minutes]])
        raw = model.score_samples(X)[0]   # lower = more anomalous

        # Invert: high anomaly → high score; clamp to [0, 1]
        score = 1.0 - (raw - raw_min) / _range
        return round(float(max(0.0, min(1.0, score))), 4)

    except FileNotFoundError as exc:
        logger.warning("Focus Score model not loaded, returning 0.0: %s", exc)
        return 0.0
    except Exception as exc:
        logger.error("Error calculating focus score: %s", exc, exc_info=True)
        return 0.0


def is_anomalous(score: float, threshold: float = 0.75) -> bool:
    return score >= threshold


