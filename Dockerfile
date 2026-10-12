FROM brainicism/bgutil-ytdlp-pot-provider:2.0.2-node AS bgutil_server

FROM python:3.11-slim

# Install FFmpeg, fonts, curl and Node.js 22 (for YouTube BotGuard PO-Token server & yt-dlp)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-dejavu-core \
    fonts-freefont-ttf \
    curl \
    ca-certificates \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-built BotGuard PO-Token Server from official image (port 4416)
COPY --from=bgutil_server /app /opt/bgutil/server

WORKDIR /app

# Install Python requirements (including latest yt-dlp + bgutil-ytdlp-pot-provider plugin)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --upgrade -r requirements.txt

# Copy application source
COPY . .

# Create storage volumes
RUN mkdir -p storage/inputs storage/outputs storage/temp

# Generate built-in assets
RUN python assets/generate_assets.py

ENV HOST=0.0.0.0
ENV PORT=8080

# Start BotGuard PO-Token Server on 127.0.0.1:4416 in background, then start FastAPI Uvicorn server
CMD ["sh", "-c", "node /opt/bgutil/server/build/main.js --port 4416 & sleep 2 && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
