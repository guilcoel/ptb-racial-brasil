"""
7b.1 Tabelas principais do manuscrito (1, 2, 3, 4) e números-chave (7d: a 3b virou a S3b, no 02). Só lê saídas existentes (etapa7b_lib.SRC).
Saídas em outputs/manuscrito/: tabelas/tab0X_*.csv, tabelas/tabelas_principais_v1_20261009.(xlsx|docx),
numeros_chave_v1_20261009.(json|md).
"""
import numpy as np
import pandas as pd
from docx import Document

import etapa7b_lib as B
import etapa0_lib as L

log = L.Logger("7b_01_tabelas", etapa="etapa7b")
R = B.Registro()
XL, DOC = [], Document()
DOC.add_heading(f"Main tables (draft, package {B.V})", level=1)
G = lambda g: B.RACE[g]
RACES = B.RACES

# ================= Tabela 1
t1 = B.rd("tab_e1_03_tabela1_long").query("regiao == 'Brasil'")
COLS = ["Branca", "Parda", "Preta", "Indigena", "Total"]
Ntot = t1[t1.variavel == "Faixa etária"].groupby("raca").n.sum()
rows = [dict(Characteristic="Live births, n", **{G(c) if c != "Total" else "Total": B.n_(Ntot[c]) for c in COLS})]


def bloco(var, rotulo, cats):
    x = t1[t1.variavel == var]
    rows.append({"Characteristic": rotulo})
    for cod, lab in cats:
        r = {"Characteristic": f"  {lab}"}
        for c in COLS:
            y = x[(x.raca == c) & (x.categoria == cod)].iloc[0]
            r[G(c) if c != "Total" else "Total"] = f"{B.n_(y.n)} ({B.pct(y.pct)})"
        rows.append(r)
    nv = x.groupby("raca").n_valido.first()
    if (Ntot - nv).max() > 0:
        rows.append({"Characteristic": "  Missing, n", **{G(c) if c != "Total" else "Total": B.n_(Ntot[c] - nv[c]) for c in COLS}})


m = t1[t1.variavel == "Idade materna (anos)"].set_index("raca")
rows.append({"Characteristic": "Maternal age, years, mean (SD)",
             **{G(c) if c != "Total" else "Total": f"{m.media[c]:.1f} ({m.dp[c]:.1f})" for c in COLS}})
bloco("Faixa etária", "Maternal age group, years, n (%)", [("<20", "<20"), ("20-34", "20–34"), (">=35", "≥35")])
bloco("Escolaridade (anos)", "Maternal education, years of schooling, n (%)",
      [("1_nenhuma", "None"), ("2_1a3anos", "1–3"), ("3_4a7anos", "4–7"), ("4_8a11anos", "8–11"), ("5_12mais", "≥12")])
bloco("Situação conjugal", "Marital status, n (%)", [("com_companheiro", "With partner"), ("sem_companheiro", "Without partner")])
bloco("Região", "Macroregion of residence, n (%)", [(k, v) for k, v in B.REG.items()])
# tercil (amostra de acesso; contagens da 3.2)
tc = B.rd("tab_e3_01_n_casos_raca_tercil_regiao").query("desfecho == 'ptb'").groupby(["raca", "tercil_reg"]).n.sum().unstack()
tc.loc["Total"] = tc.sum()
rows.append({"Characteristic": "Prenatal care access tertile (within macroregion), n (%)"})
for t in ["T1", "T2", "T3"]:
    rows.append({"Characteristic": f"  {B.TERC[t]}", **{G(c) if c != "Total" else "Total":
                 f"{B.n_(tc.loc[c, t])} ({B.pct(100 * tc.loc[c, t] / tc.loc[c].sum())})" for c in COLS}})
rows.append({"Characteristic": "  Missing (no health region), n", **{G(c) if c != "Total" else "Total": B.n_(Ntot[c] - tc.loc[c].sum()) for c in COLS}})
bloco("Início do pré-natal", "Prenatal care initiation, n (%)", [("1º trimestre", "1st trimester"), ("2º trimestre", "2nd trimester"),
                                                                  ("3º trimestre", "3rd trimester")])
bloco("Consultas pré-natal", "Prenatal care visits, n (%)", [("0", "0"), ("1-3", "1–3"), ("4-6", "4–6"), ("7+", "≥7")])
bloco("Tipo de parto", "Mode of delivery, n (%)", [("vaginal", "Vaginal"), ("cesárea", "Cesarean")])
im = B.rd("tab_e3_00a_ig_metodo_raca").set_index("raca")
rows.append({"Characteristic": "Gestational age estimation method, n (%)"})
for cod, lab in [("DUM", "Last menstrual period (TPMETESTIM code 8)"), ("outro_metodo", "Physical exam or other method, incl. ultrasound (codes 1–2)"),
                 ("ignorado", "Unknown (code 9 or missing)")]:
    rows.append({"Characteristic": f"  {lab}", **{G(c) if c != "Total" else "Total": f"{B.n_(im.loc[c, cod])} ({B.pct(im.loc[c, 'pct_' + cod])})" for c in COLS}})
pv = B.rd("tab_e6b_01_ptb_raca_metodo").query("ig_metodo == 'todos'")
rows.append({"Characteristic": "Outcomes, cases/denominator (%)"})
for d_ in B.ORDER:
    x = pv[pv.desfecho == d_].set_index("raca")
    tot_c, tot_n = x.casos.sum(), x.n.sum()
    r = {"Characteristic": f"  {B.OUTC[d_]}"}
    for c in COLS:
        cc, nn = (tot_c, tot_n) if c == "Total" else (x.casos[c], x.n[c])
        r[G(c) if c != "Total" else "Total"] = f"{B.n_(cc)}/{B.n_(nn)} ({100 * cc / nn:.2f})"
        R.add(f"prev_{d_}_{c}", 100 * cc / nn, f"{100 * cc / nn:.2f}%", "tab_e6b_01_ptb_raca_metodo",
              f"Prevalence of {B.OUTC[d_]}, {G(c) if c != 'Total' else c}", f"desfecho={d_}, ig_metodo=todos" + ("" if c != "Total" else ", soma das raças"))
    rows.append(r)
T1 = pd.DataFrame(rows).fillna("")
rod1 = (B.NOTE_RACE + " Percentages are column percentages among births with non-missing data. " + B.NOTE_TERC +
        " The denominators of provider-initiated and spontaneous preterm birth exclude the 131,809 preterm births that could not "
        "be classified (missing labor induction or cesarean timing); therefore provider-initiated + spontaneous \u2260 total preterm "
        "birth. TPMETESTIM code 8 is not described in the public SINASC data dictionaries and was identified empirically as "
        "births with a reported last menstrual period (Online Resource 2); SGA: singletons 24–42 weeks with valid sex and birth weight (INTERGROWTH-21st, <10th centile). "
        "Sources: tab_e1_03_tabela1_long, tab_e3_01_n_casos_raca_tercil_regiao, tab_e3_00a_ig_metodo_raca, tab_e6b_01_ptb_raca_metodo.")
