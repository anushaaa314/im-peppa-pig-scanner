// Home page logic: kick off the scan, listen to live progress, build the table.

const runBtn = document.getElementById("run-btn");
const choiceSel = document.getElementById("choice");

const progressCard = document.getElementById("progress-card");
const progressLabel = document.getElementById("progress-label");
const matchCount = document.getElementById("match-count");
const barFill = document.getElementById("bar-fill");
const progressNote = document.getElementById("progress-note");

const resultsCard = document.getElementById("results-card");
const resultsHead = document.getElementById("results-head");
const resultsBody = document.getElementById("results-body");
const resultsTitle = document.getElementById("results-title");
const emptyMsg = document.getElementById("empty-msg");

let currentChoice = "a";
let lastResults = [];
let sortState = { key: "Above_Close%", asc: true };

// Which columns to show, in order. The compression column depends on choice.
function columnsFor(choice) {
  return [
    { key: "Ticker", label: "Ticker", numeric: false },
    { key: "Close", label: "Close", numeric: true },
    { key: "Above_Close%", label: "% > 10wk high", numeric: true },
    { key: "Above_AVWAP%", label: "% > AVWAP", numeric: true },
    choice === "a"
      ? { key: "Past_Range%", label: "10wk range %", numeric: true }
      : { key: "CV_Ratio", label: "CV ratio", numeric: true },
    { key: "Body/Range", label: "Body/Range %", numeric: true },
    { key: "CMF", label: "CMF", numeric: true },
    { key: "Volume_vs_Average", label: "Vol vs avg", numeric: true },
    { key: "EMA_LONG", label: "40wk EMA", numeric: true },
    { key: "EMA_SHORT", label: "10wk EMA", numeric: true },
  ];
}

runBtn.addEventListener("click", startScan);

function startScan() {
  currentChoice = choiceSel.value;
  runBtn.disabled = true;
  runBtn.textContent = "Scanning…";

  // reset UI
  progressCard.classList.remove("hidden");
  resultsCard.classList.add("hidden");
  emptyMsg.classList.add("hidden");
  resultsHead.innerHTML = "";
  resultsBody.innerHTML = "";
  barFill.style.width = "0%";
  progressNote.textContent = "";
  progressLabel.textContent = "Warming up…";
  matchCount.textContent = "0 matches";

  const es = new EventSource("/scan?choice=" + currentChoice);
  let finished = false;

  es.onmessage = (e) => {
    const msg = JSON.parse(e.data);

    if (msg.type === "progress") {
      const pct = msg.total ? Math.round((msg.checked / msg.total) * 100) : 0;
      barFill.style.width = pct + "%";
      progressLabel.textContent =
        "Checked " + msg.checked + " / " + msg.total + "  (" + pct + "%)";
      matchCount.textContent =
        msg.matches + (msg.matches === 1 ? " match" : " matches");
      if (msg.note) progressNote.textContent = "⚠ " + msg.note;
    } else if (msg.type === "done") {
      finished = true;
      es.close();
      progressLabel.textContent =
        "Done! Checked " + msg.checked + " / " + msg.total;
      barFill.style.width = "100%";
      lastResults = msg.results || [];
      renderResults();
      resetButton();
    } else if (msg.type === "error") {
      finished = true;
      es.close();
      progressNote.textContent = "⚠ Error: " + msg.message;
      resetButton();
    }
  };

  es.onerror = () => {
    // the browser fires this when the server closes the stream normally too,
    // so only treat it as a real error if we never finished.
    if (!finished) {
      progressNote.textContent =
        "⚠ Lost connection to the scan. Is app.py still running?";
      es.close();
      resetButton();
    }
  };
}

function resetButton() {
  runBtn.disabled = false;
  runBtn.textContent = "Run Scan";
}

function renderResults() {
  const cols = columnsFor(currentChoice);

  if (!lastResults.length) {
    resultsCard.classList.add("hidden");
    emptyMsg.classList.remove("hidden");
    emptyMsg.textContent = "No tickers passed all 7 checks this time. 🐷";
    return;
  }

  resultsTitle.textContent = lastResults.length + " matches";

  // header
  resultsHead.innerHTML = "";
  cols.forEach((c) => {
    const th = document.createElement("th");
    th.textContent = c.label;
    if (c.key !== "Ticker") {
      th.classList.add("sortable");
      if (sortState.key === c.key) {
        th.classList.add(sortState.asc ? "sort-asc" : "sort-desc");
      }
      th.addEventListener("click", () => {
        if (sortState.key === c.key) sortState.asc = !sortState.asc;
        else sortState = { key: c.key, asc: true };
        renderResults();
      });
    }
    resultsHead.appendChild(th);
  });

  // sort
  const sorted = [...lastResults].sort((a, b) => {
    const va = a[sortState.key], vb = b[sortState.key];
    if (va == null) return 1;
    if (vb == null) return -1;
    return sortState.asc ? va - vb : vb - va;
  });

  // body
  resultsBody.innerHTML = "";
  sorted.forEach((row) => {
    const tr = document.createElement("tr");
    cols.forEach((c) => {
      const td = document.createElement("td");
      if (c.key === "Ticker") {
        const a = document.createElement("a");
        a.href = "/ticker/" + row.Ticker + "?choice=" + currentChoice;
        a.textContent = row.Ticker;
        a.className = "ticker-link";
        a.target = "_blank";      // open the detail page in a new tab...
        a.rel = "noopener";       // ...so the results table stays put in this one
        td.appendChild(a);
      } else {
        const v = row[c.key];
        td.textContent = v == null ? "—" : v;
      }
      tr.appendChild(td);
    });
    resultsBody.appendChild(tr);
  });

  resultsCard.classList.remove("hidden");
  emptyMsg.classList.add("hidden");
}
