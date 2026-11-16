"""
6.5 Multiplicidade e hierarquia de todas as estimativas de interação reportadas (ICR e Wald), com EP agrupado por região
de saúde (Etapa 3 refeita com etapa3_02_knol.py --rs; 4.1c refeita aqui; 6.4 e 6.3 da Etapa 6).
Hierarquia (definida antes de olhar os q-valores):
  principal    — 3.2 raça × tercil de acesso dentro da região, desfechos pig, ptb, ptb_esp, ptb_ind (ICR das 3 raças × T1/T2
                 e Wald global por desfecho).
  secundária   — 3.3a índice contínuo, 3.3b tercil nacional, 3.6 limites (PTB sem classificação), 6.3 razão de RRR
                 T1/T3 (multinomial), 6.4 análise robusta à datação.
  exploratória — 3.3c (3.2 estratificado por macrorregião), 3.4 raça × região, 3.5 raça × idade / escolaridade / período,
                 lbw_termo (3.2), 4.1c raça × método da IG.
  Sensibilidades (Etapas 4, 4b, 6.1b, imputação múltipla) não entram como hipóteses: replicam a principal.
q-valor de Benjamini–Hochberg (1995) só dentro da família exploratória (ICR e Wald juntos).
Saída: tab_e6_05_multiplicidade.
"""
import numpy as np
import pandas as pd
from scipy import stats

import etapa1_lib as E
import etapa3_lib as T
import etapa4_lib as S4
import etapa6_lib as E6
import etapa0_lib as L

log = E6.logger("05_multiplicidade")
TB, S = L.TAB, L.STAMP
it = pd.read_csv(TB / f"tab_e3_02_interacao_rs_v1_{S}.csv")
wd = pd.read_csv(TB / f"tab_e3_02_wald_rs_v1_{S}.csv")
PRINC = {"pig", "ptb", "ptb_esp", "ptb_ind"}


def familia(analise, desf):
    if analise == "3.2_tercil_reg":
        return "principal" if desf in PRINC else ("secundaria" if desf.endswith(("_a", "_b")) else "exploratoria")
    if analise in ("3.3b_tercil_nac",):
        return "secundaria"
    return "exploratoria"


rows = []
for _, r in it.iterrows():
    fam = familia(r.analise, r.desfecho)
    if r.analise == "3.2_tercil_reg" and r.desfecho.endswith(("_a", "_b")):
        fam, an = "secundaria", "3.6_limites"
    else:
        an = r.analise
    rows.append(dict(familia=fam, analise=an, desfecho=r.desfecho, estrato=r.estrato, tipo="ICR", termo=f"{r.raca}×{r.nivel}",
                     estimativa=r.ICR_pp, lo=r.ICR_lo, hi=r.ICR_hi, p=r.ICR_p))
for _, r in wd.iterrows():
    fam = familia(r.analise, r.desfecho)
    an = r.analise
    if r.analise == "3.2_tercil_reg" and r.desfecho.endswith(("_a", "_b")):
        fam, an = "secundaria", "3.6_limites"
    rows.append(dict(familia=fam, analise=an, desfecho=r.desfecho, estrato=r.estrato, tipo="Wald", termo=f"χ²({r.gl})",
                     estimativa=r.chi2, lo=np.nan, hi=np.nan, p=r.p))
# 3.3a contínuo: interação por 5 p.p. do índice (RP); p pelo IC na escala log
ct = pd.read_csv(TB / f"tab_e3_03a_indice_continuo_rs_v1_{S}.csv").drop_duplicates(["desfecho", "raca"])
for _, r in ct.iterrows():
    se = (np.log(r.int_hi) - np.log(r.int_lo)) / (2 * E.Z)
    rows.append(dict(familia="secundaria" if r.desfecho in PRINC else "exploratoria", analise="3.3a_indice_continuo",
                     desfecho=r.desfecho, estrato="Brasil", tipo="RP_interacao_5pp", termo=f"{r.raca}×índice",
                     estimativa=r.RP_por_5pp_interacao, lo=r.int_lo, hi=r.int_hi, p=2 * stats.norm.sf(abs(np.log(r.RP_por_5pp_interacao) / se))))
# 6.4 robusta à datação
for _, r in pd.read_csv(TB / f"tab_e6_04_interacao_v1_{S}.csv").iterrows():
    rows.append(dict(familia="secundaria", analise="6.4_outro_sem_implausivel", desfecho=r.desfecho, estrato="Brasil", tipo="ICR",
                     termo=f"{r.raca}×{r.nivel}", estimativa=r.ICR_pp, lo=r.ICR_lo, hi=r.ICR_hi, p=r.ICR_p))
