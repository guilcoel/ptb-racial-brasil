"""
7b.2 Material suplementar (ESM) S1–S8 e declaração de disponibilidade de dados e código. Só lê saídas existentes.
  7d (v15), Online Resources na ordem de 1ª citação: ESM_1.pdf = S8 (Online Resource 1: STROBE + RECORD, com página e linha, montado no
  etapa7d_01); ESM_2.pdf = S7 (Online Resource 2: S7a variáveis e códigos, RECORD 6.1, Etapa 7c.1; S7b dicionário operacional; código 8);
  ESM_3.pdf = Supplementary Methods (Online Resource 3, do docx dos autores, etapa7d_01); ESM_4.xlsx = S1, S1b, S2, S2b, S3, S3b, S4, S4b, S5,
  S5c, S5d, S6 (Online Resource 4; uma aba cada; a S3b é a antiga Tabela 3b); ESM_5.pdf = S9 (Online Resource 5, etapa7b_03).
  S5b (Centro-Oeste, modelo da RSP por método) fica só em outputs/manuscrito/suplementar (não vai para Submissao).
"""
import platform
import re
import subprocess

import docx
import pandas as pd

import etapa7b_lib as B
import etapa0_lib as L

log = L.Logger("7b_02_suplementar", etapa="etapa7b")
XL = []
SUPT = {}


def guarda(df, nome, titulo, rodape, esm=True):
    B.grava_tabela(df, nome, titulo, rodape, pasta=B.SUPD, xlsx_conjunto=XL if esm else None)
    SUPT[nome] = (titulo, df, rodape)


# ---------- S1 fluxograma e excluídos × incluídos
f6 = B.rd("tab06_fluxograma_regiao").query("regiao == 'Brasil'")
f7 = B.rd("tab07_fluxograma_motivos").query("regiao == 'Brasil'")
EN = {"0_fonte": "Live births to residents, 2015\u20132024 (SINASC)", "1_raca": "Excluded: maternal race/skin color missing or Asian (amarela)",
      "2_ig": "Excluded: gestational age missing or outside 22\u201344 weeks", "3_esc": "Excluded: maternal education missing or unknown",
      "4_idade": "Excluded: maternal age missing, <10 or >60 years"}
MOT = {("1_raca", "3"): "Asian (amarela)", ("1_raca", "nulo"): "missing", ("2_ig", "<22"): "<22 weeks", ("2_ig", ">44"): ">44 weeks",
       ("2_ig", "nulo"): "missing", ("3_esc", "9"): "unknown (code 9)", ("3_esc", "nulo"): "missing", ("4_idade", "99"): "code 99",
       ("4_idade", "<10"): "<10 years", ("4_idade", ">60 (exc. 99)"): ">60 years", ("4_idade", "nulo"): "missing"}
rows = []
for _, r in f6.iterrows():
    det = "; ".join(f"{MOT[(r.passo, m.motivo)]} {B.n_(m.n)}" for _, m in f7[f7.passo == r.passo].iterrows())
    rows.append({"Step": EN[r.passo], "Excluded, n": B.n_(r.excluidos) if r.excluidos else "", "Breakdown": det, "Remaining, n": B.n_(r.restante)})
S1 = pd.DataFrame(rows)
# 7c.5: justificativa aprovada da exclusão da raça Asian (amarela); % recalculado das fontes (117,549 / 27,489,150)
N_AM = int(f7[(f7.passo == "1_raca") & (f7.motivo == "3")].n.iloc[0])
N_FONTE = int(f6[f6.passo == "0_fonte"].restante.iloc[0])
PCT_AM = 100 * N_AM / N_FONTE
assert f"{PCT_AM:.2f}" == "0.43", PCT_AM
JUST_AM = (f"excluded because this small group ({PCT_AM:.2f}% of registered births) would not yield stable estimates in analyses "
           "stratified by access tertile within macroregion, and to keep the eligibility criteria of our regional study")
f8 = B.rd("tab08_ptb_incluidos_excluidos")
s1r = B.rd("tab_e7b1_02_s1_restrito")
GR = {"incluidos": "Included", "excluidos": "Excluded (all)", "excluidos_1_raca": "Excluded: race/skin color",
      "excluidos_2_ig": "Excluded: gestational age", "excluidos_3_esc": "Excluded: education", "excluidos_4_idade": "Excluded: maternal age"}
S1x = pd.DataFrame([{"Region": "Brazil" if r.regiao == "Brasil" else B.REG[r.regiao], "Group": GR[r.grupo], "Births, n": B.n_(r.n),
                     "With GA 22\u201344 weeks, n": B.n_(r.n_ig_22_44), "Preterm (22\u201336 weeks), n": B.n_(r.n_ptb_22_44),
                     "Preterm, % (GA 22\u201344 weeks)": "" if pd.isna(r.ptb_pct_22_44) else f"{r.ptb_pct_22_44:.2f}"}
                    for _, r in s1r[s1r.grupo != "excluidos_2_ig"].iterrows()])
u8 = f8.set_index(["regiao", "grupo"])
guarda(pd.concat([S1, pd.DataFrame([{}]), S1x], ignore_index=True).fillna(""), "S1_flow_excluded",
       "Table S1. STROBE flow of the study population and preterm birth among excluded vs included births",
       "Sequential exclusion steps (the first unmet criterion counts). "
       f"Births to mothers of Asian (amarela) race/skin color were {JUST_AM}. Lower panel: preterm birth (22\u201336 weeks) among births with a "
       "recorded gestational age of 22\u201344 weeks, the range of the analytic sample; births excluded at the gestational age step "
       "have no gestational age in that range and are not shown. Without this restriction (gestational age recorded at any value, "
       f"including <22 weeks), preterm birth was {u8.loc[('Brasil', 'excluidos')].ptb_pct:.2f}% among excluded vs "
       f"{u8.loc[('Brasil', 'incluidos')].ptb_pct:.2f}% among included births (tab08_ptb_incluidos_excluidos). Preterm births without "
       "spontaneous/provider-initiated classification: 131,809 in the analytic sample, 131,801 in the sample with a health region "
       "(8 are among the 533 births without a health region). Sources: tab06_fluxograma_regiao, tab07_fluxograma_motivos, "
       "tab_e7b1_02_s1_restrito, tab08_ptb_incluidos_excluidos, tab_e7b1_04_naoclass.")

# ---------- S1b dados faltantes (antes das exclusões)
c = B.rd("tab01_completude_ano").groupby("variavel")[["n", "n_ausente", "n_ignorado"]].sum()
VARS = [("RACACORMAE", "Maternal race/skin color"), ("SEMAGESTAC", "Gestational age, weeks"), ("PESO", "Birth weight"),
        ("ESCMAE", "Maternal education"), ("ESTCIVMAE", "Marital status"), ("IDADEMAE", "Maternal age"),
        ("MESPRENAT", "Month of prenatal care initiation"), ("STTRABPART", "Induced labor (STTRABPART)"),
        ("STCESPARTO", "Cesarean before labor onset (STCESPARTO)"), ("TPROBSON", "Robson group (TPROBSON)")]
rows = []
for v, lab in VARS:
    x = c.loc[v]
    rows.append({"Variable": lab, "SINASC field": v, "Records, n": B.n_(x.n), "Missing, n (%)": f"{B.n_(x.n_ausente)} ({100 * x.n_ausente / x.n:.2f})",
                 "Coded unknown, n (%)": f"{B.n_(x.n_ignorado)} ({100 * x.n_ignorado / x.n:.2f})"})
tp = B.rd("tab_e2_01_tpmetestim_ano_regiao").query("universo == 'todos' and regiao == 'Brasil'")
nul, ign = (tp.n * tp.pct_nulo / 100).sum(), (tp.n * tp.pct_9 / 100).sum()
rows.append({"Variable": "Gestational age estimation method", "SINASC field": "TPMETESTIM", "Records, n": B.n_(tp.n.sum()),
             "Missing, n (%)": f"\u2248{B.n_(nul)} ({100 * nul / tp.n.sum():.2f})", "Coded unknown, n (%)": f"\u2248{B.n_(ign)} ({100 * ign / tp.n.sum():.2f})"})
rb = B.rd("tab_e6_03a_robson")
sc_ = int(rb[rb.tipo == "sem_classif"].n.sum())
rows.append({"Variable": "Preterm births without spontaneous/provider-initiated classification (analytic sample)",
             "SINASC field": "STTRABPART, STCESPARTO, PARTO", "Records, n": B.n_(rb[rb.tipo != "termo"].n.sum()),
             "Missing, n (%)": f"{B.n_(sc_)} ({100 * sc_ / rb[rb.tipo != 'termo'].n.sum():.2f})", "Coded unknown, n (%)": ""})
guarda(pd.DataFrame(rows), "S1b_missing_data", "Table S1b. Missing and unknown values before exclusions (STROBE 12c/14b)",
       "All live births to residents 2015\u20132024 (n = 27,489,150) except the last row (preterm births in the analytic sample). "
       "Coded unknown: codes for 'ignored' (9, 99, 9999) and, for TPROBSON, group 11 (not documented in the CGIAE data structure). "
       "TPMETESTIM counts are approximate (\u2248), derived from yearly percentages rounded to 0.01%. Provider-initiated: STTRABPART = 1 "
       "(induced) or cesarean before labor onset; spontaneous: STTRABPART = 2 and vaginal birth or cesarean after labor onset. "
       "Sources: tab01_completude_ano, tab_e2_01_tpmetestim_ano_regiao, tab_e6_03a_robson.")

