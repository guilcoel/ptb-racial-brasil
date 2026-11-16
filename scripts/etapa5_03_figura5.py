"""
5.4 Fig. 5 — MAIHDA do PIG.
a: risco previsto de PIG por estrato (Modelo 2, fixos + aleatório; IC 95% por simulação), 540 estratos ordenados,
   cor e marcador por raça, linha horizontal no risco do estrato de referência (Branca, ≥12 anos, 20–34, SE, T3).
b: efeitos aleatórios de estrato do Modelo 2 (û_j, escala logit, IC 95% pela variância condicional), ordenados.
Padrão da revista: TIFF 600 dpi LZW, 174 mm, Arial, letras de painel, sem título interno, PNG de pré-visualização.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import etapa0_lib as L

log = L.Logger("03_figura5", etapa="etapa5")
plt.rcParams.update({"font.family": "Arial", "font.size": 8, "axes.linewidth": 0.6,
                     "xtick.major.width": 0.6, "ytick.major.width": 0.6})
MM = 1 / 25.4
COR = {"Branca": "#3a3a3a", "Parda": "#b8461b", "Preta": "#0b7a55", "Indigena": "#1c5cab"}
MK = {"Branca": "o", "Parda": "s", "Preta": "D", "Indigena": "^"}
LAB = {"Branca": "White", "Parda": "Brown (Parda)", "Preta": "Black (Preta)", "Indigena": "Indigenous"}
REF = "Branca|ge12|20a34|SE|T3"
p = pd.read_csv(L.TAB / f"tab_e5_03_predicoes_v1_{L.STAMP}.csv")
assert len(p) == 540
fig, axs = plt.subplots(2, 1, figsize=(174 * MM, 150 * MM))


def painel(ax, col, lo, hi, ylab, ref):
    q = p.sort_values(col).reset_index(drop=True)
    x = np.arange(len(q))
    ax.vlines(x, q[lo], q[hi], colors=q.raca.map(COR), lw=0.45, alpha=0.5)
    for i, rr in q.iterrows():   # na ordem do ranking: nenhuma raça fica sistematicamente por baixo
        ax.scatter(i, rr[col], marker=MK[rr.raca], s=4.5, color=COR[rr.raca], edgecolors="white", linewidths=0.15, zorder=3)
    for g in ["Branca", "Parda", "Preta", "Indigena"]:
        ax.scatter([], [], marker=MK[g], s=4.5, color=COR[g], label=LAB[g])
    ax.axhline(ref, color="#9a9990", lw=0.7, ls="--", zorder=1)
    ax.set_xlim(-6, len(q) + 5)
    ax.set_xticks([])
    ax.set_ylabel(ylab)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.grid(axis="y", color="#e6e5df", lw=0.5)
    return q


r = p[p.estrato == REF].iloc[0]
painel(axs[0], "p_pct", "p_lo", "p_hi", "Predicted SGA risk, %", r.p_pct)
axs[0].text(len(p) - 2, r.p_pct, "Reference stratum", ha="right", va="bottom", fontsize=7, color="#5f5e58")
painel(axs[1], "u", "u_lo", "u_hi", "Stratum random effect, logit", 0.0)
axs[1].set_xlabel("Intersectional strata (n = 540), ranked")
for ax, letra in zip(axs, "ab"):
    ax.text(-0.06, 1.02, letra, transform=ax.transAxes, fontsize=10, fontweight="bold", ha="right")
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, frameon=False, ncol=4, loc="upper center", fontsize=8, markerscale=1.8)
fig.tight_layout(rect=(0, 0, 1, 0.96))
nome = f"fig5_maihda_pig_v1_{L.STAMP}"
fig.savefig(L.PROJ / "outputs/figures" / f"{nome}.tiff", dpi=600, format="tiff", pil_kwargs={"compression": "tiff_lzw"})
fig.savefig(L.PROJ / "outputs/figures" / f"{nome}.png", dpi=200)
log(f"figura {nome} gravada; referência p = {r.p_pct:.2f}%")
