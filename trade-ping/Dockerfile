FROM python:3.11-slim

RUN adduser --disabled-password --gecos '' appuser
USER appuser
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Compile protobuf
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. trade.proto

ENV REDIS_HOST=redis
ENV TRADE_CORE_HOST=mock-trade-core
ENV TRADE_CORE_PORT=50051

EXPOSE 8000
CMD ["python", "app.py"]
