# Use official Python 3.11 image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source files
COPY . .

# Set environment variables (optional, can override in Render dashboard)
ENV AITOKEN=your_telegram_token
ENV GEMINI_API_KEY=your_gemini_api_key

# Command to run your bot
CMD ["python", "ai.py"]