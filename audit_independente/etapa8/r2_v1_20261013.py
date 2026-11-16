"""Rodada 2 — confere as correções do coordenador (26/10) e que nada mais mudou; acrescenta linhas R2. ao comparacao_8 (sem apagar as da rodada 1).
Usa os res_*_r2 (blocos A–I refeitos com RODADA=r2) e checagens próprias. Sandbox com guarda só para o gerador do RESUMO."""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa8")
import csv
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import openpyxl
import pandas as pd

from comum_v1_20261013 import PROJ, MS, TB, AUD, V12, V13, md5

os.environ["GIT_OPTIONAL_LOCKS"] = "0"
L = []
ok = lambda n, c, d="": (L.append(dict(verificacao="R2." + n, ok=bool(c), detalhe=str(d))), print("OK   " if c else "FALHA", n, "|", str(d)[:250]))
r1 = {b: {i["verificacao"]: i for i in json.load(open(AUD / f"res_{b}_r1_v1_20261013.json"))} for b in "a b c1 c2 d e f g h i".split()}
r2 = {b: {i["verificacao"]: i for i in json.load(open(AUD / f"res_{b}_r2_v1_20261013.json"))} for b in "a b c1 c2 d e f g h i".split()}

# blocos refeitos: o que mudou entre a rodada 1 e a 2
EXPL = {"A2.05": "contagem inclui os arquivos novos do próprio auditor (61→79)", "A2.06": "CSVs ignorados novos do auditor (45→49)",
        "C1.04": "ruído de soma em ponto flutuante do DuckDB (4.3e-14→5.7e-14)",
        "D4.03": "posições no rodapé deslocadas +57 caracteres = o trecho novo das equipes", "D4.04": "inserção (d) 1151→1208 caracteres = mesmo trecho",
        "D9.02": "MANIFEST: data de geração 2026-10-13→2026-10-26"}
for b in ("a", "b", "c1", "c2", "d", "i", "h"):
    dif = sorted(k for k in r1[b] if r1[b][k]["ok"] != r2[b].get(k, {}).get("ok") or r1[b][k]["detalhe"] != r2[b].get(k, {}).get("detalhe"))
    nexp = [k for k in dif if k[:5] not in EXPL or not r2[b][k]["ok"]]
    ok(f"{b.upper()}0.01 bloco {b.upper()} refeito: todas OK como na rodada 1; detalhes iguais, fora diferenças explicadas ({len(r2[b])} verificações)",
       not nexp and len(r1[b]) == len(r2[b]) and all(i["ok"] for i in r2[b].values()),
       "; ".join(f"{k[:5]}: {EXPL[k[:5]]}" for k in dif if k[:5] in EXPL) or "idêntico")
# A: git — mesmas mudanças (A2.01–A2.09 iguais) já cobertas acima; HEAD
ok("A1.01 HEAD continua dc54fb9; mesmo conjunto de modificados/renomeados/não rastreados/ignorados novos da rodada 1 (bloco A idêntico)",
   all(i["ok"] for i in r2["a"].values()))

# D: o rodapé da S2b muda só no trecho das equipes
NOVO = "(Family Health Strategy teams and other primary care teams, parameterized or equivalent by professional working hours;"
VELHO = "(Family Health Strategy and parameterized primary care teams;"
ROD1 = ("(d) Tertiles, defined within each macroregion as in (a), of primary health care coverage (Family Health Strategy and parameterized primary care "
        "teams; Ministry of Health public report Cobertura da Atenção Básica, 2007–2020) in the mother's health region of residence in the previous year: "
        "population-weighted mean of the official municipal monthly coverage over the 12 months; T1 = lowest coverage. Births 2015–2021 only, because the "
        "official series ends in December 2020 (18,624,544 births for preterm birth (total)). (e) Comparator for (d): tertiles of the access index recomputed "
        "in the same births (2015–2021) with the same algorithm. Primary health care coverage measures the supply of teams relative to the population, not "
        "the use of prenatal care: across health region-years it was weakly correlated with the access index (Spearman ρ = −0.10) and inversely with the "
        "population of the health region (ρ = −0.49); coverage and access index tertiles agreed for 33.2% of births (linear-weighted κ = 0.05); 47.5% of "
        "Indigenous births were in the highest coverage tertile and 16.2% in the lowest (access index, 2015–2021: 53.2% in T1 and 16.4% in T3). IC "
        "(interaction contrast) = risk difference (Indigenous vs White) within T1 minus the same difference within T3, per 100 live births. In (b), the Wald "
        "test jointly tests the 6 race × tertile interaction terms (Brown, Black, and Indigenous × T1 and T2; 6 df); in (d) and (e), it jointly tests the "
        "Indigenous × T1 and Indigenous × T2 terms (2 df), with the same cluster-robust covariance. 95% CIs and Wald tests from cluster-robust variance with "
        "clustering by health region of residence (G = 433). (b) to (e) belong to the secondary family of the analysis hierarchy (no multiplicity "
        "adjustment). Sources: tab_e3_02_interacao_rs, tab_e3_02_wald_rs, tab_e3_03a_indice_continuo_rs, tab_e8_04_interacao, tab_e8_04_wald, "
        "tab_e8_03_spearman, tab_e8_03_concordancia_resumo, tab_e8_03_raca_por_tercil.")  # rodapé da rodada 1 (impresso pelo auditor em 26/10)


