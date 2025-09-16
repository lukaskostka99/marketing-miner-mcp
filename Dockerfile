FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends         ca-certificates         && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

# Default runtime env
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV MCP_HTTP_PATH=/mcp
EXPOSE 8000

# Start Streamable HTTP transport (Smithery expects HTTP, not STDIO)
CMD ["python", "server.py"]
