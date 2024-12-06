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
RUN rm -rf /var/lib/apt/lists/*

# --- #

COPY src/api/requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY --from=0 /build/build /app/build
COPY src/api/src .

EXPOSE 80
# ENV PORT=80

CMD [ "python3", "main.py"]

