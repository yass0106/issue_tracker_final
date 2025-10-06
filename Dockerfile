# ================================
# 1. Base Image
# ================================
FROM python:3.11-slim

# Prevent Python from writing .pyc files & buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ================================
# 2. Set Work Directory
# ================================
WORKDIR /app

# ================================
# 3. Install System Dependencies
# ================================
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ================================
# 4. Install Python Dependencies
# ================================
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# ================================
# 5. Copy Project
# ================================
COPY . .

# ================================
# 6. Collect Static Files
# (optional — for production)
# ================================
RUN python manage.py collectstatic --noinput

# ================================
# 7. Expose Port
# ================================
EXPOSE 8000

# ================================
# 8. Start Server
# Using Daphne to support WebSockets
# ================================
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "your_project_name.asgi:application"]
