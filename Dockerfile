FROM python:3.10-slim

## Install system dependencies

RUN apt-get update && \
DEBIAN_FRONTEND="noninteractive" apt-get install -y --no-install-recommends \
python3-pip \
build-essential \
ffmpeg \
git && \
rm -rf /var/lib/apt/lists/\*

## Upgrade pip and install dependencies

RUN pip3 install --no-cache-dir -U pip wheel setuptools==69.5.1 COPY ./requirements.txt /tmp/requirements.txt RUN pip3 install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

## Copy application code

COPY . /code
WORKDIR /code

## Expose port for Render.com

## EXPOSE 8000

## Run gunicorn for Flask app

CMD \["gunicorn", "--bind", "0.0.0.0:8000", "Bot.admin_panel:app"\]