# ---------- S2 Knol para PTB espontâneo
cj, dn, it, wd = B.rd("tab_e6_01a_conjunto"), B.rd("tab_e6_01a_dentro"), B.rd("tab_e6_01a_interacao"), B.rd("tab_e6_01a_wald")
cnt = B.rd("tab_e3_01_n_casos_raca_tercil_regiao").groupby(["desfecho", "raca", "tercil_reg"])[["n", "casos"]].sum()
ncm = B.rd("tab_e7b1_04_m2")
nci = B.rd("tab_e7b1_04_interacao").query("raca == 'Indigena' and nivel == 'T1'").set_index(["sensibilidade", "desfecho"])
CEN = {"i_todos_indicados": "all 131,809 unclassified preterm births counted as provider-initiated",
       "ii_todos_espontaneos": "all 131,809 unclassified preterm births counted as spontaneous"}
blk = [{"Race / tertile": "Sensitivity: unclassified preterm births (bounds)"}]
for cen_, lab in CEN.items():
    for d_ in ("ptb_esp", "ptb_ind"):
        y = nci.loc[(cen_, f"{d_}__{cen_}")]
        blk.append({"Race / tertile": f"{B.OUTC[d_]}, {lab}", "IC per 100 (95% CI)": B.rd_(y.ICR_pp, y.ICR_lo, y.ICR_hi) + " (Indigenous\u00d7T1)",
                    "IC p": B.pval(y.ICR_p)})
        for g in B.RACES[1:]:
            x = ncm[(ncm.cenario == cen_) & (ncm.desfecho == d_) & (ncm.raca == g)].iloc[0]
            blk.append({"Race / tertile": f"  {B.RACE[g]} vs White, PR M2", "Joint PR vs White\u2013T3 (95% CI)": B.pr(x.PR, x.PR_lo, x.PR_hi)})
guarda(pd.concat([pd.DataFrame(B.painel_knol("ptb_esp", cj, dn, it, wd, cnt)), pd.DataFrame([{}]), pd.DataFrame(blk)], ignore_index=True).fillna(""),
       "S2_knol_spontaneous",
       "Table S2. Modification of racial disparities by access tertile: spontaneous preterm birth (secondary outcome), and bounds "
       "for unclassified preterm births",
       "Same specification and definitions as Table 3. " + B.NOTE_TERC + " " + B.NOTE_CLUSTER +
       " Bounds block: the 131,809 preterm births without spontaneous/provider-initiated classification ("
       + ", ".join(f"{r.pct_dos_ptb:.2f}% of preterm births among {B.RACE[r.raca]}" for _, r in
                   B.rd("tab_e7b1_04_naoclass").query("amostra == 'analitica'").iterrows()) +
       " women) were all recoded as provider-initiated, or all as spontaneous; "
       "PR from model M2 in the full analytic sample (reported in the 'Joint PR' column); IC (interaction contrast) Indigenous\u00d7T1 from the Table 3 "
       "model (sample with a health region; 131,801 unclassified). Sources: tab_e6_01a_* (desfecho = ptb_esp), "
       "tab_e3_01_n_casos_raca_tercil_regiao, tab_e7b1_04_m2, tab_e7b1_04_interacao, tab_e7b1_04_naoclass.")

# ---------- S2b especificações alternativas do acesso (Etapa 7c.4; só leitura de saídas com EP por região de saúde)
ai = B.rd("tab_e3_02_interacao_rs").query("estrato == 'Brasil' and raca == 'Indigena'")
aw = B.rd("tab_e3_02_wald_rs").query("estrato == 'Brasil' and analise == '3.3b_tercil_nac'").set_index("desfecho")
ac = B.rd("tab_e3_03a_indice_continuo_rs").query("raca == 'Indigena'").drop_duplicates("desfecho").set_index("desfecho")
assert (aw.G == 433).all() and (aw.gl == 6).all()
# Etapa 8: (d) tercis da cobertura da Atenção Básica e (e) comparador, tercis do índice recalculados, nascimentos de 2015–2021
e8i = B.rd("tab_e8_04_interacao").query("raca == 'Indigena' and nivel == 'T1'").set_index(["exposicao", "desfecho"])
e8w = B.rd("tab_e8_04_wald").set_index(["exposicao", "desfecho"])
assert (e8w.G == 433).all()
sp8 = B.rd("tab_e8_03_spearman").query("estrato == 'Brasil'").set_index("par").rho
cr8 = B.rd("tab_e8_03_concordancia_resumo").iloc[0]
rt8 = B.rd("tab_e8_03_raca_por_tercil").query("raca == 'Indigena'").set_index("medida")
COL8 = {"tercil_aps": "(d) Primary health care coverage tertiles, 2015\u20132021", "tercil_ind21": "(e) Access index tertiles, 2015\u20132021"}
rows = []
for d_ in ["ptb", "pig", "ptb_ind"]:
    a = ai[(ai.analise == "3.2_tercil_reg") & (ai.nivel == "T1") & (ai.desfecho == d_)].iloc[0]
    n_ = ai[(ai.analise == "3.3b_tercil_nac") & (ai.nivel == "T1_pior") & (ai.desfecho == d_)].iloc[0]
    c = ac.loc[d_]
    rows.append({"Outcome": B.OUTC[d_],
                 "(a) Main, tertiles within macroregion: IC Indigenous\u00d7T1 per 100 (95% CI)": B.rd_(a.ICR_pp, a.ICR_lo, a.ICR_hi),
                 "(b) National tertiles: IC Indigenous\u00d7T1 per 100 (95% CI)": B.rd_(n_.ICR_pp, n_.ICR_lo, n_.ICR_hi),
                 "(b) National tertiles: Wald p (6 df)": B.pval(aw.p[d_]),
                 "(c) Continuous index: interaction PR per 5 percentage points (95% CI)": B.pr(c.RP_por_5pp_interacao, c.int_lo, c.int_hi)})
    for ex_, col_ in COL8.items():
        y, w = e8i.loc[(ex_, d_)], e8w.loc[(ex_, d_)]
        rows[-1][f"{col_}: IC Indigenous\u00d7T1 per 100 (95% CI)"] = B.rd_(y.ICR_pp, y.ICR_lo, y.ICR_hi)
        rows[-1][f"{col_}: Wald p, Indigenous terms (2 df)"] = B.pval(w.p_ind_2gl)
        rows[-1][f"{col_}: Wald p, 6 race\u00d7tertile terms (6 df)"] = B.pval(w.p_6gl)     # Etapa 8b (v14)
guarda(pd.DataFrame(rows), "S2b_access_specifications",
       "Table S2b. Alternative specifications of access to early prenatal care and of primary health care coverage",
       "Indigenous vs White. All models: model M2 plus the access variable and race \u00d7 access terms; births with a health region "
       "(the 533 without one are excluded). (a) Main specification (Table 3): tertiles of the access index defined within each "
       "macroregion. (b) Tertiles defined on the national distribution of health region \u00d7 year (2015\u20132024), weighted by "
       "births; T1 = worst access. (c) Access index as a continuous variable (percentage of births with prenatal care initiated in "
       "the first trimester, among births with known month of prenatal care initiation, in the mother's health region of residence in "
       "the previous year), per 5 percentage points; interaction "
       "PR = multiplicative change in the Indigenous vs White PR per 5-point increase in the index (PR < 1: the ratio decreases with "
       "better access). "
       "(d) Tertiles, defined within each macroregion as in (a), of primary health care coverage (Family Health Strategy teams and other primary care teams, "
       "parameterized or equivalent by professional working hours; Ministry of Health public report Cobertura da Aten\u00e7\u00e3o B\u00e1sica, 2007\u20132020) in the "
       "mother's health region of residence in the previous year: population-weighted mean of the official municipal monthly coverage "
       "over the 12 months; T1 = lowest coverage. Births 2015\u20132021 only, because the official series ends in December 2020 "
       f"({B.n_(e8w.N[('tercil_aps', 'ptb')])} births for preterm birth (total)). (e) Comparator for (d): tertiles of the access index "
       "recomputed in the same births (2015\u20132021) with the same algorithm. Primary health care coverage measures the supply of "
       "teams relative to the population, not the use of prenatal care: across health region-years it was weakly correlated with the "
       f"access index (Spearman \u03c1 = {B.num(sp8['cobertura_x_indice'])}) and inversely with the population of the health region "
       f"(\u03c1 = {B.num(sp8['cobertura_x_populacao'])}); coverage and access index tertiles agreed for {B.pct(cr8.pct_diagonal)}% of births "
       f"(linear-weighted \u03ba = {B.num(cr8.kappa_ponderado_linear)}); {B.pct(rt8.loc['tercil_aps', 'T3'])}% of Indigenous births were in "
       f"the highest coverage tertile and {B.pct(rt8.loc['tercil_aps', 'T1'])}% in the lowest (access index, 2015\u20132021: "
       f"{B.pct(rt8.loc['tercil_ind21', 'T1'])}% in T1 and {B.pct(rt8.loc['tercil_ind21', 'T3'])}% in T3). "
       "IC (interaction contrast) = risk difference (Indigenous vs White) within T1 minus the same difference within "
       "T3, per 100 live births. In (b), the Wald test jointly tests the 6 race \u00d7 tertile interaction terms (Brown, Black, and "
       "Indigenous \u00d7 T1 and T2; 6 df); in (d) and (e), it jointly tests the Indigenous \u00d7 T1 and Indigenous \u00d7 T2 terms (2 df) "
       "and, separately, the 6 race \u00d7 tertile terms of its own tertiles (6 df), with the same cluster-robust covariance. 95% CIs and Wald tests from cluster-robust variance with clustering by health region of "
       "residence (G = 433). (b) to (e) belong to the secondary family of the analysis hierarchy (no multiplicity adjustment). Sources: "
       "tab_e3_02_interacao_rs, tab_e3_02_wald_rs, tab_e3_03a_indice_continuo_rs, tab_e8_04_interacao, tab_e8_04_wald, tab_e8_03_spearman, "
       "tab_e8_03_concordancia_resumo, tab_e8_03_raca_por_tercil.")

