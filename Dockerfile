# SPDX-License-Identifier: Apache-2.0

FROM python:3.13-slim@sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY requirements/p8.lock /app/requirements/p8.lock
RUN python -m pip install --no-cache-dir --require-hashes -r /app/requirements/p8.lock

COPY migrations /app/migrations
COPY src /app/src

RUN groupadd --gid 10001 digital-colleagues \
    && useradd --uid 10001 --gid 10001 --no-create-home digital-colleagues \
    && mkdir /state \
    && chown digital-colleagues:digital-colleagues /state

USER 10001:10001

CMD ["python", "-m", "uvicorn", "digital_colleagues.local.asgi:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
