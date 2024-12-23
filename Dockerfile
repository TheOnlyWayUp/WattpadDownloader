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

# Install git, wkhtmltopdf (https://raw.githubusercontent.com/JazzCore/python-pdfkit/b7bf798b946fa5655f8e82f0d80dec6b6b13d414/ci/before-script.sh), exiftool
RUN apt update

RUN apt install -y git build-essential xorg libssl-dev libxrender-dev wget libpango-1.0-0 libpangoft2-1.0-0

# Thanks https://www.reddit.com/r/linux4noobs/comments/1adnavi/comment/kk2uq7u
# RUN wget https://archive.debian.org/debian/pool/main/libj/libjpeg8/libjpeg8_8b-1_amd64.deb
# RUN apt install ./libjpeg8_8b-1_amd64.deb 

ENV WKHTML2PDF_VERSION='0.12.6.1-3'
RUN wget "https://github.com/wkhtmltopdf/packaging/releases/download/${WKHTML2PDF_VERSION}/wkhtmltox_${WKHTML2PDF_VERSION}.bookworm_amd64.deb"
RUN apt install -y ./wkhtmltox_${WKHTML2PDF_VERSION}.bookworm_amd64.deb
RUN rm wkhtmltox_${WKHTML2PDF_VERSION}.bookworm_amd64.deb

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
# COPY src/api/pyproject.toml pyproject.toml
# COPY src/api/uv.lock uv.lock

COPY src/api/exiftool.config exiftool.config
RUN uv pip install -r requirements.txt --system
COPY --from=0 /build/build /app/src/build
COPY src/api/src src

RUN ln -s /app/src/pdf/fonts /tmp/fonts

WORKDIR /app/src

EXPOSE 80
# ENV PORT=80

CMD [ "python3", "main.py"]