# ---------- S3 multinomial
rr = B.rd("tab_e6_03b_rrr")
LAB = {"Brasil": "Brazil", "por_tercil": "Within tertile", "razao_RRR_T1_vs_T3": "Ratio of RRR, T1 vs T3"}
S3 = pd.DataFrame([{"Analysis": LAB[r.analise], "Tertile": B.TERC.get(r.tercil, r.tercil if r.tercil != "todos" else "All"),
                    "Outcome category": "Spontaneous" if r.categoria == "espontaneo" else "Provider-initiated", "Race": B.RACE[r.raca],
                    "RRR (95% CI)": B.pr(r.RRR, r.lo, r.hi), "N": B.n_(r.N), "Clusters": B.n_(r.G)} for _, r in rr.iterrows()])
guarda(S3, "S3_multinomial", "Table S3. Multinomial logistic regression: spontaneous and provider-initiated vs term births",
       "Baseline-category logit (reference: term birth), covariates of model M2; RRR vs White. Within-tertile RRR from the model with "
       "tertile and race\u00d7tertile terms (access sample). 131,809 preterm births without classification excluded. " + B.NOTE_TERC + " " +
       B.NOTE_CLUSTER + " Source: tab_e6_03b_rrr.")

# ---------- S3b cortes dos tercis por macrorregião (7d, v15: a antiga Tabela 3b, que saiu das tabelas principais)
ct = B.rd("tab_e3_01_tercis_regiao_cortes").set_index("regiao")
cr = B.rd("tab_e3_01_n_casos_raca_tercil_regiao").groupby(["regiao", "tercil_reg", "desfecho"])[["n", "casos"]].sum()
rows = []
for reg in ["N", "NE", "SE", "S", "CO"]:
    c = ct.loc[reg]
    for t in ["T1", "T2", "T3"]:
        r = {"Macroregion": B.REG[reg], "Tertile": B.TERC[t],
             "Cut-points, % first-trimester initiation (T1/T2; T2/T3)": f"{c.corte_T1_T2:.1f}; {c.corte_T2_T3:.1f}" if t == "T1" else "",
             "Health regions, n": B.n_(c.n_regioes_saude) if t == "T1" else "",
             "Live births, n": B.n_(cr.loc[(reg, t, "ptb")].n)}
        for d_ in B.ORDER:
            k = cr.loc[(reg, t, d_)]
            r[f"{B.OUTC[d_]}, %"] = f"{100 * k.casos / k.n:.2f}"
        rows.append(r)
T3b = pd.DataFrame(rows)
rod3b = (B.NOTE_TERC + " Cut-points are computed on the joint distribution of health region × year (2015–2024) within each "
         "macroregion, weighted by births; a health region can change tertile across years. Prevalences use the denominators of "
         "each outcome. Sources: tab_e3_01_tercis_regiao_cortes, tab_e3_01_n_casos_raca_tercil_regiao.")
guarda(T3b, "S3b_terciles_region", "Table S3b. Access tertiles by macroregion: cut-points, health regions, births, and "
       "outcome prevalence", rod3b)

# ---------- S4 exploratória com BH
mu = B.rd("tab_e6_05_multiplicidade").query("familia == 'exploratoria'")
AN = {"3.3c_estratificado": "Main model stratified by macroregion", "3.5_idade": "Race \u00d7 maternal age group",
      "3.5_escolaridade": "Race \u00d7 maternal education", "3.4_regiao": "Race \u00d7 macroregion", "3.5_periodo": "Race \u00d7 period",
      "3.2_tercil_reg": "Main model, low birth weight at term", "4.1c_raca_x_ig_metodo": "Race \u00d7 GA estimation method",
      "3.3a_indice_continuo": "Continuous access index"}
OC = dict(B.OUTC, lbw_termo="Low birth weight at term")


def fmt_est(r):
    if r.tipo == "ICR":
        return B.rd_(r.estimativa, r.lo, r.hi)
    if r.tipo == "Wald":
        return f"\u03c7\u00b2 = {r.estimativa:.1f}"
    return B.pr(r.estimativa, r.lo, r.hi)


def termo_en(t):
    for k, v in B.RACE.items():
        t = t.replace(k, v)
    return t.replace("\u00d7>=35", "\u00d7\u226535").replace("le7", "\u22647 y").replace("8a11", "8\u201311 y").replace("ge12", "\u226512 y")


S4 = pd.DataFrame([{"Analysis": AN.get(r.analise, r.analise), "Stratum": B.REG.get(r.estrato, r.estrato if r.estrato != "Brasil" else "Brazil"),
                    "Outcome": OC.get(r.desfecho, r.desfecho), "Statistic": {"ICR": "IC"}.get(r.tipo, r.tipo), "Term": termo_en(r.termo), "Estimate (95% CI)": fmt_est(r),
                    "p": B.pval(r.p), "p (BH)": B.pval(r.q_BH)} for _, r in mu.iterrows()])
foco = S4[S4.Analysis.isin([AN["3.3c_estratificado"], AN["3.5_idade"], AN["3.5_escolaridade"]])]
guarda(foco, "S4_exploratory_strata", "Table S4. Exploratory analyses: stratification by macroregion, maternal age, and education",
       f"Exploratory family: {len(mu)} tests (IC, Wald, and continuous-index interactions) with Benjamini\u2013Hochberg adjusted p-values "
       "computed within the whole family (full family in Table S4b). IC (interaction contrast) per 100 live births. " + B.NOTE_TERC + " " + B.NOTE_CLUSTER +
       " Source: tab_e6_05_multiplicidade.")
guarda(S4, "S4b_exploratory_family", "Table S4b. Full exploratory family with Benjamini\u2013Hochberg adjusted p-values",
       "Hierarchy defined before inspecting q-values: primary (Table 3), secondary, exploratory. IC, interaction contrast (per 100 live "
       "births). Source: tab_e6_05_multiplicidade.")

# ---------- S5 plausibilidade (sem o Centro-Oeste)
ip = B.rd("tab_e4b_01_implausivel_brasil")
MET = {"DUM": "LMP (code 8)", "outro_metodo": "Other method (codes 1\u20132)", "ignorado": "Unknown"}
rows = []
for (g, m), x in ip.groupby(["raca", "ig_metodo"]):
    x = x.set_index("criterio")
    rows.append({"Race": B.RACE[g], "GA method": MET[m], "Singleton preterm births 24\u201336 wk, n": B.n_(x.n_prematuros["b"]),
                 "Birth weight >P97, % (95% CI)": f"{x.pct['b']:.2f} ({x.ic_lo['b']:.2f}\u2013{x.ic_hi['b']:.2f})",
                 "Birth weight \u22652,500 g, % (95% CI)": f"{x.pct['a']:.2f} ({x.ic_lo['a']:.2f}\u2013{x.ic_hi['a']:.2f})",
                 "Birth weight >P90, % (95% CI)": f"{x.pct['c']:.2f} ({x.ic_lo['c']:.2f}\u2013{x.ic_hi['c']:.2f})"})
S5 = pd.DataFrame(rows)
S5["_o"] = S5.Race.map({v: i for i, v in enumerate(B.RACE.values())})
S5 = S5.sort_values(["_o", "GA method"]).drop(columns="_o")
guarda(S5, "S5_weight_ga_plausibility", "Table S5. Birth weight\u2013gestational age plausibility among singleton preterm births by race/skin color and dating method",
       "Centiles: INTERGROWTH-21st newborn standards, gestational age in days = weeks\u00d77 + 3. Wilson 95% CIs. Source: tab_e4b_01_implausivel_brasil.")
