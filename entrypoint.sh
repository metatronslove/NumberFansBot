#!/bin/bash
# Ensure /code is writable by appuser
chown -R appuser:appuser /code
chmod -R u+w /code

# Run the application
exec "$@"
