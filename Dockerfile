FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir \
    mcp \
    pyvo \
    pandas

COPY . .

ENTRYPOINT ["python", "server.py"]