FROM brainicism/bgutil-ytdlp-pot-provider:2.0.2-node AS bgutil_server

FROM python:3.11-slim

# Install FFmpeg, fonts, curl, tar, procps and Node.js 22
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-dejavu-core \
    fonts-freefont-ttf \
    curl \
    ca-certificates \
    gnupg \
    tar \
    procps \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install wgcf and wireproxy for Cloudflare WARP userspace proxy (multi-arch support: amd64 / arm64)
RUN ARCH=$(dpkg --print-architecture) && \
    curl -fsSL "https://github.com/ViRb3/wgcf/releases/download/v2.3.1/wgcf_2.3.1_linux_${ARCH}" -o /usr/local/bin/wgcf && \
    chmod +x /usr/local/bin/wgcf && \
    curl -fsSL "https://github.com/windtf/wireproxy/releases/download/v1.1.3/wireproxy_linux_${ARCH}.tar.gz" | tar -xz -C /usr/local/bin/ && \
    chmod +x /usr/local/bin/wireproxy

# Copy pre-built BotGuard PO-Token Server from official image (port 4416)
COPY --from=bgutil_server /app /opt/bgutil/server

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --upgrade -r requirements.txt

# Copy application source
COPY . .

# Create storage volumes & warp directory
RUN mkdir -p storage/inputs storage/outputs storage/temp /opt/warp && \
    chmod +x entrypoint.sh

# Generate built-in assets
RUN python assets/generate_assets.py

ENV HOST=0.0.0.0
ENV PORT=8080

CMD ["/app/entrypoint.sh"]
