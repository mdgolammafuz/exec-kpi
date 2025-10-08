from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="execkpi_daily",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    tags=["execkpi"],   
    catchup=False,         
    max_active_runs=1,      
) as dag:

    dbt_build = BashOperator(
        task_id="dbt_build_kpi",
        bash_command="cd $AIRFLOW_HOME/../dbt_project && dbt run -s kpi",
    )

    train_model = BashOperator(
        task_id="bqml_train",
        bash_command="bq query --use_legacy_sql=false < $AIRFLOW_HOME/../sql/20_ml_xgb_create_model.sql",
        pool="bqml_model_pool",
    )

    dbt_build >> train_model
