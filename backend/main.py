import os
import json
from pathlib import Path
from typing import Any, List, Optional

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import bigquery

app = FastAPI(title="ExecKPI backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # relax for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT = os.getenv("GCP_PROJECT", "exec-kpi")
DATASET = os.getenv("BQ_DATASET", "execkpi")
SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def _bq_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT)


def _to_native(obj: Any) -> Any:
    """Recursively convert numpy/scalars to plain Python so FastAPI can jsonify."""
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_native(v) for v in obj]
    return obj


# ------------------------------------------------------------------------------
# KPI / SQL runner
# ------------------------------------------------------------------------------

@app.post("/kpi/query")
def kpi_query(payload: dict):
    sql_file = payload.get("sql_file")
    params: List[dict] = payload.get("params") or []

    if not sql_file:
        raise HTTPException(status_code=400, detail="sql_file is required")

    file_path = SQL_DIR / sql_file
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"SQL file {sql_file} not found")

    sql = file_path.read_text(encoding="utf-8")

    bq_params = []
    for p in params:
        bq_params.append(
            bigquery.ScalarQueryParameter(p["name"], p["type"], p["value"])
        )

    job_config = bigquery.QueryJobConfig(query_parameters=bq_params)
    df = _bq_client().query(sql, job_config=job_config).result().to_dataframe()

    return {
        "rows": len(df),
        "columns": list(df.columns),
        "data": df.to_dict(orient="records"),
    }


# ------------------------------------------------------------------------------
# A/B endpoints
# ------------------------------------------------------------------------------

@app.get("/ab/sample")
def ab_sample():
    sample = {
        "A": {"success": 120, "total": 1000},
        "B": {"success": 150, "total": 980},
    }
    return {"sample": _to_native(sample)}


@app.post("/ab/test")
def ab_test(payload: dict):
    from math import sqrt
    from scipy.stats import norm, chi2

    try:
        a_s = int(payload["a_success"])
        a_n = int(payload["a_total"])
        b_s = int(payload["b_success"])
        b_n = int(payload["b_total"])
        alpha = float(payload.get("alpha", 0.05))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"bad payload: {e}")

    if a_n <= 0 or b_n <= 0:
        raise HTTPException(status_code=400, detail="group sizes must be > 0")

    p_a = a_s / a_n
    p_b = b_s / b_n
    uplift = p_b - p_a

    total = a_n + b_n
    exp = total / 2
    chi2_stat = ((a_n - exp) ** 2) / exp + ((b_n - exp) ** 2) / exp
    srm_p = 1 - chi2.cdf(chi2_stat, df=1)

    pooled = (a_s + b_s) / total
    se = sqrt(pooled * (1 - pooled) * (1 / a_n + 1 / b_n))
    z = uplift / se
    p_val = 2 * (1 - norm.cdf(abs(z)))
    ci_low = uplift - 1.96 * se
    ci_high = uplift + 1.96 * se
    significant = bool(p_val < alpha)

    resp = {
        "group": {
            "A": {"success": a_s, "total": a_n, "rate": p_a},
            "B": {"success": b_s, "total": b_n, "rate": p_b},
        },
        "uplift": uplift,
        "p_value": p_val,
        "ci_95": [ci_low, ci_high],
        "srm_p": srm_p,
        "significant": significant,
    }
    return _to_native(resp)


# ------------------------------------------------------------------------------
# ML endpoints
# ------------------------------------------------------------------------------

def _extract_last_json(stdout: str) -> Optional[dict]:
    idx = stdout.rfind("{")
    if idx == -1:
        return None
    tail = stdout[idx:]
    try:
        return json.loads(tail)
    except Exception:
        return None


@app.post("/ml/train")
def ml_train():
    import subprocess
    import sys

    script_path = Path(__file__).resolve().parent / "train_explain.py"
    if not script_path.exists():
        raise HTTPException(status_code=500, detail="train_explain.py not found")

    proc = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"trainer failed: {proc.stderr or proc.stdout}",
        )

    out = proc.stdout
    parsed = _extract_last_json(out)
    if parsed is not None:
        return _to_native(parsed)

    return {
        "output": out.splitlines()
    }


@app.get("/ml/latest")
def ml_latest():
    metrics_path = Path("artifacts") / "metrics.json"
    if not metrics_path.exists():
        raise HTTPException(status_code=404, detail="No ML artifacts yet")
    data = json.loads(metrics_path.read_text(encoding="utf-8"))
    return _to_native(data)


@app.get("/ml/shap")
def ml_shap():
    shap_path = Path("artifacts") / "shap_summary.json"
    if not shap_path.exists():
        raise HTTPException(status_code=404, detail="No SHAP summary yet")
    data = json.loads(shap_path.read_text(encoding="utf-8"))
    return _to_native(data)
