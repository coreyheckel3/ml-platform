FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system forgeml && adduser --system --ingroup forgeml forgeml

RUN pip install --no-cache-dir \
    scikit-learn \
    xgboost \
    lightgbm \
    torch \
    mlflow

COPY ml ./ml
USER forgeml

CMD ["python", "-m", "ml.libraries.forgeml_sdk"]