B.grava_tabela(T1, "tab01_characteristics", "Table 1. Characteristics of live births by maternal race/skin color, Brazil, 2015–2024",
               rod1, xlsx_conjunto=XL, docx_doc=DOC)
for c in COLS:
    R.add(f"n_{c}", int(Ntot[c]), B.n_(Ntot[c]), "tab_e1_03_tabela1_long", f"Live births in the analytic sample, {G(c) if c != 'Total' else c}", "regiao=Brasil")

# ================= Tabela 2
mm = B.rd("tab_e6b_01_modelos_m1m3")
at = B.rd("tab_e3_00b_atenuacao_ic_rs").set_index(["desfecho", "raca"])
rows = []
for d_ in B.ORDER:
    rows.append({"Outcome / race": B.OUTC[d_]})
    rows.append({"Outcome / race": "  White (reference)", "M1 PR (95% CI)": "1.00", "M2 PR (95% CI)": "1.00", "M3 PR (95% CI)": "1.00"})  # 7c.1: White primeiro
    for g in RACES[1:]:
        x = mm[(mm.desfecho == d_) & (mm.raca == g)].set_index("modelo")
        a = at.loc[(d_, g)]
        m2 = x.loc["M2"]
        mostra = abs(a.RP_M2cc - 1) >= 0.10          # valor não arredondado (Etapa 7b.1)
        aten = 100 * (a.RP_M2cc - a.RP_M3) / (a.RP_M2cc - 1)
        rows.append({"Outcome / race": f"  {G(g)}", "M1 PR (95% CI)": B.pr(x.loc["M1"].PR, x.loc["M1"].PR_lo, x.loc["M1"].PR_hi),
                     "M2 PR (95% CI)": B.pr(m2.PR, m2.PR_lo, m2.PR_hi), "M3 PR (95% CI)": B.pr(x.loc["M3"].PR, x.loc["M3"].PR_lo, x.loc["M3"].PR_hi),
                     "ΔPR M2→M3 (95% CI)": B.rd_(a.dRP, a.dRP_lo, a.dRP_hi),
                     "Attenuation, % (95% CI)": B.rd_(aten, a.aten_lo, a.aten_hi) if mostra else "n.a."})
        R.add(f"dPR_{d_}_{g}", float(a.dRP), B.rd_(a.dRP, a.dRP_lo, a.dRP_hi), "tab_e3_00b_atenuacao_ic_rs",
              f"\u0394PR M2cc\u2192M3, {B.OUTC[d_]}, {G(g)}", f"desfecho={d_}, raca={g}")
        for mod in ("M1", "M2", "M3"):
            R.add(f"PR_{mod}_{d_}_{g}", float(x.loc[mod].PR), B.pr(x.loc[mod].PR, x.loc[mod].PR_lo, x.loc[mod].PR_hi), "tab_e6b_01_modelos_m1m3",
                  f"PR {mod}, {B.OUTC[d_]}, {G(g)} vs White", f"modelo={mod}, desfecho={d_}, raca={g}")
T2 = pd.DataFrame(rows).fillna("")
nn = mm.groupby(["desfecho", "modelo"]).N.first().unstack()
rod2 = ("PR, prevalence ratio from Poisson regression (log link) fitted to aggregated covariate patterns; reference: White. "
        "M1: race/skin color only. M2: + maternal age group, year, and macroregion. M3 (extended model): M2 + maternal education and marital status "
        "(complete cases for marital status). " + B.NOTE_CLUSTER +
        " \u0394PR (primary measure of attenuation) = PR_M2cc \u2212 PR_M3, where M2cc is M2 refitted in the M3 complete-case sample; "
        "attenuation, % = (PR_M2cc \u2212 PR_M3)/(PR_M2cc \u2212 1) \u00d7 100, on the linear PR scale, shown only when "
        "|PR_M2cc \u2212 1| \u2265 0.10 (unrounded), otherwise n.a. With PR < 1, a positive attenuation means movement toward the null; "
        "values above 100% mean that the M3 PR crosses the null. 95% CIs of \u0394PR and attenuation from a cluster bootstrap "
        "resampling health regions (500 replicates, seed 42). "
        "N, M1 and M2 / M2cc and M3 (births excluded from M2cc and M3 for missing marital status): " +
        "; ".join(f"{B.OUTC[d_]} {B.n_(nn.loc[d_, 'M2'])} / {B.n_(nn.loc[d_, 'M3'])} ({B.n_(nn.loc[d_, 'M2'] - nn.loc[d_, 'M3'])})"
                  for d_ in B.ORDER) + ". " +
        "Sources: tab_e6b_01_modelos_m1m3, tab_e3_00b_atenuacao_ic_rs.")
B.grava_tabela(T2, "tab02_models_m1m3", "Table 2. Prevalence ratios by maternal race/skin color in models M1–M3", rod2,
               xlsx_conjunto=XL, docx_doc=DOC)
# 7c.3: N do M2 e do M3 (= M2cc; casos completos de estado civil) e excluídos por estado civil ausente (fonte: tab_e6b_01_modelos_m1m3)
assert (nn.M1 == nn.M2).all() and (nn.M2cc == nn.M3).all()
for d_ in B.ORDER:
    R.add(f"N_M2_{d_}", int(nn.loc[d_, "M2"]), B.n_(nn.loc[d_, "M2"]), "tab_e6b_01_modelos_m1m3", f"N, models M1 and M2, {B.OUTC[d_]}",
          f"modelo=M2, desfecho={d_}")
    R.add(f"N_M3_{d_}", int(nn.loc[d_, "M3"]), B.n_(nn.loc[d_, "M3"]), "tab_e6b_01_modelos_m1m3",
          f"N, models M2cc and M3 (complete cases for marital status), {B.OUTC[d_]}", f"modelo=M3 (= M2cc), desfecho={d_}")
    R.add(f"n_excl_estciv_{d_}", int(nn.loc[d_, "M2"] - nn.loc[d_, "M3"]), B.n_(nn.loc[d_, "M2"] - nn.loc[d_, "M3"]), "tab_e6b_01_modelos_m1m3",
          f"Births excluded from M2cc and M3 for missing marital status, {B.OUTC[d_]}", f"N(modelo=M2) − N(modelo=M3), desfecho={d_}")