def rodape(p):
    ws = openpyxl.load_workbook(p)["S2b_access_specifications"]
    v = [str(x) for row in ws.iter_rows(values_only=True) for x in row if x and "(d) Tertiles" in str(x)]
    return v[0] if len(v) == 1 else ""


for nome, p in (("pacote", MS / "suplementar" / f"ESM_1_tables_S1_S6_{V13}.xlsx"), ("Submissao", PROJ / "Submissao/ESM_1.xlsx")):
    r = rodape(p)
    ok(f"D1.0{1 if nome == 'pacote' else 2} rodapé da S2b (ESM_1 {nome}): = o da rodada 1 com só o trecho das equipes trocado "
       "('...teams and other primary care teams, parameterized or equivalent by professional working hours;')",
       r.count(NOVO) == 1 and r[r.index("(d) Tertiles"):].replace(NOVO, VELHO) == ROD1, f"{len(r)} caracteres")
ok("D1.03 a descrição nova cobre as equipes equivalentes por carga horária (ressalva H2.05 da rodada 1 atendida)", "equivalent by professional working hours" in NOVO)
J = (MS / f"numeros_chave_{V13}.json").read_bytes()
ok("D1.04 nenhum número muda: numeros_chave_v13 .json/.md, S2b CSV, disponibilidade e legendas com o mesmo MD5 da rodada 1 (MANIFEST da rodada 1)",
   md5(MS / f"numeros_chave_{V13}.json")[:12] == "6d11323c10b9" and md5(MS / f"numeros_chave_{V13}.md")[:12] == "97a299b33ec6"
   and md5(MS / f"suplementar/S2b_access_specifications_{V13}.csv")[:12] == "746f23492a01"
   and md5(MS / "data_code_availability.md")[:12] == "3f8c3386efc9" and md5(MS / "legendas_figuras.md")[:12] == "8d9ec061d6be")
ok("D1.05 regerados com bytes diferentes mas conteúdo igual ao da v12 (bloco D refeito 26/26): xlsx/docx principais, ESM_1, PDFs S7/S8/ESM_2–4 "
   "(metadados de data); figuras com os mesmos pixels", all(i["ok"] for i in r2["d"].values()), f"{sum(i['ok'] for i in r2['d'].values())}/{len(r2['d'])}")
man = (MS / "MANIFEST.md").read_text()
rows = re.findall(r"^\| (manuscrito/\S+|Submissao/\S+) \| [^|]*\| (?:[^|]|\\\|)*\| ([0-9a-f]{12}) \|$", man, flags=re.M)
bad = [f for f, h in rows if md5(PROJ / ("outputs/" + f if f.startswith("manuscrito/") else f))[:12] != h]
ok("D1.06 MANIFEST regerado: MD5 de cada um dos 49 arquivos = disco; texto fora dos MD5 igual ao da rodada 1 (bloco D9 idêntico)",
   not bad and len(rows) == 49 and r1["d"]["D9.02 MANIFEST v13 × v12 (com o rótulo de versão trocado): mudam só cabeçalho/histórico, a linha da S2b e MD5"]["detalhe"]
   == r2["d"]["D9.02 MANIFEST v13 × v12 (com o rótulo de versão trocado): mudam só cabeçalho/histórico, a linha da S2b e MD5"]["detalhe"].replace("2026-10-26", "2026-10-13"),
   bad or "só a data de geração (26/10) muda no texto")
