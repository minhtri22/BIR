FROM python:3.12-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY requirements.lock pyproject.toml alembic.ini ./
COPY migrations ./migrations
COPY apps ./apps
COPY packages ./packages

RUN pip install --no-cache-dir -r requirements.lock

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8000"]

