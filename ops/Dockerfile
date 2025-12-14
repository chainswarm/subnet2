FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY evaluation/ ./evaluation/
COPY template/ ./template/
COPY neurons/ ./neurons/
COPY alembic/ ./alembic/
COPY config.py .
COPY alembic.ini .

CMD ["python", "-c", "print('subnet ready')"]
