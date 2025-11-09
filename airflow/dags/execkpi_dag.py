from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator

# Airflow is in:   $AIRFLOW_HOME = exec-kpi/airflow
# Project root is: $AIRFLOW_HOME/..
REPO_DIR = "$AIRFLOW_HOME/.."
DBT_DIR = "$AIRFLOW_HOME/../dbt_project"

with DAG(
    dag_id="execkpi_daily",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    tags=["execkpi"],
) as dag:

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_DIR} && dbt run",
    )

    dbt_test_gold = BashOperator(
        task_id="dbt_test_gold",
        bash_command=f"cd {DBT_DIR} && dbt test --select gold",
    )

    train_local_model = BashOperator(
        task_id="train_local_model",
        bash_command=f"cd {REPO_DIR} && python backend/train_explain.py",
    )

    dbt_run >> dbt_test_gold >> train_local_model
