# ====================================================================
# STAGE 1: The "Builder" Stage
# ====================================================================
FROM python:3.11-slim as builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev

COPY requirements.txt .
# Use --prefix=/install to isolate packages, making them easier to copy
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

COPY . .

# IMPORTANT: Set the DJANGO_SETTINGS_MODULE for the collectstatic command
# This was already correct in your file.
RUN DJANGO_SETTINGS_MODULE=sheltertree_project.settings.production /install/bin/python manage.py collectstatic --noinput

# ====================================================================
# STAGE 2: The "Runner" Stage
# ====================================================================
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE=sheltertree_project.settings.production

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libjpeg62-turbo \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system app && adduser --system --group app

# Copy installed packages from the builder stage
COPY --from=builder /install /usr/local

# Copy the application code from the builder stage
# This includes the staticfiles directory created by collectstatic
COPY --from=builder /app /app

RUN chown -R app:app /app

USER app

# The command to run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "sheltertree_project.wsgi:application"]