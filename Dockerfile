# Use an official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy backend code
COPY backend/ /app/backend/

# Install backend dependencies
RUN pip install --upgrade pip && \
    pip install -r /app/backend/requirements.txt

# Expose FastAPI port
EXPOSE 8000

# Copy frontend (for static serving or development)
COPY frontend/ /app/frontend/

# Optionally install a simple web server for static files
RUN pip install fastapi[all] && pip install uvicorn

# Start FastAPI backend
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
