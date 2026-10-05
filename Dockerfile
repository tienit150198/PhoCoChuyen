FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOST=0.0.0.0 PORT=8765 QUIET=1
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
RUN groupadd --gid 10001 game && useradd --uid 10001 --gid game --create-home game
COPY server.py /app/
COPY game /app/game
COPY public /app/public
COPY reference/data /app/reference/data
RUN mkdir -p /app/storage && chown -R game:game /app
USER game
EXPOSE 8765
VOLUME ["/app/storage"]
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request,os;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8765')+'/api/health',timeout=4)" || exit 1
CMD ["python", "server.py"]
