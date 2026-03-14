FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Layer 1: PyTorch CPU only (Save 4GB+)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Layer 2: All other dependencies
COPY requirements_docker.txt .
RUN pip install --no-cache-dir -r requirements_docker.txt

# Layer 3: Application Code & Data
COPY src/ ./src/
COPY chroma_db/ ./chroma_db/

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
