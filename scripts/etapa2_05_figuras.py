"""
2.5 Figuras no padrão da revista (J Racial Ethn Health Disparities): TIFF 600 dpi (LZW), 174 mm de largura,
Arial 8–9 pt, sem título interno, marcador distinto por raça além da cor, contraste ≥ 4.5:1 contra branco
(cinza #3a3a3a 11.6:1; azul #1c5cab 6.6; laranja #b8461b 5.3; verde #0b7a55 5.3). PNG de pré-visualização (200 dpi).
Paleta conferida no validador da skill dataviz (--pairs all): CVD e visão normal PASS; o cinza (Branca, referência)
falha só as checagens de matiz (luminosidade/croma), mitigado pelo marcador próprio e pela legenda.

Fig. 1: prevalência bruta de PTB espontâneo e indicado por raça (Brasil), IC 95% Wilson.
Fig. 2: RP do M2 por raça (vs Branca) para os 5 desfechos (forest plot, eixo log).
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import etapa1_lib as E
import etapa0_lib as L

log = L.Logger("05_figuras", etapa="etapa2")
plt.rcParams.update({"font.family": "Arial", "font.size": 8, "axes.linewidth": 0.6,
                     "xtick.major.width": 0.6, "ytick.major.width": 0.6})
MM = 1 / 25.4
COR = {"Branca": "#3a3a3a", "Parda": "#b8461b", "Preta": "#0b7a55", "Indigena": "#1c5cab"}
MK = {"Branca": "o", "Parda": "s", "Preta": "D", "Indigena": "^"}
LAB = {"Branca": "White", "Parda": "Brown (Parda)", "Preta": "Black (Preta)", "Indigena": "Indigenous"}
FIG = L.PROJ / "outputs" / "figures"
FIG.mkdir(exist_ok=True)


def salva(fig, nome):
    fig.savefig(FIG / f"{nome}.tiff", dpi=600, format="tiff", pil_kwargs={"compression": "tiff_lzw"})
    fig.savefig(FIG / f"{nome}.png", dpi=200)
    log(f"figura {nome}.tiff (600 dpi) + .png")


def eixo(ax):
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.grid(axis="y", color="#e6e5df", lw=0.5)
    ax.set_axisbelow(True)


# Fig. 1
d = pd.read_parquet(L.PROC / f"sinasc_brasil_2015_2024_v3_{L.STAMP}", columns=["incl", "raca", "ptb_esp", "ptb_ind"],
                    filters=[("incl", "==", True)])
rows = []
for desf in ("ptb_esp", "ptb_ind"):
    s = d[d[desf].notna()]
    for g in E.L.RACA_ORDER:
        x = s.loc[s.raca == g, desf]
        p, lo, hi = E.wilson(int(x.sum()), len(x))
        rows.append(dict(desfecho=desf, raca=g, casos=int(x.sum()), n=len(x), p=100 * p, lo=100 * lo, hi=100 * hi))
f1 = pd.DataFrame(rows)
f1.to_csv(L.TAB / f"tab_e2_05_fig1_dados_v1_{L.STAMP}.csv", index=False)
fig, axs = plt.subplots(1, 2, figsize=(174 * MM, 70 * MM), sharey=True)
for ax, (desf, tit, letra) in zip(axs, [("ptb_esp", "Spontaneous preterm birth, % (95% CI)", "a"),
                                       ("ptb_ind", "Provider-initiated preterm birth, % (95% CI)", "b")]):
    q = f1[f1.desfecho == desf].set_index("raca").loc[E.L.RACA_ORDER]
    for i, g in enumerate(E.L.RACA_ORDER):
        ax.errorbar(i, q.p[g], yerr=[[q.p[g] - q.lo[g]], [q.hi[g] - q.p[g]]], fmt=MK[g], color=COR[g], ms=5,
                    capsize=2, lw=0.9, markeredgecolor="white", markeredgewidth=0.5)
        ax.annotate(f"{q.p[g]:.1f}", (i, q.hi[g]), xytext=(0, 3), textcoords="offset points", ha="center", fontsize=7.5)
    ax.set_xticks(range(4), [LAB[g].replace(" (", "\n(") for g in E.L.RACA_ORDER])
    ax.set_xlim(-0.5, 3.5)
    ax.text(-0.02, 1.02, letra, transform=ax.transAxes, fontsize=10, fontweight="bold", ha="right")
    ax.set_ylabel(tit)
    ax.yaxis.set_tick_params(labelleft=True)
    eixo(ax)
axs[0].set_ylim(0, None)
fig.tight_layout()
salva(fig, f"fig1_ptb_espontaneo_indicado_raca_v1_{L.STAMP}")

# Fig. 2
t = pd.read_csv(L.TAB / f"tab_e2_04_modelos_long_v1_{L.STAMP}.csv")
m = t[(t.modelo == "M2") & (t.regiao == "Brasil")]
DES = [("ptb", "Preterm birth (<37 wk)"), ("ptb_esp", "Spontaneous PTB"), ("ptb_ind", "Provider-initiated PTB"),
       ("lbw_termo", "Term low birth weight"), ("pig", "Small for gestational age")]
RAC = ["Parda", "Preta", "Indigena"]
fig, ax = plt.subplots(figsize=(174 * MM, 95 * MM))
ylab, ypos = [], []
y = 0
for desf, nome in DES:
    for j, g in enumerate(RAC):
        r = m[(m.desfecho == desf) & (m.raca == g)].iloc[0]
        yy = y - j * 0.28
        ax.errorbar(r.RP, yy, xerr=[[r.RP - r.RP_lo], [r.RP_hi - r.RP]], fmt=MK[g], color=COR[g], ms=4.5, capsize=1.8,
                    lw=0.9, markeredgecolor="white", markeredgewidth=0.4, label=LAB[g] if desf == "ptb" else None)
        ax.text(2.75, yy, f"{r.RP:.2f} ({r.RP_lo:.2f}–{r.RP_hi:.2f})", va="center", fontsize=7.5)
    ylab.append(nome)
    ypos.append(y - 0.28)
    y -= 1.3
ax.axvline(1, color="#3a3a3a", lw=0.7, ls="--")
ax.set_xscale("log")
ax.set_xlim(0.4, 2.7)
ticks = [0.5, 0.75, 1, 1.5, 2, 2.5]
ax.set_xticks(ticks, [str(v) for v in ticks])
ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
ax.set_yticks(ypos, ylab)
ax.set_xlabel("Prevalence ratio vs White (95% CI), model M2")
ax.text(2.75, 0.55, "PR (95% CI)", fontsize=7.5, fontweight="bold")
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
ax.legend(frameon=False, ncol=3, loc="lower left", bbox_to_anchor=(0.0, 1.02), fontsize=8)
fig.tight_layout()
fig.subplots_adjust(right=0.80)
salva(fig, f"fig2_forest_m2_desfechos_v1_{L.STAMP}")
