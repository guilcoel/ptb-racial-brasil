"""
8.3 Tercis de acesso para a sensibilidade da Etapa 8, nos nascimentos de 2015–2021 (a série oficial de cobertura vai até 2020):
  tercil_aps   — cobertura da Atenção Básica da região de saúde de residência no ano anterior (etapa8_02);
  tercil_ind21 — índice de pré-natal da Etapa 2 (etapa2_03, t−1), com os tercis RECALCULADOS em 2015–2021 (comparador).
Os dois com o algoritmo do etapa3_01_tercis_regiao.py: dentro de cada macrorregião, pares (região de saúde, ano) ordenados pelo
valor t−1 (desempate por região e ano), ponderados pelos nascimentos da amostra analítica do par; corte1 = menor valor com fração
acumulada ≥ 1/3; corte2 = idem ≥ 2/3; T1 = valor ≤ corte1 (pior acesso: menor cobertura ou menor índice); T3 = > corte2.
Conferência do algoritmo: aplicado ao índice em 2015–2024, reproduz o tercil_reg do etapa3_01 em todos os pares.
Amostra: amostra analítica de 2015–2021 com região de saúde (sem os nascimentos de município ignorado).
Descritivos: Spearman região × ano (t−1) da cobertura com o índice e com a população da região (média dos 12 meses, etapa8_02);
concordância dos tercis nos nascimentos (tabela cruzada; % na diagonal e kappa ponderado linear); distribuição de cada raça entre os
tercis; n e casos por macrorregião × raça × tercil (sinaliza n < 1,000 ou casos < 50).
Saídas: data/processed/tercil_aps_regsaude_ano_v1 (par → tercil_aps, tercil_ind21, agregado), tab_e8_03_cortes,
  tab_e8_03_concordancia (tabela cruzada), tab_e8_03_concordancia_resumo, tab_e8_03_spearman, tab_e8_03_raca_por_tercil,
  tab_e8_03_n_casos_raca_tercil.
Rodar da raiz: python3 scripts/etapa8_03_tercis.py
"""
import numpy as np
import pandas as pd
from scipy import stats

import etapa3_lib as T
import etapa0_lib as L

log = L.Logger("8_03_tercis", etapa="etapa8")
OUT = ["ptb", "ptb_esp", "ptb_ind", "pig"]
d0 = T.load(["CO_REGSAUD", "regiao", "raca"] + OUT)
d0 = d0[d0.CO_REGSAUD.notna()].copy()
d0["regiao"] = d0.regiao.astype(str)
ind = pd.read_csv(L.PROC / f"indice_acesso_regsaude_ano_v1_{L.STAMP}.csv", dtype={"CO_REGSAUD": str})
ind = ind[["CO_REGSAUD", "ano", "indice"]].assign(ano=lambda x: x.ano + 1).rename(columns={"indice": "indice_t1"})
cob = pd.read_csv(L.PROC / f"cobertura_ab_regsaude_ano_v1_{L.STAMP}.csv", dtype={"CO_REGSAUD": str})
cob = (cob[["CO_REGSAUD", "ano", "cobertura_ab", "pop_media"]].assign(ano=lambda x: x.ano + 1)
       .rename(columns={"cobertura_ab": "cob_t1", "pop_media": "pop_t1"}))
K = ["CO_REGSAUD", "ano"]


def tercis(d, col, nome):
    """= etapa3_01_tercis_regiao.py, para qualquer coluna de valor t−1."""
    cortes, mapa = [], []
    for reg in L.REGIOES:
        w = d[d.regiao == reg].groupby(K).agg(n=("raca", "size"), v=(col, "first")).reset_index()
        w = w.sort_values(["v", "CO_REGSAUD", "ano"]).reset_index(drop=True)
        cw = w.n.cumsum() / w.n.sum()
        c1 = w.v[cw >= 1 / 3].iloc[0]
        c2 = w.v[cw >= 2 / 3].iloc[0]
        w[nome] = pd.cut(w.v, [-np.inf, c1, c2, np.inf], labels=["T1", "T2", "T3"]).astype(str)
        sh = w.groupby(nome).n.sum() / w.n.sum() * 100
        cortes.append(dict(medida=nome, regiao=reg, corte_T1_T2=c1, corte_T2_T3=c2, n_regioes_saude=w.CO_REGSAUD.nunique(),
                           n_pares=len(w), n_nasc=int(w.n.sum()), **{f"pct_nasc_{k}": v for k, v in sh.items()}))
        mapa.append(w[K + [nome]])
    return pd.DataFrame(cortes), pd.concat(mapa)


# conferência: o algoritmo reproduz o tercil_reg do etapa3_01 (índice, 2015–2024)
_, chk = tercis(d0.merge(ind, on=K, how="left"), "indice_t1", "tercil_reg")
ref = pd.read_csv(L.PROC / f"tercil_reg_regsaude_ano_v1_{L.STAMP}.csv", dtype={"CO_REGSAUD": str})[K + ["tercil_reg"]]
cc = chk.merge(ref, on=K, how="outer", suffixes=("", "_e3"), indicator=True)
assert (cc._merge == "both").all() and (cc.tercil_reg == cc.tercil_reg_e3).all()
log(f"conferência: o algoritmo reproduz o tercil_reg do etapa3_01 nos {len(cc):,} pares de 2015–2024")

