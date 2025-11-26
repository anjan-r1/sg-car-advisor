FROM python:3.11-slim

# Don't write .pyc, flush output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (build-essential in case any wheel compilation is needed)
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Hugging Face Spaces will set $PORT, default to 7860
EXPOSE 7860

# Start Flask app via gunicorn
CMD ["bash", "-c", "gunicorn -w 2 -b 0.0.0.0:${PORT:-7860} app:app"]
