"""
Train the Isolation Forest Focus Score model.

Usage:
    python -m ai.train_model

Outputs:
    ai/models/isolation_forest.pkl
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

DATA_PATH = pathlib.Path(__file__).parent / "training_data" / "sessions.csv"
MODEL_DIR = pathlib.Path(__file__).parent / "models"
MODEL_PATH = MODEL_DIR / "isolation_forest.pkl"

FEATURES = ["bytes_downloaded_mb", "bytes_uploaded_mb", "duration_minutes"]
CONTAMINATION = 0.10    # matches fraud ratio in synthetic data
N_ESTIMATORS = 200
RANDOM_STATE = 42


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

    df = load_or_generate_data()
    X = df[FEATURES].values
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

    # Sklearn IF: predict() returns +1=normal, -1=anomaly
    y_pred_raw = model.predict(X_test)
    y_pred = np.where(y_pred_raw == -1, 1, 0)   # convert to 0/1

    print("\nClassification report on held-out test set:")
    print(classification_report(y_test, y_pred, target_names=["normal", "anomaly"]))

    joblib.dump(model, MODEL_PATH)
    print(f"\nModel saved → {MODEL_PATH}")


if __name__ == "__main__":
    train()