# ================= Tabela 3
cj, dn, it, wd = B.rd("tab_e6_01a_conjunto"), B.rd("tab_e6_01a_dentro"), B.rd("tab_e6_01a_interacao"), B.rd("tab_e6_01a_wald")
cnt = B.rd("tab_e3_01_n_casos_raca_tercil_regiao").groupby(["desfecho", "raca", "tercil_reg"])[["n", "casos"]].sum()
rr5 = B.rd("tab_e7b1_05_reri_recod").set_index(["raca", "nivel"])
COLRR = "RERI, recoded (reference = lowest-risk joint stratum), provider-initiated only (95% CI)"
rows = []
for d_ in ["ptb", "pig", "ptb_ind"]:
    w = wd[wd.desfecho == d_].iloc[0]
    assert int(cnt.loc[d_].n.sum()) == int(w.N)
    rows.append({"Race / tertile": f"{B.OUTC[d_]} (N = {B.n_(w.N)}; Wald test of the 6 interaction terms: χ² = {w.chi2:.1f}, "
                                   f"{int(w.gl)} df, p = {B.pval(w.p)})"})
    for g in RACES:
        for t in ["T1", "T2", "T3"]:
            c = cj[(cj.desfecho == d_) & (cj.raca == g) & (cj.nivel == t)].iloc[0]
            k = cnt.loc[(d_, g, t)]
            r = {"Race / tertile": f"  {G(g)} – {B.TERC[t]}", "Cases": B.n_(k.casos), "Non-cases": B.n_(k.n - k.casos),
                 "Joint PR vs White–T3 (95% CI)": "1.00 (reference)" if (g, t) == ("Branca", "T3") else B.pr(c.RP, c.RP_lo, c.RP_hi),
                 "Joint RD per 100 vs White–T3 (95% CI)": "0.00 (reference)" if (g, t) == ("Branca", "T3") else B.rd_(c.DR_pp, c.DR_lo, c.DR_hi)}
            if g != "Branca":
                x = dn[(dn.desfecho == d_) & (dn.raca == g) & (dn.nivel == t)].iloc[0]
                r["Within-tertile PR vs White (95% CI)"] = B.pr(x.RP, x.RP_lo, x.RP_hi)
                r["Within-tertile RD per 100 (95% CI)"] = B.rd_(x.DR_pp, x.DR_lo, x.DR_hi)
                if t != "T3":
                    y = it[(it.desfecho == d_) & (it.raca == g) & (it.nivel == t)].iloc[0]
                    r["IC per 100 (95% CI)"] = B.rd_(y.ICR_pp, y.ICR_lo, y.ICR_hi)
                    r["IC p"] = B.pval(y.ICR_p)
                    r["RERI (95% CI)"] = B.rd_(y.RERI, y.RERI_lo, y.RERI_hi)
                    r["Multiplicative interaction (95% CI)"] = B.pr(y.int_mult, y.int_mult_lo, y.int_mult_hi)
                    if d_ == "ptb_ind":
                        z = rr5.loc[(g, t)]
                        r[COLRR] = B.rd_(z.RERI_recod, z.lo, z.hi)
                        R.add(f"RERI_recod_ptb_ind_{g}_{t}", float(z.RERI_recod), B.rd_(z.RERI_recod, z.lo, z.hi), "tab_e7b1_05_reri_recod",
                              f"Recoded RERI (reference {G(z.referencia.split('-')[0])}\u2013{z.referencia.split('-')[1]}), provider-initiated PTB, {G(g)}\u00d7{t}", f"raca={g}, nivel={t}")
                    if g == "Indigena" and t == "T1":
                        R.add(f"ICR_Ind_T1_{d_}", float(y.ICR_pp), B.rd_(y.ICR_pp, y.ICR_lo, y.ICR_hi), "tab_e6_01a_interacao",
                              f"IC Indigenous×T1, {B.OUTC[d_]} (per 100)", f"desfecho={d_}, raca=Indigena, nivel=T1")
            rows.append(r)
    R.add(f"Wald_p_{d_}", float(w.p), B.pval(w.p), "tab_e6_01a_wald", f"Wald p (6 race×tertile terms), {B.OUTC[d_]}", f"desfecho={d_}")
T3 = pd.DataFrame(rows).fillna("")
rod3 = ("Effect modification on the additive and multiplicative scales (Knol & VanderWeele, 2012), model M2 plus tertile and "
        "race×tertile terms; reference: White–T3. " + B.NOTE_TERC + " Cases and non-cases are the counts in each race × "
        "tertile cell. Joint PR/RD compare each race–tertile cell with White–T3; within-tertile PR/RD compare each race with White "
        "in the same tertile. PR and RD are marginally standardized over the model sample; RD and IC per 100 live births. "
        + B.NOTE_IC + " RERI = PR11 − PR10 − PR01 + 1; multiplicative interaction = "
        "PR(race|Tk)/PR(race|T3). For provider-initiated preterm birth, where the joint exposures are 'preventive' (PR < 1), the "
        "RERI computed with White\u2013T3 as reference is distorted (Knol et al., Eur J Epidemiol 2011; doi:10.1007/s10654-011-9554-9); "
        "the IC, on the risk-difference scale, is the primary additive measure, and the last column gives the RERI recoded with the "
        "lowest-risk joint stratum of each 2\u00d72 table as reference (Knol & VanderWeele 2012), 95% CI by the delta method. "
        + B.NOTE_CLUSTER + " Sample: births with a defined health region; the N (e.g., 25,808,207 for preterm birth) excludes "
        "the 533 births without a health region. The provider-initiated N (25,676,406) also excludes 131,801 unclassified preterm "
        "births (131,809 in the full analytic sample; 8 of them are among the 533 births without a health region). "
        "Sources: tab_e6_01a_conjunto, tab_e6_01a_dentro, tab_e6_01a_interacao, tab_e6_01a_wald, tab_e3_01_n_casos_raca_tercil_regiao, "
        "tab_e7b1_05_reri_recod.")
B.grava_tabela(T3, "tab03_knol_tercile", "Table 3. Modification of racial disparities by prenatal care access tertile: preterm birth, "
               "SGA, and provider-initiated preterm birth", rod3, xlsx_conjunto=XL, docx_doc=DOC)

# 7d (v15): a Tabela 3b saiu das tabelas principais e virou a Tabela S3b (etapa7b_02_suplementar.py, ESM_4.xlsx)

