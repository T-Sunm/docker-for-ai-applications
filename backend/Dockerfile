FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_DIR=/models

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        libxcb1 \
        libgl1 \
        libglib2.0-0t64 \
    && rm -rf /var/lib/apt/lists/*

COPY app ./src
COPY scripts ./scripts

EXPOSE 8000
CMD ["uvicorn", "main:app", "--app-dir", "/app/src", "--host", "0.0.0.0", "--port", "8000"]
