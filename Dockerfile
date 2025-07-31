FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Installer docker CLI
RUN apt-get update && \
    apt-get install -y docker.io curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy backend code
COPY backend/ /app/backend/

# Install backend dependencies
RUN pip install --upgrade pip && \
    pip install -r /app/backend/requirements.txt

# Expose FastAPI port
EXPOSE 8000

# Copy frontend (optional)
COPY frontend/ /app/frontend/

# Install FastAPI and Uvicorn
RUN pip install fastapi[all] && pip install uvicorn

# Run FastAPI app
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
