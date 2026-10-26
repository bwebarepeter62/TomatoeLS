FROM python:3.11-slim

WORKDIR /app

# Ensure Python output is sent straight to terminal without buffering
ENV PYTHONUNBUFFERED=1

# Install system libraries needed by Pillow/ReportLab and image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy repository files into the container
COPY . .

# Default port (Render overrides with dynamic $PORT)
ENV PORT=7860
EXPOSE 7860

# Start production Gunicorn server with 1 worker and 2 threads to optimize RAM for TensorFlow
CMD exec gunicorn --bind 0.0.0.0:${PORT:-7860} --workers 1 --threads 2 --timeout 120 wsgi:app
