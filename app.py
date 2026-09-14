import json

from flask import Flask, Response, render_template, request, stream_with_context

from muddy_puddles import tickers
from scanner_web import run_scan, get_ticker_detail

app = Flask(__name__)
TOTAL_TICKERS = len(tickers)


def _sse(payload):
    """Format one Server-Sent-Events message."""
    return f"data: {json.dumps(payload)}\n\n"


@app.route("/")
def index():
    return render_template("index.html", total=TOTAL_TICKERS)


@app.route("/scan")
def scan():
    """Streams live progress while the scan runs (Server-Sent Events)."""
    choice = request.args.get("choice", "a")
    if choice not in ("a", "b"):
        choice = "a"

    @stream_with_context
    def generate():
        try:
            for msg in run_scan(choice):
                yield _sse(msg)
        except Exception as e: 
            yield _sse({"type": "error", "message": str(e)})

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no", 
    }
    return Response(generate(), mimetype="text/event-stream", headers=headers)


@app.route("/ticker/<symbol>")
def ticker(symbol):
    symbol = symbol.upper()
    choice = request.args.get("choice", "a")
    if choice not in ("a", "b"):
        choice = "a"

    detail = get_ticker_detail(symbol, choice)
    if detail is None:
        return render_template("ticker.html", ticker=symbol, choice=choice,
                               error=f"No data available for {symbol}.")

    return render_template(
        "ticker.html",
        ticker=symbol,
        choice=choice,
        res=detail["res"],
        chart_json=json.dumps(detail["chart"]),
        error=None,
    )

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, threaded=True)
