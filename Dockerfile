FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && \
    DEBIAN_FRONTEND="noninteractive" apt-get install -y --no-install-recommends \
    python3-pip \
    build-essential \
    ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser

# Create /code directory with correct permissions
RUN mkdir /code && \
    chown -R appuser:appuser /code

# Upgrade pip and install dependencies
RUN pip3 install --no-cache-dir -U pip wheel setuptools==69.5.1
COPY ./requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Copy application code and entrypoint
COPY --chown=appuser:appuser . /code
COPY --chown=appuser:appuser entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
WORKDIR /code

# Create config file with proper permissions
RUN touch Config/config.yml && \
    echo "{}" > Config/config.yml && \
    chown appuser:appuser Config/config.yml && \
    chmod u+w Config/config.yml

# Switch to non-root user
USER appuser

# Expose port (Render assigns dynamically, so this is informational)
EXPOSE $PORT

# Use entrypoint
ENTRYPOINT ["/entrypoint.sh"]
CMD ["sh", "-c", "python Bot/seed_admin.py && uvicorn Bot.admin_panel:app --host 0.0.0.0 --port $PORT --lifespan off"]
