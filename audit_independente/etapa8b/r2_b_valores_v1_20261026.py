"""Bloco B — valores: os 6 p de 6 gl recalculados de tab_e8_04_wald (csv puro + qui-quadrado), comparados com S2b (CSV, ESM_1 do pacote e de
Submissao/), números-chave (.json e .md), coluna certa (d ← tercil_aps; e ← tercil_ind21), e com a auditoria da Etapa 8 (modelos_auditor)."""
import csv
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from comum_v1_20261026 import *
from scipy.stats import chi2
import openpyxl

B = Bloco("b")
OUTC = {"ptb": "Preterm birth (total)", "pig": "SGA", "ptb_ind": "Provider-initiated preterm birth"}
COLX = {"tercil_aps": "(d) Primary health care coverage tertiles, 2015–2021", "tercil_ind21": "(e) Access index tertiles, 2015–2021"}
SUF = {"tercil_aps": "aps", "tercil_ind21": "indice_2015_2021"}
with open(TB / "tab_e8_04_wald_v1_20261008.csv", newline="") as f:
    W = {(r["exposicao"], r["desfecho"]): r for r in csv.DictReader(f)}
B.ok("B1.01", "tab_e8_04_wald: 6 linhas (2 exposições × 3 desfechos), G = 433, mtime anterior a cdddf8f",
     len(W) == 6 and all(r["G"] == "433" for r in W.values()) and (TB / "tab_e8_04_wald_v1_20261008.csv").stat().st_mtime < int(git("log", "-1", "--format=%ct", BASE)),
     sorted(W))
# p a partir do qui-quadrado, de forma independente
dp = {k: abs(chi2.sf(float(r["chi2_6gl"]), 6) - float(r["p_6gl"])) / float(r["p_6gl"]) for k, r in W.items()}
B.ok("B1.02", "p_6gl = P(χ²₆ > chi2_6gl) recalculado com scipy (diferença relativa < 1e-9) nas 6 linhas", max(dp.values()) < 1e-9, f"máx {max(dp.values()):.1e}")
esp = {k: pfmt(chi2.sf(float(r["chi2_6gl"]), 6)) for k, r in W.items()}
B.ok("B1.03", "formatação própria (3 algarismos significativos; <0.0001) dos 6 p", True, {f"{SUF[e]}_{d}": v for (e, d), v in esp.items()})

# S2b CSV v14
with open(MS / "suplementar" / f"S2b_access_specifications_{V14}.csv", newline="", encoding="utf-8") as f:
    rd = list(csv.reader(f))
hdr = rd[0]
linhas = {r[0]: dict(zip(hdr, r)) for r in rd[1:]}
c6 = {e: f"{COLX[e]}: Wald p, 6 race×tertile terms (6 df)" for e in COLX}
cel = {(e, d): linhas[OUTC[d]][c6[e]] for e in COLX for d in OUTC}
B.ok("B2.01", "S2b CSV v14: as 6 células de 6 gl = p recalculado e formatado aqui", all(cel[k] == esp[k] for k in esp), {f"{k[0]}|{k[1]}": (cel[k], esp[k]) for k in esp})
# coluna certa: o valor da coluna (d) não bate com o tercil_ind21 e vice-versa
troca = all(cel[("tercil_aps", d)] != esp[("tercil_ind21", d)] for d in OUTC if esp[("tercil_aps", d)] != esp[("tercil_ind21", d)])
B.ok("B2.02", "coluna certa: (d) recebe tercil_aps e (e) tercil_ind21 (com os valores trocados a comparação falharia)", troca and all(cel[k] == esp[k] for k in esp))
B.ok("B2.03", "cabeçalho: 11 colunas; cada 6 gl logo depois do Wald indígena de 2 gl da mesma letra; (d) antes de (e)",
     len(hdr) == 11 and hdr[6] == f"{COLX['tercil_aps']}: Wald p, Indigenous terms (2 df)" and hdr[7] == c6["tercil_aps"]
     and hdr[9] == f"{COLX['tercil_ind21']}: Wald p, Indigenous terms (2 df)" and hdr[10] == c6["tercil_ind21"], hdr[5:])
# 2 gl intactos e coerentes
c2 = all(linhas[OUTC[d]][f"{COLX[e]}: Wald p, Indigenous terms (2 df)"] == pfmt(chi2.sf(float(W[(e, d)]["chi2_ind_2gl"]), 2)) for e in COLX for d in OUTC)
B.ok("B2.04", "as células de 2 gl (já existentes) continuam = P(χ²₂) recalculado de tab_e8_04_wald", c2)
B.ok("B2.05", "ordem das linhas: PTB total, PIG, PTB indicado (3 linhas)", [r[0] for r in rd[1:]] == list(OUTC.values()))


