"""
2.3 Índice de acesso ao pré-natal por região de saúde × ano.

índice(r, t) = % de nascidos vivos de mães residentes em r, no ano t, com MESPRENAT 1–3,
               entre os registros com MESPRENAT válido (1–9; 99, nulo e qualquer outro código ficam fora; nascimentos sem região de saúde ficam fora do índice)
Universo: TODOS os nascidos vivos residentes (brutos 2014–2024), não só a amostra analítica.
Cada nascimento de t recebe o índice de t−1 (2015 recebe 2014; o arquivo de 2014 tem MESPRENAT).
Tercis: cortes na distribuição conjunta (região de saúde × ano 2015–2024) do índice t−1, ponderada pelo
  número de nascimentos da amostra analítica (sem os 533 de município ignorado), de modo que cada tercil
  tenha ~1/3 dos nascimentos. T1 = pior acesso.
Sanidade: Spearman entre o índice e a % de 7+ consultas (CONSULTAS = 4 entre válidos 1–4) na mesma região-ano.
Saídas: data/processed/indice_acesso_regsaude_ano_v1 (índice por região-ano, agregado),
  tab_e2_03_* (completude, cortes, distribuição, composição, prevalências, spearman).
"""
import numpy as np
import pandas as pd
from scipy import stats

import etapa1_lib as E1
import etapa0_lib as L

log = L.Logger("03_indice_acesso", etapa="etapa2")
mp = pd.read_csv(L.PROC / f"municipio_regsaude_dez24_v1_{L.STAMP}.csv", dtype=str)
mp = dict(zip(mp.CODMUNRES, mp.CO_REGSAUD))


def num(s):
    if pd.api.types.is_float_dtype(s) or pd.api.types.is_integer_dtype(s):
        return s.astype("Int16")
    return pd.to_numeric(s.astype("string").str.strip().replace({"": pd.NA}), errors="raise").astype("Int16")


agg, comp = [], []
for y in range(2014, 2025):
    r = pd.read_parquet(L.RAW / f"sinasc_{y}.parquet", columns=["CODMUNRES", "MESPRENAT", "CONSULTAS"])
    cod = r.CODMUNRES.astype("string").str.strip()
    mes, con = num(r.MESPRENAT), num(r.CONSULTAS)
    d = pd.DataFrame({"CO_REGSAUD": cod.map(mp), "macro": cod.str.slice(0, 1).map(L.REGIAO),
                      "mes_valido": mes.between(1, 9).fillna(False), "tri1": mes.between(1, 3).fillna(False),
                      "mes_nulo": mes.isna(), "mes_99": (mes == 99).fillna(False),
                      "con_valido": con.between(1, 4).fillna(False), "con7": (con == 4).fillna(False)})
    d["ano"] = y
    c = d.groupby(["ano", "macro"])[["mes_valido", "mes_nulo", "mes_99"]].agg(["sum", "size"])
    comp.append(pd.DataFrame({"n": c[("mes_valido", "size")], "n_valido": c[("mes_valido", "sum")],
                              "n_nulo": c[("mes_nulo", "sum")], "n_99": c[("mes_99", "sum")]}).reset_index())
    g = d[d.CO_REGSAUD.notna()].groupby(["CO_REGSAUD", "ano"])
    agg.append(g[["mes_valido", "tri1", "con_valido", "con7"]].sum().join(g.size().rename("n_nasc")).reset_index())
    log(f"{y}: MESPRENAT válido {100 * d.mes_valido.mean():.2f}%", len(d))

A = pd.concat(agg)
A["indice"] = 100 * A.tri1 / A.mes_valido
A["pct_7cons"] = 100 * A.con7 / A.con_valido
A.to_csv(L.PROC / f"indice_acesso_regsaude_ano_v1_{L.STAMP}.csv", index=False)
C = pd.concat(comp)
Cb = C.groupby("ano")[["n", "n_valido", "n_nulo", "n_99"]].sum().reset_index().assign(macro="Brasil")
C = pd.concat([C, Cb])
C["pct_valido"] = (100 * C.n_valido / C.n).round(2)
C.to_csv(L.TAB / f"tab_e2_03_mesprenat_completude_v1_{L.STAMP}.csv", index=False)
log(f"índice: {len(A):,} região-anos; {A.CO_REGSAUD.nunique()} regiões; min/max = {A.indice.min():.1f}/{A.indice.max():.1f}; "
    f"região-anos com < 50 válidos: {int((A.mes_valido < 50).sum())}")

rho, p = stats.spearmanr(A.indice, A.pct_7cons)
rho_w = stats.spearmanr(A[A.ano >= 2015].indice, A[A.ano >= 2015].pct_7cons)[0]
pd.DataFrame([dict(spearman_rho_2014_2024=rho, p=p, n_regiao_anos=len(A), spearman_rho_2015_2024=rho_w)]).to_csv(
    L.TAB / f"tab_e2_03_spearman_indice_consultas_v1_{L.STAMP}.csv", index=False)