d = d0[d0.ano <= 2021].merge(cob, on=K, how="left").merge(ind, on=K, how="left")
assert d.cob_t1.notna().all() and d.indice_t1.notna().all()
log("amostra 2015–2021 com região de saúde", len(d))
Ca, Ma = tercis(d, "cob_t1", "tercil_aps")
Ci, Mi = tercis(d, "indice_t1", "tercil_ind21")
C = pd.concat([Ca, Ci])
C.to_csv(L.out_name("tab_e8_03_cortes"), index=False)
for r in C.itertuples():
    log(f"{r.medida} {r.regiao}: T1 ≤ {r.corte_T1_T2:.3f} < T2 ≤ {r.corte_T2_T3:.3f} < T3; % nasc "
        f"T1={r.pct_nasc_T1:.2f}, T2={r.pct_nasc_T2:.2f}, T3={r.pct_nasc_T3:.2f}")
M = Ma.merge(Mi, on=K, how="outer", validate="1:1")
assert M.notna().all().all()
pares = d.groupby(K).agg(cob_t1=("cob_t1", "first"), indice_t1=("indice_t1", "first"), pop_t1=("pop_t1", "first"),
                         n_nasc=("raca", "size")).reset_index()
M = M.merge(pares, on=K, how="left", validate="1:1")
M.to_csv(L.PROC / f"tercil_aps_regsaude_ano_v1_{L.STAMP}.csv", index=False)
d = d.merge(M[K + ["tercil_aps", "tercil_ind21"]], on=K, how="left")
assert d.tercil_aps.notna().all() and d.tercil_ind21.notna().all()

# Spearman região × ano (t−1), sem ponderação, Brasil e por macrorregião: cobertura × índice e cobertura × população da região
M["macro"] = M.CO_REGSAUD.str[0].map(L.REGIAO)
sp = []
for par, col in (("cobertura_x_indice", "indice_t1"), ("cobertura_x_populacao", "pop_t1")):
    for m, g in [("Brasil", M)] + list(M.groupby("macro")):
        r_ = stats.spearmanr(g.cob_t1, g[col])
        sp.append(dict(par=par, estrato=m, n_pares=len(g), rho=r_[0], p=r_[1]))
SP = pd.DataFrame(sp)
SP.to_csv(L.out_name("tab_e8_03_spearman"), index=False)
log("Spearman (t−1), região × ano 2015–2021: " + "; ".join(f"{r.par} {r.estrato} {r.rho:.3f}" for r in SP.itertuples()))

# concordância dos tercis nos nascimentos
ct = pd.crosstab(d.tercil_aps, d.tercil_ind21)
p = ct.to_numpy() / ct.to_numpy().sum()
i = np.arange(3)
w = 1 - np.abs(i[:, None] - i[None, :]) / 2
po, pe = (w * p).sum(), (w * np.outer(p.sum(1), p.sum(0))).sum()
kappa = (po - pe) / (1 - pe)
CT = (ct / ct.to_numpy().sum() * 100).reset_index().melt(id_vars="tercil_aps", var_name="tercil_ind21", value_name="pct_nasc")
CT["n_nasc"] = ct.reset_index().melt(id_vars="tercil_aps", value_name="n").n.to_numpy()
CT.to_csv(L.out_name("tab_e8_03_concordancia"), index=False)
pd.DataFrame([dict(n_nasc=int(ct.to_numpy().sum()), pct_diagonal=100 * np.trace(p), kappa_ponderado_linear=kappa,
                   pct_T1_aps_que_e_T1_indice=100 * ct.loc["T1", "T1"] / ct.loc["T1"].sum())]).to_csv(
    L.out_name("tab_e8_03_concordancia_resumo"), index=False)
log(f"concordância dos tercis (nascimentos): diagonal {100 * np.trace(p):.2f}%; kappa ponderado linear {kappa:.3f}; "
    f"T1 da APS que é T1 do índice: {100 * ct.loc['T1', 'T1'] / ct.loc['T1'].sum():.2f}%")

# distribuição de cada raça entre os tercis
rp = pd.concat([pd.crosstab(d.raca, d[c], normalize="index").mul(100).reset_index().assign(medida=c)
                .rename(columns={c: "x"}) for c in ("tercil_aps", "tercil_ind21")])
rp.columns.name = None
rp.to_csv(L.out_name("tab_e8_03_raca_por_tercil"), index=False)
log("raça por tercil (% da raça):\n" + rp.round(2).to_string(index=False))

rows = []
for desf in OUT:
    s = d[d[desf].notna()]
    g = s.groupby(["regiao", "raca", "tercil_aps"], observed=True)[desf].agg(["size", "sum"]).reset_index()
    g.columns = ["regiao", "raca", "tercil_aps", "n", "casos"]
    g.insert(0, "desfecho", desf)
    rows.append(g)
N = pd.concat(rows)
N["casos"] = N.casos.astype(int)
N["celula_pequena"] = (N.n < 1000) | (N.casos < 50)
N.to_csv(L.out_name("tab_e8_03_n_casos_raca_tercil"), index=False)
pq = N[N.celula_pequena]
log(f"células raça × tercil_aps × região com n < 1,000 ou casos < 50: {len(pq)} de {len(N)} "
    f"({', '.join(sorted(set(pq.desfecho + ':' + pq.regiao.astype(str) + ':' + pq.raca.astype(str))))})")