# ---------- S5c "outro método" separado em código 1 e código 2 (Etapa 7b.2; diagnóstico de mensuração)
dd_ = B.rd("tab_e7b2_01_dist")
dt_ = B.rd("tab_e7b2_01_dist_tercil")
mm_ = B.rd("tab_e7b2_01_m2")
ii_ = B.rd("tab_e7b2_01_interacao").query("raca == 'Indigena' and nivel == 'T1'").set_index(["sensibilidade", "desfecho"])
ww_ = B.rd("tab_e7b2_01_wald").set_index(["sensibilidade", "desfecho"])
pp_ = B.rd("tab_e7b2_01_p97")
cc_ = B.rd("tab_e7b2_01_casos_ind")
COD = {1: "Code 1 (physical exam)", 2: "Code 2 (other method, incl. ultrasound)"}
rows = []
for cod, lab in COD.items():
    for _, r in dd_[dd_.codigo == cod].iterrows():
        rows.append({"TPMETESTIM": lab, "Block": "Births, n (% of all births of the race)", "Race": B.RACE[r.raca],
                     "Value": f"{B.n_(r.n)} ({r.pct_da_raca:.1f})"})
    for _, r in dt_[dt_.codigo == cod].iterrows():
        rows.append({"TPMETESTIM": lab, "Block": "% of births with this code, by access tertile", "Race": B.RACE[r.raca],
                     "Tertile": B.TERC[r.tercil], "Value": f"{r.pct:.1f} ({B.n_(r.n_codigo)}/{B.n_(r.n_total)})"})
    for d_ in ("ptb", "pig", "ptb_ind"):
        for _, r in mm_[(mm_.cenario == f"codigo_{cod}") & (mm_.desfecho == d_)].iterrows():
            rows.append({"TPMETESTIM": lab, "Block": f"PR M2 vs White, {B.OUTC[d_]}", "Race": B.RACE[r.raca], "Value": B.pr(r.PR, r.PR_lo, r.PR_hi),
                         "N": B.n_(r.N)})
        y, w = ii_.loc[(f"codigo_{cod}", d_)], ww_.loc[(f"codigo_{cod}", d_)]
        cs = cc_[(cc_.codigo == cod) & (cc_.desfecho == d_)]
        inst = ", ".join(f"{r.tercil} {int(r.casos)}" for _, r in cs.iterrows())
        rows.append({"TPMETESTIM": lab, "Block": f"IC Indigenous\u00d7T1 per 100, {B.OUTC[d_]}", "Race": "Indigenous",
                     "Value": B.rd_(y.ICR_pp, y.ICR_lo, y.ICR_hi), "Wald p (6 terms)": B.pval(w.p),
                     "Indigenous cases by tertile": inst + (" \u2014 UNSTABLE (<30 cases in a cell)" if cs.instavel.any() else "")})
    for _, r in pp_[pp_.codigo == cod].iterrows():
        rows.append({"TPMETESTIM": lab, "Block": "Singleton preterm births 24\u201336 wk with weight >P97, % (95% CI)", "Race": B.RACE[r.raca],
                     "Value": f"{r.pct:.2f} ({r.ic_lo:.2f}\u2013{r.ic_hi:.2f})", "N": B.n_(r.n_prematuros)})
guarda(pd.DataFrame(rows).fillna(""), "S5c_other_method_by_code",
       "Table S5c. 'Other method' gestational age dating split into TPMETESTIM code 1 (physical exam) and code 2 (other method, "
       "which includes ultrasound per the Live Birth Declaration manual)",
       "Diagnostic of gestational age measurement error, not effect modification: the dating method depends on access and race, so "
       "strata by method condition on a post-exposure variable and no stratum is unbiased. PR from model M2 (each code subsample); IC "
       "(interaction contrast) and Wald from the Table 3 model (sample with a health region). " + B.NOTE_TERC + " " + B.NOTE_CLUSTER +
       " Cells with fewer than 30 Indigenous cases in any tertile are flagged as unstable. Weight >P97: INTERGROWTH-21st, gestational "
       "age in days = weeks\u00d77 + 3, Wilson 95% CI. Sources: tab_e7b2_01_{dist,dist_tercil,m2,interacao,wald,p97,casos_ind}.")
# ---------- S5d PTB espontâneo por código e Wald dos termos indígenas (Etapa 7b.3)
em_ = B.rd("tab_e7b3_01_esp_m2")
ei_ = B.rd("tab_e7b3_01_esp_interacao").query("nivel == 'T1'")
w2_ = B.rd("tab_e7b3_02_wald_ind")
rci = B.rd("tab_e7b2_02_reclass_interacao").query("desfecho == 'ptb_reclass' and nivel == 'T1'")
CODL = {"codigo_1": "Code 1 (physical exam)", "codigo_2": "Code 2 (other method, incl. ultrasound)", "codigo_8": "Code 8 (LMP)"}
CENL = dict(CODL, principal="Main analysis", reclass_p97="Weight >P97 preterm reclassified (all methods)",
            outro_metodo_1_2="Other method, codes 1\u20132", robusta_datacao="Dating-robust (other method, no preterm weight >P97)",
            sem_CE_DF="Excluding CE and DF")
rows = []
for cen_, lab in CODL.items():
    for _, r in em_[em_.cenario == cen_].iterrows():
        rows.append({"Block": "Spontaneous preterm birth by dating code: PR M2 vs White", "Scenario": lab, "Outcome": B.OUTC["ptb_esp"],
                     "Term": B.RACE[r.raca], "Estimate (95% CI)": B.pr(r.PR, r.PR_lo, r.PR_hi), "N": B.n_(r.N)})
    for _, r in ei_[ei_.cenario == cen_].iterrows():
        rows.append({"Block": "Spontaneous preterm birth by dating code: IC \u00d7T1 per 100", "Scenario": lab, "Outcome": B.OUTC["ptb_esp"],
                     "Term": f"{B.RACE[r.raca]}\u00d7T1", "Estimate (95% CI)": B.rd_(r.ICR_pp, r.ICR_lo, r.ICR_hi), "p": B.pval(r.ICR_p)})
for _, r in w2_[w2_.cenario != "sem_2024"].iterrows():   # 7c.1: sensibilidade sem 2024 retirada do pacote
    rows.append({"Block": "Wald tests: Indigenous terms (2 df) and all 6 race\u00d7tertile terms", "Scenario": CENL[r.cenario],
                 "Outcome": B.OUTC[r.desfecho] + (" (reclassified)" if r.cenario == "reclass_p97" else ""),
                 "Wald p, Indigenous terms (2 df)": f"{B.pval(r.p_ind_2gl)} (\u03c7\u00b2 = {r.chi2_ind_2gl:.2f})",
                 "Wald p, 6 terms": f"{B.pval(r.p_6gl)} (\u03c7\u00b2 = {r.chi2_6gl:.2f})", "N": B.n_(r.N)})
for _, r in rci.iterrows():
    rows.append({"Block": "Weight >P97 reclassified: IC \u00d7T1 of total preterm birth, all races (source of the 6-df Wald)",
                 "Scenario": CENL["reclass_p97"], "Outcome": B.OUTC["ptb"], "Term": f"{B.RACE[r.raca]}\u00d7T1",
                 "Estimate (95% CI)": B.rd_(r.ICR_pp, r.ICR_lo, r.ICR_hi), "p": B.pval(r.ICR_p)})
guarda(pd.DataFrame(rows).fillna(""), "S5d_spontaneous_by_code_wald",
       "Table S5d. Spontaneous preterm birth by gestational age dating code, and Wald tests restricted to the Indigenous interaction terms",
       "Diagnostic conditional on the dating method, not effect modification. Spontaneous preterm birth excludes unclassified preterm "
       "births from the denominator. PR from model M2 in each code subsample; IC (interaction contrast) and Wald from the Table 3 model (sample with a health "
       "region). The Indigenous Wald test (2 df) jointly tests the Indigenous\u00d7T1 and Indigenous\u00d7T2 terms with the same "
       "cluster-robust covariance as the 6-df test. In the weight >P97 reclassification, unclassified preterm births stay excluded "
       "from the spontaneous preterm birth denominator (as in all spontaneous analyses), even when reclassified as non-cases of total "
       "preterm birth. " + B.NOTE_TERC + " " + B.NOTE_CLUSTER +
       " Sources: tab_e7b3_01_esp_m2, tab_e7b3_01_esp_interacao, tab_e7b3_02_wald_ind, tab_e7b2_02_reclass_interacao.")

co = B.rd("tab_e4b_04_co_estratos_rs").query("ep in ['hc0', 'cluster']")
ESTR = {"todos": "All", "DUM": "LMP (code 8)", "outro_metodo": "Other method", "ignorado": "Unknown"}
S5b = pd.DataFrame([{"Stratum": ESTR[r.estrato], "Model": r.modelo, "Measure": "OR" if r.medida == "OR" else "PR",
                     "Variance": "Health-region cluster" if r.ep == "cluster" else "HC0 (as in the original article)",
                     "Race": B.RACE[r.raca], "Estimate (95% CI)": B.pr(r.est, r.lo, r.hi), "N": B.n_(r.N), "Cases": B.n_(r.casos)}
                    for _, r in co.iterrows()])
guarda(S5b, "S5b_centerwest_rsp_by_method_INTERNAL",
       "Table S5b (INTERNAL, not for submission). Center-West replication of the RSP model by dating method",
       "M1 = race; M5 = race + age + education + year + state (RSP 2026;60:e44). Not for submission until discussed with advisors. "
       "Source: tab_e4b_04_co_estratos_rs.", esm=False)

# ---------- S6 MAIHDA
e5 = B.rd("tab_e5_02_modelos")
area = B.rd("tab_e6_06_maihda_area")
auca = B.rd("tab_e6b_02_auc_area")
afx = B.rd("tab_e7b1_03_auc_fixa").set_index("modelo")
MOD = {"M1 nulo": "M1 null (stratum)", "M2 efeitos principais": "M2 main effects (stratum)", "M2 + ano (estrato × ano)": "M2 + year",
       "M1 nulo — outro método": "M1 null, other-method dating only", "M2 — outro método": "M2, other-method dating only"}
rows = []
for _, r in e5[e5.modelo.isin(MOD)].iterrows():
    rows.append({"Model": MOD[r.modelo], "Stratum variance (95% CI)": f"{r.s2:.4f} ({r.s2_lo_perfil:.4f}\u2013{r.s2_hi_perfil:.4f})",
                 "Health-region variance (95% CI)": "", "VPC stratum, % (95% CI)": f"{r.VPC_pct:.2f} ({r.VPC_lo:.2f}\u2013{r.VPC_hi:.2f})",
                 "VPC health region, %": "", "PCV, % (95% CI)": "" if pd.isna(r.PCV_pct) else (f"{r.PCV_pct:.1f}" + ("" if pd.isna(r.PCV_lo) else f" ({r.PCV_lo:.1f}\u2013{r.PCV_hi:.1f})")),
                 "AUC (95% CI, DeLong)": f"{r.AUC:.3f} ({r.AUC_lo:.3f}\u2013{r.AUC_hi:.3f})",
                 "AUC, fixed part only (95% CI, DeLong)": (f"{afx.AUC_parte_fixa['m2']:.4f} ({afx.AUC_fixa_lo['m2']:.4f}\u2013{afx.AUC_fixa_hi['m2']:.4f})"
                                                          if r.modelo == "M2 efeitos principais" else ""),
                 "Correlation of stratum effects with M2/M1": ""})
