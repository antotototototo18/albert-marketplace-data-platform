"""Group 6's pipeline, once a day: extract a day of orders, merge it into bronze, run dbt.

This file is structure only. The scheduler re-parses it on a timer, so nothing at
module level connects to a database, reads data or imports anything heavy; the
work happens in the containers built in lessons 5 and 6.

Every task that writes says how a second run is made harmless: see
docs/orchestration.md and docs/adr/0007-idempotency.md.
"""

import os

import pendulum
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.sdk import DAG
from airflow.timetables.interval import CronDataIntervalTimetable
from docker.types import Mount


PROJECT = "data-engineering-i1"
REGISTRY = f"europe-west1-docker.pkg.dev/{PROJECT}/dataeng"
# Pinned to a build tag that is never reused (ADR-0006). Not to the digest: the
# Docker provider (4.5.9) cannot find a local image named by digest, so it tries
# to pull it, and the worker has no registry credentials (403, 2026-11-06). The
# host pulls the images; docs/runbooks/failed-run.md checks tag = digest below.
#   group6-ingestion  sha256:d273c33b9e0e3d23914927f48e8630cd83afc68f4952b1ad10857cbe2e23b3b4
#   group6-transform  sha256:e05e888f638b1dc0b9e1b435e6201bda792705b3b3b6d6587e183061439d38a2
INGESTION_IMAGE = f"{REGISTRY}/group6-ingestion:20261106T-step7-01"
TRANSFORM_IMAGE = f"{REGISTRY}/group6-transform:20261106T-step7-01"
CLOUD_SDK_IMAGE = "google/cloud-sdk:slim"

# Paths on the HOST: DockerOperator asks the host's Docker to start each container.
HOST_DIR = os.environ["HOST_DIR"]
GCLOUD_DIR = os.environ["GCLOUD_DIR"]
gcloud_mount = Mount(source=GCLOUD_DIR, target="/gcloud-ro", type="bind", read_only=True)
data_mount = Mount(source=f"{HOST_DIR}/out", target="/data", type="bind")

# The run's own period, never the clock: this is what makes a back-fill mean anything.
SINCE = "{{ data_interval_start | ds }}"
UNTIL = "{{ data_interval_end | ds }}"
STAGE_SUFFIX = "{{ data_interval_start | ds_nodash }}"

# One merge per table. The key is the table's identity in the source, and lesson 5's
# tests (unique on stg_orders.order_id, unique_combination on stg_order_items)
# check it really is unique, because BigQuery will not.
MERGES = {
    "orders": f"""
MERGE `{PROJECT}.group6_bronze.orders_raw` AS t
USING `{PROJECT}.group6_bronze.stage_orders_{STAGE_SUFFIX}` AS s
ON t.order_id = s.order_id
WHEN MATCHED THEN UPDATE SET
  buyer_id = s.buyer_id, discount_id = s.discount_id, payment_id = s.payment_id,
  order_date = s.order_date, _loaded_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT (order_id, buyer_id, discount_id, payment_id, order_date, _loaded_at)
  VALUES (s.order_id, s.buyer_id, s.discount_id, s.payment_id, s.order_date, CURRENT_TIMESTAMP())
""",
    "order_items": f"""
MERGE `{PROJECT}.group6_bronze.order_items_raw` AS t
USING `{PROJECT}.group6_bronze.stage_order_items_{STAGE_SUFFIX}` AS s
ON t.order_id = s.order_id AND t.p_id = s.p_id
WHEN MATCHED THEN UPDATE SET
  qty = s.qty, price_at_purchase = s.price_at_purchase, _loaded_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT (order_id, p_id, qty, price_at_purchase, _loaded_at)
  VALUES (s.order_id, s.p_id, s.qty, s.price_at_purchase, CURRENT_TIMESTAMP())
""",
}

# gcloud writes into its config directory, and the mount is read-only: work on a copy.
# bq authenticates with the Application Default Credentials, the same file dbt uses,
# not with gcloud's own login: that one asks to re-authenticate every few hours and
# a container cannot answer ("Reauthentication failed", 2026-11-06). One credential
# to keep fresh instead of two.
BQ = f"bq --headless --project_id={PROJECT} --location=europe-west1"
BQ_LABELS = (
    "--label=team:group6 --label=environment:course "
    "--label=pipeline:marketplace --label=component:bronze"
)
GCLOUD_SETUP = (
    "set -euo pipefail; cp -r /gcloud-ro /tmp/gcloud; export CLOUDSDK_CONFIG=/tmp/gcloud; "
    "export CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE=/gcloud-ro/application_default_credentials.json"
)
LOAD = f"""{GCLOUD_SETUP}
{BQ} load {BQ_LABELS} --source_format=PARQUET --replace "group6_bronze.stage_${{TABLE}}_${{STAGE_SUFFIX}}" "/data/${{TABLE}}/${{SINCE}}.parquet"
{BQ} query {BQ_LABELS} --use_legacy_sql=false --maximum_bytes_billed=1073741824 "$MERGE_SQL"
{BQ} query {BQ_LABELS} --use_legacy_sql=false --format=pretty "SELECT '$TABLE' AS tbl,
  (SELECT COUNT(*) FROM \\`{PROJECT}.group6_bronze.stage_${{TABLE}}_${{STAGE_SUFFIX}}\\`) AS n_staged,
  (SELECT COUNT(*) FROM \\`{PROJECT}.group6_bronze.${{TABLE}}_raw\\`) AS n_in_bronze"
"""
DROP_STAGING = f"""{GCLOUD_SETUP}
{BQ} query {BQ_LABELS} --use_legacy_sql=false "
DROP TABLE IF EXISTS \\`{PROJECT}.group6_bronze.stage_orders_${{STAGE_SUFFIX}}\\`;
DROP TABLE IF EXISTS \\`{PROJECT}.group6_bronze.stage_order_items_${{STAGE_SUFFIX}}\\`;"
"""

