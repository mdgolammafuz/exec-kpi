"""
ExecKPI trainer: load BQ features, train 3 models, pick best, save artifacts,
and compute SHAP feature importance (now that columns are coerced).
"""

import json
import os
import pickle
from pathlib import Path
from typing import Optional, Any

import numpy as np
import pandas as pd
from google.api_core.exceptions import NotFound
from google.cloud import bigquery
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split

# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------
ARTIFACT_DIR = Path(os.getenv("EXECKPI_ARTIFACT_DIR", "artifacts"))
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", os.getenv("GCP_PROJECT", "exec-kpi"))
FEATURE_TABLE_ENV = os.getenv("EXECKPI_FEATURE_TABLE", "").strip()

# dbt is creating exec-kpi:execkpi_execkpi.<model>
CANDIDATE_TABLES = [
    FEATURE_TABLE_ENV if FEATURE_TABLE_ENV else None,
    f"{PROJECT_ID}.execkpi_execkpi.features_conversion",
    f"{PROJECT_ID}.execkpi.features_conversion",
]


# ---------------------------------------------------------------------
# BQ helpers
# ---------------------------------------------------------------------
def find_existing_features_table(client: bigquery.Client) -> str:
    print("[trainer] probing candidate feature tables in BigQuery...")
    for table_fq in CANDIDATE_TABLES:
        if not table_fq:
            continue
        print(f"[trainer] -> trying {table_fq}")
        try:
            client.query(f"SELECT * FROM `{table_fq}` LIMIT 1").result().to_dataframe()
            print(f"[trainer] using feature table: {table_fq}")
            return table_fq
        except NotFound:
            print(f"[trainer]    not found: {table_fq}")
        except Exception as e:
            print(f"[trainer]    error probing {table_fq}: {e}")
    raise RuntimeError(
        "Could not find features_conversion in any known dataset.\n"
        "Run: dbt build (writes to exec-kpi:execkpi_execkpi) or set EXECKPI_FEATURE_TABLE."
    )


def _coerce_cell(v: Any) -> float:
    """
    BigQuery sometimes gives us weird stringy numbers like '[6.874376E-1]'.
    This tries to make *everything* a float.
    """
    if v is None:
        return 0.0
    # list/array-like -> take first
    if isinstance(v, (list, tuple)):
        return _coerce_cell(v[0]) if v else 0.0
    # plain number
    if isinstance(v, (int, float, np.integer, np.floating)):
        return float(v)
    # stringy number, maybe wrapped in [] or with E
    if isinstance(v, str):
        s = v.strip()
        if s.startswith("[") and s.endswith("]"):
            s = s[1:-1].strip()
        try:
            return float(s)
        except Exception:
            return 0.0
    # fallback
    return 0.0


def load_features() -> pd.DataFrame:
    client = bigquery.Client(project=PROJECT_ID)
    table_fq = find_existing_features_table(client)
    print(f"[trainer] loading from {table_fq}...")
    df = client.query(f"SELECT * FROM `{table_fq}`").result().to_dataframe()
    print(f"[trainer] loaded {len(df)} rows, {len(df.columns)} columns")

    if df.empty:
        raise RuntimeError(f"Feature table {table_fq} returned 0 rows")

    # columns we won't treat as features
    target_col = "will_convert_14d"
    id_cols = {"user_id"}

    feature_cols = [c for c in df.columns if c not in id_cols | {target_col}]
    print(f"[trainer] cleaning {len(feature_cols)} feature columns...")

    for col in feature_cols:
        df[col] = df[col].map(_coerce_cell).astype(float)

    # stash for metrics / response
    df._feature_table_fq = table_fq  # type: ignore[attr-defined]
    return df


# ---------------------------------------------------------------------
# Model candidates
# ---------------------------------------------------------------------
def get_model_candidates():
    # xgboost is present in your venv now
    import xgboost as xgb

    models = [
        ("logistic_regression", LogisticRegression(max_iter=1000), True),
        ("random_forest", RandomForestClassifier(n_estimators=200, random_state=42), True),
        (
            "xgboost",
            xgb.XGBClassifier(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.08,
                subsample=0.9,
                colsample_bytree=0.9,
                eval_metric="auc",
                n_jobs=4,
            ),
            True,
        ),
    ]
    return models


def train_and_eval(model, X_train, X_test, y_train, y_test, supports_proba: bool):
    model.fit(X_train, y_train)

    if supports_proba and hasattr(model, "predict_proba"):
        proba = model.predict_proba(X_test)[:, 1]
    else:
        if hasattr(model, "decision_function"):
            scores = model.decision_function(X_test)
            proba = 1 / (1 + np.exp(-scores))
        else:
            preds = model.predict(X_test)
            proba = preds.astype(float)

    auc = float(roc_auc_score(y_test, proba))
    acc = float(accuracy_score(y_test, (proba >= 0.5).astype(int)))
    return auc, acc


