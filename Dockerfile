FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for EasyOCR and PyMuPDF
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY app/ ./app/
COPY data/ ./data/
COPY models/ ./models/

# Create __init__.py files
RUN touch src/__init__.py src/ingestion/__init__.py src/ner/__init__.py \
    src/flagging/__init__.py src/llm/__init__.py \
    src/history/__init__.py src/api/__init__.py

EXPOSE 8000 8501

# Default: run FastAPI
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
