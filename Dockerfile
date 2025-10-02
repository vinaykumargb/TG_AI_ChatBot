# Use official Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy local files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
ENV GEMINI_API_KEY=${GEMINI_API_KEY}

# Run your bot
CMD ["python", "ai.py"]