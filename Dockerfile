FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && \
    DEBIAN_FRONTEND="noninteractive" apt-get install -y --no-install-recommends \
    python3-pip \
    build-essential \
    ffmpeg \
    git && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash appuser && \
    mkdir /code && \
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

# Expose port for Render.com
EXPOSE 8000

# Use entrypoint
ENTRYPOINT ["/entrypoint.sh"]
CMD ["sh", "-c", "python Bot/seed_admin.py && gunicorn Bot.admin_panel:app -b 0.0.0.0:8000"]
