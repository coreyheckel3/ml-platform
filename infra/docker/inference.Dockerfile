FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system forgeml && adduser --system --ingroup forgeml forgeml
RUN pip install --no-cache-dir fastapi uvicorn mlflow scikit-learn

COPY ml ./ml
USER forgeml

EXPOSE 8080

CMD ["python", "-m", "ml.libraries.forgeml_sdk.inference_runtime"]

