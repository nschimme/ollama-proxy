# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any necessary dependencies
RUN pip install --no-cache-dir aiohttp

# Expose the port the app runs on
EXPOSE 11434

# Define environment variable
ENV TARGET_URL=http://192.168.0.200:11434

# Run the application
CMD ["python", "proxy.py"]

