web: gunicorn joy_lms.wsgi --workers 2 --bind 0.0.0.0:$PORT --timeout 120
worker: celery -A joy_lms worker --loglevel=info --concurrency=2
beat: celery -A joy_lms beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
