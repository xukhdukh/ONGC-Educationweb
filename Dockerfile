FROM python:3.12-slim

# System dependencies (needed for psycopg2, OCR, etc.)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    libffi-dev \
    libssl-dev \
    libmagic1 \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip (IMPORTANT for modern packages like torch, streamlit, etc.)
RUN pip install --upgrade pip

# Install Python dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Collect static files (safe even if settings vary)
RUN python manage.py collectstatic --noinput --settings=joy_lms.settings.base || true

# Expose port for Render
EXPOSE 8000

# Run Django app (Gunicorn recommended for production)
CMD ["gunicorn", "joy_lms.wsgi:application", "--bind", "0.0.0.0:8000"]
