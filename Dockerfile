# 1. Python version
FROM python:3.11

# 2. Specify the working directory
WORKDIR /app

# 3. Copy the current directory contents into the container
COPY . /app

# 4. pip installing the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Port
EXPOSE 8080

# 6. Terminal command to run the app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]

ENV PYTHONUNBUFFERED=1