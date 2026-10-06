FROM python:3.12-slim
WORKDIR /app
COPY app/requirements-live.txt app/requirements.txt ./
RUN pip install --no-cache-dir -r requirements-live.txt orjson psutil
COPY app/ ./
COPY seed.py supervise.py ./capacity/
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 QUIET=1
