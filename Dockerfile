FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev gcc libffi-dev libssl-dev \
    libmagic1 poppler-utils tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements/base.txt requirements/base.txt
RUN pip install --no-cache-dir -r requirements/base.txt

COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput --settings=joy_lms.settings.base || true

EXPOSE 8000