# ESM_1 do pacote e de Submissao/
def s2b_xl(p):
    wb = openpyxl.load_workbook(p, read_only=True)
    ws = wb["S2b_access_specifications"]
    rows = [tuple(c for c in r) for r in ws.iter_rows(values_only=True)]
    h = rows[2]
    return h, {r[0]: dict(zip(h, r)) for r in rows[3:6]}, rows


for nome, p in [("pacote", MS / "suplementar" / f"ESM_1_tables_S1_S6_{V14}.xlsx"), ("Submissao", SUB / "ESM_1.xlsx")]:
    h, L, rows = s2b_xl(p)
    okx = list(h) == hdr and all(L[OUTC[d]][c6[e]] == esp[(e, d)] for e in COLX for d in OUTC) and \
        all(str(L[r[0]][c]) == v for r in rd[1:] for c, v in zip(hdr, r))
    B.ok(f"B3.0{1 if nome == 'pacote' else 2}", f"ESM_1 ({nome}), aba S2b: cabeçalho e as 33 células = CSV; 6 gl = p recalculado", okx, nome)
B.ok("B3.03", "ESM_1 de Submissao/ = ESM_1 do pacote (mesmo conteúdo da aba S2b)", s2b_xl(SUB / "ESM_1.xlsx")[2] == s2b_xl(MS / "suplementar" / f"ESM_1_tables_S1_S6_{V14}.xlsx")[2])

# números-chave
J = json.load(open(MS / f"numeros_chave_{V14}.json"))
JD = {i["id"]: i for i in J}
nk = all(JD[f"Wald6_{SUF[e]}_{d}"]["valor_formatado"] == esp[(e, d)] and abs(JD[f"Wald6_{SUF[e]}_{d}"]["valor_bruto"] - float(W[(e, d)]["p_6gl"])) <= 1e-15 * max(1, float(W[(e, d)]["p_6gl"]))
         and JD[f"Wald6_{SUF[e]}_{d}"]["filtro"] == f"exposicao={e}, desfecho={d}" for e in COLX for d in OUTC)
B.ok("B4.01", "JSON: Wald6_aps_* e Wald6_indice_2015_2021_* com valor_formatado = recalculado, valor_bruto = p_6gl (|dif| ≤ 1e-15) e filtro da exposição certa", nk,
     {k: (JD[k]["valor_formatado"], JD[k]["valor_bruto"]) for k in JD if k.startswith("Wald6")})
desc_ok = all(("primary health care coverage" in JD[f"Wald6_aps_{d}"]["descricao"]) and ("access index" in JD[f"Wald6_indice_2015_2021_{d}"]["descricao"])
              and OUTC[d] in JD[f"Wald6_aps_{d}"]["descricao"] for d in OUTC)
B.ok("B4.02", "descrições dos 6 números-chave citam a exposição e o desfecho certos", desc_ok)
md = (MS / f"numeros_chave_{V14}.md").read_text()
mdl = {}
for l in md.splitlines():
    m = re.match(r"^\| (Wald6_\S+) \| ([^|]+) \|", l)
    if m:
        mdl[m.group(1)] = m.group(2).strip()
B.ok("B4.03", "MD: as 6 linhas Wald6_* com o mesmo valor do JSON", len(mdl) == 6 and all(mdl[k] == JD[k]["valor_formatado"] for k in mdl), mdl)
B.ok("B4.04", "números-chave: 255 = 249 + 6, ids únicos", len(J) == 255 and len(JD) == 255)
# auditoria independente da Etapa 8 (estimativas agregadas já existentes)
with open(PROJ / "audit_independente/etapa8/modelos_auditor_v1_20261013.csv", newline="") as f:
    MA = {}
    for r in csv.DictReader(f):
        MA[(r["exposicao"], r["desfecho"])] = float(r["p_6gl"])
dma = {k: abs(MA[k] - float(W[k]["p_6gl"])) / float(W[k]["p_6gl"]) for k in W}
B.ok("B5.01", "p_6gl = o do R da auditoria independente da Etapa 8 (modelos_auditor; dif. relativa < 1e-6)", max(dma.values()) < 1e-6, f"máx {max(dma.values()):.1e}")
B.grava()
