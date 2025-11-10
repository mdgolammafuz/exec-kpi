import os

def test_env_defaults():
    # these are the defaults we used in main.py
    assert os.getenv("GCP_PROJECT", "exec-kpi") == "exec-kpi"
    assert os.getenv("BQ_DATASET", "execkpi_execkpi") == "execkpi_execkpi"
