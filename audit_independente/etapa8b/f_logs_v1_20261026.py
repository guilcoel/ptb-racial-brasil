"""Bloco F — logs × mtimes: execuções desde cdddf8f (etapa7b e etapa8b), nenhum etapa8_0[1-4] depois de cdddf8f, data/ e outputs/tables intactos,
saídas da v14 na janela da 2ª rodada, scripts editados antes de rodar."""
import os
import re
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from comum_v1_20261026 import *

B = Bloco("f")
TC = int(git("log", "-1", "--format=%ct", BASE).strip())
LOGD = PROJ / "outputs/logs"
RX = re.compile(r"^\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\] \[([^\]]+)\] (.*)")


def ev(nome):
    out = []
    for l in (LOGD / nome).read_text(errors="replace").splitlines():
        m = RX.match(l)
        if m:
            t = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").timestamp()
            if t > TC:
                out.append((t, m.group(2), m.group(3)))
    return out


e7 = ev("etapa7b_20261008.log")
seq = []
for t, s, msg in e7:
    k = {"7b_01_tabelas": "01", "7b_02_suplementar": "02", "7b_03_figuras": "03", "7b_04_submissao": "04"}.get(s)
    if s == "7b_checa":
        k = "checa" if msg.startswith("autoauditoria 7b:") else ("FALHA" if msg.startswith("FALHA") else None)
    if k:
        seq.append((datetime.fromtimestamp(t).strftime("%d/%m %H:%M:%S"), k, msg[:60] if k == "checa" else ""))
B.ok("F1.01", "etapa7b log depois de cdddf8f: exatamente 01, 02, 03, 04, checa, 04 duas vezes, nenhuma FALHA",
     [k for _, k, _ in seq] == ["01", "02", "03", "04", "checa", "04"] * 2, [f"{a} {b}" for a, b, _ in seq])
h = [a for a, _, _ in seq]
B.ok("F1.02", "rodada 1 em 26/10 10:59–11:00 e rodada 2 em 26/10 12:27–12:28",
     len(h) == 12 and all(x.startswith("26/10 10:59") or x.startswith("26/10 11:00") for x in h[:6]) and all(x.startswith("26/10 12:27") or x.startswith("26/10 12:28") for x in h[6:]), h)
B.ok("F1.03", "os dois checa: 137/137 OK", [m for _, k, m in seq if k == "checa"] == ["autoauditoria 7b: 137/137 OK"] * 2, [m for _, k, m in seq if k == "checa"])
nk = [msg for t, s, msg in e7 if s == "7b_01_tabelas" and "números-chave:" in msg]
B.ok("F1.04", "as duas rodadas do 01 registram 255 números-chave", len(nk) == 2 and all("números-chave: 255" in m for m in nk), [m[30:70] for m in nk])
outros7 = sorted({s for _, s, _ in e7} - {"7b_01_tabelas", "7b_02_suplementar", "7b_03_figuras", "7b_04_submissao", "7b_checa"})
B.ok("F1.05", "nenhum outro script no log da etapa7b depois de cdddf8f", not outros7, outros7)
e8b = ev("etapa8b_20261008.log")
B.ok("F1.06", "etapa8b log: só o gerador do RESUMO (26/10 12:33:59), depois da 2ª rodada", [(datetime.fromtimestamp(t).strftime("%H:%M:%S"), s) for t, s, _ in e8b] == [("12:33:59", "8b_01_resumo")],
     [(datetime.fromtimestamp(t).strftime("%H:%M:%S"), s, m[:80]) for t, s, m in e8b])
# nenhum etapa8_0[1-4] (nem nada de análise) depois de cdddf8f, em todos os logs
tard = []
for f in LOGD.iterdir():
    if f.name.startswith("._") or not f.is_file():
        continue
    for t, s, m in ev(f.name):
        if re.match(r"^8_0[1-4]", s) or not (s.startswith("7b_") or s.startswith("8b_")):
            tard.append((f.name, s, datetime.fromtimestamp(t).strftime("%d/%m %H:%M")))
B.ok("F2.01", "nenhum etapa8_0[1-4] (nem script de análise) em qualquer log depois de cdddf8f; só 7b_* e 8b_*", not tard, tard[:5])
mod_logs = sorted(f.name for f in LOGD.iterdir() if f.is_file() and f.stat().st_mtime > TC)
B.ok("F2.02", "logs modificados depois de cdddf8f: só etapa7b e etapa8b", mod_logs == ["etapa7b_20261008.log", "etapa8b_20261008.log"], mod_logs)
# data/ e outputs/tables
novos_d = []
for dp, dn, fn in os.walk(PROJ / "data"):
    for x in dn + fn:
        p = Path(dp) / x
        if p.lstat().st_mtime > TC:
            novos_d.append(str(p.relative_to(PROJ)))
