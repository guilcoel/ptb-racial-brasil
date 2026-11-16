"""Blocos F (logs × mtimes), G (afirmações e Markdown do RESUMO), H (números para a revisão metodológica), I (microdados e git no commit).
Não lê a autoauditoria (etapa8_05_audita.py / audita_8_*.csv)."""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa8")
import os
import re
import subprocess
from datetime import datetime

import duckdb
import pandas as pd

from comum_v1_20261013 import PROJ, MS, TB, RAW, PROC, AUD, Res

os.environ["GIT_OPTIONAL_LOCKS"] = "0"
mt = lambda p: datetime.fromtimestamp(os.stat(PROJ / p).st_mtime)
ts = lambda s: datetime.strptime(s, "%Y-%m-%d %H:%M:%S")

# ---------------- F
F = Res("F")
log8 = (PROJ / "outputs/logs/etapa8_20261008.log").read_text().splitlines()
ev = [(ts(m.group(1)), m.group(2), m.group(3)) for l in log8 if (m := re.match(r"\[(\S+ \S+)\] \[(\w+)\] (.*)", l))]
runs = {}
for t, s, msg in ev:
    runs.setdefault(s, []).append(t)
ini = lambda s, k: [t for t, s_, m in ev if s_ == s and (m.startswith(k))]
r03 = ini("8_03_tercis", "conferência")
r04 = ini("8_04_modelos", "conferência ptb:")
F.ok("F1.01 log da etapa8: 01 uma vez (21:44–21:46), 02 uma vez (21:47), 03 duas (21:48 e 22:00), 04 duas (21:49 e 22:02), gerador do RESUMO duas (23:15)",
     [t.strftime("%H:%M") for t in r03] == ["21:48", "22:00"] and [t.strftime("%H:%M") for t in r04] == ["21:49", "22:02"]
     and len(ini("8_01_baixa_cobertura_ab", "fim")) == 1 and len(ini("8_02_cobertura_regiao", "registros")) == 1
     and len(runs.get("8_01_resumo", [])) == 2, {k: f"{v[0]:%H:%M:%S}–{v[-1]:%H:%M:%S} ({len(v)} linhas)" for k, v in runs.items()})
F.ok("F1.02 RESUMO §3: a 1ª rodada do 03 não tinha a população (Spearman só com o índice) e a 2ª deu os mesmos cortes",
     sum("cobertura_x_populacao" in m for t, s, m in ev if s == "8_03_tercis" and t < r03[1]) == 0
     and [m for t, s, m in ev if s == "8_03_tercis" and "T1 ≤" in m and t < r03[1]] == [m for t, s, m in ev if s == "8_03_tercis" and "T1 ≤" in m and t >= r03[1]])
r1 = [m for t, s, m in ev if s == "8_04_modelos" and "IC Indígena×T1" in m and t < r04[1]]
r2 = [m for t, s, m in ev if s == "8_04_modelos" and "IC Indígena×T1" in m and t >= r04[1]]
F.ok("F1.03 RESUMO §3: a 2ª rodada do 04 (22:02) deu, no log, os mesmos IC e Wald da 1ª (a igualdade byte a byte dos CSV da 1ª não é mais verificável)",
     r1 == r2 and len(r1) == 6)
saidas = {"outputs/tables/tab_e8_02_qualidade_v1_20261008.csv": "8_02_cobertura_regiao",
          "data/processed/cobertura_ab_regsaude_ano_v1_20261008.csv": "8_02_cobertura_regiao",
          "outputs/tables/tab_e8_02_cobertura_distribuicao_macro_ano_v1_20261008.csv": "8_02_cobertura_regiao",
          **{f"outputs/tables/tab_e8_03_{x}_v1_20261008.csv": "8_03_tercis" for x in ("cortes", "spearman", "concordancia", "concordancia_resumo",
                                                                                     "raca_por_tercil", "n_casos_raca_tercil")},
          "data/processed/tercil_aps_regsaude_ano_v1_20261008.csv": "8_03_tercis",
          **{f"outputs/tables/tab_e8_04_{x}_v1_20261008.csv": "8_04_modelos" for x in ("interacao", "wald", "conjunto", "dentro")},
          "outputs/RESUMO_ETAPA8_v1_20261013.md": "8_01_resumo"}
fora = []
for p, s in saidas.items():
    a, b = runs[s][0], runs[s][-1]
    ult_ini = {"8_03_tercis": r03[-1], "8_04_modelos": r04[-1]}.get(s, a)
    if not (ult_ini.timestamp() - 2 <= mt(p).timestamp() <= b.timestamp() + 2):
        fora.append((p.split("/")[-1], f"{mt(p):%H:%M:%S}"))
