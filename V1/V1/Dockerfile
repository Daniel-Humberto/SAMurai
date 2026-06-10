FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

WORKDIR /app

ENV PYTHONUNBUFFERED=1


RUN apt-get update && apt-get install -y \
    git wget curl \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender-dev \
    libv4l-dev v4l-utils \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -q -r requirements.txt

RUN git clone https://github.com/facebookresearch/sam2.git /app/sam2 && \
    cd /app/sam2 && pip install -e . -q

COPY app/ /app/app/
COPY static/ /app/static/

COPY scripts/download_checkpoint.sh /app/scripts/download_checkpoint.sh

EXPOSE 7860

CMD ["python", "-m", "app.main"]
