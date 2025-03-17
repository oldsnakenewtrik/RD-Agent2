FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN pip install -e .

# Expose the port Railway will use
EXPOSE ${PORT:-3000}

# Default command if none is provided in Railway dashboard
CMD ["python", "main.py", "kaggle", "--competition", "your-competition-id"]
