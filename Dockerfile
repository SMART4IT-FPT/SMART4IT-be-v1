FROM python:3.10.16-slim

# Set working directory
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source code
COPY . .

# Expose FastAPI default port
EXPOSE 7860

# Run the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