# ---------------------------------------------------------------------
# SHAP
# ---------------------------------------------------------------------
def maybe_compute_shap(best_name: str, best_model, X_train: pd.DataFrame, artifact_dir: Path):
    """
    Now that features are float64, shap.TreeExplainer should work.
    We'll save a *ranked* list at artifacts/shap_importance.json
    so the API can just serve it.
    """
    try:
      import shap  # type: ignore
    except Exception:
      print("[trainer][shap] shap not installed, skipping.")
      return

    if best_name not in {"xgboost", "random_forest"}:
        # still save nothing — it's fine
        return

    n = min(200, len(X_train))
    sample = X_train.sample(n=n, random_state=42)
    X_np = sample.to_numpy(dtype=float, copy=True)
    print(f"[trainer][shap] computing feature importance...")
    print(f"[trainer][shap] X_np shape: {X_np.shape}, dtype: {X_np.dtype}")

    try:
        explainer = shap.TreeExplainer(best_model)
        shap_vals = explainer.shap_values(X_np)

        # xgboost sometimes returns list[class]
        if isinstance(shap_vals, list):
            shap_vals = shap_vals[0]

        mean_abs = np.mean(np.abs(shap_vals), axis=0)
        feature_names = list(sample.columns)

        feats = [
            {"feature": f, "mean_abs_shap": float(m)}
            for f, m in zip(feature_names, mean_abs)
        ]
        feats.sort(key=lambda x: x["mean_abs_shap"], reverse=True)

        artifact_dir.mkdir(parents=True, exist_ok=True)
        out_path = artifact_dir / "shap_importance.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "source": "shap",
                    "feature_names": feature_names,
                    "importances": feats,
                },
                f,
                indent=2,
            )
        print("[trainer][shap] saved to artifacts/shap_importance.json")
    except Exception as e:
        # we *do* want to keep training success even if SHAP flops
        print(f"[trainer][shap] failed: {e}")


# ---------------------------------------------------------------------
# Save artifacts
# ---------------------------------------------------------------------
def save_artifacts(best_name, best_model, columns, all_metrics, artifact_dir: Path):
    artifact_dir.mkdir(parents=True, exist_ok=True)

    model_path = artifact_dir / "model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(best_model, f)

    cols_path = artifact_dir / "columns.json"
    with open(cols_path, "w", encoding="utf-8") as f:
        json.dump(columns, f, indent=2)

    metrics_path = artifact_dir / "metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(all_metrics, f, indent=2)

    return {
        "model_path": str(model_path),
        "columns_path": str(cols_path),
        "metrics_path": str(metrics_path),
    }


# ---------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------
def main():
    print("[trainer] loading features...")
    df = load_features()

    target_col = "will_convert_14d"
    if target_col not in df.columns:
        raise RuntimeError(f"Target column {target_col} not found in features table")

    feature_table_fq = getattr(df, "_feature_table_fq", "UNKNOWN")

    X = df.drop(columns=[target_col, "user_id"], errors="ignore")
    # at this point we already coerced to float in load_features()
    y = df[target_col].astype(int)

    print(f"[trainer] X shape: {X.shape}, dtypes: {list(set(X.dtypes))}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    candidates = get_model_candidates()
    all_metrics: dict[str, dict] = {}
    best_name: Optional[str] = None
    best_model = None
    best_auc = -1.0
    best_acc = -1.0

    for name, model, supports_proba in candidates:
        print(f"[trainer] training {name} ...")
        auc, acc = train_and_eval(model, X_train, X_test, y_train, y_test, supports_proba)
        all_metrics[name] = {
            "auc": auc,
            "accuracy": acc,
            "rows": int(len(df)),
            "target": target_col,
            "feature_table": feature_table_fq,
        }
        print(f"[trainer] {name}: auc={auc:.4f}, acc={acc:.4f}")

        if auc > best_auc or (auc == best_auc and acc > best_acc):
            best_auc = auc
            best_acc = acc
            best_name = name
            best_model = model

    if best_model is None or best_name is None:
        raise RuntimeError("No models trained successfully")

    print(f"[trainer] best model: {best_name} (auc={best_auc:.4f}, acc={best_acc:.4f})")

    all_metrics["_chosen"] = {
        "name": best_name,
        "auc": best_auc,
        "accuracy": best_acc,
        "feature_table": feature_table_fq,
    }

    paths = save_artifacts(best_name, best_model, list(X.columns), all_metrics, ARTIFACT_DIR)
    maybe_compute_shap(best_name, best_model, X_train, ARTIFACT_DIR)

    print("[trainer] training complete.")
    print(json.dumps({**all_metrics["_chosen"], **paths}, indent=2))


if __name__ == "__main__":
    main()
