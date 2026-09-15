# Use official Python 3.11 slim image
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (for building packages if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and application files
COPY src/ ./src/
COPY app.py main.py generate_samples.py ./
COPY data/ ./data/

# Create output directories
RUN mkdir -p output/structured_data output/customer_emails output/case_summaries

# Expose FastAPI server port
EXPOSE 8000

# Default command launches FastAPI server with uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