B.ok("F3.01", "data/: nenhum arquivo ou pasta com mtime depois de cdddf8f", not novos_d, novos_d[:5])
nt = [f.name for f in TB.iterdir() if f.lstat().st_mtime > TC]
B.ok("F3.02", "outputs/tables: nenhum arquivo com mtime depois de cdddf8f (e a pasta também)", not nt and TB.stat().st_mtime < TC, nt[:5])
# saídas da v14 na janela da 2ª rodada
t = {k: datetime.strptime(f"2026-10-26 {x}", "%Y-%m-%d %H:%M:%S").timestamp() for k, x in
     [("ini", "12:27:00"), ("01", "12:27:38"), ("02", "12:27:43"), ("03", "12:27:48"), ("04a", "12:27:50"), ("ck", "12:28:47"), ("04", "12:28:50")]}
def em(p, a, b):
    m = p.stat().st_mtime
    return a - 15 <= m <= b + 2
jan = ([(f, "ini", "01") for f in (MS / "tabelas").glob(f"*_{V14}.*")] + [(MS / f"numeros_chave_{V14}.{x}", "ini", "01") for x in ("json", "md")] +
       [(f, "01", "02") for f in (MS / "suplementar").glob(f"*_{V14}.*") if not f.name.startswith("S9_")] + [(MS / "data_code_availability.md", "01", "02")] +
       [(f, "02", "03") for f in list((MS / "figuras").glob(f"*_{V14}.*")) + list((MS / "suplementar").glob(f"S9_*_{V14}.*"))] + [(MS / "legendas_figuras.md", "02", "03")] +
       [(MS / f"checa_7b_{V14}.csv", "04a", "ck"), (MS / "MANIFEST.md", "ck", "04")] + [(SUB / "ESM_4.pdf", "ck", "04")] +
       [(SUB / n, "01", "02") for n in ("ESM_1.xlsx", "ESM_2.pdf", "ESM_3.pdf")] + [(SUB / f"Fig{k}.tif", "02", "03") for k in range(1, 5)])   # copy2 preserva o mtime da origem
fora = [(f.name, datetime.fromtimestamp(f.stat().st_mtime).strftime("%H:%M:%S")) for f, a, b in jan if not em(f, t[a], t[b])]
B.ok("F4.01", "cada saída da v14 (e MANIFEST, disponibilidade, legendas, Submissao/) com mtime na janela do script que a grava na 2ª rodada (cópias do 04 com o mtime da origem, por copy2)",
     not fora and len(jan) >= 45, f"{len(jan)} arquivos; fora {fora[:6]}")
scr = {"scripts/etapa7b_lib.py": "01", "scripts/etapa7b_01_tabelas.py": "01", "scripts/etapa7b_02_suplementar.py": "01", "scripts/etapa7b_04_submissao.py": "01", "scripts/etapa7b_checa.py": "04a"}
tarde = [(s, datetime.fromtimestamp((PROJ / s).stat().st_mtime).strftime("%H:%M:%S")) for s, k in scr.items() if (PROJ / s).stat().st_mtime > t[k]]
B.ok("F4.03", "scripts do pacote editados antes da 2ª rodada (nenhum depois de rodar)", not tarde, tarde)
t_res = datetime.strptime("2026-10-26 12:33:59", "%Y-%m-%d %H:%M:%S").timestamp()
aud = MS / "audita_8b_v1_20261026.csv"
seqf = [("audita_8b csv", aud.stat().st_mtime), ("etapa8b_01_audita.py", (PROJ / "scripts/etapa8b_01_audita.py").stat().st_mtime),
        ("_resumo8b_texto", (MS / "_resumo8b_texto_v1_20261026.md").stat().st_mtime), ("gerador", (PROJ / "scripts/resumos/etapa8b_01_resumo.py").stat().st_mtime),
        ("RESUMO", (PROJ / "outputs/RESUMO_ETAPA8b_v1_20261026.md").stat().st_mtime)]
fmt = [(n, datetime.fromtimestamp(x).strftime("%H:%M:%S")) for n, x in seqf]
B.ok("F4.04", "autoauditoria gravada depois do 04 final e antes do RESUMO; script dela editado antes de gravá-la; texto e gerador antes do RESUMO; RESUMO = hora do log",
     t["04"] <= seqf[0][1] <= t_res and seqf[1][1] <= seqf[0][1] and seqf[2][1] <= t_res and seqf[3][1] <= t_res and abs(seqf[4][1] - t_res) <= 2, fmt)
B.grava()
