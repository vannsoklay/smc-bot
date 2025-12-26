# Use official Python base image
FROM python:latest

# Set working directory
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose gRPC port
EXPOSE 50051

# Run the server
CMD ["python", "-m", "app.main"]