log(f"Spearman índice × % 7+ consultas: rho = {rho:.3f} (p = {p:.1e}, n = {len(A)})")

# atribuição t−1 à amostra analítica
d = pd.read_parquet(L.PROC / f"sinasc_brasil_2015_2024_v3_{L.STAMP}",
                    columns=["incl", "ano", "CO_REGSAUD", "regiao", "raca", "ptb", "ptb_esp", "ptb_ind", "pig"],
                    filters=[("incl", "==", True)])
d["ano"] = d.ano.astype(int)
d["CO_REGSAUD"] = d.CO_REGSAUD.astype(object)
prev = A[["CO_REGSAUD", "ano", "indice"]].assign(ano=lambda x: x.ano + 1).rename(columns={"indice": "indice_t1"})
d = d.merge(prev, on=["CO_REGSAUD", "ano"], how="left")
sem = d.indice_t1.isna()
log(f"amostra sem índice t−1: {int(sem.sum())} (sem região de saúde: {int(d.CO_REGSAUD.isna().sum())})")
assert int(sem.sum()) == int(d.CO_REGSAUD.isna().sum())

# tercis ponderados por nascimentos (amostra analítica)
w = d[~sem].groupby(["CO_REGSAUD", "ano"]).agg(n=("ptb", "size"), indice_t1=("indice_t1", "first")).reset_index()
w = w.sort_values("indice_t1")
cw = w.n.cumsum() / w.n.sum()
c1 = w.indice_t1[cw >= 1 / 3].iloc[0]
c2 = w.indice_t1[cw >= 2 / 3].iloc[0]
d["tercil"] = pd.cut(d.indice_t1, [-np.inf, c1, c2, np.inf], labels=["T1_pior", "T2", "T3_melhor"], right=True)
sh = d.tercil.value_counts(normalize=True).sort_index()
pd.DataFrame([dict(corte_T1_T2=c1, corte_T2_T3=c2, **{f"pct_nasc_{k}": 100 * v for k, v in sh.items()},
                   n_regiao_anos=len(w), regra="T1: índice ≤ corte1; T2: corte1 < índice ≤ corte2; T3: > corte2")]).to_csv(
    L.TAB / f"tab_e2_03_tercis_cortes_v1_{L.STAMP}.csv", index=False)
log(f"cortes: T1 ≤ {c1:.3f} < T2 ≤ {c2:.3f} < T3; % nascimentos {dict((k, round(100 * v, 2)) for k, v in sh.items())}")
d[["CO_REGSAUD", "ano", "indice_t1", "tercil"]].drop_duplicates().to_csv(
    L.PROC / f"tercil_regsaude_ano_v1_{L.STAMP}.csv", index=False)

# distribuição do índice por macrorregião e ano (região-anos ponderados por nascimentos residentes)
A["macro"] = A.CO_REGSAUD.str.slice(0, 1).map(L.REGIAO)


def wq(x, wt, q):
    o = np.argsort(x.to_numpy())
    xs, ws = x.to_numpy()[o], wt.to_numpy()[o]
    return xs[np.searchsorted(np.cumsum(ws) / ws.sum(), q)]


dist = []
for (mac, y), g in A.groupby(["macro", "ano"]):
    dist.append(dict(macro=mac, ano=y, n_regioes=len(g), media_pond=np.average(g.indice, weights=g.n_nasc),
                     p25=wq(g.indice, g.n_nasc, 0.25), mediana=wq(g.indice, g.n_nasc, 0.5), p75=wq(g.indice, g.n_nasc, 0.75),
                     minimo=g.indice.min(), maximo=g.indice.max()))
pd.DataFrame(dist).round(2).to_csv(L.TAB / f"tab_e2_03_indice_distribuicao_macro_ano_v1_{L.STAMP}.csv", index=False)

# composição racial por tercil e regional por tercil
comp_r = pd.crosstab(d.raca, d.tercil, normalize="index") * 100
comp_r.round(2).to_csv(L.TAB / f"tab_e2_03_raca_por_tercil_v1_{L.STAMP}.csv")
pd.crosstab(d.regiao, d.tercil, normalize="index").mul(100).round(2).to_csv(
    L.TAB / f"tab_e2_03_macro_por_tercil_v1_{L.STAMP}.csv")

# prevalências por raça × tercil (Wilson)
rows = []
for desf in ["ptb", "ptb_esp", "ptb_ind", "pig"]:
    s = d[d[desf].notna() & d.tercil.notna()]
    for (g, t), x in s.groupby(["raca", "tercil"], observed=True)[desf]:
        k, n = int(x.sum()), len(x)
        pp, lo, hi = E1.wilson(k, n)
        rows.append(dict(desfecho=desf, raca=g, tercil=t, casos=k, denominador=n, prev_pct=100 * pp, ic_lo=100 * lo, ic_hi=100 * hi))
pd.DataFrame(rows).to_csv(L.TAB / f"tab_e2_03_prev_raca_tercil_v1_{L.STAMP}.csv", index=False)
log("descritivas do índice gravadas")
