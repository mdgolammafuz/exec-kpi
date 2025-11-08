import os
from typing import Any, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.cloud import bigquery
import json
from pathlib import Path

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", os.getenv("GCP_PROJECT", "exec-kpi"))
BQ_DATASET = os.getenv("EXECKPI_BQ_DATASET", os.getenv("BQ_DATASET", "execkpi"))
SQL_DIR = os.getenv("EXECKPI_SQL_DIR", "sql")
ARTIFACT_DIR = Path(os.getenv("EXECKPI_ARTIFACT_DIR", "artifacts"))

app = FastAPI(title="ExecKPI Backend", version="0.4")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _bq_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID)


def _read_sql_file(name: str) -> str:
    path = os.path.join(SQL_DIR, name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"SQL file not found: {name}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class SQLParam(BaseModel):
    name: str
    type: str
    value: Any


class SQLRequest(BaseModel):
    sql_file: str
    params: Optional[List[SQLParam]] = None


class ABTestRequest(BaseModel):
    a_success: int
    a_total: int
    b_success: int
    b_total: int
    alpha: float = 0.05


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/kpi/query")
def kpi_query(req: SQLRequest):
    sql = _read_sql_file(req.sql_file)
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(p.name, p.type, p.value)
            for p in (req.params or [])
        ]
    )
    df = _bq_client().query(sql, job_config=job_config).result().to_dataframe()
    return {
        "rows": len(df),
        "columns": list(df.columns),
        "data": df.to_dict(orient="records"),
    }


@app.get("/ab/sample")
def ab_sample():
    try:
        df = _bq_client().query(
            f"SELECT ab_group as variant, users as success, users as total FROM `{PROJECT_ID}.{BQ_DATASET}.ab_metrics`"
        ).result().to_dataframe()
        if not df.empty:
            grouped = (
                df.groupby("variant")[["success", "total"]]
                .sum()
                .to_dict(orient="index")
            )
            return {"sample": grouped}
    except Exception:
        pass

    return {
        "sample": {
            "A": {"success": 120, "total": 1000},
            "B": {"success": 160, "total": 1000},
        }
    }


@app.post("/ab/test")
def ab_test(req: ABTestRequest):
    import numpy as np
    from scipy.stats import chi2_contingency

    table = np.array(
        [
            [req.a_success, req.a_total - req.a_success],
            [req.b_success, req.b_total - req.b_success],
        ]
    )
    chi2, p, dof, _ = chi2_contingency(table, correction=True)
    return {
        "p_value": float(p),
        "chi2": float(chi2),
        "significant": bool(p < req.alpha),
    }


@app.post("/ml/train")
def ml_train():
    """
    Call the trainer script logic (we could import and call).
    For now we shell out to keep it simple inside the repo.
    """
    # simplest: run python script from here
    exit_code = os.system("python backend/train_explain.py")
    if exit_code != 0:
        raise HTTPException(status_code=500, detail="ML training failed")

    # after training, return latest
    return ml_latest()


@app.get("/ml/latest")
def ml_latest():
    """
    Return latest metrics/artifacts from artifacts/
    """
    metrics_path = ARTIFACT_DIR / "metrics.json"
    if not metrics_path.exists():
        raise HTTPException(status_code=404, detail="No ML artifacts found")

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    return {
        "metrics": metrics,
        "artifacts": {
            "model": str(ARTIFACT_DIR / "model.xgb"),
            "columns": str(ARTIFACT_DIR / "columns.json"),
            "shap_values": str(ARTIFACT_DIR / "shap_values.npy"),
        },
    }
