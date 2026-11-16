"""
3.1 Tercis do índice de acesso (t−1) DENTRO de cada macrorregião.

Para cada macrorregião: pares (região de saúde, ano 2015–2024) ordenados pelo índice t−1, ponderados pelos
nascimentos da amostra analítica daquele par (sem os 533 de município ignorado); corte1 = menor índice com
fração acumulada ≥ 1/3; corte2 = idem ≥ 2/3. T1 = índice ≤ corte1 (pior acesso da região); T3 = > corte2.
Mesmo algoritmo da Etapa 2 (etapa2_03_indice_acesso.py), aplicado por região.
Saídas: data/processed/tercil_reg_regsaude_ano_v1 (par -> tercil_reg), tab_e3_01_tercis_regiao_cortes,
        tab_e3_01_n_casos_raca_tercil_regiao (com sinalização n < 1,000 ou casos < 50).
"""
import numpy as np
import pandas as pd

import etapa3_lib as T
import etapa0_lib as L

log = T.logger("01_tercis_regiao")
d = T.load(["CO_REGSAUD", "regiao", "raca", "ptb", "ptb_esp", "ptb_ind", "pig", "lbw_termo"])
ind = pd.read_csv(L.PROC / f"indice_acesso_regsaude_ano_v1_{L.STAMP}.csv", dtype={"CO_REGSAUD": str})
ind = ind[["CO_REGSAUD", "ano", "indice"]].assign(ano=lambda x: x.ano + 1).rename(columns={"indice": "indice_t1"})
d = d[d.CO_REGSAUD.notna()].merge(ind, on=["CO_REGSAUD", "ano"], how="left")
assert d.indice_t1.notna().all()
log("amostra com região de saúde", len(d))

cortes, mapa = [], []
for reg in L.REGIOES:
    w = d[d.regiao == reg].groupby(["CO_REGSAUD", "ano"]).agg(n=("raca", "size"), indice_t1=("indice_t1", "first")).reset_index()
    w = w.sort_values(["indice_t1", "CO_REGSAUD", "ano"]).reset_index(drop=True)
    cw = w.n.cumsum() / w.n.sum()
    c1 = w.indice_t1[cw >= 1 / 3].iloc[0]
    c2 = w.indice_t1[cw >= 2 / 3].iloc[0]
    w["tercil_reg"] = pd.cut(w.indice_t1, [-np.inf, c1, c2, np.inf], labels=["T1", "T2", "T3"]).astype(str)
    sh = w.groupby("tercil_reg").n.sum() / w.n.sum() * 100
    cortes.append(dict(regiao=reg, corte_T1_T2=c1, corte_T2_T3=c2, n_regioes_saude=w.CO_REGSAUD.nunique(), n_pares=len(w),
                       n_nasc=int(w.n.sum()), **{f"pct_nasc_{k}": v for k, v in sh.items()}))
    mapa.append(w[["CO_REGSAUD", "ano", "indice_t1", "tercil_reg"]].assign(regiao=reg))
    log(f"{reg}: T1 ≤ {c1:.3f} < T2 ≤ {c2:.3f} < T3; % nasc " + ", ".join(f"{k}={v:.2f}" for k, v in sh.items()))
C = pd.DataFrame(cortes)
C.to_csv(L.TAB / f"tab_e3_01_tercis_regiao_cortes_v1_{L.STAMP}.csv", index=False)
M = pd.concat(mapa)
M.to_csv(L.PROC / f"tercil_reg_regsaude_ano_v1_{L.STAMP}.csv", index=False)

d = d.merge(M[["CO_REGSAUD", "ano", "tercil_reg"]], on=["CO_REGSAUD", "ano"], how="left")
assert d.tercil_reg.notna().all()
rows = []
for desf in ["ptb", "ptb_esp", "ptb_ind", "pig", "lbw_termo"]:
    s = d[d[desf].notna()]
    g = s.groupby(["regiao", "raca", "tercil_reg"], observed=True)[desf].agg(["size", "sum"]).reset_index()
    g.columns = ["regiao", "raca", "tercil_reg", "n", "casos"]
    g.insert(0, "desfecho", desf)
    rows.append(g)
N = pd.concat(rows)
N["casos"] = N.casos.astype(int)
N["celula_pequena"] = (N.n < 1000) | (N.casos < 50)
N.to_csv(L.TAB / f"tab_e3_01_n_casos_raca_tercil_regiao_v1_{L.STAMP}.csv", index=False)
pq = N[N.celula_pequena]
log(f"células raça × tercil × região com n < 1,000 ou casos < 50: {len(pq)} de {len(N)} "
    f"({', '.join(sorted(set(pq.desfecho + ':' + pq.regiao.astype(str) + ':' + pq.raca.astype(str))))})")
