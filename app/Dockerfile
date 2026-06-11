FROM python:3.11-slim

WORKDIR /app

# Install uv for fast package installation
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Compile pyproject.toml to requirements.txt and install dependencies using uv
RUN uv pip compile pyproject.toml -o requirements.txt && uv pip install --system -r requirements.txt

# Copy application source code
COPY . .

# Expose port
EXPOSE 8080

# Set Python Path
ENV PYTHONPATH=/app

# Run uvicorn FastAPI server
CMD ["uvicorn", "app.fast_api_app:app", "--host", "0.0.0.0", "--port", "8080"]