# ================= Tabela 4 (Indígena)
m2p = B.rd("tab_e6_01a_m2").query("cluster == 'regsaude' and raca == 'Indigena'").set_index("desfecho")
sc = B.rd("tab_e6b_01_m2_cenarios").query("raca == 'Indigena'").set_index(["cenario", "desfecho"])
ia = B.rd("tab_e6_01a_interacao").query("raca == 'Indigena' and nivel == 'T1'").set_index("desfecho")
ib = B.rd("tab_e6_01b_interacao").query("raca == 'Indigena' and nivel == 'T1'").set_index(["sensibilidade", "desfecho"])
rb_m2 = B.rd("tab_e6_04_m2").query("raca == 'Indigena'").set_index("desfecho")
rb_it = B.rd("tab_e6_04_interacao").query("raca == 'Indigena' and nivel == 'T1'").set_index("desfecho")
mi_m2 = B.rd("tab_e4_06_mi_m2_rubin_rs").query("raca == 'Indigena'").set_index("desfecho")
mi_it = B.rd("tab_e4_06_mi_rubin_rs").query("raca == 'Indigena' and nivel == 'T1'").set_index("desfecho")
lim = B.rd("tab_e6_07b_limites")
ic1 = B.rd("tab_e7b1_01_cenarios_interacao").query("raca == 'Indigena' and nivel == 'T1'").set_index("sensibilidade")
wd1 = B.rd("tab_e7b1_01_cenarios_wald").set_index("sensibilidade")
wd0 = B.rd("tab_e6_01a_wald").set_index("desfecho")
wdr = B.rd("tab_e6_04_wald").set_index("desfecho")
nc_m2 = B.rd("tab_e7b1_04_m2").query("raca == 'Indigena'").set_index(["cenario", "desfecho"])
nc_it = B.rd("tab_e7b1_04_interacao").query("raca == 'Indigena' and nivel == 'T1'").set_index(["sensibilidade", "desfecho"])
c2_m2 = B.rd("tab_e7b2_01_m2").query("raca == 'Indigena'").set_index(["cenario", "desfecho"])
c2_it = B.rd("tab_e7b2_01_interacao").query("raca == 'Indigena' and nivel == 'T1'").set_index(["sensibilidade", "desfecho"])
c2_wd = B.rd("tab_e7b2_01_wald").set_index(["sensibilidade", "desfecho"])
rc_m2 = B.rd("tab_e7b2_02_reclass_m2").query("raca == 'Indigena'").set_index("desfecho")
rc_it = B.rd("tab_e7b2_02_reclass_interacao").query("raca == 'Indigena' and nivel == 'T1'").set_index("desfecho")
rc_wd = B.rd("tab_e7b2_02_reclass_wald").set_index("desfecho")
w2 = B.rd("tab_e7b3_02_wald_ind").set_index(["cenario", "desfecho"])
CEN_W2 = {"Main analysis": "principal", "LMP-dated births only (code 8)": "codigo_8", "Other-method dating only (codes 1\u20132)": "outro_metodo_1_2",
          "Dating-robust: other method, excluding preterm births with weight >P97": "robusta_datacao",
          "Other method: code 2 only (other method; includes ultrasound per the Live Birth Declaration manual)": "codigo_2",
          "Weight >P97 preterm reclassified as non-cases (all methods)": "reclass_p97", "Excluding CE and DF": "sem_CE_DF"}
# 7c.1: a sensibilidade "Excluding 2024" foi retirada do pacote por decisão do Guilherme (2026-10-09); as tabelas de origem ficam
SEM_2024 = "sem_2024"
PEND = "not estimated (pending)"


def prs(t, d):
    return B.pr(t.loc[d].PR if "PR" in t.columns else t.loc[d].RP, t.loc[d].PR_lo if "PR_lo" in t.columns else t.loc[d].RP_lo,
                t.loc[d].PR_hi if "PR_hi" in t.columns else t.loc[d].RP_hi)


def icr(t, k):
    return B.rd_(t.loc[k].ICR_pp, t.loc[k].ICR_lo, t.loc[k].ICR_hi)


rows = []
cen = [("Main analysis", lambda d: prs(m2p, d), lambda d: icr(ia, d), "25,808,740"),
       ("LMP-dated births only (code 8)", lambda d: prs(sc.xs("so_DUM"), d),
        lambda d: icr(ic1, "so_DUM") if d == "ptb" else icr(ib, ("4.1_DUM", d)), B.n_(sc.loc[("so_DUM", "ptb")].N)),
       ("Other-method dating only (codes 1–2)", lambda d: prs(sc.xs("so_outro_metodo"), d),
        lambda d: icr(ic1, "so_outro_metodo") if d == "ptb" else icr(ib, ("4.1_outro_metodo", d)), B.n_(sc.loc[("so_outro_metodo", "ptb")].N)),
       ("Dating-robust: other method, excluding preterm births with weight >P97", lambda d: prs(rb_m2, d) if d in rb_m2.index else "n.a.",
        lambda d: icr(rb_it, d) if d in rb_it.index else "n.a.", B.n_(rb_m2.loc["ptb"].N)),
       ("Other method: code 2 only (other method; includes ultrasound per the Live Birth Declaration manual)",
        lambda d: prs(c2_m2.xs("codigo_2"), d), lambda d: icr(c2_it, ("codigo_2", d)), B.n_(c2_m2.loc[("codigo_2", "ptb")].N)),
       ("Weight >P97 preterm reclassified as non-cases (all methods)",
        lambda d: prs(rc_m2, "ptb_reclass") if d == "ptb" else ("n.a." if d == "pig" else "n.a. (not reclassified)"),
        lambda d: icr(rc_it, "ptb_reclass") if d == "ptb" else ("n.a." if d == "pig" else "n.a. (not reclassified)"), "25,808,740"),
       ("Multiple imputation of race/skin color (m = 10)", lambda d: prs(mi_m2, d), lambda d: icr(mi_it, d), "25,808,740 + imputed"),
       ("Excluding CE and DF", lambda d: prs(sc.xs("sem_CE_DF"), d),
        lambda d: icr(ic1, "sem_CE_DF") if d == "ptb" else icr(ib, ("4.3_sem_CE_DF", d)), B.n_(sc.loc[("sem_CE_DF", "ptb")].N))]
WALD = {"Main analysis": wd0.p["ptb"], "LMP-dated births only (code 8)": wd1.p["so_DUM"],
        "Other-method dating only (codes 1–2)": wd1.p["so_outro_metodo"],
        "Dating-robust: other method, excluding preterm births with weight >P97": wdr.p["ptb"],
        "Excluding CE and DF": wd1.p["sem_CE_DF"],
        "Other method: code 2 only (other method; includes ultrasound per the Live Birth Declaration manual)": c2_wd.p[("codigo_2", "ptb")],
        "Weight >P97 preterm reclassified as non-cases (all methods)": rc_wd.p["ptb_reclass"]}
for nome, fpr, ficr, nn_ in cen:
    r = {"Scenario": nome, "N": nn_}
    for d_ in ["ptb", "pig", "ptb_ind"]:
        r[f"{B.OUTC[d_]}: PR M2 (95% CI)"] = fpr(d_)
        r[f"{B.OUTC[d_]}: IC Indigenous×T1 per 100 (95% CI)"] = ficr(d_)
        if d_ == "ptb":
            r["Preterm birth (total): Wald p, 6 race\u00d7tertile terms"] = B.pval(WALD[nome]) if nome in WALD else "n.a."
            r["Preterm birth (total): Wald p, Indigenous terms (2 df)"] = (B.pval(w2.p_ind_2gl[(CEN_W2[nome], "ptb")])
                                                                           if nome in CEN_W2 else "n.a.")
    rows.append(r)
for k, rot in [("pig_k0", "GA in days = weeks×7 + 0 (SGA only)"), ("pig_k6", "GA in days = weeks×7 + 6 (SGA only)")]:
    r = {"Scenario": rot, "N": B.n_(sc.loc[(k, k)].N)}
    for d_ in ["ptb", "pig", "ptb_ind"]:
        r[f"{B.OUTC[d_]}: PR M2 (95% CI)"] = prs(sc.xs(k), k) if d_ == "pig" else "n.a."
        r[f"{B.OUTC[d_]}: IC Indigenous×T1 per 100 (95% CI)"] = icr(ib, (f"4.5_{k}", k)) if d_ == "pig" else "n.a."
    rows.append(r)
