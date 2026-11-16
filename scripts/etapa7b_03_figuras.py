"""
7b.3 Figuras do manuscrito (Springer/JREHD: 84 ou 174 mm; Arial 8–12 pt; texto preto; combinada ≥ 600 dpi, arte de linha
1,200 dpi; informação nunca só pela cor: marcador/estilo de linha/hachura; linhas ≥ 0.3 pt; sem título embutido).
Só lê saídas existentes (etapa7b_lib.rd). Saídas: outputs/manuscrito/figuras/figNN_*_v1_20261009.(tif|png), suplementar/S9_*,
legendas_figuras.md.
  Fig 1 fluxograma STROBE (arte de linha, 1,200 dpi)      Fig 2 forest PR M1–M3 (4 desfechos)
  Fig 3 RD conjunta raça × tercil (SGA, PTB indicado)      Fig 4 datação (a % PTB, b % > P97, c PR Indígena PTB por cenário)
  S9 caterpillar MAIHDA (PIG)
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd

import etapa7b_lib as B
import etapa0_lib as L

log = L.Logger("7b_03_figuras", etapa="etapa7b")
plt.rcParams.update({"font.family": "Arial", "font.size": 8, "axes.linewidth": 0.6, "xtick.major.width": 0.6,
                     "ytick.major.width": 0.6, "text.color": "black", "axes.labelcolor": "black", "xtick.color": "black",
                     "ytick.color": "black", "hatch.linewidth": 0.5})
MM = 1 / 25.4
COR = {"Branca": "#3a3a3a", "Parda": "#b8461b", "Preta": "#0b7a55", "Indigena": "#1c5cab"}   # contraste ≥ 4.5:1 em branco
MK = {"Branca": "o", "Parda": "s", "Preta": "D", "Indigena": "^"}
LS = {"Branca": "-", "Parda": "--", "Preta": ":", "Indigena": "-."}
LEG = []


def salva(fig, nome, dpi=600, pasta=None):
    pasta = pasta or B.FIGD
    tif = pasta / f"{nome}_{B.V}.tif"
    fig.savefig(tif, dpi=dpi, format="tiff", pil_kwargs={"compression": "tiff_lzw"})
    # 7d (v15): TIFF em RGB, sem canal alfa. O Agg grava RGBA; com alfa = 255 em todo pixel, tirar o alfa não muda nenhum valor RGB
    from PIL import Image
    im = Image.open(tif)
    im.load()
    if im.mode == "RGBA":
        if im.getchannel("A").getextrema() != (255, 255):           # raise, e não assert (o python -O desliga assert)
            raise RuntimeError(f"alfa < 255 em {tif.name}: a conversão para RGB mudaria pixels")
        im.convert("RGB").save(tif, format="TIFF", compression="tiff_lzw", dpi=im.info["dpi"])
    fig.savefig(pasta / f"{nome}_{B.V}.png", dpi=200)
    plt.close(fig)
    return tif


def limpa(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


# ---------- Fig 1 fluxograma
f6 = B.rd("tab06_fluxograma_regiao").query("regiao == 'Brasil'").set_index("passo")
f7 = B.rd("tab07_fluxograma_motivos").query("regiao == 'Brasil'")
wd = B.rd("tab_e6_01a_wald").set_index("desfecho")
pv = B.rd("tab_e6b_01_ptb_raca_metodo").query("ig_metodo == 'todos'").groupby("desfecho").n.sum()
rb = B.rd("tab_e6_04_m2").query("raca == 'Indigena'").set_index("desfecho")
im = B.rd("tab_e3_00a_ig_metodo_raca").set_index("raca")
mot = lambda p, m: int(f7[(f7.passo == p) & (f7.motivo == m)].n.iloc[0])
fig = plt.figure(figsize=(174 * MM, 190 * MM))
ax = fig.add_axes([0, 0, 1, 1])   # 1 unidade = 1 mm
ax.set_xlim(0, 174)
ax.set_ylim(0, 190)
ax.axis("off")


def caixa(x, y, w, h, txt, fs=8, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="square,pad=0", fc="white", ec="black", lw=0.6))
    ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal", linespacing=1.3)


def seta(x0, y0, x1, y1):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="-|>", lw=0.6, color="black", mutation_scale=7))


caixa(20, 174, 90, 13, f"Live births to residents, Brazil, 2015\u20132024\n(SINASC): n = {B.n_(f6.restante['0_fonte'])}", bold=True)
ex = [("1_raca", f"Maternal race/skin color missing\nor Asian (amarela): n = {B.n_(f6.excluidos['1_raca'])}\n(missing {B.n_(mot('1_raca', 'nulo'))};\n"
                 f"Asian (amarela) {B.n_(mot('1_raca', '3'))})"),
      ("2_ig", f"Gestational age missing or outside\n22\u201344 weeks: n = {B.n_(f6.excluidos['2_ig'])}\n(missing {B.n_(mot('2_ig', 'nulo'))}; "
               f"<22 wk {B.n_(mot('2_ig', '<22'))};\n>44 wk {B.n_(mot('2_ig', '>44'))})"),
      ("3_esc", f"Maternal education missing\nor unknown: n = {B.n_(f6.excluidos['3_esc'])}"),
      ("4_idade", f"Maternal age missing, <10 or\n>60 years: n = {B.n_(f6.excluidos['4_idade'])}")]
alt = [18, 22, 13, 13]
y, yb = 174, 172
for (p_, tx), h in zip(ex, alt):
    yb = yb - h - 3
    ym = yb + h / 2
    ax.plot([65, 65], [y, ym], color="black", lw=0.6)
    seta(65, ym, 104, ym)
    caixa(104, yb, 68, h, tx)
    y = ym
seta(65, y, 65, 96)
caixa(6, 76, 94, 20, f"Analytic sample: n = {B.n_(f6.restante['4_idade'])}\nWhite {B.n_(im.loc['Branca', ['DUM', 'outro_metodo', 'ignorado']].sum())}; "
                      f"{B.RACE['Parda']} {B.n_(im.loc['Parda', ['DUM', 'outro_metodo', 'ignorado']].sum())};\nBlack {B.n_(im.loc['Preta', ['DUM', 'outro_metodo', 'ignorado']].sum())}; "
                      f"Indigenous {B.n_(im.loc['Indigena', ['DUM', 'outro_metodo', 'ignorado']].sum())}", bold=True)
sub = [(f"Preterm birth\n(total)\nn = {B.n_(pv['ptb'])}", 2), (f"Spontaneous or\nprovider-initiated\npreterm birth\nn = {B.n_(pv['ptb_esp'])}\n(131,809 preterm\nunclassified)", 45),
       (f"SGA: singletons\n24\u201342 wk, valid sex\nand weight\nn = {B.n_(pv['pig'])}", 88),
       (f"Dating-robust:\nother method, no\npreterm weight >P97\nn = {B.n_(rb.loc['ptb'].N)}", 131)]
for tx, x in sub:
    seta(65, 76, x + 20.5, 66)
    caixa(x, 36, 41, 30, tx)
caixa(4, 2, 166, 24, f"Effect modification by access tertile: births without a health region excluded (n = 533)\n"
                     f"Preterm birth N = {B.n_(wd.N['ptb'])}; SGA N = {B.n_(wd.N['pig'])};\nspontaneous or provider-initiated preterm birth N = {B.n_(wd.N['ptb_ind'])}\n"
                     f"({B.n_(wd.N['ptb'] - wd.N['ptb_ind'])} unclassified preterm births excluded; 8 of the 131,809 are among the 533)")
for x in (22.5, 65.5, 108.5):
    seta(x, 36, x, 26)
t1 = salva(fig, "fig01_flowchart", dpi=1200)
LEG.append(("Fig. 1", f"fig01_flowchart_{B.V}.tif",
            "STROBE flow diagram of the study population. Live births to residents in Brazil, 2015–2024 (SINASC), sequential exclusion "
            "criteria, analytic sample by maternal race/skin color, and outcome-specific analytic subsets. SGA, small for gestational age "
            "(INTERGROWTH-21st, <10th centile). Race/skin color: mother's, recorded on the Live Birth Declaration."))

# ---------- Fig 2 forest M1–M3
mm = B.rd("tab_e6b_01_modelos_m1m3")
fig, axs = plt.subplots(1, 4, figsize=(174 * MM, 78 * MM), sharey=True)
MODMK = {"M1": ("o", "white"), "M2": ("s", "black"), "M3": ("D", "#9a9a9a")}
for ax, d_, letra in zip(axs, B.ORDER, "abcd"):
    for i, g in enumerate(["Parda", "Preta", "Indigena"]):
        for j, mo in enumerate(["M1", "M2", "M3"]):
            x = mm[(mm.desfecho == d_) & (mm.raca == g) & (mm.modelo == mo)].iloc[0]
            yy = 3 - i + (1 - j) * 0.22
            ax.plot([x.PR_lo, x.PR_hi], [yy, yy], color="black", lw=0.8)
            ax.plot(x.PR, yy, marker=MODMK[mo][0], mfc=MODMK[mo][1], mec="black", mew=0.6, ms=4, ls="none",
                    label=mo if (d_ == "ptb" and g == "Parda") else None)
    ax.axvline(1, color="black", lw=0.5, ls=":")
    ax.set_xscale("log")
    ax.set_xticks([0.5, 0.75, 1, 1.5, 2, 3])
    ax.set_xticklabels(["0.5", "0.75", "1", "1.5", "2", "3"])
    ax.set_xlim(0.28, 3.2)
    ax.minorticks_off()
    ax.set_title(B.OUTC[d_].replace(" preterm birth", "\npreterm birth").replace("Preterm birth (total)", "Preterm birth\n(total)"), fontsize=8)
    ax.text(-0.05, 1.12, letra, transform=ax.transAxes, fontsize=10, fontweight="bold", ha="right")
    ax.set_xlabel("PR vs White (log scale)")
    limpa(ax)
axs[0].set_yticks([3, 2, 1])
axs[0].set_yticklabels([B.RACE[g] for g in ["Parda", "Preta", "Indigena"]])
fig.legend(axs[0].get_legend_handles_labels()[0], ["M1: race/skin color", "M2: + age, year, macroregion", "M3: M2 + education, marital status"],
           loc="upper center", ncol=3, frameon=False, fontsize=8)
fig.tight_layout(rect=(0, 0, 1, 0.9))
salva(fig, "fig02_pr_race_m1m3")
LEG.append(("Fig. 2", f"fig02_pr_race_m1m3_{B.V}.tif",
            "Prevalence ratios (PR, 95% CI) of (a) total preterm birth, (b) SGA, (c) provider-initiated preterm birth, and (d) "
            "spontaneous preterm birth by maternal race/skin color (reference: White) in models M1–M3. Poisson regression; 95% CIs "
            "with clustering by health region of residence. Open circles, M1; filled squares, M2; gray diamonds, M3 (extended model: M2 + "
            "maternal education and marital status)."))

# ---------- Fig 3 RD conjunta raça × tercil
cj = B.rd("tab_e6_01a_conjunto")
it = B.rd("tab_e6_01a_interacao").query("raca == 'Indigena' and nivel == 'T1'").set_index("desfecho")
fig, axs = plt.subplots(1, 2, figsize=(174 * MM, 80 * MM))
for ax, d_, letra in zip(axs, ["pig", "ptb_ind"], "ab"):
    for k, g in enumerate(B.RACES):
        x = cj[(cj.desfecho == d_) & (cj.raca == g)].set_index("nivel").loc[["T1", "T2", "T3"]]
        xs = np.arange(3) + (k - 1.5) * 0.08
        ax.errorbar(xs, x.DR_pp, yerr=[x.DR_pp - x.DR_lo, x.DR_hi - x.DR_pp], color=COR[g], marker=MK[g], ms=4, mfc=COR[g], mec="white",
                    mew=0.4, lw=0.9, ls=LS[g], capsize=2, label=B.RACE[g])
    ax.axhline(0, color="black", lw=0.5)
    ax.set_xticks(range(3))
    ax.set_xticklabels(["T1\n(worst access)", "T2", "T3\n(best access)"])
    ax.set_ylabel("Joint RD per 100 live births vs White–T3")
    ax.set_title(B.OUTC[d_], fontsize=8)
    y = it.loc[d_]
    lo_, hi_ = ax.get_ylim()
    ax.set_ylim(lo_, hi_ + 0.18 * (hi_ - lo_)) if d_ == "pig" else ax.set_ylim(lo_ - 0.18 * (hi_ - lo_), hi_)
    ax.text(0.98, 0.98 if d_ == "pig" else 0.02, f"IC Indigenous×T1 = {B.rd_(y.ICR_pp, y.ICR_lo, y.ICR_hi)}", transform=ax.transAxes,
            ha="right", va="top" if d_ == "pig" else "bottom", fontsize=8)
    ax.text(-0.08, 1.06, letra, transform=ax.transAxes, fontsize=10, fontweight="bold", ha="right")
    limpa(ax)
fig.legend(*axs[0].get_legend_handles_labels(), loc="upper center", ncol=4, frameon=False, fontsize=8)
fig.tight_layout(rect=(0, 0, 1, 0.92))
salva(fig, "fig03_rd_race_tercile")
LEG.append(("Fig. 3", f"fig03_rd_race_tercile_{B.V}.tif",
            "Joint risk differences (RD per 100 live births, 95% CI) by maternal race/skin color and prenatal care access tertile, relative "
            "to White women in T3, for (a) SGA and (b) provider-initiated preterm birth. Model M2 with tertile and race×tertile terms; "
            "marginal standardization; 95% CIs with clustering by health region. Tertiles defined within macroregion; T1 = worst access "
            "(lowest percentage of first-trimester prenatal care initiation). IC, interaction contrast (Knol & VanderWeele): risk difference "
            "(group vs White) within T1 minus the same difference within T3, per 100 live births."))

# ---------- Fig 4 datação
pm = B.rd("tab_e6b_01_ptb_raca_metodo").query("desfecho == 'ptb'")
ip = B.rd("tab_e4b_01_implausivel_brasil").query("criterio == 'b'")
sc = B.rd("tab_e6b_01_m2_cenarios").query("raca == 'Indigena' and desfecho == 'ptb'").set_index("cenario")
m2 = B.rd("tab_e6_01a_m2").query("cluster == 'regsaude' and raca == 'Indigena' and desfecho == 'ptb'").iloc[0]
fig = plt.figure(figsize=(174 * MM, 120 * MM))
gs = fig.add_gridspec(2, 2, height_ratios=[1, 0.8])
MET = [("DUM", "LMP (code 8)", "////"), ("outro_metodo", "Other method (codes 1–2)", "")]
for (pos, tab, col, ylab, letra) in [(gs[0, 0], pm, "pct", "Preterm birth, %", "a"), (gs[0, 1], ip, "pct", "Preterm births with weight >P97, %", "b")]:
    ax = fig.add_subplot(pos)
    for j, (m, lab, h) in enumerate(MET):
        vals = [tab[(tab.raca == g) & (tab.ig_metodo == m)][col].iloc[0] for g in B.RACES]
        ax.bar(np.arange(4) + (j - 0.5) * 0.38, vals, width=0.36, color="white" if h else "#bdbdbd", edgecolor="black", hatch=h, lw=0.6, label=lab)
    ax.set_xticks(range(4))
    ax.set_xticklabels([B.RACE[g] for g in B.RACES])
    ax.set_ylabel(ylab)
    ax.text(-0.1, 1.04, letra, transform=ax.transAxes, fontsize=10, fontweight="bold", ha="right")
    limpa(ax)
    if letra == "a":
        fig.legend(*ax.get_legend_handles_labels(), loc="upper center", ncol=2, frameon=False, fontsize=8)
ax = fig.add_subplot(gs[1, :])
cen = [("Main analysis", m2.RP, m2.RP_lo, m2.RP_hi), ("LMP-dated only", sc.loc["so_DUM"].PR, sc.loc["so_DUM"].PR_lo, sc.loc["so_DUM"].PR_hi),
       ("Other-method dating only", sc.loc["so_outro_metodo"].PR, sc.loc["so_outro_metodo"].PR_lo, sc.loc["so_outro_metodo"].PR_hi),
       ("Dating-robust (other method,\nno preterm weight >P97)", rb.loc["ptb"].RP, rb.loc["ptb"].RP_lo, rb.loc["ptb"].RP_hi)]
for i, (lab, e, lo, hi) in enumerate(cen):
    yy = len(cen) - i
    ax.plot([lo, hi], [yy, yy], color="black", lw=0.9)
    ax.plot(e, yy, marker="^", color=COR["Indigena"], mec="black", mew=0.4, ms=5)
    ax.text(3.0, yy, B.pr(e, lo, hi), va="center", ha="right", fontsize=8)
ax.axvline(1, color="black", lw=0.5, ls=":")
ax.set_xscale("log")
ax.set_xticks([0.6, 0.8, 1, 1.25, 1.6, 2])
ax.set_xticklabels(["0.6", "0.8", "1", "1.25", "1.6", "2"])
ax.set_xlim(0.6, 3.05)
ax.minorticks_off()
ax.set_yticks(range(len(cen), 0, -1))
ax.set_yticklabels([c[0] for c in cen])
ax.set_xlabel("PR of total preterm birth, Indigenous vs White (model M2, log scale)")
ax.text(-0.27, 1.04, "c", transform=ax.transAxes, fontsize=10, fontweight="bold", ha="right")
limpa(ax)
fig.tight_layout(rect=(0, 0, 1, 0.94))
salva(fig, "fig04_dating")
LEG.append(("Fig. 4", f"fig04_dating_{B.V}.tif",
            "Gestational age dating and racial disparities in preterm birth. (a) Preterm birth prevalence by maternal race/skin color and "
            "gestational age estimation method (LMP, last menstrual period, TPMETESTIM code 8; other method, codes 1–2, including "
            "ultrasound). (b) Percentage of singleton preterm births (24–36 weeks) with birth weight above the 97th INTERGROWTH-21st centile. "
            "(c) PR of total preterm birth, Indigenous vs White (model M2, 95% CI with clustering by health region), in the main analysis, "
            "by dating method, and in the dating-robust subsample (other-method dating, excluding preterm births with weight >P97; "
            f"n = {B.n_(rb.loc['ptb'].N)})."))

# ---------- S9 caterpillar MAIHDA (antiga Fig S1; mesmo desenho da Etapa 5)
p = B.rd("tab_e5_03_predicoes")
ref = p[p.estrato == "Branca|ge12|20a34|SE|T3"].iloc[0]
fig, axs = plt.subplots(2, 1, figsize=(174 * MM, 150 * MM))
for ax, col, lo, hi, ylab, rv in [(axs[0], "p_pct", "p_lo", "p_hi", "Predicted SGA risk, %", ref.p_pct), (axs[1], "u", "u_lo", "u_hi", "Stratum random effect (logit)", 0.0)]:
    q = p.sort_values(col).reset_index(drop=True)
    ax.vlines(np.arange(len(q)), q[lo], q[hi], colors=q.raca.map(COR), lw=0.45, alpha=0.6)
    for i, r in q.iterrows():
        ax.scatter(i, r[col], marker=MK[r.raca], s=4.5, color=COR[r.raca], edgecolors="white", linewidths=0.15, zorder=3)
    ax.axhline(rv, color="black", lw=0.6, ls="--")
    ax.set_xticks([])
    ax.set_ylabel(ylab)
    limpa(ax)
for g in B.RACES:
    axs[0].scatter([], [], marker=MK[g], s=12, color=COR[g], label=B.RACE[g])
axs[0].legend(loc="upper left", frameon=False, fontsize=8)
axs[1].set_xlabel("540 intersectional strata, ranked")
for ax, letra in zip(axs, "ab"):
    ax.text(-0.06, 1.02, letra, transform=ax.transAxes, fontsize=10, fontweight="bold", ha="right")
fig.tight_layout()
salva(fig, "S9_maihda_caterpillar", pasta=B.SUPD)
fig2 = plt.figure()
plt.close(fig2)
LEG.append(("Online Resource 5 (Fig. S9)", f"S9_maihda_caterpillar_{B.V}.tif",
            "Intersectional MAIHDA of SGA: (a) predicted SGA risk (model M2, fixed plus stratum random effects; 95% CI by simulation) for the "
            "540 strata, ranked, with the reference stratum (White; ≥12 years of schooling; 20–34 years; Southeast; T3) as the dashed "
            "line; (b) stratum random effects (95% CI from the conditional variance). Marker shape and color indicate race/skin color. "
            "T1 = worst access tertile."))

# legendas (7c.1: nota Brown/Black do IBGE em toda legenda com rótulos de raça/cor)
LEG = [(k, f, t + " " + B.NOTE_BROWN) for k, f, t in LEG]
md = ["# Figure legends (draft, English)", "", f"Package {B.V}; all figures from existing outputs (sources in MANIFEST.md).", ""]
for k, f, t in LEG:
    md += [f"**{k}.** {t}", "", f"File: `{f}`", ""]
(B.MS / "legendas_figuras.md").write_text("\n".join(md))
# 7d: no exFAT, regravar o TIFF (RGB) deixa ._* (xattrs); dot_clean -m os remove, como o 02 faz em suplementar/
import subprocess
for d_ in (B.FIGD, B.SUPD):
    subprocess.run(["dot_clean", "-m", str(d_)], check=True)
    if list(d_.glob("._*")):                          # raise, e não assert (o python -O desliga assert)
        raise RuntimeError(f"._* em {d_}")
log(f"figuras: {[x[1] for x in LEG]}")