for i, r in area.iterrows():
    a = auca.iloc[i]
    rows.append({"Model": ["A1 null, stratum \u00d7 health region (cross-classified)", "A2 main effects, cross-classified"][i],
                 "Stratum variance (95% CI)": f"{r.s2_estrato:.4f} ({r.s2_estrato_lo:.4f}\u2013{r.s2_estrato_hi:.4f})",
                 "Health-region variance (95% CI)": f"{r.s2_regsaude:.4f} ({r.s2_regsaude_lo:.4f}\u2013{r.s2_regsaude_hi:.4f})",
                 "VPC stratum, % (95% CI)": f"{r.VPC_estrato_pct:.2f}", "VPC health region, %": f"{r.VPC_regsaude_pct:.2f}",
                 "PCV, % (95% CI)": "" if pd.isna(r.PCV_estrato_pct) else f"{r.PCV_estrato_pct:.1f}",
                 "AUC (95% CI, DeLong)": f"{a.AUC:.3f} ({a.AUC_lo:.3f}\u2013{a.AUC_hi:.3f})",
                 "Correlation of stratum effects with M2/M1": f"{r.cor_u_estrato_vs_E5:.3f}"})
S6a = pd.DataFrame(rows)
pr5 = B.rd("tab_e5_03_predicoes")


def lab_estr(s):
    g, e, a, rg, t = s.split("|")
    return (f"{B.RACE[g]}; {dict(le7='\u22647 y', ge12='\u226512 y').get(e, '8\u201311 y')}; "
            f"{dict(lt20='<20', ge35='\u226535').get(a, '20\u201334')}; {B.REG[rg]}; {t}")


tb = pd.concat([pr5.sort_values("p_pct", ascending=False).head(10).assign(lista="Highest 10"),
                pr5.sort_values("p_pct").head(10).assign(lista="Lowest 10")])
S6b = pd.DataFrame([{"List": r.lista, "Stratum (race; education; age; macroregion; tertile)": lab_estr(r.estrato), "Births, n": B.n_(r.n),
                     "Observed SGA, %": f"{r.obs_pct:.2f}", "Predicted SGA, % (95% CI)": f"{r.p_pct:.2f} ({r.p_lo:.2f}\u2013{r.p_hi:.2f})",
                     "Ratio vs reference (95% CI)": B.pr(r.razao, r.razao_lo, r.razao_hi)} for _, r in tb.iterrows()])
rod6 = ("Intersectional MAIHDA of SGA: 540 strata (race/skin color \u00d7 education \u00d7 age \u00d7 macroregion \u00d7 access tertile; "
        "25,028,320 births); logistic multilevel models (lme4, Laplace) on aggregated data. VPC = \u03c3\u00b2/(\u03c3\u00b2 + \u03c0\u00b2/3) "
        "(Evans et al. 2024); cross-classified VPC = \u03c3\u00b2_k/(\u03c3\u00b2_stratum + \u03c3\u00b2_region + \u03c0\u00b2/3) (BMJ Open 2020;10:e036130); "
        "PCV = proportional change in stratum variance from the null to the main-effects model. Variance CIs: profile likelihood; PCV CI: "
        "parametric bootstrap (500 replicates). The conditional AUC (predicted probability of each stratum, fixed plus random "
        "effects) is the same in M1 and M2 because M2 only moves the between-stratum variance from the stratum random effects to "
        "the fixed effects; the AUC of the fixed part of M2 alone shows that almost all of the discrimination comes from the "
        "additive main effects, consistent with the PCV of 86.8%. Predicted risks from M2 (fixed + stratum random effects), 95% CIs by simulation; "
        "reference stratum White; \u226512 y; 20\u201334; Southeast; T3. " + B.NOTE_TERC +
        " Sources: tab_e5_02_modelos, tab_e6_06_maihda_area, tab_e6b_02_auc_area, tab_e7b1_03_auc_fixa, tab_e5_03_predicoes.")
guarda(pd.concat([S6a, pd.DataFrame([{}]), S6b], ignore_index=True).fillna(""), "S6_maihda", "Table S6. Intersectional MAIHDA of SGA", rod6)

# ---------- S7 = Online Resource 2 (PDF): S7a variáveis e códigos (RECORD 6.1; Etapa 7c.1), S7b dicionário operacional, código 8
dic = B.rd("dicionario_variaveis_v3")
cc = B.rd("tab_e6_02a_concordancia").query("sub == 'todas validas'")
pre = B.rd("tab_e6_02b_tpmetestim_2010_2014")
c8 = cc[cc.tp.astype(str) == "8"].iloc[0]
assert (cc[cc.tp.astype(str) != "8"].pct_dum_valida == 0).all()          # DUM válida em 0% dos códigos 1, 2, 9
p13 = pre[(pre.ano == 2013) & (pd.to_numeric(pre.tp, errors="coerce") == 8)].iloc[0]
EV8 = (f"code 8 first appears in {int(p13.ano)}, when the {B.n_(p13.n)} code-8 records are exactly the {B.n_(p13.n_dtultmenst)} "
       f"records with a filled LMP date (DTULTMENST); in the 2015–2024 analytic sample, a valid LMP date is present in "
       f"{c8.pct_dum_valida:.3f}% of code-8 records and in 0% of records with codes 1, 2, or 9, and LMP-based gestational age agrees "
       f"with SEMAGESTAC exactly in {c8.pct_exata:.1f}% and within ±1 week in {c8.pct_pm1:.2f}%")
REGRA = ("Preterm births only. Provider-initiated = STTRABPART 1 OR (PARTO 2 AND STCESPARTO 1); spontaneous = not provider-initiated "
         "AND STTRABPART 2 AND (PARTO 1 OR (PARTO 2 AND STCESPARTO 2)); unclassified = all other preterm births. Provider-initiated is "
         "evaluated first; missing values meet no condition.")