for cen_, rot in [("i_todos_indicados", "Unclassified preterm births (131,809) all counted as provider-initiated"),
                  ("ii_todos_espontaneos", "Unclassified preterm births (131,809) all counted as spontaneous")]:
    r = {"Scenario": rot, "N": B.n_(nc_m2.loc[(cen_, "ptb_ind")].N)}
    for d_ in ["ptb", "pig", "ptb_ind"]:
        r[f"{B.OUTC[d_]}: PR M2 (95% CI)"] = prs(nc_m2.xs(cen_), "ptb_ind") if d_ == "ptb_ind" else "n.a. (unchanged)"
        r[f"{B.OUTC[d_]}: IC Indigenous\u00d7T1 per 100 (95% CI)"] = icr(nc_it, (cen_, f"ptb_ind__{cen_}")) if d_ == "ptb_ind" else "n.a. (unchanged)"
    r["Preterm birth (total): Wald p, 6 race\u00d7tertile terms"] = "n.a."
    r["Preterm birth (total): Wald p, Indigenous terms (2 df)"] = "n.a."
    rows.append(r)
    for d_ in ("ptb_ind", "ptb_esp"):
        x = nc_m2.loc[(cen_, d_)]
        R.add(f"PR_naoclass_{cen_}_{d_}_Indigena", float(x.PR), B.pr(x.PR, x.PR_lo, x.PR_hi), "tab_e7b1_04_m2",
              f"PR M2 Indigenous, {B.OUTC[d_]}, unclassified PTB scenario {cen_}", f"cenario={cen_}, desfecho={d_}")
    y = nc_it.loc[(cen_, f"ptb_ind__{cen_}")]
    R.add(f"ICR_naoclass_{cen_}_ptb_ind", float(y.ICR_pp), B.rd_(y.ICR_pp, y.ICR_lo, y.ICR_hi), "tab_e7b1_04_interacao",
          f"IC Indigenous\u00d7T1, provider-initiated PTB, unclassified scenario {cen_}", f"sensibilidade={cen_}, desfecho=ptb_ind")
for k_, x in ic1.drop(index=SEM_2024).iterrows():
    R.add(f"ICR_Ind_T1_ptb_{k_}", float(x.ICR_pp), B.rd_(x.ICR_pp, x.ICR_lo, x.ICR_hi), "tab_e7b1_01_cenarios_interacao",
          f"IC Indigenous\u00d7T1, preterm birth (total), scenario {k_}", f"sensibilidade={k_}")
    R.add(f"Wald_p_ptb_{k_}", float(wd1.p[k_]), B.pval(wd1.p[k_]), "tab_e7b1_01_cenarios_wald",
          f"Wald p (6 terms), preterm birth (total), scenario {k_}", f"sensibilidade={k_}")
r = {"Scenario": "Live-birth bounds: Indigenous fetal death ratio 1–2× national (corrected PR M2, range)", "N": "—"}
for d_ in ["ptb", "pig", "ptb_ind"]:
    x = lim[lim.desfecho == d_]
    r[f"{B.OUTC[d_]}: PR M2 (95% CI)"] = f"{B.num(x.RP_M2_corrigida.min())} to {B.num(x.RP_M2_corrigida.max())}" if len(x) else "n.a."
    r[f"{B.OUTC[d_]}: IC Indigenous×T1 per 100 (95% CI)"] = "n.a."
rows.append(r)
T4 = pd.DataFrame(rows).fillna("n.a.")
# Etapa 8: nota geral para as células "n.a." (decisão da 7c.6b, redação 8; aprovada na Etapa 8 para a v13)
NOTA_NA = ("n.a., not applicable or not estimated. Gestational age in days changes SGA only; the dating-robust analysis and the weight "
           ">P97 reclassification do not apply to SGA; live-birth bounds were computed only for preterm birth (total) and SGA, as a "
           "correction of the PR M2 without a race\u00d7tertile model, so IC and Wald tests are not estimated. 'Unchanged' and 'not "
           "reclassified': the scenario does not change the outcome, so the main-analysis estimates apply; for the unclassified-preterm-"
           "birth scenarios this also holds for the Wald tests of total preterm birth. ")
rod4 = ("Indigenous vs White. PR from model M2 (no tertile terms); IC (interaction contrast) Indigenous×T1 from the race×tertile "
        "model (Table 3 specification), per 100 live births. " + B.NOTE_CLUSTER + " " + B.NOTE_TERC +
        " Dating-robust analysis: births dated by physical exam or other method (codes 1–2, which include ultrasound per the "
        "Live Birth Declaration manual), excluding singleton preterm births 24–36 weeks with birth weight above the 97th "
        "INTERGROWTH-21st centile (42,893 excluded); not applicable to SGA. Multiple imputation: PR M2 and IC fitted in the "
        "access sample, combined with Rubin's rules. Joint Wald tests were not computed for the multiple-imputation analysis. Live-birth bounds: P* = (LB·p + FD·q)/(LB + FD), with the Indigenous "
        "fetal death to live birth ratio k·f/(1 − f), k = 1, 1.5, 2, f = national fetal death ratio (9.70 per 1,000 total "
        "births), q = observed proportion of the outcome among fetal deaths or 1; range over scenarios. "
        "Wald p, Indigenous terms (2 df): joint test of the Indigenous\u00d7T1 and Indigenous\u00d7T2 interaction terms with the same "
        "cluster-robust covariance as the 6-df test (which also includes the Brown and Black terms). "
        "Dating-method strata (LMP only, other method, code 2 only) condition on a variable that depends on access and race; they are "
        "diagnostics of gestational age measurement error, not effect modification, and no stratum is unbiased. Weight >P97 "
        "reclassification: singleton preterm births 24\u201336 weeks with birth weight above the 97th INTERGROWTH-21st centile (gestational "
        "age in days = weeks\u00d77 + 3) counted as non-cases in all dating methods (410,747 preterm births), denominator unchanged; "
        "provider-initiated preterm birth was not reclassified. "
        "Unclassified preterm births: the 131,809 preterm births without spontaneous/provider-initiated classification were all "
        "recoded as provider-initiated (or all as spontaneous) and the models refitted (PR in the full analytic sample; IC in the "
        "sample with a health region, where 131,801 are unclassified). N: sample of the PR M2; IC and Wald samples exclude the 533 "
        "births without a health region. " + NOTA_NA +
        "Sources: tab_e6_01a_m2, tab_e6_01a_wald, tab_e7b1_01_cenarios_interacao, tab_e7b1_01_cenarios_wald, tab_e6_04_wald, "
        "tab_e7b1_04_m2, tab_e7b1_04_interacao, tab_e7b2_01_{m2,interacao,wald}, tab_e7b2_02_reclass_{m2,interacao,wald}, tab_e7b3_02_wald_ind, tab_e6_01a_interacao, tab_e6b_01_m2_cenarios, tab_e6_01b_interacao, tab_e6_04_m2, "
        "tab_e6_04_interacao, tab_e4_06_mi_m2_rubin_rs, tab_e4_06_mi_rubin_rs, tab_e6_07b_limites.")
