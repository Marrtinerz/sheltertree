# Use an official Python runtime as a parent image
FROM python:3

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1


# --- ADD THIS SECTION ---
# Install system dependencies, including gettext for translations
RUN apt-get update && apt-get install -y gettext --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*
# --- END SECTION ---
    
# Set the working directory in the container
WORKDIR /app

# Install dependencies
# We copy the requirements file first to take advantage of Docker caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
RUN python manage.py populate_locations

# Copy the rest of the project files into the container
COPY . /app/

# The command to run when the container starts
# We will override this in docker-compose, but it's good practice to have it.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]