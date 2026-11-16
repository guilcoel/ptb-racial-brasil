"""
1.4 Prevalências com IC 95% de Wilson para PTB, subtipos, lbw_termo e PIG, por
(a) raça × região (+ Brasil), (b) raça × idade_cat, (c) raça × esc_cat, (d) raça × ano.
Denominadores: PTB e subtipos = amostra analítica; lbw_termo = 37–41 sem com peso válido;
PIG = elegíveis (única, 24–42 sem, sexo e peso válidos).
Também lê os pares (casos, denominador) da base em nível individual para a auditoria (1.4 = agregado).
Saídas: tab_e1_04_prevalencias (longa, numérica), tab_e1_04_prev_raca_regiao_fmt, fig01_ptb_raca_regiao.

Argumento opcional: --sem-ce-df (sensibilidade 1.7) -> sufixo _semCEDF.
"""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import etapa1_lib as E

SENS = "--sem-ce-df" in sys.argv
SUF = "_semCEDF" if SENS else ""
log = E.logger("04_prevalencias" + SUF)
d = E.load(["raca", "regiao", "uf", "idade_cat", "esc_cat", "ano", "ptb", "ptb_sub", "lbw_termo", "pig"])
if SENS:
    d = d[~d.uf.isin(["CE", "DF"])]
log("amostra", len(d))
d["ptb_extremo"] = (d.ptb_sub == "1_extremo_lt28").astype(int)
d["ptb_muito"] = (d.ptb_sub == "2_muito_28a31").astype(int)
d["ptb_mod_tardio"] = (d.ptb_sub == "3_moderado_tardio_32a36").astype(int)
OUT = ["ptb", "ptb_extremo", "ptb_muito", "ptb_mod_tardio", "lbw_termo", "pig"]
d["Brasil"] = "Brasil"
d["raca_t"] = d.raca.astype(object)

rows = []
for estrato, col in [("regiao", "regiao"), ("brasil", "Brasil"), ("idade_cat", "idade_cat"),
                     ("esc_cat", "esc_cat"), ("ano", "ano")]:
    for desf in OUT:
        s = d[d[desf].notna()]
        for raca_lab, ss in [("Total", s)] + [(g, s[s.raca == g]) for g in E.L.RACA_ORDER]:
            g = ss.groupby(col, observed=True)[desf].agg(["sum", "size"]).reset_index()
            for _, r in g.iterrows():
                p, lo, hi = E.wilson(r["sum"], r["size"])
                rows.append(dict(estrato=estrato, nivel=str(r[col]), raca=raca_lab, desfecho=desf,
                                 casos=int(r["sum"]), denominador=int(r["size"]),
                                 prev_pct=100 * p, ic_lo=100 * lo, ic_hi=100 * hi))
t = pd.DataFrame(rows)
t.to_csv(E.L.TAB / f"tab_e1_04_prevalencias{SUF}_v1_{E.L.STAMP}.csv", index=False)
log(f"prevalências: {len(t):,} linhas")

f = t[t.estrato.isin(["regiao", "brasil"])].copy()
f["valor"] = (f.casos.map(E.fmt_n) + " / " + f.denominador.map(E.fmt_n) + "; " + f.prev_pct.map(E.fmt_f) +
              " (" + f.ic_lo.map(E.fmt_f) + "–" + f.ic_hi.map(E.fmt_f) + ")")
w = f.pivot_table(index=["desfecho", "nivel"], columns="raca", values="valor", aggfunc="first")
w = w[["Total"] + E.L.RACA_ORDER]
w.to_csv(E.L.TAB / f"tab_e1_04_prev_raca_regiao_fmt{SUF}_v1_{E.L.STAMP}.csv")

# figura: PTB por raça em cada região (+ Brasil), IC 95% Wilson
COR = {"Branca": "#2a78d6", "Parda": "#eb6834", "Preta": "#1baf7a", "Indigena": "#eda100"}
MK = {"Branca": "o", "Parda": "s", "Preta": "D", "Indigena": "^"}
LAB = {"Branca": "White", "Parda": "Parda (Brown)", "Preta": "Preta (Black)", "Indigena": "Indigenous"}
REG = ["Brasil", "N", "NE", "SE", "S", "CO"]
REGLAB = {"Brasil": "Brazil", "N": "North", "NE": "Northeast", "SE": "Southeast", "S": "South", "CO": "Center-West"}
p = f[(f.desfecho == "ptb") & (f.raca != "Total")]
fig, ax = plt.subplots(figsize=(7.5, 4.2))
for i, g in enumerate(E.L.RACA_ORDER):
    q = p[p.raca == g].set_index("nivel").loc[REG]
    x = np.arange(len(REG)) + (i - 1.5) * 0.17
    ax.errorbar(x, q.prev_pct, yerr=[q.prev_pct - q.ic_lo, q.ic_hi - q.prev_pct], fmt=MK[g], color=COR[g],
                ms=6, lw=1.5, capsize=2.5, label=LAB[g], markeredgecolor="white", markeredgewidth=0.6)
ax.set_xticks(np.arange(len(REG)), [REGLAB[r] for r in REG])
ax.axvline(0.5, color="#c9c8c0", lw=0.8)
ax.set_ylabel("Preterm birth, % (95% CI)")
ax.grid(axis="y", color="#e6e5df", lw=0.6)
ax.set_axisbelow(True)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
ax.legend(ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.12), fontsize=8.5)
fig.tight_layout()
fn = E.L.PROJ / "outputs" / "figures" / f"fig01_ptb_raca_regiao{SUF}_v1_{E.L.STAMP}.png"
fn.parent.mkdir(exist_ok=True)
fig.savefig(fn, dpi=300)
log(f"figura gravada: {fn.name}")
