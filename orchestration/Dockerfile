# Airflow's own image, pinned, plus the one thing it does not ship: the Docker
# provider, which is what DockerOperator comes from. Without this line the DAG
# fails to import with ModuleNotFoundError and the UI shows no DAG at all.
FROM apache/airflow:3.3.2
RUN pip install --no-cache-dir apache-airflow-providers-docker==4.5.9
