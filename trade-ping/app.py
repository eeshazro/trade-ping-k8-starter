import os, time, pathlib, subprocess, grpc, redis
from flask import Flask, request, render_template_string
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

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

# Prometheus metrics
REQUESTS_TOTAL = Counter("trade_ping_requests_total", "Total trade ping requests")
FAILURES_TOTAL = Counter("trade_ping_failures_total", "Total failures")
LATENCY_HIST = Histogram("trade_ping_request_latency_seconds", "Round‑trip latency seconds", buckets=[0.005,0.01,0.02,0.05,0.1,0.2,0.5,1])

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
TRADE_CORE_HOST = os.getenv("TRADE_CORE_HOST", "localhost")
TRADE_CORE_PORT = os.getenv("TRADE_CORE_PORT", "50051")

r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

app = Flask(__name__)

HTML = """<!doctype html>
<title>Trade Ping</title>
<h1>Submit Trade Ping</h1>
<form method="post">
  Instrument: <input name="instrument" value="AAPL"><br>
  Side: <select name="side"><option>BUY</option><option>SELL</option></select><br>
  Quantity: <input type="number" name="quantity" value="100"><br>
  Price: <input step="0.01" name="price" value="193.50"><br>
  Trader ID: <input name="trader_id" value="alpha007"><br>
  <input type="submit" value="Submit">
</form>
{% if resp %}
<h2>Response</h2>
<pre>{{ resp }}</pre>
{% endif %}
<h2>Recent Trades</h2>
<pre>{{ recent }}</pre>
"""


def submit_trade(trade_dict):
    channel = grpc.insecure_channel(f"{TRADE_CORE_HOST}:{TRADE_CORE_PORT}")
    stub = trade_pb2_grpc.TradeServiceStub(channel)
    REQUESTS_TOTAL.inc()
    start = time.perf_counter()
    try:
        response = stub.SubmitTrade(trade_pb2.TradeRequest(**trade_dict))
        latency = time.perf_counter() - start
        LATENCY_HIST.observe(latency)
        return response, latency
    except grpc.RpcError as exc:
        FAILURES_TOTAL.inc()
        raise

@app.route("/", methods=["GET", "POST"])
def index():
    resp_data = None
    if request.method == "POST":
        trade = {
            "instrument": request.form["instrument"],
            "side": request.form["side"],
            "quantity": int(request.form["quantity"]),
            "price": float(request.form["price"]),
            "trader_id": request.form["trader_id"]
        }
        resp, latency = submit_trade(trade)
        record = {**trade, "trade_id": resp.trade_id, "latency_ms": int(latency*1000)}
        r.lpush("recent_trades", str(record))
        r.ltrim("recent_trades", 0, 9)
        resp_data = record
    recent = "\n".join(r.lrange("recent_trades", 0, 9))
    return render_template_string(HTML, resp=resp_data, recent=recent)

@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
