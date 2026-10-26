FROM python:3.11-slim

WORKDIR /app

# Ensure Python output is sent straight to terminal without buffering
ENV PYTHONUNBUFFERED=1

# Install Python dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy repository files into the container
COPY . .

# Expose port (7860 is the default port for Hugging Face Spaces)
ENV PORT=7860
EXPOSE 7860

# Start production Gunicorn server with 1 worker to optimize RAM for TensorFlow
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--workers", "1", "--threads", "2", "--timeout", "120", "app:app"]
