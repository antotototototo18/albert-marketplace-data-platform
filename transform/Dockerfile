FROM python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DBT_PROFILES_DIR=/app/transform DBT_SEND_ANONYMOUS_USAGE_STATS=false
WORKDIR /app/transform
COPY transform/requirements.lock /tmp/requirements.lock
RUN python -m pip install --no-cache-dir -r /tmp/requirements.lock && python -m pip check \
    && groupadd --gid 10001 job && useradd --uid 10001 --gid job --create-home job
COPY --chown=10001:10001 transform/ /app/transform/
RUN chown job:job /app/transform
USER 10001:10001
RUN dbt deps
ENTRYPOINT ["dbt"]
CMD ["build"]
