"""
Generate synthetic RADIUS session data for training the Isolation Forest model.

Distribution:
  Normal sessions (90%)  — typical lecture browsing:
    bytes_downloaded_mb  ~ LogNormal(mu=2.5, sigma=0.8)   ≈ 5–30 MB
    bytes_uploaded_mb    ~ LogNormal(mu=1.0, sigma=0.6)   ≈ 1–5 MB
    duration_minutes     ~ Normal(50, 5) clipped [30, 90]

  Anomalous sessions (10%) — video streaming / bandwidth fraud:
    bytes_downloaded_mb  ~ Uniform(400, 800)
    bytes_uploaded_mb    ~ LogNormal(mu=2.0, sigma=0.5)   ≈ 3–10 MB
    duration_minutes     ~ Normal(50, 5) clipped [30, 90]  (same room, same time)
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

SEED = 42
N_TOTAL = 10_000
FRAUD_RATIO = 0.10

rng = np.random.default_rng(SEED)

n_fraud = int(N_TOTAL * FRAUD_RATIO)
n_normal = N_TOTAL - n_fraud


def gen_duration(n: int) -> np.ndarray:
    return np.clip(rng.normal(50, 8, n), 20, 180)


# Normal sessions
dl_normal = np.exp(rng.normal(2.5, 0.8, n_normal))   # LogNormal: mostly 5–30 MB
ul_normal = np.exp(rng.normal(1.0, 0.6, n_normal))
dur_normal = gen_duration(n_normal)
label_normal = np.zeros(n_normal, dtype=int)           # 0 = normal

# Anomalous sessions (high bandwidth)
dl_fraud = rng.uniform(400, 800, n_fraud)
ul_fraud = np.exp(rng.normal(2.0, 0.5, n_fraud))
dur_fraud = gen_duration(n_fraud)
label_fraud = np.ones(n_fraud, dtype=int)             # 1 = anomaly

df = pd.DataFrame({
    "bytes_downloaded_mb": np.concatenate([dl_normal, dl_fraud]),
    "bytes_uploaded_mb":   np.concatenate([ul_normal, ul_fraud]),
    "duration_minutes":    np.concatenate([dur_normal, dur_fraud]),
    "label":               np.concatenate([label_normal, label_fraud]),
})

df = df.sample(frac=1, random_state=SEED).reset_index(drop=True)

out_path = pathlib.Path(__file__).parent / "sessions.csv"
df.to_csv(out_path, index=False)
print(f"Generated {len(df)} sessions → {out_path}")
print(df["label"].value_counts().rename({0: "normal", 1: "anomaly"}))