DBT_ENVIRONMENT = {
    "GOOGLE_APPLICATION_CREDENTIALS": "/gcloud-ro/application_default_credentials.json",
    # group6 writes the shared group6_silver/group6_gold; a member can point the
    # DAG at their own datasets while developing (DBT_DATASET=group6_l07_<name>).
    "DBT_DATASET": os.environ.get("DBT_DATASET", "group6"),
}


def alert(context):
    """Email one person once a task has failed for the last time (after its retries).

    on_failure_callback, not on_retry_callback: a retry is Airflow having another
    go, and an alert on every attempt teaches the group to ignore the inbox.
    """
    import smtplib
    from email.message import EmailMessage

    ti = context["task_instance"]
    message = EmailMessage()
    message["Subject"] = f"[group6 Airflow] {ti.dag_id}.{ti.task_id} failed"
    message["From"] = os.environ["SMTP_USER"]
    message["To"] = os.environ["ALERT_EMAIL_TO"]
    message.set_content(
        f"{ti.dag_id}.{ti.task_id} failed for {context['data_interval_start']} "
        f"(run {ti.run_id}, attempt {ti.try_number}).\n\n"
        "What to do: docs/runbooks/failed-run.md, starting with this task's log in the UI."
    )
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "587")), timeout=30) as smtp:
        smtp.starttls()
        smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(message)


with DAG(
    dag_id="group6_marketplace_daily",
    # Airflow 3 runs "@daily" as a zero-length interval by default. This timetable
    # gives the lesson's semantics: the run for 15 September covers 15 September,
    # midnight to midnight UTC, and starts once that day is over.
    schedule=CronDataIntervalTimetable("@daily", timezone="UTC"),
    # The first day the DAG owns: the legacy export ends on 2026-09-14.
    start_date=pendulum.datetime(2026, 9, 15, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={
        # Longer than what is retried: the extractor already retries its own
        # connection for about a minute, dbt and bq retry their own jobs once.
        "retries": 2,
        "retry_delay": pendulum.duration(minutes=5),
        "on_failure_callback": alert,
    },
    tags=["group6", "marketplace"],
) as dag:

    common = {"auto_remove": "success", "mount_tmp_dir": False}

    loads = []
    for table in ("orders", "order_items"):
        extract = DockerOperator(
            task_id=f"extract_{table}",
            image=INGESTION_IMAGE,
            command="ingestion.extract_interval",
            network_mode="albert-marketplace_default",
            environment={"TABLE": table, "SINCE": SINCE, "UNTIL": UNTIL, "BRONZE_URI": "/data"},
            # Not templated, not shown in the UI's rendered fields.
            private_environment={"DATABASE_URL": os.environ["SOURCE_DATABASE_URL"]},
            mounts=[data_mount],
            **common,
        )
        load = DockerOperator(
            task_id=f"load_{table}",
            image=CLOUD_SDK_IMAGE,
            entrypoint="/bin/bash",
            command=["-c", LOAD],
            environment={"TABLE": table, "SINCE": SINCE, "STAGE_SUFFIX": STAGE_SUFFIX,
                         "MERGE_SQL": MERGES[table]},
            mounts=[gcloud_mount, data_mount],
            **common,
        )
        extract >> load
        loads.append(load)

    # Scratch tables cost money and confuse the next reader: they go whether or
    # not the loads succeeded. The alert is on the task that failed, so a green
    # drop_staging cannot hide a red load.
    drop_staging = DockerOperator(
        task_id="drop_staging",
        image=CLOUD_SDK_IMAGE,
        entrypoint="/bin/bash",
        command=["-c", DROP_STAGING],
        environment={"STAGE_SUFFIX": STAGE_SUFFIX},
        mounts=[gcloud_mount],
        trigger_rule="all_done",
        **common,
    )

    # The quality gate. Not dbt run then dbt test: on 2026-11-06 that let a
    # duplicated order line reach gold before any test looked at it (an alarm).
    # dbt build tests each model as it is built and skips everything downstream
    # of a failure, so the bad row stops at staging (a lock).
    dbt_build = DockerOperator(
        task_id="dbt_build", image=TRANSFORM_IMAGE, command="build",
        environment=DBT_ENVIRONMENT, mounts=[gcloud_mount], **common,
    )

    loads >> drop_staging
    loads >> dbt_build
