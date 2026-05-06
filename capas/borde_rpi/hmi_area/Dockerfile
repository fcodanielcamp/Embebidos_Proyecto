# Cambiamos buster por bullseye para evitar los repositorios obsoletos
FROM python:3.9-slim-bullseye

# Instalación de dependencias
RUN apt-get update && apt-get install -y \
    python3-dev \
    libgpiod-dev \
    build-essential \
    libopencv-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "hmi_main.py"]