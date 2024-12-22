FROM node:20

WORKDIR /build
COPY src/frontend/package*.json .
RUN rm -rf node_modules
RUN rm -rf build
RUN npm install
COPY src/frontend/. .
RUN npm run build
# Thanks https://stackoverflow.com/q/76988450

FROM python:3.10-slim

WORKDIR /app

# Install git, exiftool

RUN add-apt-repository ppa:apt-fast/stable
RUN apt install -y apt-fast
RUN apt update

RUN apt-fast install -y git build-essential xorg libssl-dev libxrender-dev libpango-1.0-0 wget

ENV EXIFTOOL_VERSION="13.06"
RUN wget "https://exiftool.org/Image-ExifTool-${EXIFTOOL_VERSION}.tar.gz"
RUN gzip -dc "Image-ExifTool-${EXIFTOOL_VERSION}.tar.gz" | tar -xf -
WORKDIR /app/Image-ExifTool-${EXIFTOOL_VERSION}
RUN perl Makefile.PL
RUN make test
RUN make install

RUN rm -rf /var/lib/apt/lists/* /app/Image-ExifTool-${EXIFTOOL_VERSION}

WORKDIR /app

# --- #

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY src/api/requirements.txt requirements.txt
COPY src/api/exiftool.config exiftool.config
RUN uv pip install -r requirements.txt --system
COPY --from=0 /build/build /app/src/build
COPY src/api/src src

# Is this still needed?
RUN ln -s /app/src/pdf/fonts /tmp/fonts

WORKDIR /app/src

EXPOSE 80

CMD [ "python3", "main.py"]