# (sistema, variável, rótulo oficial em inglês, rótulo oficial em português (verbatim), códigos usados e recodificação, uso)
# rótulos: docs/referencias/SINASC_Estrutura_2024.pdf (CGIAE) e Dicionario_SIM_2025.pdf; códigos: ficha 7c.0 (scripts citados lá)
VARS7 = [
    ("SINASC", "RACACORMAE", "Mother's race/skin color: 1 White (branca); 2 Black (preta); 3 Asian (amarela); 4 Brown (parda); 5 Indigenous (indígena)",
     "Tipo de raça e cor da mãe: 1– Branca; 2– Preta; 3– Amarela; 4– Parda; 5– Indígena.",
     "1 → White (reference); 4 → Brown; 2 → Black; 5 → Indigenous. Excluded at step 1 of the exclusion cascade: code 3, "
     "missing, and any code outside {1, 2, 4, 5}. Multiple imputation (sensitivity): missing values imputed over codes 1–5 by "
     "multinomial logistic regression; births imputed as code 3 excluded.",
     "Exclusion; exposure; sensitivity (multiple imputation)"),
    ("SINASC", "SEMAGESTAC", "Number of weeks of gestation", "Número de semanas de gestação.",
     "Completed weeks. Inclusion: 22–44 (missing or outside the range excluded). Preterm birth: <37. SGA: eligible 24–42 "
     "(gestational age in days = 7×weeks + 3; +0 and +6 in sensitivity analyses). Weight >P97 reclassification: singleton "
     "preterm births 24–36. Low birth weight at term: 37–41.",
     "Exclusion; outcome (preterm birth); SGA eligibility; sensitivity"),
    ("SINASC", "TPMETESTIM", "Method used [to estimate gestational age]: 1 physical exam; 2 other method; 9 unknown",
     "Método utilizado. Valores: 1– Exame físico; 2– Outro método; 9– Ignorado.",
     "8 (not in the data dictionary) → last menstrual period (LMP); 1 or 2 → other method (the Live Birth Declaration manual "
     "records ultrasound as 'other method'); 9 or missing → unknown. Codes 1 and 2 also analyzed separately. Empirical evidence "
     "for code 8: " + EV8 + ".",
     "Dating diagnostics (strata by method; dating-robust analysis = codes 1–2 excluding preterm weight >P97); Table 1"),
    ("SINASC", "DTULTMENST", "Date of last menstrual period (LMP): dd mm yyyy", "Data da última menstruação (DUM): dd mm aaaa",
     "Valid = an existing date (ddmmyyyy) earlier than DTNASC, with an interval ≤365 days. LMP-based gestational age = "
     "floor((DTNASC − DTULTMENST)/7) completed weeks. Not used in any model.",
     "Validation of TPMETESTIM code 8 only"),
    ("SINASC", "STTRABPART", "Labor induced? 1 yes; 2 no; 3 not applicable; 9 unknown",
     "Trabalho de parto induzido? Valores: 1– Sim; 2– Não; 3– Não se aplica; 9– Ignorado.",
     REGRA + " STTRABPART 3, 9, or missing → unclassified unless cesarean with STCESPARTO 1.",
     "Outcome (spontaneous vs provider-initiated preterm birth)"),
    ("SINASC", "STCESPARTO", "Did the cesarean occur before labor started? 1 yes; 2 no; 3 not applicable; 9 unknown",
     "Cesárea ocorreu antes do trabalho de parto iniciar? Valores: 1– Sim; 2– Não; 3– Não se aplica; 9– Ignorado.",
     "Used only for cesareans (PARTO 2): 1 → provider-initiated; 2 → spontaneous if STTRABPART 2; 3, 9, or missing → "
     "unclassified unless STTRABPART 1. Not used for vaginal births (missing for nearly all vaginal births in 2015; code 3 recorded "
     "from 2016).",
     "Outcome (classification)"),
    ("SINASC", "PARTO", "Type of delivery: 1 vaginal; 2 cesarean; 9 unknown", "Tipo de parto: 1– Vaginal; 2– Cesário; 9– Ignorado",
     "1 (vaginal) and 2 (cesarean) in the classification rule (see STTRABPART); 9 or missing → unclassified unless STTRABPART 1. "
     "Table 1: mode of delivery (1, 2).",
     "Outcome (classification); Table 1"),
    ("SINASC", "MESPRENAT", "Month of gestation in which prenatal care started", "Mês de gestação em que iniciou o pré‐natal",
     "Valid 1–9; 99, missing, and any other value excluded from numerator and denominator. Access index = % of live births with "
     "MESPRENAT 1–3 among those with valid MESPRENAT, by health region of residence × year, over all resident live births "
     "2014–2024; each birth receives the index of year t−1; tertiles within macroregion, weighted by births (T1 = worst "
     "access). Table 1: 1–3, 4–6, 7–9 = 1st, 2nd, 3rd trimester.",
     "Exposure (access index and tertiles); Table 1"),
    ("SINASC", "GRAVIDEZ", "Type of pregnancy: 1 single; 2 twin; 3 triplet or more; 9 unknown",
     "Tipo de gravidez: 1– Única; 2– Dupla; 3– Tripla ou mais; 9– Ignorado.",
     "1 → singleton; 2–3 → multiple; 9 or missing → missing. SGA, weight >P97 reclassification, and low birth "
     "weight at term restricted to GRAVIDEZ 1.",
     "SGA eligibility; sensitivity"),
    ("SINASC", "SEXO", "Sex: 1 M male; 2 F female; 0 I unknown", "Sexo: 1- M – Masculino; 2- F – Feminino; 0- I – ignorado",
     "1 → male, 2 → female (sex-specific INTERGROWTH-21st centiles); 0 or missing → not eligible for SGA or the weight "
     ">P97 criterion (not imputed).",
     "SGA; sensitivity"),
    ("SINASC", "PESO", "Birth weight in grams", "Peso ao nascer em gramas.",
     "Valid 100–7,000 g for SGA and weight plausibility. SGA = INTERGROWTH-21st weight-for-gestational-age centile <0.10 (R "
     "package gigs, value2centile, family ig_nbs, acronym wfga). Weight >P97 = centile >0.97 among singleton preterm births "
     "24–36 weeks (reclassified as non-cases in sensitivity analyses); alternative criterion ≥2,500 g. Low birth weight at "
     "term: <2,500 g (singletons, 37–41 weeks).",
     "Outcome (SGA); sensitivity"),
    ("SINASC", "ESCMAE", "Schooling, in completed years of study: 1 none; 2 1–3 years; 3 4–7 years; 4 8–11 years; 5 12 or more; 9 unknown",
     "Escolaridade, em anos de estudo concluídos: 1 – Nenhuma; 2 – 1 a 3 anos; 3 – 4 a 7 anos; 4 – 8 a 11 anos; 5 – 12 e mais; 9 – Ignorado.",
     "Inclusion: 1–5 (9 or missing excluded). Model M3: five categories (reference ≥12). MAIHDA strata and race × "
     "education (exploratory): ≤7 (codes 1–3), 8–11 (4), ≥12 (5). ESCMAE2010 not used.",
     "Exclusion; covariate (M3); MAIHDA strata; imputation model"),
    ("SINASC", "ESTCIVMAE", "Mother's marital status: 1 single; 2 married; 3 widowed; 4 legally separated/divorced; 5 stable union; 9 unknown",
     "Situação conjugal da mãe: 1– Solteira; 2– Casada; 3– Viúva; 4– Separada judicialmente/divorciada; 5– União estável; 9– Ignorada.",
     "With partner = 2 or 5 (reference); without partner = 1, 3, or 4; 9 or missing → missing (M3 fitted in complete cases; "
     "separate 'missing' category in the imputation model).",
     "Covariate (M3); imputation model"),
    ("SINASC", "IDADEMAE", "Mother's age", "Idade da mãe",
     "Inclusion: 10–60 years (missing, <10, >60, and code 99 excluded). Groups: <20; 20–34 (reference); ≥35.",
     "Exclusion; covariate (M2, M3); MAIHDA strata"),
    ("SINASC", "CODMUNRES", "IBGE code of the municipality of residence", "Código IBGE do município de residência",
     "6 digits in the data. 1st digit → macroregion (1 North, 2 Northeast, 3 Southeast, 4 South, 5 Center-West); first 2 digits "
     "→ state; municipality → health region (DATASUS territorial base, December 2024; 433 regions). Codes ending in 0000 "
     "(unknown municipality; 533 births in the analytic sample) have no health region: excluded from tertile analyses, one cluster "
     "per state in the other models.",
     "Exposure unit (health region); covariate (macroregion); variance clustering; sensitivity (excluding CE and DF)"),
    ("SINASC", "DTNASC", "Date of birth: dd mm yyyy", "Data de nascimento: dd mm aaaa",
     "Year of birth (= year of the file) → year (categorical covariate, reference 2015) and period (2015–2019, 2020–2021, "
     "2022–2024); timing of the 1-year lag of the access index; LMP-based gestational age (with DTULTMENST).",
     "Covariate (year); exposure timing; validation"),
    ("SINASC", "CONSULTAS", "Number of prenatal visits: 1 none; 2 1–3; 3 4–6; 4 7 or more; 9 unknown",
     "Número de consultas de pré‐natal. Valores: 1– Nenhuma; 2– de 1 a 3; 3– de 4 a 6; 4– 7 e mais; 9– Ignorado.",
     "Table 1: 1 → 0, 2 → 1–3, 3 → 4–6, 4 → ≥7 visits. Validity check of the access index: % with code 4 "
     "among codes 1–4, by health region × year (Spearman correlation with the index).",
     "Description (Table 1); validation of the access index"),
    ("SINASC", "TPROBSON", "Robson group code, generated by the system", "Código do Grupo de Robson, gerado pelo sistema",
     "Not used in the outcome definitions. Tabulated by spontaneous/provider-initiated classification and race (validation); group 11 "
     "(not documented in the data structure) counted as unknown in the missing-data table.",
     "Validation; missing-data description"),
    ("SIM", "TIPOBITO", "Type of death: 1 fetal; 2 non-fetal", "Tipo do óbito: 1-Fetal; 2-Não Fetal",
     "1 → fetal death. Fetal death = TIPOBITO 1 AND (valid SEMAGESTAC ≥22 OR [SEMAGESTAC missing, 9, or 99 AND GESTACAO "
     "2–6] OR PESO ≥500 g); the three criteria are combined with OR.",
     "Live-birth bounds (fetal deaths, 2015–2024)"),
    ("SIM", "SEMAGESTAC", "Number of weeks of gestation (two digits; 9 unknown)",
     "Nº de semanas de gestação: números com dois algarismos; 9 - ignorado",
     "9 and 99 treated as missing. Fetal-death criterion: ≥22. q for preterm birth = proportion <37 among fetal deaths with "
     "SEMAGESTAC 22–44; q for SGA restricted to 24–42 (INTERGROWTH-21st grid).",
     "Live-birth bounds"),
    ("SIM", "GESTACAO", "Weeks of gestation (old form): 1 <22; 2 22–27; 3 28–31; 4 32–36; 5 37–41; 6 ≥42",
     "Semanas de gestação (formulário antigo): 1 - Menos de 22 semanas; 2 - 22 a 27 semanas; 3 - 28 a 31 semanas; "
     "4 - 32 a 36 semanas; 5 - 37 a 41 semanas; 6 - 42 e + semanas",
     "Used only when SEMAGESTAC is missing, 9, or 99: 2–6 → fetal death.",
     "Live-birth bounds (fetal death definition)"),
    ("SIM", "PESO", "Birth weight in grams", "Peso ao nascer em gramas",
     "≥500 g → fetal death (OR with the gestational age criteria); 100–7,000 g required for the SGA grid (q for SGA = "
     "proportion with centile <0.10 among singleton fetal deaths 24–42 weeks with sex 1 or 2).",
     "Live-birth bounds"),
    ("SIM", "SEXO", "Sex: M,1 male; F,2 female; I,0,9 unknown", "Sexo: M,1 – masculino; F,2 – feminino; I,0,9 - ignorado",
     "M \u2192 1, F \u2192 2; I, 0, and 9 \u2192 missing; only 1 and 2 match the INTERGROWTH-21st grid. In 2015\u20132024 the field holds only codes "
     "0, 1, and 2 (no letter codes), so the recoding does not change q for SGA.",
     "Live-birth bounds (q for SGA)"),
    ("SIM", "GRAVIDEZ", "Type of pregnancy: 1 single; 2 twin; 3 triplet or more; 9 unknown",
     "Tipo de gravidez: 1 – única; 2 – dupla; 3 – tripla e mais; 9 – ignorada",
     "1 → singleton (q for SGA).", "Live-birth bounds (q for SGA)"),
    ("SIM", "CODMUNRES", "Municipality of residence code (for fetal deaths, the mother's residence)",
     "Código do município de residência. Em caso de óbito fetal, considerar o município de residência da mãe",
     "1st digit → macroregion, for fetal death ratios by macroregion × year (descriptive).", "Live-birth bounds (description)"),
]
S7A = pd.DataFrame(VARS7, columns=["System", "Variable", "Official label (English translation)", "Official label (Portuguese, data dictionary)",
                                   "Codes used and recoding in this study", "Use"])