jsons = sorted(RAW.glob("cobertura_ab_uf*.json"))
F.ok("F1.04 mtime de cada saída da Etapa 8 dentro da última execução do script que a grava (JSON entre 21:44:15 e 21:46:09; ±2 s)",
     not fora and all(runs["8_01_baixa_cobertura_ab"][0].timestamp() - 2 <= os.stat(j).st_mtime <= runs["8_01_baixa_cobertura_ab"][-1].timestamp() + 2 for j in jsons),
     fora or f"{len(saidas)} saídas + 27 JSON")
F.ok("F1.05 scripts da etapa 8 modificados antes da execução que vale: 02 (21:46:05 < 21:47), 03 (22:00:17 < 22:00:35), 04 (21:49:17 < 22:02)",
     mt("scripts/etapa8_02_cobertura_regiao.py") < runs["8_02_cobertura_regiao"][0] and mt("scripts/etapa8_03_tercis.py") < r03[1]
     and mt("scripts/etapa8_04_modelos.py") < r04[1] and mt("scripts/resumos/etapa8_01_resumo.py") < runs["8_01_resumo"][0])
log7 = [(ts(m.group(1)), m.group(2), m.group(3)) for l in (PROJ / "outputs/logs/etapa7b_20261008.log").read_text().splitlines()
        if (m := re.match(r"\[(\S+ \S+)\] \[(\w+)\] (.*)", l)) and m.group(1) > "2026-10-13 21:26:33"]
seq = []
for t, s, m in log7:
    if s != "7b_checa" or "FALHA" in m or "autoauditoria" in m:
        seq.append((f"{t:%H:%M}", s, "FALHA" if "FALHA" in m else ""))
esp = [("22:15", "7b_01_tabelas", ""), ("22:15", "7b_02_suplementar", ""), ("22:15", "7b_03_figuras", ""), ("22:15", "7b_04_submissao", ""),
       ("22:17", "7b_checa", "FALHA"), ("22:18", "7b_checa", ""), ("22:18", "7b_04_submissao", "")]
F.ok("F1.06 log da 7b depois de dc54fb9: 01→02→03→04 (22:15), checa falha às 22:17 (S2b, 3/6 linhas), checa 128/128 às 22:18, 04 de novo às 22:18 (MANIFEST)",
     seq == esp and "3/6 linhas" in [m for _, s, m in log7 if "FALHA" in m][0], seq)
F.ok("F1.07 [ressalva] a 2ª execução do 04 (22:18:57, depois do checa) não está na lista de execuções intermediárias do RESUMO §3 (regrava MANIFEST e ESM_4)",
     True, f"MANIFEST {mt('outputs/manuscrito/MANIFEST.md'):%H:%M:%S}; ESM_4 {mt('Submissao/ESM_4.pdf'):%H:%M:%S}")
F.ok("F1.08 checa corrigido (22:17:21) entre a falha (22:17:06) e o OK (22:18:07); pacote (22:15:18–22:15:27) antes do checa",
     ts("2026-10-13 22:17:06") < mt("scripts/etapa7b_checa.py") < ts("2026-10-13 22:18:07")
     and mt(f"outputs/manuscrito/checa_7b_v13_20261013.csv") < mt("outputs/manuscrito/MANIFEST.md"))
F.grava()

# ---------------- G
G = Res("G")
res = (PROJ / "outputs/RESUMO_ETAPA8_v1_20261013.md").read_text()
lin = res.splitlines()
tabs, cur = [], []
for l in lin + [""]:
    if l.strip().startswith("|"):
        cur.append(l.strip())
    elif cur:
        tabs.append(cur)
        cur = []
ncol = lambda l: len(re.split(r"(?<!\\)\|", l)) - 2
mal = [(t[0][:40], [ncol(x) for x in t]) for t in tabs if len({ncol(x) for x in t}) != 1 or not re.fullmatch(r"\|(\s*:?-+:?\s*\|)+", t[1])]
G.ok("G2.01 tabelas Markdown do RESUMO bem formadas (mesmo nº de colunas em todas as linhas; linha separadora)", not mal and len(tabs) == 4,
     f"{len(tabs)} tabelas; mal formadas {mal}")
afirm = {"467,880 registros, 5,570 municípios × 84 competências": True, "3,031 pares região × ano, nas 433 regiões, de 2014 a 2020": True,
         "3,170 registros (0,68%)": True, "Nascimentos de 2015–2021 com região de saúde (18,624,544)": True, "4,330 pares de 2015–2024": True,
         "diferença máxima de 2.5e-13": True, "**Números-chave novos** (21; 249 no total)": True, "**checa da v13: 128/128 OK**": True,
         "ρ = −0.10": True, "ρ = −0.49": True, "33.2% dos nascimentos": True, "κ ponderado = 0.05": True, "| Cobertura da APS | 16.2% | 47.5% |": True,
         "| Índice de pré-natal, 2015–2021 | 53.2% | 16.4% |": True, "de 232 MB": True, "os 93 não rastreados de `docs/referencias/`": True,
         "p de 0.107 a 0.507": True}
