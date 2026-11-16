"""Bloco H — o que entraria no commit: nada de data/ ou outputs/tables, nenhum microdado, nenhum CSV com células n pequenas, nenhum ._*."""
import csv
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from comum_v1_20261026 import *

B = Bloco("h")
st = git("status", "--porcelain=v1", "-uall", "-z").split("\0")
vai, i = [], 0
while i < len(st):
    e = st[i]
    if not e:
        i += 1; continue
    if e[0] == "R":
        vai.append(e[3:]); i += 2; continue
    p = e[3:]
    if not (e.startswith("??") and (p.startswith("docs/referencias/") or p.startswith("audit_independente/etapa8b/"))):
        vai.append(p)
    i += 1
vai = sorted(set(vai))
B.ok("H1.01", "conjunto do commit: 104 caminhos (12 modificados + 38 renomeados + 54 novos), fora docs/referencias e a pasta do auditor", len(vai) == 104, len(vai))
ruim = [p for p in vai if p.startswith(("data/", "outputs/tables/", "outputs/logs/", "outputs/figures/")) or Path(p).name.startswith("._")
        or Path(p).name == ".DS_Store" or re.search(r"\.(parquet|dbc|dbf|rds|rda|rdata|feather|sqlite|db|gz|zip|7z|sav|dta)$", p, re.I)]
B.ok("H1.02", "nada em data/, outputs/tables, outputs/logs; nenhum parquet/dbc/rds/zip; nenhum ._*/.DS_Store", not ruim, ruim)
ign = [p for p in vai if subprocess.run(["git", "-C", str(PROJ), "check-ignore", "-q", "--no-index", p]).returncode == 0] if False else []
import subprocess
ign = [p for p in vai if subprocess.run(["git", "-C", str(PROJ), "check-ignore", "-q", p]).returncode == 0]
B.ok("H1.03", "nenhum caminho do conjunto é ignorado pelo .gitignore (não exigiria add -f)", not ign, ign)
big = [(p, (PROJ / p).stat().st_size) for p in vai if (PROJ / p).stat().st_size > 10e6]
B.ok("H1.04", "nenhum arquivo > 10 MB", not big, big)
IDS = re.compile(r"(?i)^(NUMERODN|NUMERODV|DTNASC|DTNASCMAE|CODMUNRES|CODMUNNASC|CODESTAB|CONTADOR|CO_REGSAUD|coMunicipioIbge)$")
csvs = [p for p in vai if p.endswith(".csv")]
info, pequenos, colid = {}, [], []
NCOL = re.compile(r"(?i)^(n|n_.*|.*_n|casos|.*cases.*|.*births.*|y|count.*|nasc.*)$")
for p in csvs:
    with open(PROJ / p, newline="", encoding="utf-8") as f:
        R = list(csv.reader(f))
    info[p] = len(R) - 1
    colid += [f"{p}:{c}" for c in R[0] if IDS.match(c)]
    for j, c in enumerate(R[0]):
        if NCOL.match(c.strip()):
            for r in R[1:]:
                v = r[j].replace(",", "").strip() if j < len(r) else ""
                if re.fullmatch(r"\d+", v) and 0 < int(v) < 10:
                    pequenos.append(f"{Path(p).name}:{c}={v}")
B.ok("H2.01", "CSVs do conjunto: sem coluna identificadora (DN, datas, município, estabelecimento, região de saúde)", not colid, colid[:4])
B.ok("H2.02", "CSVs do conjunto: no máximo 1.000 linhas (agregados)", max(info.values()) <= 1000, f"{len(csvs)} CSVs; maior {max(info.items(), key=lambda x: x[1])}")
B.ok("H2.03", "CSVs do conjunto: nenhuma contagem 1–9 em coluna de n/casos/nascimentos", not pequenos, pequenos[:6])
# os CSVs novos são idênticos aos da v13 já versionada (exceto S2b, que só ganha p-valores; checa e audita são verificações)
novos_csv = [p for p in csvs if V14 in p]
iguais = [p for p in novos_csv if "S2b_" not in p and "checa_7b" not in p and
          (PROJ / p).read_bytes() == git("show", f"{BASE}:" + p.replace(V14, V13), binary=True)]
B.ok("H2.04", "CSVs da v14 (fora S2b e checa) com os mesmos bytes dos da v13 já versionados em cdddf8f (nenhuma contagem nova)",
     len(iguais) == len([p for p in novos_csv if "S2b_" not in p and "checa_7b" not in p]), f"{len(iguais)} iguais")
s2b = (PROJ / f"outputs/manuscrito/suplementar/S2b_access_specifications_{V14}.csv").read_text()
B.ok("H2.05", "S2b v14: só estimativas (IC, PR, p); nenhum inteiro isolado de contagem", not re.search(r",\d+,|,\d+$", s2b, re.M))
aud = MS / "audita_8b_v1_20261026.csv"
with open(aud, newline="", encoding="utf-8") as f:
    RA = list(csv.reader(f))
B.ok("H2.06", "audita_8b (entra no commit): só colunas de verificação, nenhuma coluna de contagem/identificador", [c for c in RA[0] if IDS.match(c) or NCOL.match(c)] == [], RA[0])
B.ok("H3.01", ".gitignore cobre data/, outputs/tables/, outputs/logs/, ._* e audit_independente/**/*.csv (os CSVs do auditor ficam fora)",
     all(x in (PROJ / ".gitignore").read_text().splitlines() for x in ["data/", "outputs/tables/", "outputs/logs/", "._*", "audit_independente/**/*.csv"]))
B.grava()
