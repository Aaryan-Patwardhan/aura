"""
Train the Isolation Forest Focus Score model.

Usage:
    python -m ai.train_model

Outputs:
    ai/models/isolation_forest.pkl     — serialised IsolationForest
    ai/models/score_bounds.pkl         — (raw_min, raw_max) for score normalisation
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

DATA_PATH   = pathlib.Path(__file__).parent / "training_data" / "sessions.csv"
MODEL_DIR   = pathlib.Path(__file__).parent / "models"
MODEL_PATH  = MODEL_DIR / "isolation_forest.pkl"
BOUNDS_PATH = MODEL_DIR / "score_bounds.pkl"

FEATURES      = ["bytes_downloaded_mb", "bytes_uploaded_mb", "duration_minutes"]
CONTAMINATION = 0.10    # matches fraud ratio in synthetic data (~10%)
N_ESTIMATORS  = 200
RANDOM_STATE  = 42


def load_or_generate_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        print("Training data not found — generating …")
        subprocess.run(
            [sys.executable, str(pathlib.Path(__file__).parent / "training_data" / "generate_synthetic_data.py")],
            check=True,
        )
    return pd.read_csv(DATA_PATH)


def train() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    df     = load_or_generate_data()
    X      = df[FEATURES].values
    y_true = df["label"].values   # 0=normal, 1=anomaly (only for eval)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_true, test_size=0.2, random_state=RANDOM_STATE, stratify=y_true
    )

    print(f"Training IsolationForest on {len(X_train)} samples …")
    model = IsolationForest(
        n_estimators=N_ESTIMATORS,
        contamination=CONTAMINATION,
        max_samples="auto",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(X_train)

    # ── Normalisation bounds ────────────────────────────────────────────────
    # score_samples() output scale depends on dataset and n_estimators.
    # We compute raw_min / raw_max on the training set and save them so
    # focus_score.py can perform a stable min-max rescale to [0.0, 1.0]:
    #   score = 1 - (raw - raw_min) / (raw_max - raw_min)
    # Lower raw = more anomalous → inverted so that high score = high risk.
    raw_train = model.score_samples(X_train)
    raw_min   = float(raw_train.min())
    raw_max   = float(raw_train.max())
    joblib.dump({"raw_min": raw_min, "raw_max": raw_max}, BOUNDS_PATH)
    print(f"Score bounds  raw_min={raw_min:.4f}  raw_max={raw_max:.4f}  → saved to {BOUNDS_PATH}")

    # ── Classification accuracy ─────────────────────────────────────────────
    y_pred_raw = model.predict(X_test)
    y_pred     = np.where(y_pred_raw == -1, 1, 0)   # +1=normal,-1=anomaly → 0/1

    print("\nClassification report on held-out test set:")
    print(classification_report(y_test, y_pred, target_names=["normal", "anomaly"]))

    # ── Score distribution verification ────────────────────────────────────
    raw_test = model.score_samples(X_test)
    _range   = raw_max - raw_min if raw_max != raw_min else 1.0
    norm_scores = np.clip(1.0 - (raw_test - raw_min) / _range, 0.0, 1.0)

    norm_idx = y_test == 0
    anom_idx = y_test == 1
    print("Score distribution (hold-out, normalised to [0,1]):")
    print(f"  NORMAL  mean={norm_scores[norm_idx].mean():.4f}  "
          f"(target <0.30)  PASS={norm_scores[norm_idx].mean() < 0.30}")
    print(f"  ANOMALY mean={norm_scores[anom_idx].mean():.4f}  "
          f"(target >0.70)  PASS={norm_scores[anom_idx].mean() > 0.70}")

    joblib.dump(model, MODEL_PATH)
    print(f"\nModel saved → {MODEL_PATH}")


if __name__ == "__main__":
    train()
