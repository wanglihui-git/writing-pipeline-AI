# Writing Pipeline AI — FastAPI API + 静态控制台 /ui
FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    WRITING_PIPELINE_ROOT=/app

WORKDIR /app

# onnxruntime 等二进制轮常见运行时依赖（较 apt 安装 gcc 更轻）
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY app ./app
COPY web ./web
COPY config/app_example.yaml config/app.yaml
COPY config/models_example.yaml config/models.yaml

RUN mkdir -p data/raw data/clean data/chroma data/meta data/tasks

EXPOSE 8980

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8980/health')"

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8980"]
