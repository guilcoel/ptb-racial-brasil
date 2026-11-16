#!/usr/bin/env python3
"""Comparacao (pos-reproducao) dos resultados independentes com os arquivos do autor (Etapa 5).
Rodar so depois de audit_e5_maihda_v1_20261008.py. Somente agregados."""
import numpy as np, pandas as pd
from scipy.special import logit

BASE = "/Volumes/Forja/ptb-racial-brasil"; OUT = f"{BASE}/audit_independente/etapa5"; TAG = "v1_20261008"
import sys
SUF = sys.argv[1] if len(sys.argv) > 1 else ""   # "_antes" / "_depois"
import os
L = open(f"{OUT}/audit_e5_compara_log_{TAG}{SUF}.txt", "w")
def log0(*a): pass
def log(*a):
    s = " ".join(map(str, a)); print(s); L.write(s + "\n")

def norm(s):
    return (s.str.replace("le7", "Ate7", regex=False).str.replace("ge12", "12mais", regex=False)
             .str.replace("|lt20|", "|<20|", regex=False).str.replace("|ge35|", "|>=35|", regex=False)
             .str.replace("|20a34|", "|20-34|", regex=False))

me = pd.read_csv(f"{OUT}/audit_e5_predicoes_{TAG}.csv")
par = pd.read_csv(f"{OUT}/audit_e5_parametros_{TAG}.csv")
fx = pd.read_csv(f"{OUT}/audit_e5_efeitos_fixos_{TAG}.csv")
es = pd.read_csv(f"{BASE}/data/processed/maihda_estratos_{TAG}.csv"); es["k"] = norm(es.estrato)
au = pd.read_csv(f"{BASE}/outputs/tables/tab_e5_03_predicoes_{TAG}.csv"); au["k"] = norm(au.estrato)
top = pd.read_csv(f"{BASE}/outputs/tables/tab_e5_03_top15_{TAG}.csv"); top["k"] = norm(top.estrato)
mod = pd.read_csv(f"{BASE}/outputs/tables/tab_e5_02_modelos_{TAG}.csv")
fa = pd.read_csv(f"{BASE}/outputs/tables/tab_e5_02_fixos_m2_{TAG}.csv")

# 1. estratos
e = me.merge(es, left_on="estrato", right_on="k", suffixes=("", "_a"), how="outer", indicator=True)
log(f"[estratos] linhas casadas: {(e._merge=='both').sum()} / auditor {len(me)} / autor {len(es)}; "
    f"n diferente: {(e.n!=e.n_a).sum()}; casos diferentes: {(e.casos!=e.casos_a).sum()}; "
    f"N autor={es.n.sum()} casos autor={es.casos.sum()}")

# 2. parametros
rows = []
for nome, lin in [("M1", "M1 nulo"), ("M2", "M2 efeitos principais")]:
    a = mod[mod.modelo == lin].iloc[0]
    for K in (1, 25):
        m = par[(par.modelo == nome) & (par.nos == K)].iloc[0]
        rows.append(dict(modelo=nome, auditor=f"{'Laplace' if K==1 else 'AGHQ25'}",
                         s2_aud=m.s2, s2_autor=a.s2, dif_rel_s2_pct=100*(m.s2-a.s2)/a.s2,
                         VPC_aud=m.VPC_pct, VPC_autor=a.VPC_pct,
                         PCV_aud=m.PCV_pct if nome == "M2" else np.nan,
                         PCV_autor=a.PCV_pct, AUC_aud=m.AUC, AUC_autor=a.AUC,
                         AUC_lo_autor=a.AUC_lo, AUC_hi_autor=a.AUC_hi))
cp = pd.DataFrame(rows); cp.to_csv(f"{OUT}/audit_e5_compara_parametros_{TAG}{SUF}.csv", index=False)
log("\n[parametros]\n" + cp.to_string(index=False))

# efeitos fixos
ren = {"esc3le7": "esc3Ate7", "idade3ge35": "idade_cat>=35", "idade3lt20": "idade_cat<20",
       "tercilT1": "tercil_regT1", "tercilT2": "tercil_regT2"}
