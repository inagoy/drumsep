ARG BASE=python:3.10-slim
FROM ${BASE}

# ffmpeg: normalization pass in processing.py. libsndfile1: demucs/torchaudio.
# git: only needed to fetch the drumsep repo/model at build time.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libsndfile1 git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir demucs gdown

# drumsep repo + pretrained Hybrid Demucs model, baked into the image so
# cold starts don't need to download ~80MB from Drive on every instance.
RUN git clone --depth 1 https://github.com/inagoy/drumsep.git /drumsep \
    && mkdir /drumsep/model \
    && cd /drumsep/model && gdown 1-Dm666ScPkg8Gt2-lK3Ua0xOudWHZBGC

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py processing.py gcs_utils.py ./

ENV PORT=8080 \
    DEMUCS_MODEL_REPO=/drumsep/model \
    DEMUCS_MODEL_NAME=49469ca8

# Single worker: demucs is CPU/RAM heavy, we rely on Cloud Run
# `--concurrency 1` + autoscaling for isolation instead of in-process
# parallelism (see infra/README.md).
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1
