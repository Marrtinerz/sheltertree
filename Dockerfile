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
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ====================================================================
# STAGE 2: The "Runner" Stage (No changes needed here)
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

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app/staticfiles /app/staticfiles/
COPY . .

RUN chown -R app:app /app
USER app

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "sheltertree_project.wsgi:application"]