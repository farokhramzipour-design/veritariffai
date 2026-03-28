# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
# We try to avoid build-essential to save space.
# psycopg[binary] should include necessary binaries.
# If you strictly need libpq-dev for some reason, we can add it back,
# but for now we try to keep it slim to avoid disk space issues.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/archives/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["sh", "-c", "set -e; if [ \"${RESET_DB_ON_START:-}\" = \"1\" ] || [ \"${RESET_DB_ON_START:-}\" = \"true\" ]; then python3 -c \"from app.infrastructure.database.session import reset_db_sync, run_migrations_sync; reset_db_sync(); run_migrations_sync(raise_on_error=True)\"; fi; CELERY_PID=''; BEAT_PID=''; if [ \"${RUN_CELERY:-}\" = \"1\" ] || [ \"${RUN_CELERY:-}\" = \"true\" ]; then celery -A app.infrastructure.workers.celery_app.celery_app worker -l ${CELERY_LOG_LEVEL:-info} -Q ${CELERY_QUEUES:-data_ingestion} --concurrency=${CELERY_CONCURRENCY:-2} & CELERY_PID=$!; fi; if [ \"${RUN_CELERY_BEAT:-}\" = \"1\" ] || [ \"${RUN_CELERY_BEAT:-}\" = \"true\" ]; then celery -A app.infrastructure.workers.celery_app.celery_app beat -l ${CELERY_LOG_LEVEL:-info} & BEAT_PID=$!; fi; gunicorn app.main:app --workers ${WEB_WORKERS:-4} --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 & WEB_PID=$!; trap 'kill -TERM $WEB_PID 2>/dev/null || true; if [ -n \"$CELERY_PID\" ]; then kill -TERM $CELERY_PID 2>/dev/null || true; fi; if [ -n \"$BEAT_PID\" ]; then kill -TERM $BEAT_PID 2>/dev/null || true; fi; wait' INT TERM; wait $WEB_PID"]
