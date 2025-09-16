FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends         ca-certificates         && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

ENV PYTHONUNBUFFERED=1

# Smithery will start the server using the smithery.yaml startCommand (stdio)
CMD ["python", "server.py"]
