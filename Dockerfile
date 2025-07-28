FROM --platform=linux/amd64 python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-jpn \
    tesseract-ocr-fra \
    tesseract-ocr-deu \
    tesseract-ocr-spa \
    libtesseract-dev \
    poppler-utils \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

# Copy application code
COPY . .

# Create directories
RUN mkdir -p /app/input /app/output

# Set Python path
ENV PYTHONPATH=/app

# Make main script executable
RUN chmod +x main.py

# Set entry point
ENTRYPOINT ["python", "main.py"]
