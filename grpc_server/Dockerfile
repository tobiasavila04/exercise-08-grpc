FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY grpc_server/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy proto and generate stubs in /app/
COPY proto/ proto/
RUN python -m grpc_tools.protoc \
      -I proto \
      --python_out=. \
      --grpc_python_out=. \
      proto/node_registry.proto

# Copy server code directly into /app/ so imports resolve
COPY grpc_server/server.py server.py

EXPOSE 50051

CMD ["python", "server.py"]
