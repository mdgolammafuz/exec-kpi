import os
from datetime import datetime
from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator

# 1. Robust Path Resolution
# Assuming this file is at: <REPO>/airflow/dags/execkpi_dag.py
# We go up two levels to find <REPO>
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
DBT_DIR = os.path.join(PROJECT_ROOT, "dbt_project")

# 2. Point to Virtual Env Binaries (Avoids "command not found")
# This assumes you are running Airflow locally. 
# In production Docker, you'd just use "dbt" if installed globally.
VENV_BIN = os.path.join(PROJECT_ROOT, ".venv", "bin")
DBT_CMD = os.path.join(VENV_BIN, "dbt")
PYTHON_CMD = os.path.join(VENV_BIN, "python")

with DAG(
    dag_id="execkpi_daily",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",  # Use 'schedule', NOT 'schedule_interval'
    catchup=False,
    max_active_runs=1,
    tags=["execkpi", "governance"],
) as dag:

    # Task 1: Run dbt Transformations (Bronze -> Silver -> Gold)
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_DIR} && {DBT_CMD} run",
        env={"dbt_project_dir": DBT_DIR} # Explicit env var often helps dbt
    )

    # Task 2: Data Quality Gate (Governance)
    # If this fails, we do NOT retrain the model.
    dbt_test_gold = BashOperator(
        task_id="dbt_test_gold",
        bash_command=f"cd {DBT_DIR} && {DBT_CMD} test --select gold",
    )

    # Task 3: ML Training Pipeline
    # Uses the project's python to run the training script
    train_local_model = BashOperator(
        task_id="train_local_model",
        bash_command=f"cd {PROJECT_ROOT} && {PYTHON_CMD} backend/train_explain.py",
    )

    # Orchestration Logic
    dbt_run >> dbt_test_gold >> train_local_model