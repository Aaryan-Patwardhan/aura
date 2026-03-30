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

import math
import os
import pathlib
from typing import Optional

import joblib
import numpy as np

_MODEL_PATH = pathlib.Path(
    os.environ.get("MODEL_PATH", pathlib.Path(__file__).parent / "models" / "isolation_forest.pkl")
)

_model = None


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


def score_session(
    bytes_downloaded_mb: float,
    bytes_uploaded_mb: float,
    duration_minutes: float,
) -> float:
    """
    Returns a proxy risk score in [0.0, 1.0].

    IsolationForest.decision_function() returns a raw anomaly score:
      - Negative values are more anomalous
      - Typical range roughly [-0.5, 0.5]

    We invert and normalize to [0, 1] using a sigmoid-like mapping.
    """
    try:
        model = _load_model()
        X = np.array([[bytes_downloaded_mb, bytes_uploaded_mb, duration_minutes]])
        raw_score = model.decision_function(X)[0]   # higher = more normal

        # Invert: anomalous → high score.  Typical raw range ≈ [-0.5, 0.5]
        # Clamp to [-0.5, 0.5] then map to [0, 1]
        inverted = -raw_score
        clamped = max(-0.5, min(0.5, inverted))
        normalized = (clamped + 0.5)  # maps [-0.5, 0.5] → [0.0, 1.0]
        return round(float(normalized), 4)

    except FileNotFoundError:
        # Model not trained yet — return 0 (no signal)
        return 0.0
    except Exception:
        return 0.0


def is_anomalous(score: float, threshold: float = 0.75) -> bool:
    return score >= threshold
