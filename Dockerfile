# Use lightweight official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY bot/ ./bot/
COPY .env.example .
COPY tv_alert_indicator.pine .

# Default command runs the Standalone 24/7 Bot
# (Can be overridden to run Webhook server via docker-compose or CMD)
CMD ["python", "-m", "bot.standalone_bot"]
