FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --system stockfight \
    && useradd --system --gid stockfight --no-create-home stockfight \
    && install -d -o stockfight -g stockfight /app/instance

COPY stockfight ./stockfight
COPY data/demo_market.csv ./data/demo_market.csv
COPY run.py .

USER stockfight
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--worker-class", "gthread", "--threads", "32", "--access-logfile", "-", "run:app"]
