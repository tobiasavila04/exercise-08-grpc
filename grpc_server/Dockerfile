FROM python:3.14-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY grpc_server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY proto/ proto/
COPY grpc_server/ .
RUN python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/node_registry.proto
CMD ["python", "server.py"]