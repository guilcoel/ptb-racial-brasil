"""
EXCEÇÃO À INDEPENDÊNCIA (registrada): única leitura de um resultado da autoauditoria nesta auditoria, permitida só para o item L2b
('a autoauditoria fechou em 100/100'). Rodado DEPOIS de todos os outros itens (K, L, M, web) estarem concluídos.
Lê: outputs/manuscrito/checa_7b_v11_20261009.csv (disco e blob de b9d6272). Não lê o checa_7b_v10 arquivado, nem
outputs/manuscrito/audita_final_7c6_*.csv, nem scripts/etapa7c6_02_audita_final.py.
Saída: excecao_L2b_7c6_final_v1_20261010.json (só contagens, nomes de colunas e igualdades; nenhuma linha copiada).
"""
import csv
import io
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

PROJ = Path("/Volumes/Forja/ptb-racial-brasil")
AQUI = Path(__file__).resolve().parent
CAM = "outputs/manuscrito/checa_7b_v11_20261009.csv"

disco = (PROJ / CAM).read_bytes()
commit = subprocess.run(["git", "-C", str(PROJ), "show", f"b9d6272:{CAM}"], capture_output=True, check=True).stdout
rows = list(csv.DictReader(io.StringIO(commit.decode("utf-8"))))
oks = [r["ok"] for r in rows]
resumo = (PROJ / "outputs/RESUMO_ETAPA7C6_v1_20261009.md").read_text()
# tabela 'Checagens da 7c.6' do RESUMO × linhas do CSV que contêm '7c.6'
tab = []
dentro = False
for l in resumo.splitlines():
    if l.startswith("| Checagem"):
        dentro = True
        continue
    if dentro and l.startswith("|:"):
        continue
    if dentro and l.startswith("|"):
        c = [x.strip() for x in l.strip().strip("|").split("|")]
        tab.append((c[0], c[1] if len(c) > 1 else ""))
    elif dentro:
        break
c7 = [(r["verificacao"], r["valor"]) for r in rows if "7c.6" in r["verificacao"]]
pad = {"data_1900_2024": r"(?<!\d)(0[1-9]|[12]\d|3[01])/(0[1-9]|1[0-2])/(19\d\d|20[01]\d|202[0-4])(?!\d)",
       "cns15": r"(?<![\d.,])[12789]\d{14}(?![\d.,])", "cpf": r"(?<!\d)\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)"}
txt = commit.decode("utf-8")
out = dict(
    quando=datetime.now().isoformat(timespec="seconds"),
    disco_igual_commit=disco == commit,
    linhas=len(rows), colunas=list(rows[0].keys()) if rows else [],
    ok_true=sum(o == "True" for o in oks), ok_outros=sorted(set(oks) - {"True"}),
    resumo_diz_100=bool(re.search(r"\*\*100/100 OK\*\*", resumo)),
    tabela_7c6_resumo_n=len(tab), linhas_7c6_csv=len(c7),
    tabela_7c6_igual_csv=[(a, b) for a, b in tab] == [(a, b.replace("|", "\\|")) for a, b in c7] or [(a, b) for a, b in tab] == c7,
    padroes_individuais={k: len(re.findall(p, txt)) for k, p in pad.items()},
    maior_campo_valor=max((len(r["valor"]) for r in rows), default=0),
)
(AQUI / "excecao_L2b_7c6_final_v1_20261010.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False, indent=1))
