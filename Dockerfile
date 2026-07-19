# Stage 1: Build the React Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Copy package files and install dependencies
COPY portal-admin-frontend/package*.json ./
RUN npm install

# Copy the rest of the frontend code and build
COPY portal-admin-frontend/ ./
RUN npm run build

# Stage 2: Build the Python Backend and serve
FROM python:3.11-slim
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend code
COPY app/ ./app/
COPY seed.py .

# Copy the built frontend from Stage 1 into the location expected by FastAPI
COPY --from=frontend-builder /app/frontend/dist ./portal-admin-frontend/dist

# Expose port 8080 (since 8000 is ERPNext and 5678 is n8n)
EXPOSE 8080

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
