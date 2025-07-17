FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Compile protobuf
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. trade.proto

EXPOSE 50051 9100
CMD ["python", "server.py"]
