"""
ExecKPI trainer: compare 3 models on features_conversion and save best.

Hard requirements:
- BigQuery table must exist (we try several names).
- xgboost must be importable (we fail if not).
"""

import json
import os
import pickle
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from google.cloud import bigquery
from google.api_core.exceptions import NotFound
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
        "Try: dbt build (which writes to exec-kpi:execkpi_execkpi) "
        "or set EXECKPI_FEATURE_TABLE to the exact table."
    )


def load_features() -> pd.DataFrame:
    client = bigquery.Client(project=PROJECT_ID)
    table_fq = find_existing_features_table(client)
    df = client.query(f"SELECT * FROM `{table_fq}`").result().to_dataframe()
    if df.empty:
        raise RuntimeError(f"Feature table {table_fq} returned 0 rows")
    # stash for metrics
    df._feature_table_fq = table_fq  # type: ignore[attr-defined]
    return df


def get_model_candidates():
    """Return list of (name, model_instance, supports_proba) with mandatory xgboost."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier

    # xgboost: mandatory now
    try:
        import xgboost as xgb  # noqa: F401
    except Exception as e:
        raise RuntimeError(
            "xgboost is required but could not be imported.\n"
            "macOS fix:\n"
            "  brew install libomp\n"
            "  python -m pip install --force-reinstall xgboost\n"
            f"Original error: {e}"
        )

    import xgboost as xgb

    models = [
        ("logistic_regression", LogisticRegression(max_iter=1000), True),
        ("random_forest",        RandomForestClassifier(n_estimators=200, random_state=42), True),
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
    return auc, acc, proba


def maybe_compute_shap(best_name: str, best_model, X_train, artifact_dir: Path):
    try:
        import shap  # noqa: F401
    except Exception:
        print("[trainer] shap not available, skipping shap values")
        return

    # only for tree models
    if best_name not in {"random_forest", "xgboost"}:
        return

    try:
        import shap

        explainer = shap.TreeExplainer(best_model)
        shap_values = explainer.shap_values(X_train)
        np.save(artifact_dir / "shap_values.npy", shap_values)
        print("[trainer] shap values saved")
    except Exception as e:
        print(f"[trainer] failed to compute shap: {e}")


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


def main():
    print("[trainer] loading features...")
    df = load_features()

    target_col = "will_convert_14d"
    if target_col not in df.columns:
        raise RuntimeError(f"Target column {target_col} not found in features table")

    feature_table_fq = getattr(df, "_feature_table_fq", "UNKNOWN")

    X = df.drop(columns=[target_col, "user_id"], errors="ignore")
    X = X.select_dtypes(include=[np.number]).fillna(0.0)
    y = df[target_col].astype(int)

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
        auc, acc, _ = train_and_eval(model, X_train, X_test, y_train, y_test, supports_proba)
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
