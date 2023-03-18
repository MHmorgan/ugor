# syntax=docker/dockerfile:1

# Docker file with gunicorn?
# https://github.com/tiangolo/uvicorn-gunicorn-docker

FROM python:3.11-alpine

ENV DATABASE="/data/ugor.sqlite3"

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

COPY . .

EXPOSE 80

# Optimize with -OO to remove debug, assertions and docstrings
CMD ["python3", "-OO", "-m", "gunicorn", "--workers", "2", "--bind", "0.0.0.0:80", "app:create_app()"]