B.grava_tabela(T4, "tab04_sensitivity", "Table 4. Sensitivity analyses for Indigenous vs White disparities", rod4, xlsx_conjunto=XL, docx_doc=DOC)
pend4 = int((T4 == PEND).sum().sum())
assert pend4 == 0, "Tabela 4 ainda tem células pendentes"

# ================= números-chave adicionais
f6 = B.rd("tab06_fluxograma_regiao").query("regiao == 'Brasil'").set_index("passo")
R.add("N_fonte", int(f6.restante["0_fonte"]), B.n_(f6.restante["0_fonte"]), "tab06_fluxograma_regiao", "Live births 2015–2024 (source)", "regiao=Brasil, passo=0_fonte")
for pss, dsc in [("1_raca", "race/skin color missing, unknown, or Asian (amarela)"), ("2_ig", "GA missing or outside 22–44 weeks"),
                 ("3_esc", "education missing or unknown"), ("4_idade", "maternal age missing, <10 or >60")]:
    R.add(f"excl_{pss}", int(f6.excluidos[pss]), B.n_(f6.excluidos[pss]), "tab06_fluxograma_regiao", f"Excluded: {dsc}", f"passo={pss}")
R.add("N_final", int(f6.restante["4_idade"]), B.n_(f6.restante["4_idade"]), "tab06_fluxograma_regiao", "Analytic sample", "passo=4_idade")
f7 = B.rd("tab07_fluxograma_motivos").query("regiao == 'Brasil' and passo == '1_raca'").set_index("motivo")
R.add("excl_amarela", int(f7.n["3"]), B.n_(f7.n["3"]), "tab07_fluxograma_motivos", "Excluded: Asian (amarela)", "passo=1_raca, motivo=3")
R.add("excl_raca_ausente", int(f7.n["nulo"]), B.n_(f7.n["nulo"]), "tab07_fluxograma_motivos", "Excluded: race/skin color missing", "motivo=nulo")
# 7c.5: % da raça Asian (amarela) entre os nascidos vivos registrados (justificativa da exclusão na S1 e na disponibilidade)
pct_am = 100 * f7.n["3"] / f6.restante["0_fonte"]
R.add("pct_amarela_fonte", float(pct_am), f"{pct_am:.2f}%", "tab07_fluxograma_motivos",
      "Asian (amarela) births as % of registered live births to residents, 2015–2024 (excl_amarela / N_fonte)",
      "numerador passo=1_raca, motivo=3; denominador N_fonte (tab06_fluxograma_regiao, passo=0_fonte)")
for d_ in B.ORDER:
    x = m2p.loc[d_]
    R.add(f"PR_M2_{d_}_Indigena_main", float(x.RP), B.pr(x.RP, x.RP_lo, x.RP_hi), "tab_e6_01a_m2", f"PR M2 Indigenous, {B.OUTC[d_]}",
          f"cluster=regsaude, desfecho={d_}")
rr = B.rd("tab_e6_03b_rrr").query("raca == 'Indigena'")
for _, x in rr.iterrows():
    R.add(f"RRR_{x.analise}_{x.tercil}_{x.categoria}".replace("/", ""), float(x.RRR), B.pr(x.RRR, x.lo, x.hi), "tab_e6_03b_rrr",
          f"Multinomial RRR Indigenous, {x.categoria}, {x.analise} {x.tercil}", f"analise={x.analise}, tercil={x.tercil}, categoria={x.categoria}")
for d_ in ["ptb", "ptb_esp", "ptb_ind"]:
    x = rb_m2.loc[d_]
    R.add(f"PR_robusta_{d_}", float(x.RP), B.pr(x.RP, x.RP_lo, x.RP_hi), "tab_e6_04_m2", f"Dating-robust PR M2 Indigenous, {B.OUTC[d_]}", f"desfecho={d_}")
R.add("N_robusta", int(rb_m2.loc["ptb"].N), B.n_(rb_m2.loc["ptb"].N), "tab_e6_04_m2", "Dating-robust sample size", "desfecho=ptb")
for g in RACES:
    R.add(f"pct_DUM_{g}", float(im.loc[g, "pct_DUM"]), f"{im.loc[g, 'pct_DUM']:.1f}%", "tab_e3_00a_ig_metodo_raca", f"% LMP-dated (code 8), {G(g)}", f"raca={g}")
ip = B.rd("tab_e4b_01_implausivel_brasil").query("criterio == 'b'")
for _, x in ip[ip.ig_metodo.isin(["DUM", "outro_metodo"])].iterrows():
    R.add(f"pct_P97_{x.raca}_{x.ig_metodo}", float(x.pct), f"{x.pct:.1f}%", "tab_e4b_01_implausivel_brasil",
          f"% of singleton preterm births with weight >P97, {G(x.raca)}, {x.ig_metodo}", f"criterio=b, raca={x.raca}, ig_metodo={x.ig_metodo}")
e5 = B.rd("tab_e5_02_modelos").set_index("modelo")
for k, nm in [("M1 nulo", "M1"), ("M2 efeitos principais", "M2")]:
    R.add(f"MAIHDA_VPC_{nm}", float(e5.VPC_pct[k]), f"{e5.VPC_pct[k]:.2f}% ({e5.VPC_lo[k]:.2f}–{e5.VPC_hi[k]:.2f})", "tab_e5_02_modelos", f"MAIHDA VPC {nm}", f"modelo={k}")
    R.add(f"MAIHDA_AUC_{nm}", float(e5.AUC[k]), f"{e5.AUC[k]:.3f} ({e5.AUC_lo[k]:.3f}–{e5.AUC_hi[k]:.3f})", "tab_e5_02_modelos", f"MAIHDA AUC {nm} (DeLong)", f"modelo={k}")
R.add("MAIHDA_PCV", float(e5.PCV_pct["M2 efeitos principais"]),
      f"{e5.PCV_pct['M2 efeitos principais']:.1f}% ({e5.PCV_lo['M2 efeitos principais']:.1f}–{e5.PCV_hi['M2 efeitos principais']:.1f})",
      "tab_e5_02_modelos", "MAIHDA PCV M1→M2", "modelo=M2 efeitos principais")
pr5 = B.rd("tab_e5_03_predicoes")
top = pr5.sort_values("p_pct", ascending=False).iloc[0]
ref = pr5[pr5.estrato == "Branca|ge12|20a34|SE|T3"].iloc[0]
R.add("MAIHDA_top_estrato", float(top.p_pct), f"{top.estrato}: {top.p_pct:.1f}% ({top.p_lo:.1f}–{top.p_hi:.1f})", "tab_e5_03_predicoes",
      "Highest predicted SGA risk stratum (M2)", "max p_pct")
R.add("MAIHDA_ref_estrato", float(ref.p_pct), f"{ref.p_pct:.1f}% ({ref.p_lo:.1f}–{ref.p_hi:.1f})", "tab_e5_03_predicoes",
      "Reference stratum White|≥12y|20–34|SE|T3 predicted SGA risk", "estrato=Branca|ge12|20a34|SE|T3")
