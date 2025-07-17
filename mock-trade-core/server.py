import random, time, pathlib, subprocess
import grpc
from concurrent import futures
from prometheus_client import start_http_server, Counter, Histogram

PROTO_PATH = pathlib.Path(__file__).with_name("trade.proto")

def compile_proto():
    subprocess.check_call([
        "python", "-m", "grpc_tools.protoc",
        f"-I{PROTO_PATH.parent}",
        f"--python_out={PROTO_PATH.parent}",
        f"--grpc_python_out={PROTO_PATH.parent}",
        str(PROTO_PATH)
    ])

try:
    import trade_pb2, trade_pb2_grpc
except ModuleNotFoundError:
    compile_proto()
    import trade_pb2, trade_pb2_grpc

REQUESTS = Counter('mock_trade_core_requests_total', 'Total trade requests received')
LATENCY = Histogram('mock_trade_core_latency_seconds', 'Backend processing latency seconds', buckets=[0.005,0.01,0.02,0.05,0.1,0.2,0.5,1])

class TradeService(trade_pb2_grpc.TradeServiceServicer):
    def SubmitTrade(self, request, context):
        start = time.perf_counter()
        time.sleep(random.uniform(0.005, 0.02))  # simulate processing delay
        latency = time.perf_counter() - start
        REQUESTS.inc()
        LATENCY.observe(latency)
        trade_id = f"TR{random.randint(1000000, 9999999)}"
        return trade_pb2.TradeResponse(status="ACCEPTED", trade_id=trade_id, latency_ms=int(latency*1000))

def serve():
    start_http_server(9100)  # Prometheus metrics
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    trade_pb2_grpc.add_TradeServiceServicer_to_server(TradeService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("mock-trade-core running on :50051, metrics :9100")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
