FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system forgeml && adduser --system --ingroup forgeml forgeml

COPY pyproject.toml README.md ./
COPY backend ./backend

RUN pip install --no-cache-dir .

USER forgeml

EXPOSE 8000

CMD ["uvicorn", "forgeml.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "backend/src"]

