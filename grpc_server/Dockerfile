FROM python:3.14-slim
WORKDIR /app
COPY grpc_server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY proto/ proto/
COPY Makefile .
COPY grpc_server/ .
RUN make proto
CMD ["python", "server.py"]