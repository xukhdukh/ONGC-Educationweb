FROM python:3.12-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev gcc libffi-dev libssl-dev \
    libmagic1 poppler-utils tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput --settings=joy_lms.settings.base || true

EXPOSE 8000
