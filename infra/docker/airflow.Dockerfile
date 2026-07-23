FROM apache/airflow:2.10.4-python3.12

USER airflow
COPY pipelines/airflow/dags /opt/airflow/dags

