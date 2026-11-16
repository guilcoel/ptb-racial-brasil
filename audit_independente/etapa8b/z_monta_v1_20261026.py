"""Monta audit_independente/etapa8b/comparacao_8b_v1_20261026.csv (verificacao, ok, detalhe) a partir de res_<bloco>_v1_20261026.json."""
import csv
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from comum_v1_20261026 import *

R = []
for b in "abcdefghz":
    p = AUD / f"res_{b}_v1_20261026.json"
    if p.exists():
        R += json.loads(p.read_text())
with open(AUD / "comparacao_8b_v1_20261026.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["verificacao", "ok", "detalhe"])
    w.writeheader()
    for r in R:
        w.writerow({"verificacao": r["verificacao"], "ok": "True" if r["ok"] else "False", "detalhe": r["detalhe"]})
from collections import Counter
n, k = Counter(), Counter()
for r in R:
    b = r["verificacao"][0]; n[b] += 1; k[b] += r["ok"]
for b in n:
    print(b, n[b], k[b])
print("total", sum(n.values()), sum(k.values()))
