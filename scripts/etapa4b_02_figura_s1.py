"""
4b.2 Fig. S1 — distribuição da IG (semanas 28–42, % de todos os nascimentos do grupo) por método de estimação,
painéis a–d por raça. Padrão da revista: TIFF 600 dpi LZW, 174 mm, Arial, letras de painel, sem título interno,
marcador e cor distintos por método (contraste ≥ 4.5:1: #3a3a3a, #b8461b, #1c5cab), PNG de pré-visualização.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import etapa0_lib as L

log = L.Logger("02_figura_s1", etapa="etapa4b")
plt.rcParams.update({"font.family": "Arial", "font.size": 8, "axes.linewidth": 0.6})
MM = 1 / 25.4
f = pd.read_csv(L.TAB / f"tab_e4b_02_dist_ig_v1_{L.STAMP}.csv")
MET = [("DUM", "LMP-based", "#3a3a3a", "o", "-"), ("outro_metodo", "Physical exam / other", "#b8461b", "s", "--"),
       ("ignorado", "Method unknown", "#1c5cab", "^", ":")]
RAC = [("Branca", "White"), ("Parda", "Brown (Parda)"), ("Preta", "Black (Preta)"), ("Indigena", "Indigenous")]
fig, axs = plt.subplots(2, 2, figsize=(174 * MM, 120 * MM), sharex=True, sharey=True)
for ax, (r, rl), letra in zip(axs.ravel(), RAC, "abcd"):
    for m, ml, cor, mk, ls in MET:
        x = f[(f.raca == r) & (f.ig_metodo == m)].sort_values("SEMAGESTAC")
        ax.plot(x.SEMAGESTAC, x.pct, color=cor, marker=mk, ms=3.2, lw=1.1, ls=ls, label=ml)
    ax.axvline(36.5, color="#9a9990", lw=0.6)
    ax.text(0.02, 0.95, rl, transform=ax.transAxes, fontsize=8, va="top")
    ax.text(-0.02, 1.03, letra, transform=ax.transAxes, fontsize=10, fontweight="bold", ha="right")
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.grid(axis="y", color="#e6e5df", lw=0.5)
    ax.set_xticks(range(28, 43, 2))
for ax in axs[1]:
    ax.set_xlabel("Gestational age, completed weeks")
for ax in axs[:, 0]:
    ax.set_ylabel("Births, %")
h, l = axs[0, 0].get_legend_handles_labels()
fig.legend(h, l, frameon=False, ncol=3, loc="upper center", fontsize=8)
fig.tight_layout(rect=(0, 0, 1, 0.94))
nome = f"figS1_dist_ig_metodo_raca_v1_{L.STAMP}"
fig.savefig(L.PROJ / "outputs/figures" / f"{nome}.tiff", dpi=600, format="tiff", pil_kwargs={"compression": "tiff_lzw"})
fig.savefig(L.PROJ / "outputs/figures" / f"{nome}.png", dpi=200)
log(f"figura {nome} gravada")