for d_ in ["ptb", "pig"]:
    x = lim[lim.desfecho == d_]
    R.add(f"limites_{d_}", [float(x.RP_M2_corrigida.min()), float(x.RP_M2_corrigida.max())],
          f"{B.num(x.RP_M2_corrigida.min())} to {B.num(x.RP_M2_corrigida.max())}", "tab_e6_07b_limites",
          f"Live-birth bounds, corrected PR M2 Indigenous, {B.OUTC[d_]} (k = 1–2; q observed or 1)", f"desfecho={d_}")

s1r = B.rd("tab_e7b1_02_s1_restrito").query("regiao == 'Brasil'").set_index("grupo")
for g_ in ("excluidos", "incluidos"):
    x = s1r.loc[g_]
    R.add(f"S1_ptb_{g_}_22_44", float(x.ptb_pct_22_44), f"{x.ptb_pct_22_44:.2f}% ({B.n_(x.n_ptb_22_44)}/{B.n_(x.n_ig_22_44)})",
          "tab_e7b1_02_s1_restrito", f"Preterm birth among {g_} births with GA 22\u201344 weeks", f"regiao=Brasil, grupo={g_}")
af = B.rd("tab_e7b1_03_auc_fixa").set_index("modelo").loc["m2"]
R.add("MAIHDA_AUC_M2_fixa", float(af.AUC_parte_fixa), f"{af.AUC_parte_fixa:.4f} ({af.AUC_fixa_lo:.4f}\u2013{af.AUC_fixa_hi:.4f})",
      "tab_e7b1_03_auc_fixa", "MAIHDA AUC, fixed part of M2 only (DeLong)", "modelo=m2")
ncn = B.rd("tab_e7b1_04_naoclass").groupby("amostra").nao_classificados.sum()
R.add("naoclass_analitica", int(ncn["analitica"]), B.n_(ncn["analitica"]), "tab_e7b1_04_naoclass", "Unclassified preterm births, analytic sample", "amostra=analitica")
R.add("naoclass_com_regiao", int(ncn["com_regiao_saude"]), B.n_(ncn["com_regiao_saude"]), "tab_e7b1_04_naoclass",
      "Unclassified preterm births, sample with health region", "amostra=com_regiao_saude")
for cod in ("codigo_1", "codigo_2"):
    for d_ in ("ptb", "pig", "ptb_ind"):
        x, y = c2_m2.loc[(cod, d_)], c2_it.loc[(cod, d_)]
        R.add(f"PR_M2_{cod}_{d_}_Indigena", float(x.PR), B.pr(x.PR, x.PR_lo, x.PR_hi), "tab_e7b2_01_m2", f"PR M2 Indigenous, {B.OUTC[d_]}, TPMETESTIM {cod[-1]} only",
              f"cenario={cod}, desfecho={d_}")
        R.add(f"ICR_Ind_T1_{cod}_{d_}", float(y.ICR_pp), B.rd_(y.ICR_pp, y.ICR_lo, y.ICR_hi), "tab_e7b2_01_interacao",
              f"IC Indigenous\u00d7T1, {B.OUTC[d_]}, TPMETESTIM {cod[-1]} only", f"sensibilidade={cod}, desfecho={d_}")
        R.add(f"Wald_p_{cod}_{d_}", float(c2_wd.p[(cod, d_)]), B.pval(c2_wd.p[(cod, d_)]), "tab_e7b2_01_wald",
              f"Wald p (6 terms), {B.OUTC[d_]}, TPMETESTIM {cod[-1]} only", f"sensibilidade={cod}, desfecho={d_}")
for d_ in ("ptb_reclass", "ptb_esp_reclass"):
    for g in B.RACES[1:]:
        x = B.rd("tab_e7b2_02_reclass_m2").query("desfecho == @d_ and raca == @g").iloc[0]
        R.add(f"PR_M2_{d_}_{g}", float(x.PR), B.pr(x.PR, x.PR_lo, x.PR_hi), "tab_e7b2_02_reclass_m2",
              f"PR M2 {B.RACE[g]}, {d_} (weight >P97 preterm reclassified, all methods)", f"desfecho={d_}, raca={g}")
    y = rc_it.loc[d_]
    R.add(f"ICR_Ind_T1_{d_}", float(y.ICR_pp), B.rd_(y.ICR_pp, y.ICR_lo, y.ICR_hi), "tab_e7b2_02_reclass_interacao",
          f"IC Indigenous\u00d7T1, {d_} (reclassified)", f"desfecho={d_}")
    R.add(f"Wald_p_{d_}", float(rc_wd.p[d_]), B.pval(rc_wd.p[d_]), "tab_e7b2_02_reclass_wald", f"Wald p (6 terms), {d_} (reclassified)", f"desfecho={d_}")
for (cen_, d_), x in w2.drop(index=SEM_2024, level="cenario").iterrows():
    R.add(f"Wald2_ind_{cen_}_{d_}", float(x.p_ind_2gl), B.pval(x.p_ind_2gl), "tab_e7b3_02_wald_ind",
          f"Wald p, Indigenous terms (2 df), {B.OUTC.get(d_, d_)}, scenario {cen_}", f"cenario={cen_}, desfecho={d_}")
em = B.rd("tab_e7b3_01_esp_m2").query("raca == 'Indigena'").set_index("cenario")
ei = B.rd("tab_e7b3_01_esp_interacao").query("raca == 'Indigena' and nivel == 'T1'").set_index("cenario")
for cen_ in ("codigo_1", "codigo_2", "codigo_8"):
    R.add(f"PR_M2_ptb_esp_{cen_}_Indigena", float(em.PR[cen_]), B.pr(em.PR[cen_], em.PR_lo[cen_], em.PR_hi[cen_]), "tab_e7b3_01_esp_m2",
          f"PR M2 Indigenous, spontaneous PTB, TPMETESTIM {cen_[-1]} only", f"cenario={cen_}")
    R.add(f"ICR_Ind_T1_ptb_esp_{cen_}", float(ei.ICR_pp[cen_]), B.rd_(ei.ICR_pp[cen_], ei.ICR_lo[cen_], ei.ICR_hi[cen_]),
          "tab_e7b3_01_esp_interacao", f"IC Indigenous\u00d7T1, spontaneous PTB, TPMETESTIM {cen_[-1]} only", f"cenario={cen_}")
