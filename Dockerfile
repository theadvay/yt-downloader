# syntax=docker/dockerfile:1
FROM python:3.12-slim

# ffmpeg lets yt-dlp merge high-resolution video + audio and convert audio.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV HOST=0.0.0.0 \
    PORT=5000

EXPOSE 5000

CMD ["python", "app.py"]