c1 = list(csv.DictReader(open(MS / f"checa_7b_{V13}.csv")))
ok("D1.07 checa_7b_v13 regerado: 128/128, 15 do bloco 9i", len(c1) == 128 and all(x["ok"] == "True" for x in c1) and sum(x["verificacao"].startswith("8 ") for x in c1) == 15)

# outputs/tables, data/, git: nada novo desde a rodada 1
T1 = datetime(2026, 10, 26, 9, 45).timestamp()
novos = [str(p.relative_to(PROJ)) for d in ("outputs/tables", "data") for p in (PROJ / d).rglob("*") if p.is_file() and p.stat().st_mtime > T1]
ok("I0.01 outputs/tables e data/: nenhum arquivo com mtime depois do início da rodada 1 (26/10 09:45)", not novos, novos[:5])
mud = sorted(str(p.relative_to(PROJ)) for p in PROJ.rglob("*") if p.is_file() and ".git/" not in str(p) and "audit_independente/etapa8" not in str(p)
             and p.stat().st_mtime > T1)
ESP = re.compile(r"^(scripts/(resumos/(LEIAME\.md|etapa8_01_resumo\.py)|etapa7b_02_suplementar\.py|etapa7b_checa\.py|etapa8_05_audita\.py)"
                 r"|outputs/manuscrito/(tabelas|figuras|suplementar)/.*_v13_20261013\.\w+|outputs/manuscrito/(numeros_chave_v13_20261013\.(json|md)|checa_7b_v13_20261013\.csv"
                 r"|MANIFEST\.md|data_code_availability\.md|legendas_figuras\.md|audita_8_v1_20261013\.csv|_resumo8_texto_v1_20261013\.md)"
                 r"|outputs/RESUMO_ETAPA8_v1_20261013\.md|outputs/logs/etapa(7b|8)_20261008\.log|Submissao/(ESM_[1-4]|Fig[1-4])\.\w+)$")
ok("I0.02 arquivos alterados desde a rodada 1: só os 5 scripts citados, o pacote v13 regerado, checa, MANIFEST, audita_8, texto e RESUMO, logs",
   all(ESP.match(m) for m in mud), f"{len(mud)} arquivos; fora do previsto {[m for m in mud if not ESP.match(m)]}")
