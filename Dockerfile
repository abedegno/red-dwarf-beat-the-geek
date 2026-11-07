# Toolchain image only: mount your own VIDEO_TS read-only and a writable workspace.
FROM node:22-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 build-essential pkg-config libdvdread-dev libdvdnav-dev libssl-dev ffmpeg ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /project
COPY app/package.json app/package-lock.json ./app/
RUN npm --prefix app ci
COPY . .
ENTRYPOINT ["python3", "tools/btg.py"]
CMD ["--help"]