for _, r in pd.read_csv(TB / f"tab_e6_04_wald_v1_{S}.csv").iterrows():
    rows.append(dict(familia="secundaria", analise="6.4_outro_sem_implausivel", desfecho=r.desfecho, estrato="Brasil", tipo="Wald",
                     termo=f"χ²({r.gl})", estimativa=r.chi2, lo=np.nan, hi=np.nan, p=r.p))
# 6.3 razão de RRR T1/T3
for _, r in pd.read_csv(TB / f"tab_e6_03b_rrr_v1_{S}.csv").query("analise == 'razao_RRR_T1_vs_T3'").iterrows():
    se = (np.log(r.hi) - np.log(r.lo)) / (2 * E.Z)
    rows.append(dict(familia="secundaria", analise="6.3_multinomial_T1/T3", desfecho=f"ptb_{r.categoria}", estrato="Brasil",
                     tipo="razao_RRR", termo=f"{r.raca}×T1", estimativa=r.RRR, lo=r.lo, hi=r.hi, p=2 * stats.norm.sf(abs(np.log(r.RRR) / se))))
# 4.1c raça × método da IG (refeito com EP por região de saúde)
d = S4.carrega()
for desf in ["ptb", "ptb_esp", "ptb_ind", "pig", "lbw_termo"]:
    s = d[d[desf].notna()]
    c = E.agrega(s, desf, ["raca", "idade_cat", "ano", "regiao", "ig_metodo"])
    c["CODMUNRES"] = c.CODMUNRES.astype(str)
    r = T.knol(E6.para_rs(c), "ig_metodo", ["DUM", "outro_metodo", "ignorado"], "DUM", mod_main="C(ig_metodo, Treatment('DUM'))",
               rotulo="ig_metodo")
    for _, x in r["interacao"].iterrows():
        rows.append(dict(familia="exploratoria", analise="4.1c_raca_x_ig_metodo", desfecho=desf, estrato="Brasil", tipo="ICR",
                         termo=f"{x.raca}×{x.nivel}", estimativa=x.ICR_pp, lo=x.ICR_lo, hi=x.ICR_hi, p=x.ICR_p))
    w = r["wald"].iloc[0]
    rows.append(dict(familia="exploratoria", analise="4.1c_raca_x_ig_metodo", desfecho=desf, estrato="Brasil", tipo="Wald",
                     termo=f"χ²({w.gl})", estimativa=w.chi2, lo=np.nan, hi=np.nan, p=w.p))
    log(f"4.1c {desf} (região de saúde): Wald χ² = {w.chi2:.1f}, p = {w.p:.2e}")
X = pd.DataFrame(rows)
X = X[X.p.notna()].copy()
ex = X.familia == "exploratoria"
pv = X.loc[ex, "p"].to_numpy()
m = len(pv)
o = np.argsort(pv)
q = np.empty(m)
q[o] = np.minimum.accumulate((pv[o] * m / np.arange(1, m + 1))[::-1])[::-1]
X.loc[ex, "q_BH"] = np.minimum(q, 1)
X.to_csv(TB / f"tab_e6_05_multiplicidade_v1_{S}.csv", index=False)
res = X.groupby(["familia", "tipo"]).agg(n=("p", "size"), p_lt_005=("p", lambda s: int((s < 0.05).sum())),
                                         q_lt_005=("q_BH", lambda s: int((s < 0.05).sum()) if s.notna().any() else np.nan)).reset_index()
log("resumo por família:\n" + res.to_string(index=False))
log(f"família exploratória: {m} testes; q < 0.05 em {int((X.q_BH < 0.05).sum())}; q < 0.10 em {int((X.q_BH < 0.10).sum())}")
pr = X[X.familia == "principal"]
log("principal:\n" + pr[["analise", "desfecho", "tipo", "termo", "estimativa", "lo", "hi", "p"]].round(4).to_string(index=False))
log("exploratória com q < 0.05:\n" + X[ex & (X.q_BH < 0.05)].sort_values("q_BH")[["analise", "desfecho", "estrato", "tipo", "termo",
                                                                                    "estimativa", "lo", "hi", "p", "q_BH"]].round(4).to_string(index=False))
