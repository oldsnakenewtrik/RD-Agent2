FROM python:3.10-slim

WORKDIR /app

# Set environment variable for setuptools-scm to use a fixed version
ENV SETUPTOOLS_SCM_PRETEND_VERSION=0.1.0

COPY . .

RUN pip install -e .

# Expose the port Railway will use
EXPOSE ${PORT:-3000}

# Default command if none is provided in Railway dashboard
CMD ["python", "main.py", "kaggle", "--competition", "your-competition-id"]
