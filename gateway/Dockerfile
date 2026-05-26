FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY gateway/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy proto and generate stubs in /app/
COPY proto/ proto/
RUN python -m grpc_tools.protoc \
      -I proto \
      --python_out=. \
      --grpc_python_out=. \
      proto/node_registry.proto

# Copy gateway app directly into /app/ so imports resolve
COPY gateway/app.py app.py

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
