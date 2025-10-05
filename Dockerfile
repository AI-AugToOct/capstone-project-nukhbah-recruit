FROM python:3.11

# Set working directory
WORKDIR /app

# Copy dependencies first (for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project (including .env)
COPY . /app

ENV PYTHONPATH=/app
ENV ENV_PATH=/app/.env

EXPOSE 8080

# Run FastAPI (src.app is correct for your structure)
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8080"]

ENV PYTHONUNBUFFERED=1
