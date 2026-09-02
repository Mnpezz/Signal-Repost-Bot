FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml requirements.txt README.md ./
COPY signal_repost_bot/ ./signal_repost_bot/

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir .

# Create volume directory for sqlite database and config
RUN mkdir -p /app/data

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["signal-repost-bot"]
CMD ["run"]