fa["termo2"] = fa.termo.replace(ren)
f2 = fx[(fx.modelo == "M2") & (fx.nos == 25)].merge(fa, left_on="termo", right_on="termo2", suffixes=("", "_a"))
log(f"\n[efeitos fixos M2] {len(f2)} termos casados; max |dif beta| AGHQ25 x autor = "
    f"{np.max(np.abs(f2.beta-f2.beta_a)):.2e}; max |dif OR| = {np.max(np.abs(f2.OR-f2.OR_a)):.2e}")
f1 = fx[(fx.modelo == "M2") & (fx.nos == 1)].merge(fa, left_on="termo", right_on="termo2", suffixes=("", "_a"))
log(f"[efeitos fixos M2] max |dif beta| Laplace(auditor) x autor = {np.max(np.abs(f1.beta-f1.beta_a)):.2e}")

# 3. predicoes
m = me.merge(au, left_on="estrato", right_on="k", suffixes=("", "_a"))
m["dif_p_pp"] = m.p_pct_M2 - m.p_pct
m["dif_p_pp_lap"] = m.p_pct_M2_laplace - m.p_pct
m["razao_u"] = m.u / m.u_modo_M2_laplace
m["razao_use"] = m.u_se / m.u_sd_M2
log(f"\n[predicoes M2, 540 estratos] max |dif p| AGHQ25 x autor = {m.dif_p_pp.abs().max():.3f} pp; "
    f"Laplace(auditor) x autor = {m.dif_p_pp_lap.abs().max():.3f} pp")
log(f"  razao u_autor/u_auditor(Laplace): media {m.razao_u.mean():.5f} dp {m.razao_u.std():.2e} "
    f"min {m.razao_u.min():.5f} max {m.razao_u.max():.5f}")
log(f"  razao u_se_autor/dp_post_auditor: media {m.razao_use.mean():.5f} dp {m.razao_use.std():.2e}")
log(f"  coerencia interna autor: max |logit(p)-xb-u| = "
    f"{np.max(np.abs(logit(m.p_pct/100) - m.xb_M2 - m.u)):.2e}")
log(f"  M1: max |p_M1 auditor - p_m1_pct autor| = {(m.p_pct_M1-m.p_m1_pct).abs().max():.4f} pp")
# correcao: o que daria o u do autor reescalado por 1/razao
m["p_autor_corr"] = 100 / (1 + np.exp(-(m.xb_M2 + m.u / m.razao_u.mean())))
log(f"  se u_autor for dividido pela razao media: max |dif p| x auditor Laplace = "
    f"{(m.p_autor_corr-m.p_pct_M2_laplace).abs().max():.4f} pp")
m.to_csv(f"{OUT}/audit_e5_compara_predicoes_{TAG}{SUF}.csv", index=False)

t_me = me.sort_values("p_pct_M2", ascending=False).head(15).reset_index(drop=True)
t_au = top[top.lista == "maior_risco"].reset_index(drop=True)
t = t_me[["estrato", "n", "casos", "pct_obs", "p_pct_M2"]].copy()
t["rank_aud"] = range(1, 16)
rank_aut = {k: i+1 for i, k in enumerate(au.sort_values("p_pct", ascending=False).k)}
t["rank_autor"] = t.estrato.map(rank_aut)
t = t.merge(au[["k", "p_pct", "u"]], left_on="estrato", right_on="k").drop(columns="k")
t["dif_pp"] = t.p_pct_M2 - t.p_pct
t.to_csv(f"{OUT}/audit_e5_compara_top15_{TAG}{SUF}.csv", index=False)
log("\n[top 15 auditor x autor]\n" + t.to_string(index=False))
so_aut = sorted(set(t_au.k) - set(t_me.estrato)); so_aud = sorted(set(t_me.estrato) - set(t_au.k))
log(f"  so no top15 do autor: {so_aut}\n  so no top15 do auditor: {so_aud}")
log(f"  mesma ordem? {list(t_au.k) == list(t_me.estrato)}")
L.close()
