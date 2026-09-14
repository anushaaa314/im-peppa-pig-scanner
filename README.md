# im peppa pig yayayayayaya
ONLY RUN THIS ON THE WEEKEND ONCE THE MARKET CLOSES, OR YOU WILL BE SCANNING AN UNFINISHED WEEK! 

A website that runs a weekly stock breakout scan across ~2,000 tickers. It
lets you watch the progress live, shows the matches in a sortable table, and
opens a detail page (with an interactive weekly chart) for any ticker you click.

I originally built the logic and scanner part of it with python and the free library yfinance, and used some AI to turn it into an actual website. The terminal-based program my_little_brother_george.py is written fully by me. 


For each ticker, it pulls 2 years of weekly candles and runs 7 checks in this order:

1. Uptrend — close above the 40-week EMA, and the 10-week EMA above the 40-week EMA
2. Breakout — closed 4–20% above the highest close of the last 10 weeks
3. Compression — the base was tight before the move (a = range tightening, b = coefficient of variation)
4. Strong bar — this week is bullish with a body ≥ 50% of its range
5. Money flow — Chaikin Money Flow is positive
6. Above AVWAP — close at/above the 52-week anchored VWAP
7. Volume — this week's volume ≥ the recent average

Only tickers that pass ALL SEVEN show up in the results table

# to run it....

```bash
pip install -r requirements.txt
python app.py
```

Then open <http://localhost:5000> in your browser, pick a compression method
(`a` or `b`), and hit **Run Scan**. A full scan takes a few minutes (it's
downloading data for ~1,000 tickers in batches). Needs an internet connection.

## Files

| File | What it is |
|------|------------|
| `muddy_puddles.py` | The ticker universe (a big Python list) |
| `my_little_brother_george.py` | The original scanner logic (untouched) |
| `scanner_web.py` | Web wrapper: live-progress scan + per-ticker chart data |
| `app.py` | Flask server (home, live scan stream, ticker detail) |
| `templates/` | The two pages (home + ticker detail) |
| `static/` | Styling + browser JavaScript |

## Notes

- The live progress uses Server-Sent Events, so keep the browser tab open while
  a scan runs.
- The ticker detail page re-downloads that one ticker fresh, so it always shows
  current data.
- Charts are drawn with Plotly (loaded from a CDN).
