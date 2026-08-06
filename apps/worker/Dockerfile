FROM python:3.12-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY requirements.lock pyproject.toml ./
COPY apps ./apps
COPY packages ./packages

RUN pip install --no-cache-dir -r requirements.lock

CMD ["python", "-m", "apps.worker.app.main"]

