import yfinance as yf
import pandas as pd
from muddy_puddles import tickers
import time
from datetime import datetime, timedelta

BATCH_SIZE = 50
EMA_LONG = 40
EMA_SHORT = 10
LOOKBACK = 10
VOLUME_MULTIPLIER = 1.0
BODY_RANGE_MIN = 50
BREAKOUT_MIN_PCT = 4
BREAKOUT_MAX_PCT = 20
CMF_PERIOD = 10
RANGE_LIMIT = 35
CV_LONG = 20
CV_SHORT = 10
CV_RATIO = 1

def ema_calc(data, duration):
    return data.ewm(span=duration, adjust=False).mean()


def cmf_calc(data, period):
    ohlc = data.iloc[-(period + 1): -1]
    high = ohlc["High"]
    low = ohlc["Low"]
    close = ohlc["Close"]
    volume = ohlc["Volume"]
    bar_range = high - low

    money_flow_multiplier = ((2 * close - low - high) / bar_range).where(
        bar_range > 0, 0)
    money_flow_volume = money_flow_multiplier * volume
    total_volume = float(volume.sum())
    if total_volume == 0:
        return 0.0

    return float(money_flow_volume.sum()/total_volume)


def cv_calc(data):
    mean = float(data.mean())
    if mean == 0:
        return 10
    return float(data.std(ddof=0)/mean) * 100


