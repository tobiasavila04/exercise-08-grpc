FROM python:3.14-slim
WORKDIR /app
COPY gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY proto/ proto/
COPY gateway/ .
RUN python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/node_registry.proto
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]