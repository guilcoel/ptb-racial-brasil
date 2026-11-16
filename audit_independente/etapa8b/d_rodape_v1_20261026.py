"""Bloco D — rodapé e rótulos da S2b: o texto novo descreve o teste de 6 gl de (d) e (e)? Termos do teste conferidos no código do etapa8_04
(etapa3_lib.knol: todos os ix__ = raça ≠ Branca × nível ≠ T3) e nos graus de liberdade da tab_e8_04_wald."""
import csv
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from comum_v1_20261026 import *
import openpyxl
from scipy.stats import chi2

B = Bloco("d")
ws = openpyxl.load_workbook(MS / "suplementar" / f"ESM_1_tables_S1_S6_{V14}.xlsx", read_only=True)["S2b_access_specifications"]
rod = [c for r in ws.iter_rows(values_only=True) for c in r if c][-1]
frase = re.search(r"In \(b\), the Wald test.*?with the same cluster-robust covariance\.", rod).group(0)
B.ok("D1.01", "rodapé: a frase dos Wald diz (b) = 6 termos (Brown, Black, Indigenous × T1 e T2); (d) e (e) = 2 gl indígena e, separadamente, os mesmos 6 termos (6 df)",
     "Brown, Black, and Indigenous × T1 and T2; 6 df" in frase and "in (d) and (e), it jointly tests the Indigenous × T1 and Indigenous × T2 terms (2 df) and, separately, the same 6 race × tertile terms as in (b) (6 df)" in frase, frase)
lib3 = (PROJ / "scripts/etapa3_lib.py").read_text()
s84 = (PROJ / "scripts/etapa8_04_modelos.py").read_text()
B.ok("D1.02", "código: o Wald de 6 gl do etapa8_04 é o r['wald'] do knol = todos os termos ix__ (raça ≠ Branca × nível ≠ T3), referência T3 (NIV, 'T3')",
     'idx = [j for j, nm in enumerate(fit["names"]) if nm.startswith("ix__")]' in lib3 and 'w6 = r["wald"].iloc[0]' in s84 and 'NIV, "T3"' in s84)
with open(TB / "tab_e8_04_wald_v1_20261008.csv", newline="") as f:
    W = list(csv.DictReader(f))
B.ok("D1.03", "graus de liberdade: p_6gl = P(χ² com 6 gl) em todas as linhas → 6 termos (Parda, Preta, Indígena × T1, T2; sem Amarela)",
     all(abs(chi2.sf(float(r["chi2_6gl"]), 6) - float(r["p_6gl"])) < 1e-12 for r in W))
with open(PROJ / "audit_independente/etapa8/modelos_auditor_v1_20261013.csv", newline="") as f:
    gl = {r["gl_ix"] for r in csv.DictReader(f)}
B.ok("D1.04", "auditoria da Etapa 8 (R): 6 coeficientes de interação em todos os modelos (gl_ix = 6)", gl == {"6"}, gl)
B.ok("D1.05", "[ressalva] 'the same 6 race × tertile terms as in (b)': em (d) e (e) os termos são raça × tercil da própria coluna (cobertura; índice 2015–2021), "
     "não os tercis nacionais de (b). A estrutura é a mesma (Brown, Black, Indigenous × T1 e T2), mas 'the same … terms' pode ser lido como os mesmos termos. "
     "Sugestão: 'the 6 race × tertile terms of its own tertiles (Brown, Black, and Indigenous × T1 and T2; 6 df)'", True)
h = next(r for r in ws.iter_rows(values_only=True) if r[0] == "Outcome")
B.ok("D1.06", "[ressalva] cabeçalhos: (b) 'Wald p (6 df)' e (d)/(e) 'Wald p, Indigenous terms (2 df)', mas as colunas novas não dizem '(6 df)': "
     "'Wald p, 6 race×tertile terms'. Não é erro; uniformizar ajudaria", True, [c for c in h if "Wald" in c])
B.ok("D1.07", "rodapé: o restante segue válido para as colunas novas ('95% CIs and Wald tests from cluster-robust variance … G = 433'; '(b) to (e) belong to the secondary family'; fontes já incluem tab_e8_04_wald)",
     "Wald tests from cluster-robust variance with clustering by health region of residence (G = 433)" in rod and "(b) to (e) belong to the secondary family" in rod and "tab_e8_04_wald" in rod
     and all(r["G"] == "433" for r in W))
B.grava()