S7A.to_csv(B.SUPD / f"S7a_variables_codes_{B.V}.csv", index=False)
ROD7A = (B.NOTE_BROWN + " Official labels from the SINASC data structure (Ministry of Health, CGIAE, 2024) and the SIM data dictionary "
         "(updated June 2025), translated; the Portuguese originals are in the CSV version of this table. Codes as implemented in the "
         "analysis scripts. Exclusion cascade (sequential): race/skin color, gestational age, education, maternal age. SINASC: Live "
         "Birth Information System; SIM: Mortality Information System; LMP: last menstrual period; SGA: small for gestational age.")
ital = lambda t: (t.replace("(parda)", "(<i>parda</i>)").replace("(preta)", "(<i>preta</i>)").replace("(branca)", "(<i>branca</i>)")
                  .replace("(indígena)", "(<i>indígena</i>)").replace("(amarela)", "(<i>amarela</i>)"))
html = [B.HTML_CSS + "<style>@page{size:A4 landscape}</style>", "<h1>Online Resource 2. Variables and codes (RECORD 6.1), operational definitions, and the gestational age "
        "estimation method code 8</h1>", "<h2>Table S7a. Variables and codes</h2>",
        "<table><colgroup><col style='width:6%'><col style='width:10%'><col style='width:22%'><col style='width:44%'><col style='width:18%'></colgroup>"
        "<tr><th>System</th><th>Variable</th><th>Official label</th><th>Codes used and recoding in this study</th><th>Use</th></tr>"]
