// Draws the weekly candlestick + strategy overlays using Plotly.
// Reads the CHART object injected by ticker.html.
(function () {
  if (typeof CHART === "undefined" || !CHART.dates || !CHART.dates.length) {
    document.getElementById("chart").innerHTML =
      "<p class='empty'>No chart data.</p>";
    return;
  }

  const d = CHART;

  const candles = {
    type: "candlestick",
    name: "price",
    x: d.dates,
    open: d.open, high: d.high, low: d.low, close: d.close,
    increasing: { line: { color: "#ef5a8e" } },   // Peppa pink up-weeks
    decreasing: { line: { color: "#b0b0bc" } },   // muted grey down-weeks
    xaxis: "x", yaxis: "y",
  };

  const emaLong = {
    type: "scatter", mode: "lines", name: d.ema_long_period + "wk EMA",
    x: d.dates, y: d.ema_long,
    line: { color: "#7e57c2", width: 2 }, xaxis: "x", yaxis: "y",
  };

  const emaShort = {
    type: "scatter", mode: "lines", name: d.ema_short_period + "wk EMA",
    x: d.dates, y: d.ema_short,
    line: { color: "#3d9be0", width: 2 }, xaxis: "x", yaxis: "y",
  };

  const avwap = {
    type: "scatter", mode: "lines", name: "52wk AVWAP",
    x: d.dates, y: d.avwap, connectgaps: false,
    line: { color: "#f59e0b", width: 2, dash: "dot" }, xaxis: "x", yaxis: "y",
  };

  const volume = {
    type: "bar", name: "volume",
    x: d.dates, y: d.volume,
    marker: { color: "#f6b6d0" }, xaxis: "x", yaxis: "y2",
  };

  const shapes = [];
  const annotations = [];
  if (d.breakout_level != null) {
    shapes.push({
      type: "line", xref: "paper", x0: 0, x1: 1,
      yref: "y", y0: d.breakout_level, y1: d.breakout_level,
      line: { color: "#43a047", width: 1.5, dash: "dash" },
    });
    annotations.push({
      xref: "paper", x: 0.01, yref: "y", y: d.breakout_level,
      text: "breakout " + d.breakout_level, showarrow: false,
      font: { color: "#43a047", size: 11 },
      bgcolor: "rgba(255,255,255,0.7)", yanchor: "bottom",
    });
  }

  const layout = {
    margin: { l: 55, r: 20, t: 10, b: 30 },
    height: 520,
    paper_bgcolor: "#ffffff",
    plot_bgcolor: "#ffffff",
    font: { family: "'Comic Sans MS','Chalkboard SE','Segoe UI',sans-serif",
            color: "#3a2a33", size: 12 },
    showlegend: false,
    xaxis: {
      domain: [0, 1], rangeslider: { visible: false }, anchor: "y2",
      gridcolor: "#f3e3ea",
    },
    yaxis: { domain: [0.26, 1], gridcolor: "#f3e3ea", title: "Price" },
    yaxis2: { domain: [0, 0.18], gridcolor: "#f3e3ea", title: "Vol" },
    shapes: shapes,
    annotations: annotations,
  };

  Plotly.newPlot("chart", [candles, emaLong, emaShort, avwap, volume], layout,
                 { responsive: true, displayModeBar: false });
})();
