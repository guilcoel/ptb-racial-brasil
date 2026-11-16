"""
3.7 Figuras (padrão da revista; paleta e marcadores da Etapa 2; TIFF 600 dpi LZW, 174 mm, Arial; PNG 200 dpi).
Fig. 3: diferença de risco (p.p.) raça vs Branca DENTRO de cada tercil de acesso da macrorregião (3.2 ii),
        a = PTB, b = PTB espontâneo, c = PIG; IC 95%.
Fig. 4: RP raça vs Branca por macrorregião, M2 estratificado (Etapa 2, tab_e2_04_modelos_long),
        a = PTB espontâneo, b = PIG; eixo log.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import etapa3_lib as T
import etapa0_lib as L

log = T.logger("05_figuras")
plt.rcParams.update({"font.family": "Arial", "font.size": 8, "axes.linewidth": 0.6,
                     "xtick.major.width": 0.6, "ytick.major.width": 0.6})
MM = 1 / 25.4
COR = {"Branca": "#3a3a3a", "Parda": "#b8461b", "Preta": "#0b7a55", "Indigena": "#1c5cab"}
MK = {"Branca": "o", "Parda": "s", "Preta": "D", "Indigena": "^"}
LAB = {"Parda": "Brown (Parda)", "Preta": "Black (Preta)", "Indigena": "Indigenous"}
RAC = ["Parda", "Preta", "Indigena"]
FIG = L.PROJ / "outputs" / "figures"


def salva(fig, nome):
    fig.savefig(FIG / f"{nome}.tiff", dpi=600, format="tiff", pil_kwargs={"compression": "tiff_lzw"})
    fig.savefig(FIG / f"{nome}.png", dpi=200)
    log(f"figura {nome}.tiff (600 dpi) + .png")


def eixo(ax, letra):
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.grid(axis="y", color="#e6e5df", lw=0.5)
    ax.set_axisbelow(True)
    ax.text(-0.02, 1.03, letra, transform=ax.transAxes, fontsize=10, fontweight="bold", ha="right")


# Fig. 3
dn = pd.read_csv(L.TAB / f"tab_e3_02_dentro_v1_{L.STAMP}.csv")
dn = dn[(dn.analise == "3.2_tercil_reg") & (dn.estrato == "Brasil")]
fig, axs = plt.subplots(1, 3, figsize=(174 * MM, 72 * MM))
for ax, (desf, ylab), letra in zip(axs, [("ptb", "Preterm birth"), ("ptb_esp", "Spontaneous PTB"),
                                         ("pig", "SGA")], "abc"):
    for j, g in enumerate(RAC):
        q = dn[(dn.desfecho == desf) & (dn.raca == g)].set_index("nivel").loc[["T1", "T2", "T3"]]
        x = np.arange(3) + (j - 1) * 0.22
        ax.errorbar(x, q.DR_pp, yerr=[q.DR_pp - q.DR_lo, q.DR_hi - q.DR_pp], fmt=MK[g], color=COR[g], ms=4.5,
                    capsize=1.8, lw=0.9, markeredgecolor="white", markeredgewidth=0.4, label=LAB[g])
    ax.axhline(0, color="#3a3a3a", lw=0.7, ls="--")
    ax.set_xticks(range(3), ["T1\n(worst)", "T2", "T3\n(best)"])
    ax.set_xlabel("Access tertile (within region)")
    ax.set_ylabel(f"{ylab}: RD vs White, pp")
    eixo(ax, letra)
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, frameon=False, ncol=3, loc="upper center", fontsize=8)
fig.tight_layout(rect=(0, 0, 1, 0.92))
salva(fig, f"fig3_dr_raca_tercil_regiao_v1_{L.STAMP}")

# Fig. 4
m = pd.read_csv(L.TAB / f"tab_e2_04_modelos_long_v1_{L.STAMP}.csv")
m = m[(m.modelo == "M2") & (m.regiao != "Brasil")]
REG = ["N", "NE", "SE", "S", "CO"]
RL = {"N": "North", "NE": "North-\neast", "SE": "South-\neast", "S": "South", "CO": "Center-\nWest"}
fig, axs = plt.subplots(1, 2, figsize=(174 * MM, 72 * MM))
for ax, (desf, ylab), letra in zip(axs, [("ptb_esp", "Spontaneous PTB"), ("pig", "SGA")], "ab"):
    for j, g in enumerate(RAC):
        q = m[(m.desfecho == desf) & (m.raca == g)].set_index("regiao").loc[REG]
        x = np.arange(5) + (j - 1) * 0.22
        ax.errorbar(x, q.RP, yerr=[q.RP - q.RP_lo, q.RP_hi - q.RP], fmt=MK[g], color=COR[g], ms=4.5, capsize=1.8,
                    lw=0.9, markeredgecolor="white", markeredgewidth=0.4, label=LAB[g])
    ax.axhline(1, color="#3a3a3a", lw=0.7, ls="--")
    ax.set_yscale("log")
    ticks = [0.75, 1, 1.5, 2, 2.5]
    ax.set_yticks(ticks, [str(t) for t in ticks])
    ax.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    ax.set_ylim(0.7, 2.9)
    ax.set_xticks(range(5), [RL[r] for r in REG])
    ax.set_ylabel(f"{ylab}: PR vs White")
    eixo(ax, letra)
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, frameon=False, ncol=3, loc="upper center", fontsize=8)
fig.tight_layout(rect=(0, 0, 1, 0.92))
salva(fig, f"fig4_rp_raca_macrorregiao_v1_{L.STAMP}")
