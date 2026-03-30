FROM python:3.11-slim

WORKDIR /app

COPY finalizer/requirements.txt /app/finalizer/requirements.txt
RUN pip install --no-cache-dir -r /app/finalizer/requirements.txt

COPY finalizer/ /app/finalizer/
COPY ai/ /app/ai/
COPY common/ /app/common/

RUN touch /app/finalizer/__init__.py \
    && touch /app/ai/__init__.py \
    && touch /app/common/__init__.py

ENV PYTHONPATH=/app

CMD ["python", "-m", "finalizer.session_finalizer"]
