# ====================================================================
# STAGE 1: The "Builder" Stage
# This stage installs dependencies and builds our static assets.
# ====================================================================
FROM python:3.11-slim as builder

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# --- REFINED: Install system dependencies for building ---
# We've added g++, libjpeg-dev, and zlib1g-dev to support
# building libsass and Pillow from your requirements.txt.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the builder
COPY . .

# Run collectstatic. This will gather all Django static files and
# also trigger django-sass-processor to compile your SASS into CSS.
RUN DJANGO_SECRET_KEY='this-is-a-dummy-key-for-the-build-process-only'
RUN DJANGO_SETTINGS_MODULE=sheltertree_project.settings.production python manage.py collectstatic --noinput

# ====================================================================
# STAGE 2: The "Runner" Stage
# This is the final, lean, and secure image that will be deployed.
# ====================================================================
FROM python:3.11-slim

WORKDIR /app

# Set environment variables for the final image
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE=sheltertree_project.settings.production

# --- REFINED: Install only necessary RUNTIME system dependencies ---
# We add libjpeg62-turbo and zlib1g which are the runtime libraries
# needed for Pillow to operate.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libjpeg62-turbo \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

# Create a dedicated, non-root user for security
RUN addgroup --system app && adduser --system --group app

# Copy the installed Python packages from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy the collected static files (including your compiled CSS) from the builder stage
COPY --from=builder /app/staticfiles /app/staticfiles/

# Copy the application code from the builder stage
COPY --from=builder /app /app

# Change ownership of all files to our non-root user
RUN chown -R app:app /app

# Switch to the non-root user
USER app

# The command to run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "sheltertree_project.wsgi:application"]