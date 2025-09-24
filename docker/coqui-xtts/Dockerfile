FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    COQUI_APP_HOME=/app \
    COQUI_DATA_HOME=/models \
    COQUI_TOS_ACCEPTED=1 \
    XDG_DATA_HOME=/models/.local/share \
    XDG_CACHE_HOME=/models/.cache \
    TTS_HOME=/models/tts

WORKDIR ${COQUI_APP_HOME}

COPY requirements.txt ./requirements.txt

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        libsndfile1 \
        git \
        build-essential \
    && pip install --upgrade pip \
    && pip install --extra-index-url https://download.pytorch.org/whl/cu121 \
        torch==2.1.2+cu121 \
        torchvision==0.16.2+cu121 \
        torchaudio==2.1.2+cu121 \
    && pip install --extra-index-url https://pypi.nvidia.com nvidia-cudnn-cu12==9.1.0.70 \
    && pip install -r requirements.txt \
    && apt-get purge -y git build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY app ./app

ENV HF_HOME=${COQUI_DATA_HOME}/huggingface \
    COQUI_CACHE_DIR=${COQUI_DATA_HOME}/cache \
    COQUI_SPEECH_PORT=5000 \
    LD_LIBRARY_PATH=/usr/local/lib/python3.10/site-packages/nvidia/cudnn/lib:${LD_LIBRARY_PATH}

EXPOSE 5000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]