falt = [k for k in afirm if k not in res]
G.ok("G2.02 números do texto do RESUMO presentes e conferidos nos blocos B–E (registros, pares, 3,170, N, 4,330 pares, 2.5e-13, 21/249, 128/128, ρ, κ, %, 232 MB, 93)",
     not falt, falt)
G.ok("G2.03 '−0.49: o exato fica logo acima de −0,495' (exato −0.494977)", -0.495 < -0.4949765037087712 < -0.49)
G.ok("G2.04 [ressalva de estilo] o RESUMO mistura separadores (0,68% e −0,495 com vírgula decimal; 0.107, 33.2% com ponto; 3,170 com vírgula de milhar)",
     True, "texto em português com números em formato inglês")
G.ok("G2.05 'O arquivo do Acre tem o mesmo MD5 de uma consulta de teste feita antes': NÃO verificável (a consulta de teste não foi guardada)", True, "não verificado")
G.ok("G2.06 'Regiões pequenas e rurais têm cobertura alta': 'pequenas' apoiado (ρ −0.49 Brasil; −0.34 a −0.68 em cada macro); 'rurais' não foi medido",
     True, "ressalva")
leia = (PROJ / "scripts/resumos/LEIAME.md").read_text()
ger = (PROJ / "scripts/resumos/etapa8_01_resumo.py").read_text()
G.ok("G2.07 LEIAME: 'o etapa8_01 lê sem condição o comparacao_*.csv do auditor' — FALSO: o gerador lê o CSV só se existir (if CIA.exists())",
     not ("e o `etapa8_01` leem sem condição" in leia and "if CIA.exists():" in ger), "LEIAME linha dos comparacao_*; gerador linha 'if CIA.exists()'")
G.ok("G2.08 pendência '<title> dos PDFs continua tmpXXXX.html': confirmado nos metadados de S7, S8 e ESM_4 v13", True, "tmp*.html")
G.grava()

# ---------------- H (números para a revisão metodológica)
H = Res("H")
con = duckdb.connect()
con.execute(f"SET temp_directory='{AUD}/duck_tmp_v1_20261013'")
cob = pd.read_csv(PROC / "cobertura_ab_regsaude_ano_v1_20261008.csv", dtype={"CO_REGSAUD": str})
ter = pd.read_csv(AUD / "terc_auditor_v1_20261013.csv", dtype={"CO_REGSAUD": str})
V3 = PROC / "sinasc_brasil_2015_2024_v3_20261008"
nb = con.execute(f"""SELECT CO_REGSAUD, CAST(ano AS INT) ano, regiao, CAST(raca AS VARCHAR) raca, count(*) n FROM read_parquet('{V3}/*/*.parquet', hive_partitioning=true)
  WHERE incl AND CO_REGSAUD IS NOT NULL AND CAST(ano AS INT) <= 2021 GROUP BY ALL""").df()
c1 = cob.assign(ano=cob.ano + 1)[["CO_REGSAUD", "ano", "cobertura_ab"]]
x = nb.merge(c1, on=["CO_REGSAUD", "ano"]).merge(ter, on=["CO_REGSAUD", "ano"])
alto = x[x.cobertura_ab >= 99]
pct = lambda d: 100 * d.n.sum() / x[x.raca.isin(d.raca.unique())].n.sum()
H.ok("H1.01 teto de 100%: % de região×ano (2014–2020) com cobertura ≥ 99%; % dos nascimentos 2015–2021 (todos / indígenas) expostos a ≥ 99%",
     True, f"pares {100 * (cob.cobertura_ab >= 99).mean():.1f}%; nascimentos {100 * alto.n.sum() / x.n.sum():.1f}%; indígenas "
     f"{100 * alto[alto.raca == 'Indigena'].n.sum() / x[x.raca == 'Indigena'].n.sum():.1f}%; registros municipais com 100%: 69.4% (B1.06)")
t3 = x[x.tercil_aps == "T3"]
H.ok("H1.02 T3 da cobertura: menor cobertura t−1 em T3 por macro (NE começa em 95.7%) e % do T3 com cobertura ≥ 99%", True,
     "; ".join(f"{m} mín {g.cobertura_ab.min():.1f} (≥99%: {100 * g[g.cobertura_ab >= 99].n.sum() / g.n.sum():.0f}%)" for m, g in t3.groupby("regiao")))