# 7c.3: especificações alternativas do acesso, EP por região de saúde (etapa3_02_knol.py --rs): 3.3b tercil nacional (IC Indígena×T1 e
# Wald dos 6 termos) e 3.3a índice contínuo (RP de interação por 5 p.p.); só números-chave (sem tabela nova no pacote)
alt_wd = B.rd("tab_e3_02_wald_rs").query("analise == '3.3b_tercil_nac' and estrato == 'Brasil'").set_index("desfecho")
assert (alt_wd.G == 433).all()
alt_it = B.rd("tab_e3_02_interacao_rs").query("analise == '3.3b_tercil_nac' and estrato == 'Brasil' and raca == 'Indigena' and nivel == 'T1_pior'").set_index("desfecho")
alt_ct = B.rd("tab_e3_03a_indice_continuo_rs").query("raca == 'Indigena'").drop_duplicates("desfecho").set_index("desfecho")
for d_ in ["ptb", "pig", "ptb_ind"]:
    y, c = alt_it.loc[d_], alt_ct.loc[d_]
    R.add(f"IC_Ind_T1_tertil_nacional_{d_}", float(y.ICR_pp), B.rd_(y.ICR_pp, y.ICR_lo, y.ICR_hi), "tab_e3_02_interacao_rs",
          f"IC Indigenous\u00d7T1, national tertiles (alternative access specification), {B.OUTC[d_]}",
          f"analise=3.3b_tercil_nac, estrato=Brasil, desfecho={d_}, raca=Indigena, nivel=T1_pior")
    R.add(f"Wald_p_tertil_nacional_{d_}", float(alt_wd.p[d_]), B.pval(alt_wd.p[d_]), "tab_e3_02_wald_rs",
          f"Wald p (6 race\u00d7tertile terms), national tertiles, {B.OUTC[d_]}", f"analise=3.3b_tercil_nac, estrato=Brasil, desfecho={d_}")
    R.add(f"RP_int_5pp_indice_continuo_{d_}", float(c.RP_por_5pp_interacao), B.pr(c.RP_por_5pp_interacao, c.int_lo, c.int_hi),
          "tab_e3_03a_indice_continuo_rs", f"Interaction PR per 5 percentage points of the continuous access index, Indigenous, {B.OUTC[d_]}",
          f"desfecho={d_}, raca=Indigena")
# 7c.7: regiões de saúde de CE e DF na base territorial (segundo motivo da sensibilidade sem CE/DF: índice sobre poucas regiões, grandes)
rsu = B.rd("tab_e7c7_01_regsaude_uf").set_index("uf")
for uf_, nome_ in (("CE", "Ceará"), ("DF", "Federal District")):
    R.add(f"n_regsaude_{uf_}", int(rsu.n_regioes_saude[uf_]), B.n_(rsu.n_regioes_saude[uf_]), "tab_e7c7_01_regsaude_uf",
          f"Health regions in {nome_} in the municipality-to-health-region map used for the access index (DATASUS territorial base, "
          "December 2024)", f"uf={uf_}")
# Etapa 8: sensibilidade com a cobertura da Atenção Básica (nascimentos de 2015–2021; S2b, colunas d e e), EP por região de saúde
e8i = B.rd("tab_e8_04_interacao").query("raca == 'Indigena' and nivel == 'T1'").set_index(["exposicao", "desfecho"])
e8w = B.rd("tab_e8_04_wald").set_index(["exposicao", "desfecho"])
assert (e8w.G == 433).all()
ROT8 = {"tercil_aps": ("aps", "primary health care coverage tertiles"),
        "tercil_ind21": ("indice_2015_2021", "access index tertiles recomputed in 2015\u20132021")}
for ex_, (sf_, txt_) in ROT8.items():
    for d_ in ["ptb", "pig", "ptb_ind"]:
        y, w = e8i.loc[(ex_, d_)], e8w.loc[(ex_, d_)]
        R.add(f"IC_Ind_T1_{sf_}_{d_}", float(y.ICR_pp), B.rd_(y.ICR_pp, y.ICR_lo, y.ICR_hi), "tab_e8_04_interacao",
              f"IC Indigenous\u00d7T1, {txt_}, births 2015\u20132021, {B.OUTC[d_]}", f"exposicao={ex_}, desfecho={d_}, raca=Indigena, nivel=T1")
        R.add(f"Wald2_ind_{sf_}_{d_}", float(w.p_ind_2gl), B.pval(w.p_ind_2gl), "tab_e8_04_wald",
              f"Wald p, Indigenous terms (2 df), {txt_}, births 2015\u20132021, {B.OUTC[d_]}", f"exposicao={ex_}, desfecho={d_}")
R.add("N_aps_2015_2021", int(e8w.N[("tercil_aps", "ptb")]), B.n_(e8w.N[("tercil_aps", "ptb")]), "tab_e8_04_wald",
      "Births 2015\u20132021 with a health region (sample of the primary health care coverage analysis, preterm birth (total))",
      "exposicao=tercil_aps, desfecho=ptb")
sp8 = B.rd("tab_e8_03_spearman").query("estrato == 'Brasil'").set_index("par")
for par_, txt_ in (("cobertura_x_indice", "the access index"), ("cobertura_x_populacao", "the population of the health region")):
    R.add(f"rho_{par_}", float(sp8.rho[par_]), B.num(sp8.rho[par_]), "tab_e8_03_spearman",
          f"Spearman correlation between primary health care coverage and {txt_} (previous year), health region-years of births 2015\u20132021",
          f"par={par_}, estrato=Brasil")
cr8 = B.rd("tab_e8_03_concordancia_resumo").iloc[0]
R.add("kappa_aps_indice", float(cr8.kappa_ponderado_linear), B.num(cr8.kappa_ponderado_linear), "tab_e8_03_concordancia_resumo",
      "Linear-weighted kappa between primary health care coverage tertiles and access index tertiles (births 2015\u20132021)", "")
R.add("pct_concordancia_aps_indice", float(cr8.pct_diagonal), f"{B.pct(cr8.pct_diagonal)}%", "tab_e8_03_concordancia_resumo",
      "Births in the same tertile of primary health care coverage and of the access index, % (births 2015\u20132021)", "")
rt8 = B.rd("tab_e8_03_raca_por_tercil").query("raca == 'Indigena'").set_index("medida")
for ex_, (sf_, txt_) in ROT8.items():
    for t_ in ("T1", "T3"):
        R.add(f"pct_Ind_{t_}_{sf_}", float(rt8.loc[ex_, t_]), f"{B.pct(rt8.loc[ex_, t_])}%", "tab_e8_03_raca_por_tercil",
              f"Indigenous births in {t_} of {txt_}, % (births 2015\u20132021)", f"medida={ex_}, raca=Indigena")
# Etapa 8b: Wald de 6 gl (todos os termos raça × tercil) das duas exposições da Etapa 8, mostrado na S2b (pacote v14)
for ex_, (sf_, txt_) in ROT8.items():
    for d_ in ["ptb", "pig", "ptb_ind"]:
        w = e8w.loc[(ex_, d_)]
        R.add(f"Wald6_{sf_}_{d_}", float(w.p_6gl), B.pval(w.p_6gl), "tab_e8_04_wald",
              f"Wald p (6 race\u00d7tertile terms), {txt_}, births 2015\u20132021, {B.OUTC[d_]}", f"exposicao={ex_}, desfecho={d_}")
B.grava_xlsx(XL, B.TABD / f"tabelas_principais_{B.V}.xlsx")
DOC.save(B.TABD / f"tabelas_principais_{B.V}.docx")
R.grava()
log(f"tabelas 1–4 gravadas (3b → S3b no 02); números-chave: {len(R.itens)}; células pendentes na Tabela 4: {pend4}; fontes lidas: {sorted(set(B.LIDAS))}")
