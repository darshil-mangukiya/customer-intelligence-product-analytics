FROM python:3.12.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.lock ./
RUN python -m pip install --no-cache-dir --require-hashes -r requirements.lock \
    && groupadd --system app \
    && useradd --system --gid app --create-home app

COPY --chown=app:app . .

USER app

CMD ["python", "-m", "etl.run_pipeline", "--customers", "5000", "--products", "250", "--orders", "25000", "--sessions", "18000"]