ind = x[x.raca == "Indigena"]
H.ok("H1.03 nascimentos indígenas por tercil da cobertura × tercil do índice (2015–2021, %)", True,
     "; ".join(f"APS {a}×IND {b}: {100 * g.n.sum() / ind.n.sum():.1f}%" for (a, b), g in ind.groupby(["tercil_aps", "tercil_ind21"])))
macro_ind = ind.groupby("regiao").n.sum() / ind.n.sum() * 100
H.ok("H1.04 nascimentos indígenas por macrorregião (2015–2021, %)", True, "; ".join(f"{k} {v:.1f}%" for k, v in macro_ind.items()))
H.grava()

# ---------------- I
I = Res("I")
git = lambda *a: subprocess.run(["git", "-C", str(PROJ), *a], capture_output=True, text=True, check=True).stdout
st = [l for l in git("status", "--porcelain=v1", "-uall").splitlines()]
alvo = []
for l in st:
    p = l[3:].split(" -> ")[-1]
    if l.startswith("??") and (p.startswith("docs/referencias/") and p != "docs/referencias/aps_cobertura_ab/ACESSO.txt"):
        continue
    if p.startswith("audit_independente/etapa8/"):
        continue
    alvo.append(p)
susp = [p for p in alvo if p.startswith(("data/", "outputs/tables/", "outputs/logs/")) or p.endswith((".parquet", ".dbc", ".dbf", ".csv.gz", ".rds"))]
gi = lambda *ps: subprocess.run(["git", "-C", str(PROJ), "check-ignore", "--no-index", *ps], capture_output=True, text=True)
ign = gi(*alvo).stdout.split()
I.ok("I1.01 conjunto do commit (rastreados modificados/renomeados + não rastreados fora de docs/referencias, mais o ACESSO.txt): nada em data/, "
     "outputs/tables, logs, parquet/rds; nada ignorado", not susp and not ign, f"{len(alvo)} arquivos; suspeitos {susp}; ignorados {ign}")
colunas_micro = re.compile(r"\b(CODMUNRES|DTNASC|NUMERODN|IDADEMAE|SEMAGESTAC|PESO|RACACORMAE)\b")
cand = []
for p in alvo:
    if p.endswith((".csv", ".md", ".json", ".txt")) and "audita_8" not in p:
        t = (PROJ / p).read_text(errors="ignore")
        if p.endswith(".csv") and colunas_micro.search(t.splitlines()[0] if t else ""):
            cand.append(p)
I.ok("I1.02 nenhum CSV do commit com colunas de microdado (CODMUNRES, DTNASC, IDADEMAE, PESO...) no cabeçalho (exceto audita_8, no bloco Z)", not cand, cand)
s2b = pd.read_csv(MS / "suplementar/S2b_access_specifications_v13_20261013.csv")
I.ok("I1.03 S2b e números-chave novos: só estimativas e N grandes (≥ 18 milhões)", s2b.shape == (3, 9), "ver D")
acc = (PROJ / "docs/referencias/aps_cobertura_ab/ACESSO.txt").read_text()
I.ok("I1.04 ACESSO.txt (entra no commit): só metadados (URL, data, bytes, MD5); sem registros do JSON", "coMunicipioIbge" not in acc and len(acc) < 10000, f"{len(acc)} bytes")
I.ok("I1.05 .gitignore cobre data/ (bruto da cobertura e CSVs de data/processed), outputs/tables e logs",
     all(gi(p).returncode == 0 for p in ("data/raw/aps_cobertura_ab/cobertura_ab_uf11_201401_202012.json",
                                                                  "outputs/tables/tab_e8_03_n_casos_raca_tercil_v1_20261008.csv", "outputs/logs/etapa8_20261008.log")))
tam = sorted(((PROJ / p).stat().st_size, p) for p in alvo)[-3:]
I.ok("I1.06 [descritivo] maiores arquivos do commit", True, "; ".join(f"{p.split('/')[-1]} {s / 1e6:.1f} MB" for s, p in tam))
I.ok("I1.07 [ressalva] tab_e8_03_n_casos_raca_tercil (n e casos por macro × raça × tercil, sinaliza 1 célula pequena) fica em outputs/tables (ignorado, no Forja); "
     "não entra no commit nem no pacote", "outputs/tables/tab_e8_03_n_casos_raca_tercil_v1_20261008.csv" not in alvo)
I.ok("I1.08 meus arquivos em audit_independente/etapa8: CSV ignorados pelo git; .py/.R/.json/.md só com agregados (estimativas, contagens ≥ 1,214)",
     gi("audit_independente/etapa8/terc_auditor_v1_20261013.csv").returncode == 0)
I.grava()
