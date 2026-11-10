FROM python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY ingestion/requirements.lock /tmp/requirements.lock
RUN python -m pip install --no-cache-dir -r /tmp/requirements.lock && python -m pip check \
    && groupadd --gid 10001 job && useradd --uid 10001 --gid job --create-home job \
    && mkdir /output && chown job:job /output
COPY ingestion/*.py ingestion/clickstream.schema.json /app/ingestion/
USER 10001:10001
ENTRYPOINT ["python", "-m"]
CMD ["ingestion.extract_orders"]