def check_ticker(ticker, weekly, choice):
    fail = lambda reason: {
        "Ticker": ticker, "passed_all": False, "reason": reason, "c1": None,
        "c2": None, "c3": None, "c4": None, "c5": None, "c6": None, "c7": None
    }

    if len(weekly) < EMA_LONG + LOOKBACK + 5:
        return fail(f"not enough data for {ticker}")

    this_week_close = float(weekly["Close"].iloc[-1])
    past_weeks = weekly.iloc[-(LOOKBACK + 1): -1]
    if len(past_weeks) < LOOKBACK:
        return fail("not enough weekly bars")


    ema_long = float(ema_calc(weekly["Close"], EMA_LONG).iloc[-1])
    ema_short = float(ema_calc(weekly["Close"], EMA_SHORT).iloc[-1])

    c1 = this_week_close > ema_long and ema_short >= ema_long
    if not c1:
        reasons = []
        if this_week_close <= ema_long: reasons.append(f"below {EMA_LONG} week EMA")
        if ema_short < ema_long: reasons.append(f"{EMA_SHORT} week EMA is below {EMA_LONG} week EMA")
        return {
            "Ticker": ticker,
            "passed_all": False,
            "reason": f"failed c1 ({', '.join(reasons)})",
            "c1": False, "c2": None, "c3": None, "c4": None, "c5": None, "c6": None, "c7": None,
            "Close": round(this_week_close, 2),
            "EMA_LONG": round(ema_long, 2),
            "EMA_SHORT": round(ema_short, 2)
        }


    past_highest_close = past_weeks["Close"].max()
    above_close_pct = (this_week_close - past_highest_close)/past_highest_close * 100

    c2 = BREAKOUT_MIN_PCT <= above_close_pct <= BREAKOUT_MAX_PCT
    if not c2:
        if above_close_pct < BREAKOUT_MIN_PCT:
            c2_reason = f"failed c2: only {round(above_close_pct, 2)}% above the highest close of the past {LOOKBACK} weeks , needs {BREAKOUT_MIN_PCT}%"
        elif above_close_pct > BREAKOUT_MAX_PCT:
            c2_reason = f"failed c2: extended {round(above_close_pct, 2)}% above the highest close of the past {LOOKBACK} weeks, max {BREAKOUT_MAX_PCT}%"
        else:
            c2_reason = "failed c2: invalid breakout"
        return {
            "Ticker": ticker,
            "passed_all": False,
            "reason": c2_reason,
            "c1": True, "c2": False, "c3": None, "c4": None, "c5": None, "c6": None, "c7": None,
            "Close": round(this_week_close, 2),
            "EMA_LONG": round(ema_long, 2),
            "EMA_SHORT": round(ema_short, 2),
            "Above_Close%": round(above_close_pct, 2)
        }


    if choice == "a":
        farther = weekly.iloc[-(LOOKBACK + 1): -(LOOKBACK//2 + 1)]
        closer = weekly.iloc[-(LOOKBACK//2 + 1):-1]
        farther_high = float(farther["High"].max())
        farther_low = float(farther["Low"].min())
        farther_range = (farther_high - farther_low) / farther_low * 100
        closer_high = float(closer["High"].max())
        closer_low = float(closer["Low"].min())
        closer_range = (closer_high - closer_low) / closer_low * 100
        all_ten_high = float(past_weeks["High"].max())
        all_ten_low = float(past_weeks["Low"].min())

        past_range_pct = (all_ten_high - all_ten_low)/all_ten_low * 100
        c3 = past_range_pct < RANGE_LIMIT and closer_range <= farther_range

    if choice == "b":
        short_closes = weekly["Close"].iloc[-(CV_SHORT + 1): -1]
        long_closes = weekly["Close"].iloc[-(CV_LONG + 1): -1]
        cv_short = cv_calc(short_closes)
        cv_long = cv_calc(long_closes)
        cv_ratio = cv_short/cv_long if cv_long > 0 else 10

        c3 = round(cv_ratio, 2) <= CV_RATIO

    if not c3:
        if choice == "a":
            if past_range_pct >= RANGE_LIMIT:
                c3_reason =  f" failed c3: past 10 weeks range = {round(past_range_pct, 2)}%; not below {RANGE_LIMIT}"
            elif closer_range > farther_range:
                c3_reason = " failed c3: range does not decrease over the ten weeks"
            else:
                c3_reason = "failed c3: invalid range/compression"
        if choice == "b":
            c3_reason = f"failed c3: coefficient of variation ratio {round(cv_ratio, 2)} > {CV_RATIO}"
        return {
            "Ticker": ticker,
            "passed_all": False,
            "reason": c3_reason,
            "c1": True, "c2": True, "c3": False, "c4": None, "c5": None, "c6": None, "c7": None,
            "Close": round(this_week_close, 2),
            "EMA_LONG": round(ema_long, 2),
            "EMA_SHORT": round(ema_short, 2),
            "Above_Close%": round(above_close_pct, 2),
            **({"Past_Range%": round(past_range_pct, 2)} if choice == "a" else {"CV_Ratio": round(cv_ratio, 2)}),
        }


    bar = weekly.iloc[-1]
    open_bar, high, low, close = float(bar["Open"]), float(bar["High"]), float(bar["Low"]), float(bar["Close"])
    range_bar = high - low
    body = close - open_bar
    is_bullish = body > 0
    body_to_range = (body/range_bar)*100 if range_bar > 0 else 0.0

    c4 = is_bullish and body_to_range >= BODY_RANGE_MIN
    if not c4:
        return {
            "Ticker": ticker,
            "passed_all": False,
            "reason": f"failed c4: body only makes up {round(body_to_range, 2)}% of the total range",
            "c1": True, "c2": True, "c3": True, "c4": False, "c5": None, "c6": None, "c7": None,
            "Close": round(this_week_close, 2),
            "EMA_LONG": round(ema_long, 2),
            "EMA_SHORT": round(ema_short, 2),
            "Above_Close%": round(above_close_pct, 2),
            **({"Past_Range%": round(past_range_pct, 2)} if choice == "a" else {"CV_Ratio": round(cv_ratio, 2)}),
            "Body/Range": round(body_to_range, 2)
        }


    cmf = cmf_calc(weekly, CMF_PERIOD)
    c5 = cmf > 0
    if not c5:
        return {
            "Ticker": ticker,
            "passed_all": False,
            "reason": f"failed c5: cmf distribution during base (CMF {round(cmf, 3)}) is negative",
            "c1": True, "c2": True, "c3": True, "c4": True, "c5": False, "c6": None, "c7": None,
            "Close": round(this_week_close, 2),
            "EMA_LONG": round(ema_long, 2),
            "EMA_SHORT": round(ema_short, 2),
            "Body/Range": round(body_to_range, 2),
            **({"Past_Range%": round(past_range_pct, 2)} if choice == "a" else {"CV_Ratio": round(cv_ratio, 2)}),
            "CMF": round(cmf, 3)
        }


    lookback_52wk = weekly.iloc[-52:]
    anchor_idx = lookback_52wk["High"].idxmax()
    anchor_pos = weekly.index.get_loc(anchor_idx)
    avwap_slice = weekly.iloc[anchor_pos:]

    typical_price = (avwap_slice["High"] + avwap_slice["Low"] + avwap_slice["Close"]) / 3
    total_vol = float(avwap_slice["Volume"].sum())
    avwap = float((typical_price * avwap_slice["Volume"]).sum() / total_vol) \
        if total_vol > 0 else this_week_close
    above_avwap_pct = (this_week_close - avwap) / avwap * 100

    c6 = this_week_close >= avwap
    if not c6:
        return {
            "Ticker": ticker,
            "passed_all": False,
            "reason": f"failed C6: (close {abs(round(above_avwap_pct, 2))}% below 52wk AVWAP)",
            "c1": True, "c2": True, "c3": True, "c4": True, "c5": True, "c6": False, "c7": None,
            "Close": round(this_week_close, 2),
            "EMA_LONG": round(ema_long, 2),
            "EMA_SHORT": round(ema_short, 2),
            "Body/Range": round(body_to_range, 2),
            **({"Past_Range%": round(past_range_pct, 2)} if choice == "a" else {"CV_Ratio": round(cv_ratio, 2)}),
            "CMF": round(cmf, 3),
            "Above_Close%": round(above_close_pct, 2),
            "Above_AVWAP%": round(above_avwap_pct, 2)
        }


    current_volume = float(weekly["Volume"].iloc[-1])
    average_past_volume = float(past_weeks["Volume"].mean())
    volume_ratio = current_volume/average_past_volume if average_past_volume > 0 else 0
    c7 = current_volume>= VOLUME_MULTIPLIER * average_past_volume
    passed_all = c1 and c2 and c3 and c4 and c5 and c6 and c7
    return {
        "Ticker": ticker,
        "passed_all": passed_all,
        "reason": "ALL PASS" if passed_all else f"failed c7: volume {round(volume_ratio, 2)} x average, needs {VOLUME_MULTIPLIER}",
        "c1": True, "c2": True, "c3": True, "c4": True, "c5": True, "c6": True, "c7": c7,
        "Close": round(this_week_close, 2),
        "EMA_LONG": round(ema_long, 2),
        "EMA_SHORT": round(ema_short, 2),
        "Body/Range": round(body_to_range, 2),
        **({"Past_Range%": round(past_range_pct, 2)} if choice == "a" else {"CV_Ratio": round(cv_ratio, 2)}),
        "CMF": round(cmf, 3),
        "Above_Close%": round(above_close_pct, 2),
        "Above_AVWAP%": round(above_avwap_pct, 2),
        "This Wk Volume": int(current_volume),
        "Volume_vs_Average": round(volume_ratio, 2)
        }


def print_status(ticker, res, error=None):
    if res is None:
        if error:
            print(f"    - {ticker:<12}  NO DATA / ERROR: {error}")
        else:
            print(f"    - {ticker:<12}  NO DATA")
        return

    if res["passed_all"]:
        print(f"{ticker} {res.get('reason', '')}")
    else:
        print(f"   - {ticker:<12}  {res.get('reason', '')}")


def run_scanner(tickers, choice):
    start = (datetime.today() - timedelta(days=2 * 365)).strftime("%Y-%m-%d")
    results = []
    total = len(tickers)

    for batch_start in range(0, total, BATCH_SIZE):
        batch = tickers[batch_start: batch_start + BATCH_SIZE]
        batch_str = " ".join(batch)
        pct = int((batch_start + len(batch)) / total * 100)
        print(f"Batch {batch_start+1}-{batch_start+len(batch)} of {total}  [{pct}%] --")

        try:
            raw_weekly = yf.download(batch_str, start=start, interval="1wk", group_by="ticker", auto_adjust=True, threads=True, progress=False)
        except Exception as e:
            print(f"\n  !  Batch error: {e}")
            time.sleep(2)
            continue

        multi = len(batch) > 1
        for ticker in batch:
            try:
                weekly = (
                    raw_weekly[ticker]
                    if multi and ticker in raw_weekly.columns.get_level_values(0)
                    else (raw_weekly if not multi else None)
                )
                if weekly is None or weekly.empty:
                    print_status(ticker=ticker, res=None)
                    continue
                res = check_ticker(ticker, weekly, choice)
                if res["c1"] and res["Above_Close%"] > 0:
                    print_status(ticker=ticker, res=res)
                if res and res["passed_all"]:
                    results.append(res)
            except Exception as ex:
                print_status(ticker, None, error=str(ex))
        time.sleep(0.3)

    print(f"\nScan complete. {len(results)} match(es) found out of {total} tickers.")
    return pd.DataFrame(results)


def print_results(scan_df, today_str, choice):
    pd.set_option("display.float_format", "{:.2f}".format)
    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.max_rows", None)

    print (f"\nRESULTS | {today_str} | {len(scan_df)} match(es)")

    if scan_df.empty:
        print("\n  No tickers passed all conditions.\n")
        return

    display_cols = [
        "Ticker",
        "Close",
        "Above_Close%",
        "Above_AVWAP%",
        "Past_Range%" if choice == "a" else "CV_Ratio",
        "Body/Range",
        "CMF",
        "Volume_vs_Average",
        "EMA_LONG",
        "EMA_SHORT"
    ]

    display_cols = [
        col for col in display_cols
        if col in scan_df.columns
    ]

    sorted_df = scan_df.sort_values(
        "Above_Close%",
        ascending=True
    )

    print("\nSorted by distance above previous 10-week close:\n")
    print(sorted_df[display_cols].to_string(index=False))


if __name__ == "__main__":
    today_str = datetime.today().strftime("%Y-%m-%d")
    choice = ""
    while choice not in ["a", "b"]:
        choice = input("Check compression using range or coefficient of variation (a for range/b for cv)?: ")

    scan_df = run_scanner(tickers, choice)
    print_results(scan_df, today_str, choice)
