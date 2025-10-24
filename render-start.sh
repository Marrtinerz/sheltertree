#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# STEP 1: Compile all SCSS source files into their final CSS output files.
# This will use the settings we configured previously, placing main.css
# into your 'static/css/' directory.

# STEP 2: Collect all static files (including the newly created main.css)
# into the STATIC_ROOT directory (/app/staticfiles).
echo "Collecting static files..."
python manage.py collectstatic --noinput

# STEP 3: Start the Gunicorn server.
# This process will now serve a site with pre-compiled, static CSS.
echo "Starting Gunicorn..."
gunicorn --bind 0.0.0.0:8000 sheltertree_project.wsgi:application