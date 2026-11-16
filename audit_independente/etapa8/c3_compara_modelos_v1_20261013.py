"""Bloco C (parte 3) — compara os modelos do auditor (R, c2) com tab_e8_04_* e com a análise principal publicada."""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa8")
import re

import pandas as pd

from comum_v1_20261013 import PROJ, TB, AUD, Res

R = Res("C2")
M = pd.read_csv(AUD / "modelos_auditor_v1_20261013.csv")
I8 = pd.read_csv(TB / "tab_e8_04_interacao_v1_20261008.csv")
W8 = pd.read_csv(TB / "tab_e8_04_wald_v1_20261008.csv").set_index(["exposicao", "desfecho"])
K = ["exposicao", "desfecho", "raca", "nivel"]
m = M[M.exposicao != "tercil_reg"].merge(I8, on=K, how="outer", suffixes=("", "_p"), indicator=True)
dmax = max((m[c] - m[c + "_p"]).abs().max() for c in ("ICR_pp", "ICR_lo", "ICR_hi"))
R.ok("C2.01 6 modelos (2 exposições × 3 desfechos): IC raça×tercil de TODAS as raças (Parda, Preta, Indígena × T1, T2) e IC 95% = tab_e8_04_interacao",
     (m._merge == "both").all() and len(m) == 36 and dmax < 1e-6, f"36 linhas; dif. máx. {dmax:.1e} p.p.")
w = M[M.exposicao != "tercil_reg"].drop_duplicates(["exposicao", "desfecho"]).set_index(["exposicao", "desfecho"])
d6 = (w.chi2_6gl - W8.chi2_6gl).abs().max() / W8.chi2_6gl.min()
d2 = ((w.chi2_ind_2gl - W8.chi2_ind_2gl).abs() / W8.chi2_ind_2gl).max()
R.ok("C2.02 Wald de 6 gl e Wald indígena de 2 gl (χ² e p) = tab_e8_04_wald, nos 6 modelos; N e G = 433 iguais",
     d6 < 1e-6 and d2 < 1e-6 and (w.N == W8.N).all() and (w.G == W8.G).all() and (W8.G == 433).all() and (w.gl_ix == 6).all(),
     f"dif. rel. máx. χ² 6 gl {d6:.1e}, 2 gl {d2:.1e}; N aps ptb {int(w.N[('tercil_aps', 'ptb')]):,}")
R.ok("C2.03 [estimador] o fator (N−1)/(N−K) do projeto é desprezível (χ² 2 gl muda < 1e-5 relativo sem ele); todos os glm convergiram",
     ((w.chi2_ind_2gl / w.chi2_ind_2gl_semfator - 1).abs() < 1e-5).all() and M.conv.all(), f"razão máx. {(w.chi2_ind_2gl / w.chi2_ind_2gl_semfator).max():.8f}")
# principal publicado
pi = pd.read_csv(TB / "tab_e3_02_interacao_rs_v1_20261008.csv").query("analise == '3.2_tercil_reg' and estrato == 'Brasil'")
pw = pd.read_csv(TB / "tab_e7b3_02_wald_ind_v1_20261008.csv").query("cenario == 'principal'").set_index("desfecho")
mp = M[M.exposicao == "tercil_reg"].merge(pi, on=["desfecho", "raca", "nivel"], suffixes=("", "_p"))
dp = max((mp[c] - mp[c + "_p"]).abs().max() for c in ("ICR_pp", "ICR_lo", "ICR_hi"))
wp = M[M.exposicao == "tercil_reg"].drop_duplicates("desfecho").set_index("desfecho")
dw = max(((wp.chi2_ind_2gl - pw.chi2_ind_2gl.reindex(wp.index)) / wp.chi2_ind_2gl).abs().max(), ((wp.chi2_6gl - pw.chi2_6gl.reindex(wp.index)) / wp.chi2_6gl).abs().max())
R.ok("C2.04 meu R reproduz a análise principal publicada (2015–2024, tercil_reg): IC de todas as raças = tab_e3_02_interacao_rs; Wald 6 e 2 gl = tab_e7b3_02_wald_ind",
     len(mp) == 18 and dp < 1e-6 and dw < 1e-6 and (wp.N == pw.N.reindex(wp.index)).all(), f"18 linhas; dif. máx. IC {dp:.1e}; Wald rel. {dw:.1e}")
log = (PROJ / "outputs/logs/etapa8_20261008.log").read_text()
conf = re.findall(r"\[8_04_modelos\] conferência (\w+): IC \(todas as raças e níveis\) = publicado \(dif\. máx\. ([\d.e+-]+)\)", log)
R.ok("C2.05 log: etapa8_04 conferiu a reprodução da análise principal nos 3 desfechos, nas 2 rodadas (dif. máx. ≤ 2.5e-13)",
     len(conf) == 6 and max(float(x) for _, x in conf) <= 2.5e-13 and "dif. máx. 2.5e-13" in log, conf[-3:])
# valores do RESUMO (tabela de resultado) contra o meu R
ind = M[(M.raca == "Indigena") & (M.nivel == "T1")].set_index(["exposicao", "desfecho"])
fmt = lambda r: f"{r.ICR_pp:.2f} ({r.ICR_lo:.2f} to {r.ICR_hi:.2f})".replace("-", "−")
fp = lambda p: "<0.0001" if p < 1e-4 else (f"{p:.3g}" if p < 0.01 else f"{p:.3f}")
res = (PROJ / "outputs/RESUMO_ETAPA8_v1_20261013.md").read_text()
lin = {"ptb": "| PTB total |", "pig": "| PIG |", "ptb_ind": "| PTB indicado |"}
falt = []
for d, l in lin.items():
    row = [x for x in res.splitlines() if x.startswith(l)][0]
    for ex in ("tercil_aps", "tercil_ind21", "tercil_reg"):
        s = f"{fmt(ind.loc[(ex, d)])}; p {fp(ind.loc[(ex, d)].p_ind_2gl)}"
        if s not in row:
            falt.append((d, ex, s))
R.ok("C2.06 tabela de resultado do RESUMO (9 células: IC Indígena×T1 e p de Wald 2 gl, (d), (e) e principal) = meu R", not falt, falt[:3] or "9/9")
R.grava()
