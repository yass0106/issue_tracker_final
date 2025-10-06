# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Expose port
EXPOSE 8000

# Run ASGI server by default
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "issue_tracker.asgi:application"]
