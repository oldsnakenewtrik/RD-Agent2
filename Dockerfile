FROM python:3.10-slim

WORKDIR /app

# Set environment variable for setuptools-scm to use a fixed version
ENV SETUPTOOLS_SCM_PRETEND_VERSION=0.1.0

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# Create a directory for data
RUN mkdir -p /app/data

# Install specific dependencies first to ensure they're available
RUN pip install rich numpy pandas matplotlib streamlit openai ipython fire

# Then install the package in development mode
RUN pip install -e .

# Expose the port Railway will use
EXPOSE ${PORT:-8080}

# Create a startup script that tries both server approaches
RUN echo '#!/bin/bash \n\
echo "Attempting to start with railway_server.py..." \n\
python railway_server.py || { \n\
  echo "First approach failed, trying railway_ui_server.py..." \n\
  python railway_ui_server.py; \n\
}' > /app/start.sh && chmod +x /app/start.sh

# Default command
CMD ["/app/start.sh"]
