# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV FLASK_APP=run.py # Points to the main run script
ENV FLASK_ENV=production
# Add any other environment variables needed by your app
# ENV MY_VARIABLE=my_value

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (if any)
# For example, if matplotlib needs fontconfig and you didn't list it in environment.yml for conda
# RUN apt-get update && apt-get install -y --no-install-recommends fontconfig && rm -rf /var/lib/apt/lists/*
# From your environment.yml, fontconfig was listed, implying it might be needed.
# If skyfield or other libraries have C extensions, you might need build-essential, etc.
# RUN apt-get update && apt-get install -y --no-install-recommends build-essential libffi-dev

# Copy the requirements file first to leverage Docker cache
COPY requirements/production.txt requirements/production.txt
COPY requirements/base.txt requirements/base.txt

# Install dependencies
# It's good practice to upgrade pip first
RUN pip install --upgrade pip
RUN pip install -r requirements/production.txt

# Copy the rest of the application code into the container
# Ensure .dockerignore is properly set up to exclude unnecessary files
COPY . .

# Make port 8080 available to the world outside this container (or your chosen Gunicorn port)
EXPOSE 8080 

# Define the command to run the application using Gunicorn
# The number of workers can be tuned. A common recommendation is (2 * CPU_CORES) + 1.
# Example: CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:8080", "run:app"] 
# run:app refers to the 'app' Flask object inside your 'run.py' script.
# However, run.py itself calls app.run(), which is for development.
# For Gunicorn, you usually point to the app object directly from the app package.
# So, it should be app:app (referring to app/__init__.py's 'app' object)
CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:8080", "app:app"] 