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

# Install git, wkhtmltopdf (https://raw.githubusercontent.com/JazzCore/python-pdfkit/b7bf798b946fa5655f8e82f0d80dec6b6b13d414/ci/before-script.sh)
RUN apt update

RUN apt install -y git

ENV WKHTML2PDF_VERSION='0.12.6-1'
RUN apt install -y build-essential xorg libssl-dev libxrender-dev wget
RUN wget "https://github.com/wkhtmltopdf/packaging/releases/download/${WKHTML2PDF_VERSION}/wkhtmltox_${WKHTML2PDF_VERSION}.bionic_amd64.deb"
RUN sudo apt install -y ./wkhtmltox_${WKHTML2PDF_VERSION}.bionic_amd64.deb
RUN rm wkhtmltox_${WKHTML2PDF_VERSION}.bionic_amd64.deb

ENV EXIFTOOL_VERSION="13.06"
RUN wget "https://exiftool.org/Image-ExifTool-${EXIFTOOL_VERSION}.tar.gz"
RUN gzip "Image-ExifTool-${EXIFTOOL_VERSION}.tar.gz" | tar -xf -
WORKDIR /app/Image-ExifTool-${EXIFTOOL_VERSION}
RUN perl Makefile.PL
RUN make test
RUN sudo make install

RUN rm -rf /var/lib/apt/lists/* /app/Image-ExifTool-${EXIFTOOL_VERSION}

WORKDIR /app

# --- #

COPY src/api/requirements.txt requirements.txt
COPY src/api/exiftool.config exiftool.config
RUN pip3 install -r requirements.txt
COPY --from=0 /build/build /app/src/build
COPY src/api/src src

WORKDIR /app/src

EXPOSE 80
# ENV PORT=80

CMD [ "python3", "main.py"]

