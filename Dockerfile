# Production image: gunicorn serving the app, static files built in, running as a non-root user.
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
RUN useradd --create-home --uid 1000 app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
# collectstatic needs settings to import; these values exist only for this build step.
RUN DJANGO_SECRET_KEY=build-only DJANGO_DEBUG=0 python manage.py collectstatic --noinput \
    && mkdir -p /app/private_media /app/media && chown -R app:app /app/private_media /app/media

USER app
EXPOSE 8000
# Shell form so PORT and WEB_CONCURRENCY (set by the host) are expanded; exec keeps gunicorn PID 1.
CMD exec gunicorn config.wsgi --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} \
    --timeout 60 --access-logfile -
