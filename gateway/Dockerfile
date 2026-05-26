FROM python:3.14-slim
WORKDIR /app
COPY gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY proto/ proto/
COPY Makefile .
COPY gateway/ .
RUN make proto
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]