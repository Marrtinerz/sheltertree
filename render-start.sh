#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Run the collectstatic command
python manage.py collectstatic --noinput

# Start the Gunicorn server
gunicorn --bind 0.0.0.0:8000 sheltertree_project.wsgi:application