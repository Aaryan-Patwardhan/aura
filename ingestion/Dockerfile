FROM python:3.11-slim

WORKDIR /app

# Install curl for health check
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY ingestion/requirements.txt /app/ingestion/requirements.txt
RUN pip install --no-cache-dir -r /app/ingestion/requirements.txt

COPY ingestion/ /app/ingestion/
COPY session_manager/ /app/session_manager/
COPY ai/ /app/ai/
COPY common/ /app/common/

# Ensure packages are importable
RUN touch /app/ingestion/__init__.py \
    && touch /app/ingestion/models/__init__.py \
    && touch /app/ingestion/parsers/__init__.py \
    && touch /app/ingestion/routers/__init__.py \
    && touch /app/session_manager/__init__.py \
    && touch /app/ai/__init__.py \
    && touch /app/common/__init__.py

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["python", "-m", "ingestion.main"]
