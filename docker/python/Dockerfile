FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    libgdal-dev \
    gdal-bin \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

COPY python /app
COPY docker/python/requirements.txt /app/requirements.txt

WORKDIR /app/scripts
RUN pip install -r /app/requirements.txt

CMD ["python", "run_routing.py"]
