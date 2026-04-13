# Use a slim version to keep the image small and "Lean"
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for some AI libs or health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (leverage Docker cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your agent code
COPY . .

# Expose the port your app runs on (usually 8000 for FastAPI or 8080)
EXPOSE 8080

# Command to run your agent
CMD ["python", "app.py"]