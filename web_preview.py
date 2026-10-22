"""KHAAN-SHIELD live log dashboard with alert stats bar."""
import html
import re
import time
from collections import Counter
from pathlib import Path

from flask import Flask, render_template_string

app = Flask(__name__)

PAGE = """
<!doctype html>
<html>
<head>
  <title>KHAAN-SHIELD Live</title>
  <meta http-equiv="refresh" content="2">
  <style>
    body { background:#0d1117; color:#c9d1d9; font-family:Consolas,monospace; margin:24px; }
    h1 { color:#58a6ff; font-size:22px; }
    .bar { margin:12px 0 14px; }
    .chip { display:inline-block; padding:6px 14px; border-radius:20px; margin-right:8px;
            font-size:14px; border:1px solid #30363d; background:#161b22; }
    .total { color:#79c0ff; } .halt { color:#ff7b72; } .crit { color:#ffa657; }
    .warn { color:#d29922; }  .norm { color:#3fb950; }
    .meta { color:#8b949e; font-size:12px; margin-bottom:10px; }
    pre { line-height:1.45; font-size:13px; white-space:pre-wrap; }
    .HALT { color:#ff7b72; font-weight:bold; }
    .CRITICAL { color:#ffa657; font-weight:bold; }
    .WARN { color:#d29922; font-weight:bold; }
    .NORMAL { color:#3fb950; }
    .wait { color:#d29922; padding:20px; border:1px dashed #30363d; border-radius:8px; }
  </style>
</head>
<body>
  <h1>🛡️ KHAAN-SHIELD Live — Mine Dumper Safety</h1>
  <div class="bar">
    <span class="chip total">Alerts: {{ total }}</span>
    <span class="chip halt">HALT: {{ counts.HALT }}</span>
    <span class="chip crit">CRITICAL: {{ counts.CRITICAL }}</span>
    <span class="chip warn">WARN: {{ counts.WARN }}</span>
    <span class="chip norm">NORMAL: {{ counts.NORMAL }}</span>
  </div>
  <div class="meta">Log: {{ log_name }} — last updated {{ updated }} — auto-refresh 2s</div>
  {% if lines %}
  <pre>{% for ln in lines %}{{ ln|safe }}
{% endfor %}</pre>
  {% else %}
  <div class="wait">⏳ Waiting for log… start the simulation with <b>python -m src.main</b></div>
  {% endif %}
</body>
</html>
"""

# counting uses the "-> LEVEL" pattern so notifier echo lines aren't double-counted
COUNT_RE = re.compile(r"->\s*(HALT|CRITICAL|WARN|NORMAL)\b")
COLOR_RE = re.compile(r"\b(HALT|CRITICAL|WARN|NORMAL)\b")

def find_log():
    logs_dir = Path("logs")
    if not logs_dir.exists():
        return None
    preferred = logs_dir / "khaan.log"
    if preferred.exists():
        return preferred
    logs = sorted(logs_dir.glob("*.log"), key=lambda p: p.stat().st_mtime)
    return logs[-1] if logs else None

def colorize(line):
    esc = html.escape(line)
    return COLOR_RE.sub(lambda m: f'<span class="{m.group(1)}">{m.group(1)}</span>', esc)

@app.route("/")
def index():
    path = find_log()
    lines, counts = [], Counter()
    if path:
        try:
            raw = path.read_text(encoding="utf-8", errors="replace").splitlines()[-400:]
            lines = [colorize(l) for l in raw]
            for l in raw:
                for m in COUNT_RE.finditer(l):
                    counts[m.group(1)] += 1
        except OSError:
            pass
    total = counts["HALT"] + counts["CRITICAL"] + counts["WARN"]
    updated = time.strftime("%H:%M:%S", time.localtime(path.stat().st_mtime)) if path else "—"
    return render_template_string(
        PAGE, lines=lines, counts=counts, total=total, updated=updated,
        log_name=path.name if path else "—"
    )

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)