"""
scanner_web.py
--------------
The bridge between your terminal scanner and the website.

It reuses your EXACT scanning logic from my_little_brother_george.py
(nothing about the strategy changes). All it adds is:

  1. run_scan(choice)  -> a generator that yields live progress as it works,
                          so the browser can watch a progress bar move, then
                          yields the final results.

  2. get_ticker_detail(ticker, choice) -> rebuilds everything for ONE ticker
                          (metrics + the c1..c7 verdict + the numbers needed
                          to draw the weekly chart on the detail page).
"""

import math
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf

# Import your list + your logic. We do NOT re-implement the strategy.
from muddy_puddles import tickers
from my_little_brother_george import (
    check_ticker,
    ema_calc,
    BATCH_SIZE,
    EMA_LONG,
    EMA_SHORT,
    LOOKBACK,
    BREAKOUT_MIN_PCT,
    BREAKOUT_MAX_PCT,
)

# Two years of weekly data, same as your scanner uses.
_LOOKBACK_DAYS = 2 * 365


def _start_date():
    return (datetime.today() - timedelta(days=_LOOKBACK_DAYS)).strftime("%Y-%m-%d")


def _extract_single(raw, ticker):
    """yfinance returns different column shapes depending on version / batch size.
    This normalizes a download down to a plain OHLCV frame for one ticker."""
    if raw is None or len(raw) == 0:
        return None
    if isinstance(raw.columns, pd.MultiIndex):
        lvl0 = raw.columns.get_level_values(0)
        if ticker in lvl0:
            return raw[ticker]
        # single-ticker download can come back as (Price, Ticker) with the
        # ticker on the *second* level -> just drop it.
        try:
            return raw.droplevel(1, axis=1)
        except Exception:
            return raw.droplevel(0, axis=1)
    return raw


# --------------------------------------------------------------------------
# 1) The live-streaming scan
# --------------------------------------------------------------------------
def run_scan(choice):
    start = _start_date()
    total = len(tickers)
    results = []
    checked = 0

    # tell the browser we're starting
    yield {"type": "progress", "checked": 0, "total": total, "matches": 0}

    for batch_start in range(0, total, BATCH_SIZE):
        batch = tickers[batch_start: batch_start + BATCH_SIZE]
        batch_str = " ".join(batch)

        try:
            raw_weekly = yf.download(
                batch_str, start=start, interval="1wk", group_by="ticker",
                auto_adjust=True, threads=True, progress=False,
            )
        except Exception as e:
            checked += len(batch)
            yield {"type": "progress", "checked": checked, "total": total,
                   "matches": len(results), "note": f"batch error: {e}"}
            time.sleep(2)
            continue

        multi = len(batch) > 1
        for ticker in batch:
            checked += 1
            try:
                weekly = (
                    raw_weekly[ticker]
                    if multi and ticker in raw_weekly.columns.get_level_values(0)
                    else (raw_weekly if not multi else None)
                )
                if weekly is None or weekly.empty:
                    continue
                res = check_ticker(ticker, weekly, choice)
                if res and res["passed_all"]:
                    results.append(_clean(res))
            except Exception:
                continue

        yield {"type": "progress", "checked": checked, "total": total,
               "matches": len(results)}
        time.sleep(0.3)

    yield {"type": "done", "checked": checked, "total": total,
           "matches": len(results), "results": results, "choice": choice}


def get_ticker_detail(ticker, choice):
    start = _start_date()
    try:
        raw = yf.download(
            ticker, start=start, interval="1wk", group_by="ticker",
            auto_adjust=True, threads=False, progress=False,
        )
    except Exception:
        return None

    weekly = _extract_single(raw, ticker)
    if weekly is None or weekly.empty:
        return None
    weekly = weekly.dropna(subset=["Open", "High", "Low", "Close"])
    if weekly.empty:
        return None

    res = _clean(check_ticker(ticker, weekly, choice))

    close = weekly["Close"]
    ema_long_series = ema_calc(close, EMA_LONG)
    ema_short_series = ema_calc(close, EMA_SHORT)

    # 52-week anchored VWAP: anchor at the highest high of the last 52 weeks,
    # then run a volume-weighted average price forward from there (your logic).
    avwap_series = pd.Series([math.nan] * len(weekly), index=weekly.index)
    breakout_level = None
    avg_past_volume = None
    if len(weekly) >= 2:
        lookback_52wk = weekly.iloc[-52:]
        anchor_idx = lookback_52wk["High"].idxmax()
        anchor_pos = weekly.index.get_loc(anchor_idx)
        avwap_slice = weekly.iloc[anchor_pos:]
        typical = (avwap_slice["High"] + avwap_slice["Low"] + avwap_slice["Close"]) / 3
        cum_vol = avwap_slice["Volume"].cumsum()
        cum_tpv = (typical * avwap_slice["Volume"]).cumsum()
        running_avwap = cum_tpv / cum_vol.replace(0, np.nan)
        avwap_series.loc[avwap_slice.index] = running_avwap.values

    if len(weekly) >= LOOKBACK + 1:
        past_weeks = weekly.iloc[-(LOOKBACK + 1): -1]
        breakout_level = float(past_weeks["Close"].max())
        avg_past_volume = float(past_weeks["Volume"].mean())

    chart = {
        "ticker": ticker,
        "dates": [d.strftime("%Y-%m-%d") for d in weekly.index],
        "open": _floats(weekly["Open"]),
        "high": _floats(weekly["High"]),
        "low": _floats(weekly["Low"]),
        "close": _floats(close),
        "volume": _floats(weekly["Volume"]),
        "ema_long": _floats(ema_long_series),
        "ema_short": _floats(ema_short_series),
        "avwap": _floats(avwap_series),
        "breakout_level": breakout_level,
        "avg_volume": avg_past_volume,
        "ema_long_period": EMA_LONG,
        "ema_short_period": EMA_SHORT,
        "lookback": LOOKBACK,
        "breakout_min_pct": BREAKOUT_MIN_PCT,
        "breakout_max_pct": BREAKOUT_MAX_PCT,
    }

    return {"ticker": ticker, "res": res, "choice": choice, "chart": chart}


# --------------------------------------------------------------------------
# helpers: make numbers safe for JSON (NaN -> None, numpy -> python)
# --------------------------------------------------------------------------
def _num(x):
    if x is None:
        return None
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating, float)):
        x = float(x)
        return None if math.isnan(x) else x
    if isinstance(x, (np.bool_,)):
        return bool(x)
    return x


def _floats(series):
    return [_num(v) for v in series.tolist()]


def _clean(d):
    """Make a result dict fully JSON-serializable."""
    if d is None:
        return None
    return {k: _num(v) for k, v in d.items()}