for r in VARS7:
    html.append(f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{ital(r[2])}</td><td>{r[4]}</td><td>{r[5]}</td></tr>")
html.append(f"</table><p class='note'>{ital(ROD7A)}</p>")
html += ["<h2>Table S7b. Operational definitions of derived variables</h2>",
         "<table><tr><th>Variable</th><th>Type</th><th>Operational definition</th></tr>"]
DIC_EN = [  # tradução fiel de dicionario_variaveis_v3 (mesma ordem; conferida em etapa7b_checa)
    ("CODMUNRES..PESO, SEXO", "raw", "18 SINASC fields + SEXO (1 male, 2 female, 0 unknown); integers, original codes preserved"),
    ("cod_uf, uf, regiao", "derived", "first 2 digits of CODMUNRES (state); macroregion from the 1st digit (N, NE, SE, S, CO)"),
    ("ano", "partition", "year of DTNASC (= year of the file)"),
    ("periodo", "derived", "2015–2019 / 2020–2021 / 2022–2024"),
    ("incl", "derived", "analytic sample (race/skin color 1/2/4/5; SEMAGESTAC 22–44; ESCMAE 1–5; IDADEMAE 10–60)"),
    ("raca", "derived", "White (1), Brown (4), Black (2), Indigenous (5); missing otherwise"),
    ("ptb", "outcome", "SEMAGESTAC < 37; missing if SEMAGESTAC missing"),
    ("ptb_sub", "outcome", "<28 extremely; 28–31 very; 32–36 moderate/late; ≥37 term or post-term"),
    ("ptb_tipo", "outcome", "only if ptb = 1. Provider-initiated = STTRABPART 1 (induced) or (PARTO 2 [cesarean] and STCESPARTO 1 "
                            "[before labor]); spontaneous = STTRABPART 2 and (PARTO 1 [vaginal] or (PARTO 2 and STCESPARTO 2)); "
                            "unclassified = otherwise"),
    ("lbw_termo", "outcome", "PESO < 2,500 g; singletons (GRAVIDEZ 1), SEMAGESTAC 37–41, PESO 100–7,000"),
    ("unica", "derived", "GRAVIDEZ 1 = 1; 2/3 = 0; 9/missing = missing"),
    ("pig_elegivel", "derived", "singleton, SEMAGESTAC 24–42, SEXO 1/2, PESO 100–7,000"),
    ("pig", "outcome", "INTERGROWTH-21st weight-for-gestational-age centile < 0.10 (R package gigs); GA in days = 7×weeks + 3; "
                       "eligible births only"),
    ("pig_k0, pig_k6", "sensitivity", "same with GA in days = 7×weeks + 0 and + 6"),
    ("pig_tabela_oficial", "sensitivity", "PESO < P10 of the official INTERGROWTH-21st PDF tables (weeks + 3 days)"),
    ("idade_cat", "derived", "<20; 20–34 (reference); ≥35 (ages 10–60)"),
    ("esc_cat", "derived", "ESCMAE 1 none; 2 1–3 years; 3 4–7; 4 8–11; 5 ≥12; 9/missing = missing"),
    ("estciv_cat", "derived", "with partner = married (2) or stable union (5); without = single (1), widowed (3), separated (4); "
                              "9/missing = missing"),
    ("TPMETESTIM", "raw", "1 physical exam; 2 other method; 9 unknown (data dictionary); 8 = undocumented, present in 100% of records "
                          "with a valid LMP date → GA from the LMP"),
    ("CO_REGSAUD", "derived", "health region (CIR), DATASUS territorial base Dec 2024, fixed for 2015–2024; missing for codes UF+0000"),
    ("ptb_esp", "outcome", "1 spontaneous PTB; 0 term or provider-initiated PTB; missing if PTB unclassified"),
    ("ptb_ind", "outcome", "1 provider-initiated PTB; 0 term or spontaneous PTB; missing if PTB unclassified"),
    ("ig_metodo", "derived", "LMP (TPMETESTIM 8) / other method (1, 2) / unknown (9 or missing)"),
    ("access index, tertile", "derived", "% of live births to residents with prenatal care initiated in months 1–3 (MESPRENAT 1–3) among "
                                         "records with valid MESPRENAT (1–9), by health region and year, assigned with a 1-year lag (t−1); tertiles within each macroregion over health "
                                         "region × year, weighted by births; T1 = worst access"),
]
assert [v for v, _, _ in DIC_EN[:-1]] == dic.variavel.tolist()
for v, tp_, df_ in DIC_EN:
    html.append(f"<tr><td>{v}</td><td>{tp_}</td><td>{df_}</td></tr>")
html.append("</table><p class='note'>" + ital(B.NOTE_BROWN) + " Operational definitions as implemented in the analysis scripts (source: "
            "dicionario_variaveis_v3, translated; access index: scripts/etapa2_03_indice_acesso.py and etapa3_01_tercis_regiao.py).</p>")
html.append("<h2>Gestational age estimation method (TPMETESTIM): code 8</h2>"
            "<p>The publicly available SINASC data dictionaries we consulted (CGIAE structure files 1996–2019 and 2024; Live Birth "
            "Declaration filling manual, 4th ed., 2022) list only codes 1 (physical exam), 2 (other method), and 9 (unknown); code 8 is "
            "not described in the publicly available SINASC data dictionaries we consulted. Empirical evidence that code 8 identifies "
            "births with a reported last menstrual period (LMP):</p><ul>"
            f"<li>Code 8 first appears in {int(p13.ano)}; that year, the {B.n_(p13.n)} records with code 8 are exactly the "
            f"{B.n_(p13.n_dtultmenst)} records with a filled LMP date (DTULTMENST).</li>"
            f"<li>2015–2024 analytic sample: a valid LMP date is present in {c8.pct_dum_valida:.3f}% of code-8 records and in 0% of "
            "records with codes 1, 2, or 9.</li>"
            f"<li>Among code-8 records, gestational age computed from the LMP (floor of days/7) agrees with SEMAGESTAC exactly in "
            f"{c8.pct_exata:.1f}% and within ±1 week in {c8.pct_pm1:.2f}% (mean difference {B.num(c8.dif_media)} weeks; SD {c8.dif_dp:.2f}).</li>"
            "<li>The Live Birth Declaration manual instructs that weeks and estimation method be filled only when the LMP is unknown, and "
            "that ultrasound be recorded as 'other method'.</li></ul>"
            "<p class='note'>Sources: tab_e6_02a_concordancia, tab_e6_02b_tpmetestim_2010_2014; documentation search in "
            "docs/referencias/tpmetestim_codigo8_busca_v1_20261008.md.</p>")
S7_HTML = "\n".join(html)
B.html_pdf(S7_HTML, B.SUPD / f"S7_variables_codes_{B.V}.pdf")
pd.DataFrame(DIC_EN, columns=["Variable", "Type", "Operational definition"]).to_csv(B.SUPD / f"S7b_dictionary_{B.V}.csv", index=False)

# ---------- S8 STROBE + RECORD (esqueleto a partir do checklist RECORD oficial, CC BY)
dd = docx.Document(B.PROJ / "docs/referencias/RECORD_checklist_acesso20261009.docx")
rows, secao = [], ""
for t in dd.tables:
    for r in t.rows:
        cel = [c.text.strip().replace("\n", " ") for c in r.cells]
        u = list(dict.fromkeys(cel))
        if len(u) == 1 or (len(u) == 2 and u[0] == ""):
            secao = u[-1]
            continue
        if cel[0] == "" and cel[1] == "Item No.":
            continue
        rows.append({"Section": secao, "Topic": cel[0], "STROBE item": cel[1], "STROBE recommendation": cel[2],
                     "RECORD item": cel[4] if len(cel) > 4 else "", "Page/location in manuscript": ""})
S8 = pd.DataFrame(rows)
S8.to_csv(B.SUPD / f"S8_strobe_record_checklist_{B.V}.csv", index=False)
h = [B.HTML_CSS, "<h1>Online Resource 1 (S8). STROBE and RECORD checklist</h1>",
     "<p class='note'>Items reproduced from the RECORD checklist (Benchimol et al., PLoS Med 2015; CC BY), which includes the STROBE "
     "items. Location column completed from the final manuscript (etapa7d_01_montagem.py; Submissao/ESM_1.pdf).</p><table><tr><th>Section</th><th>Topic</th><th>Item</th>"
     "<th>STROBE recommendation</th><th>RECORD item</th><th>Page/location</th></tr>"]
for _, r in S8.iterrows():
    h.append(f"<tr><td>{r.Section}</td><td>{r.Topic}</td><td>{r['STROBE item']}</td><td>{r['STROBE recommendation']}</td>"
             f"<td>{r['RECORD item']}</td><td></td></tr>")
h.append("</table>")
B.html_pdf("\n".join(h), B.SUPD / f"S8_strobe_record_checklist_{B.V}.pdf")

# ---------- ESM_4.xlsx (7d: Online Resource 4; S1–S6 com a S3b, sem S5b) e cópia do xlsx de trabalho
B.grava_xlsx(XL, B.SUPD / f"ESM_4_tables_S1_S6_{B.V}.xlsx")

# ---------- disponibilidade de dados e código (Etapa 7c.1)
def ver(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, shell=True).stdout.strip()


import importlib
PYMODS = {"pandas": "pandas", "numpy": "numpy", "scipy": "scipy", "statsmodels": "statsmodels", "patsy": "patsy", "pyarrow": "pyarrow",
          "duckdb": "duckdb", "scikit-learn": "sklearn", "matplotlib": "matplotlib"}
pyv = {k: importlib.import_module(m).__version__ for k, m in PYMODS.items()}
RPKG = ["lme4", "data.table", "MASS", "gigs", "growthstandards", "arrow"]          # pacotes carregados pelos scripts .R (nnet não é usado)
rv = ver("Rscript -e 'cat(R.version.string); for(p in c(" + ",".join(f'\"{p}\"' for p in RPKG) +
         ")) cat(\"\\n\", p, packageDescription(p)$Version)'")
assert all(p in rv for p in RPKG), rv
acc = (B.PROJ / "docs/referencias/censo2022/ACESSO.txt").read_text().strip().splitlines()
ter = (B.PROJ / "docs/referencias/territorio_dez24/ACESSO.txt").read_text().strip().splitlines()
aps = (B.PROJ / "docs/referencias/aps_cobertura_ab/ACESSO.txt").read_text().strip().splitlines()   # Etapa 8 (etapa8_01)
aps_tot = re.match(r"Total: 27 UFs; ([\d,]+) registros; ([\d,]+) municípios", aps[3]).groups()
aps_dia = sorted({l[:10] for l in aps[5:] if re.match(r"\d{4}-\d{2}-\d{2} ", l)})
assert len(aps_dia) == 1, aps_dia
# 7c.2: datas = metadado das cópias locais do hub CliMaterna (sinasc_2014–2022: 2026-03-06; 2023: 2026-03-25; 2024: 2026-06-27; ficha 7c.0,
# pergunta 17), não datas de publicação pelo DATASUS; conferência independente por UF em 2026-10-02 (diferença 0)
GITHUB = "[URL after the repository is created and tagged]"
ETAPA = "Etapa 7d: montagem da Submissao (pacote v15)"
txt = f"""# Data and code availability (draft, package {B.V}, Etapa 7d)

## Sources (RECORD 1.3, 12.1)
- **SINASC live birth microdata, 2015–2024** (plus 2014 for the lagged access index; Ministry of Health, SVSA/DAENT/CGIAE; distributed
  by DATASUS). Files by state of residence (DNRES), documented path `ftp://ftp.datasus.gov.br/dissemin/publicos/SINASC/1996_/Dados/DNRES/`
  (files DN{{UF}}{{YYYY}}.dbc); 2024 from the national file (DNBR2024). The analyses used final-release national files obtained via the
  CliMaterna data hub (Torezzan et al., Data Brief 2025;62:111920; doi:10.1016/j.dib.2025.111920), whose local copies are dated March 6,
  2026 (2014–2022), March 25, 2026 (2023), and June 27, 2026 (2024), and verified against an independent download from the DATASUS server
  on October 2, 2026 (identical record counts by state and year; all files from the final, non-preliminary directory).
- **SIM fetal deaths (SIM-DOFET), 2015–2024**, for the live-birth bounds: DATASUS, `ftp://ftp.datasus.gov.br/dissemin/publicos/SIM/CID10/DOFET/`
  (files DOFET{{YY}}.dbc, final directory); downloaded on 2026-10-02.
- **Health regions (territorial base, December 2024)**: {ter[1].replace('FTP datado', 'FTP file dated') if len(ter) > 1 else ''}; accessed {ter[0].replace('acesso: ', '')}; {ter[2] if len(ter) > 2 else ''}.
- **Primary health care coverage, 2014–2020** (Ministry of Health, public report "Cobertura da Atenção Básica (2007 - 2020)",
  https://relatorioaps.saude.gov.br/cobertura/ab), for the sensitivity analysis in Table S2b: municipal monthly coverage queried through
  the report's own interface (`https://relatorioaps-prd.saude.gov.br/cobertura/ab`, municipal level, January 2014 to December 2020, one
  query per state) on {aps_dia[0]}; {aps_tot[0]} records ({aps_tot[1]} municipalities); sizes and MD5 of the 27 files in
  docs/referencias/aps_cobertura_ab/ACESSO.txt.
- **IBGE 2022 Census, SIDRA table 9605** (resident population by color or race, municipality level): {acc[0].replace('URL: ', '')}; accessed {acc[1].replace('acesso: ', '')}; {acc[3] if len(acc) > 3 else ''}.
- **INTERGROWTH-21st newborn size standards** (birth weight centiles): R package gigs; official tables (grow_*_bw_table.pdf) downloaded on 2026-10-08 for validation.
- **Data dictionaries**: SINASC data structure (CGIAE, 2024) and SIM data dictionary (updated June 2025), accessed 2026-10-08; variables
  and codes in Online Resource 2 (Table S7a, RECORD 6.1).

## Eligibility (STROBE 6a)
- Births to mothers of Asian (amarela) race/skin color were {JUST_AM} ({PCT_AM:.2f}% = {N_AM:,} / {N_FONTE:,} live births to residents,
  2015–2024; Table S1; tab07_fluxograma_motivos, tab06_fluxograma_regiao).

## Software
- Python {platform.python_version()}: """ + ", ".join(f"{k} {v}" for k, v in pyv.items()) + f"""
- {rv.splitlines()[0] if rv else 'R'}: """ + ", ".join(x.strip() for x in rv.splitlines()[1:]) + f"""
- Own implementations (no external package): aggregated Poisson estimation with cluster-robust variance and marginal standardization
  (scripts/etapa1_lib.py); interaction contrasts (scripts/etapa3_lib.py); multinomial logit by Newton–Raphson (scripts/etapa6_lib.py,
  fit_mnl; validated against statsmodels MNLogit in scripts/etapa7c1_01_valida_mnl.py); MAIHDA AUC and its DeLong confidence interval
  (scripts/etapa5_02_maihda.R; the pROC package is not used).
- Analysis code: local git repository, to be deposited at {GITHUB}. Reference version of the analyses and of this package: the commit
  "{ETAPA}" (its hash is given by `git log --grep "^Etapa 7d:"`; a file cannot contain the hash of the commit that adds it).
  Commit 173fecd, cited in earlier drafts, is the Etapa 7b.2 commit (package v3), not the reference version.

## Draft statement (English)
> Data availability: This study used de-identified, publicly available data from the Brazilian Live Birth Information System
> (SINASC) and Mortality Information System (SIM), distributed by DATASUS, Ministry of Health of Brazil, the Ministry of Health primary
> health care coverage report (Cobertura da Atenção Básica, 2007–2020), and the 2022 Census of the
> Brazilian Institute of Geography and Statistics (IBGE, SIDRA table 9605). The data can be obtained from these sources without
> restriction. Aggregated tables underlying the results are provided in the Online Resources. The analysis code (Python and R) will
> be deposited at {GITHUB} upon publication.

Ethics: secondary analysis of public-domain, de-identified data (Brazilian National Health Council Resolution 510/2016) — wording to be confirmed by the authors.
"""
(B.MS / "data_code_availability.md").write_text(txt)
# 7c.7: os PDFs do Chrome saem com com.apple.quarantine, que o exFAT guarda em ._*; dot_clean -m os remove (como o 04 faz em Submissao/)
subprocess.run(["dot_clean", "-m", str(B.SUPD)], check=True)
if list(B.SUPD.glob("._*")):                             # raise, e não assert (o python -O desliga assert)
    raise RuntimeError(f"._* em {B.SUPD}")
log(f"suplementar: {len(SUPT)} tabelas; S7 (Online Resource 2: S7a variáveis e códigos, S7b dicionário, código 8) e S8 em PDF; "
    f"ESM_4 com {len(XL)} abas; disponibilidade gravada")