st = subprocess.run(["git", "-C", str(PROJ), "status", "--porcelain=v1", "-uall"], capture_output=True, text=True).stdout.splitlines()
head = subprocess.run(["git", "-C", str(PROJ), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
ok("I0.03 git: HEAD dc54fb9, sem commit novo; mesmos 13 modificados e 38 renomeados; não rastreados novos só do auditor",
   head == "dc54fb9" and sum(l[:2] == " M" for l in st) == 13 and sum(l[:1] == "R" for l in st) == 38
   and not [l for l in st if l.startswith("??") and "etapa8" in l and "audit_independente" not in l and l[3:] not in
            ("scripts/etapa8_01_baixa_cobertura_ab.py", "scripts/etapa8_02_cobertura_regiao.py", "scripts/etapa8_03_tercis.py", "scripts/etapa8_04_modelos.py",
             "scripts/etapa8_05_audita.py", "scripts/resumos/etapa8_01_resumo.py", "outputs/RESUMO_ETAPA8_v1_20261013.md")], f"{len(st)} linhas de status")

# G2.07 e G1.02
leia = (PROJ / "scripts/resumos/LEIAME.md").read_text()
ok("G1.01 LEIAME corrigido: o etapa8_01 lê o comparacao 'só se existir'; a frase 'sem condição' vale só para os três antigos",
   "e o `etapa8_01` leem sem condição" not in leia and "O `etapa8_01` lê o dele só se existir" in leia and r2["g"]["G2.07 LEIAME: 'o etapa8_01 lê sem condição o comparacao_*.csv do auditor' — FALSO: o gerador lê o CSV só se existir (if CIA.exists())"]["ok"])
au = (PROJ / "scripts/etapa8_05_audita.py").read_text()
ok("G1.02 TROCAS da autoauditoria acompanham o LEIAME novo", "O `etapa8_01` lê o dele só se existir" in au)
ger = (PROJ / "scripts/resumos/etapa8_01_resumo.py").read_text()
ok("G1.03 gerador: regex ^(R\\d+\\.[A-Za-z]|[A-Z]) e NOMES_IA com os meus blocos", r'r"^(R\d+\.[A-Za-z]|[A-Z])"' in ger and "NOMES_IA = {}" not in ger)
g12 = r2["e"]["G1.02 gerador com CSV de 2 rodadas (teste sintético no sandbox): a rodada 2 aparece agrupada pelos blocos (B, C), não num bloco 'R'"]
ok("G1.04 gerador com CSV sintético de 2 rodadas (sandbox): a rodada 2 sai separada em B e C (antes: tudo em 'R'); [ressalva] o rótulo fica 'R2.B.' sem o nome do bloco",
   "R2.B." in g12["detalhe"] and "R2.C." in g12["detalhe"], g12["detalhe"])

# sandbox mínimo com guarda: o gerador reproduz o RESUMO atual (com o CSV da rodada 1 por link)
SB = Path(tempfile.mkdtemp(prefix="aud8_r2_"))
assert not str(SB.resolve()).startswith("/Volumes/Forja")
(SB / "g").mkdir()
shutil.copy2(Path(__file__).with_name("e_sandbox_v1_20261013.py"), SB / "tmp_e.py")   # só para extrair a guarda
gsrc = (SB / "tmp_e.py").read_text()
(SB / "g/sitecustomize.py").write_text(gsrc.split("write_text(r'''", 1)[1].split("''')", 1)[0])
(SB / "tmp_e.py").unlink()
REPO = SB / "repo"
ENV = dict(os.environ, PYTHONPATH=f"{SB}/g:{REPO}/scripts", PYTHONDONTWRITEBYTECODE="1")
t = subprocess.run([sys.executable, "-c", f"open('{AUD}/guarda_r2_teste', 'w')"], env=ENV, capture_output=True, text=True)
assert "GUARDA_FORJA" in t.stderr and not (AUD / "guarda_r2_teste").exists()
subprocess.run(["git", "clone", "-q", "-s", str(PROJ), str(REPO)], check=True)
for rel in ("scripts/resumos/etapa8_01_resumo.py", "scripts/etapa0_lib.py", "outputs/manuscrito/_resumo8_texto_v1_20261013.md", "outputs/manuscrito/audita_8_v1_20261013.csv",
            f"outputs/manuscrito/checa_7b_{V13}.csv", f"outputs/manuscrito/numeros_chave_{V13}.json", f"outputs/manuscrito/_arquivo_v12/numeros_chave_{V12}.json"):
    (REPO / rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROJ / rel, REPO / rel)
(REPO / "outputs/logs").mkdir(parents=True, exist_ok=True)
(REPO / "audit_independente/etapa8").mkdir(parents=True, exist_ok=True)
os.symlink(AUD / "comparacao_8_v1_20261013.csv", REPO / "audit_independente/etapa8/comparacao_8_v1_20261013.csv")
g = subprocess.run([sys.executable, "-B", f"{REPO}/scripts/resumos/etapa8_01_resumo.py"], cwd=REPO, env=ENV, capture_output=True, text=True)
igual = g.returncode == 0 and (REPO / "outputs/RESUMO_ETAPA8_v1_20261013.md").read_bytes() == (PROJ / "outputs/RESUMO_ETAPA8_v1_20261013.md").read_bytes()
shutil.rmtree(SB)
ok("G1.05 o gerador (sandbox com guarda, meu CSV da rodada 1 por link) reproduz o RESUMO regerado byte a byte; sandbox apagado", igual and not SB.exists(), g.stderr[-200:])

# RESUMO: conteúdo das correções
R = (PROJ / "outputs/RESUMO_ETAPA8_v1_20261013.md").read_text()
ok("G2.01 H2.03: sem 'some'; leitura como ausência de evidência", " some" not in R.replace("soma", "") and "ausência de evidência" in R,
   [l.strip()[:120] for l in R.splitlines() if "ausência de evidência" in l][:1])
ok("G2.02 H2.04: Wald de 6 gl citado (sem números novos) e pendência para o pesquisador", "6 gl" in R and "0.0037" not in R and "0.016" not in R,
   [l.strip()[:140] for l in R.splitlines() if "6 gl" in l][:2])
ok("G2.03 H2.02 e H2.06 registrados (dentro das macros; teto de 100%)", ("dentro das macro" in R or "dentro de cada macro" in R) and "100%" in R)
ok("G2.04 'rurais' removido da afirmação (a palavra só aparece na nota que registra a remoção)",
   [l for l in R.splitlines() if "rurais" in l] == [l for l in R.splitlines() if "rurais" in l and "saiu do texto" in l], [l.strip()[:100] for l in R.splitlines() if "rurais" in l])
ok("G2.05 seção 3: 2ª execução do 04 e rodada de 26/10", "26/10" in R and ("22:18" in R or "2ª execução do `etapa7b_04`" in R or "de novo" in R),
   [l.strip()[:140] for l in R.splitlines() if "26/10" in l][:2])
sec2 = R.split("## 2. Auditoria independente")[1].split("## 3.")[0]
ok("G2.06 seção 2 com a minha rodada 1: 138/140 e as 2 falhas (G1.02, G2.07)", "138/140" in sec2 and "G1.02" in sec2 and "G2.07" in sec2,
   re.findall(r"rodada 1: \d+/\d+", sec2))
tabs, cur = [], []
for l in R.splitlines() + [""]:
    if l.strip().startswith("|"):
        cur.append(l.strip())
    elif cur:
        tabs.append(cur)
        cur = []
nc = lambda l: len(re.split(r"(?<!\\)\|", l)) - 2
ok("G2.07 tabelas Markdown do RESUMO bem formadas", all(len({nc(x) for x in t}) == 1 for t in tabs), f"{len(tabs)} tabelas")
for k in ("ρ = −0.10", "33.2%", "| PIG | 1.35 (−1.94 to 4.65); p 0.507 |", "**checa da v13: 128/128 OK**", "(21; 249 no total)"):
    pass
ok("G2.08 números do resultado no RESUMO inalterados (tabela de resultado = meu R; C2.06 refeito OK)",
   r2["c2"]["C2.06 tabela de resultado do RESUMO (9 células: IC Indígena×T1 e p de Wald 2 gl, (d), (e) e principal) = meu R"]["ok"])

# F: execuções de 26/10
log7 = [(m.group(1), m.group(2), m.group(3)) for l in (PROJ / "outputs/logs/etapa7b_20261008.log").read_text().splitlines()
        if (m := re.match(r"\[(2026-10-26 \S+)\] \[(\w+)\] (.*)", l))]
seq = [s for _, s, m in log7 if s != "7b_checa" or "autoauditoria" in m or "FALHA" in m]
ok("F1.01 log 7b de 26/10: 01→02→03→04, checa 128/128 (sem falha), 04", seq == ["7b_01_tabelas", "7b_02_suplementar", "7b_03_figuras", "7b_04_submissao", "7b_checa",
                                                                            "7b_04_submissao"] and any("128/128" in m for _, _, m in log7), seq)
log8 = [l for l in (PROJ / "outputs/logs/etapa8_20261008.log").read_text().splitlines() if l.startswith("[2026-10-26")]
ok("F1.02 log etapa8 de 26/10: só o gerador do RESUMO (1 execução, 10:26:41); etapa8_01–04 não rodaram de novo", len(log8) == 1 and "8_01_resumo" in log8[0], log8)
a8 = pd.read_csv(MS / "audita_8_v1_20261013.csv")
ok("Z1.01 autoauditoria regerada: 65/65", len(a8) == 65 and a8.ok.astype(str).str.lower().eq("true").all())

# grava
if os.environ.get("GRAVA") == "1":
  with open(AUD / "comparacao_8_v1_20261013.csv", "a", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["verificacao", "ok", "detalhe"])
    for l in L:
        w.writerow(l)
print(f"rodada 2: {sum(l['ok'] for l in L)}/{len(L)}")
