FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1     PORT=8000     HOST=0.0.0.0     MCP_HTTP_PATH=/mcp

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

EXPOSE 8000

CMD ["python", "server.py"]
