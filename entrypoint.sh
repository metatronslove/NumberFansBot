#!/bin/bash
# Ensure Config directory is writable
chown -R appuser:appuser /code/Config
chmod -R u+w /code/Config

# Run the application
exec "$@"
