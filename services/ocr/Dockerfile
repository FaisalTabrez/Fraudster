FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /service
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libgomp1 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
COPY requirements-model.txt .
COPY install_model.py runtime-wheels.json ./
ARG INSTALL_OCR=false
RUN pip install --no-cache-dir -r requirements.txt
RUN if [ "$INSTALL_OCR" = "true" ]; then python install_model.py; fi
COPY app ./app

USER 65532:65532
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
