FROM node:20-alpine

WORKDIR /build
COPY src/frontend/package*.json .
RUN rm -rf node_modules
RUN rm -rf build
RUN npm install
COPY src/frontend/. .
RUN npm run build
# Thanks https://stackoverflow.com/q/76988450

FROM python:3.13-slim

WORKDIR /app

RUN apt update && \
    apt install -y git build-essential python3.13-dev libglib2.0-0 libpango-1.0-0 libpangoft2-1.0-0 && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*
# aiohttp-client-cache depends on multipart, which requires python3.13-dev to build successfully on 3.13
# weasyprint depends on libgoject, libpango, and libpangoft2
# https://github.com/TheOnlyWayUp/WattpadDownloader/pull/82#discussion_r2470358950


WORKDIR /app

# --- #

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY src/api/pyproject.toml /app
RUN uv sync && uv cache clean
COPY src/api/ /app
COPY --from=0 /build/build /app/src/build

RUN ln -s /app/src/pdf/fonts /tmp/fonts

WORKDIR /app/src

EXPOSE 80

CMD [ "uv", "run", "main.py"]
