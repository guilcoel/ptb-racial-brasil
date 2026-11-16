"""
7c.2 SEXO do SIM-DOFET nos limites de nascidos vivos (Etapa 6.7b). DuckDB sobre os parquets do SIM (somente leitura; só agregados).
Defeito apontado na auditoria dos Métodos: etapa6_07 lia SEXO com TRY_CAST(... AS INT); um código em letra (M/F/I), se existisse,
viraria nulo e sairia do q do PIG.
 (a) SEXO como texto, por ano: todos os registros do DOFET 2015–2024 e os óbitos fetais pelo critério da Etapa 1.6.
 (b) q do PIG antes (TRY_CAST, como em etapa6_07) e depois (M → 1, F → 2; 1 e 2 mantidos; I, 0, 9 e qualquer outro → ausente),
     mesma grade gigs (+3 dias) e mesmo filtro (óbito fetal, GRAVIDEZ 1).
 (c) limites com a fórmula de etapa6_07 (P* = (p + odds·q)/(1 + odds), odds = k·f/(1 − f); RP M2 corrigida = RP M2 × RP*/RP bruta),
     com p, f e RP M2 lidos de tab_e6_07b_limites. Conferência: com o q de lá, os limites publicados são reproduzidos (< 1e-12).
Saídas: tab_e7c2_01_sexo_sim (contagens por ano × código), tab_e7c2_01_q_pig, tab_e7c2_01_limites (o pacote passa a ler esta).
"""
import duckdb
import numpy as np
import pandas as pd

import etapa0_lib as L

log = L.Logger("7c2_01_sexo_sim", etapa="etapa7c2")
TB, S = L.TAB, L.STAMP
SIM = __import__("os").environ.get("SIM_DOFET_PARQUET", "/Volumes/Forja/Doc/dados_artigos_perinatais_clima/02_sim/_dofet/parquet/ano=*/uf=*.parquet")  # 9a: caminho local por variável de ambiente   # = etapa6_07 (linha 59)
SEM = "TRY_CAST(trim(CAST(SEMAGESTAC AS VARCHAR)) AS INT)"
FET = f"""TRIM(CAST(TIPOBITO AS VARCHAR))='1' AND (
  ({SEM} IS NOT NULL AND {SEM} NOT IN (9,99) AND {SEM} >= 22)
  OR (({SEM} IS NULL OR {SEM} IN (9,99)) AND TRY_CAST(trim(CAST(GESTACAO AS VARCHAR)) AS INT) BETWEEN 2 AND 6)
  OR TRY_CAST(trim(CAST(PESO AS VARCHAR)) AS INT) >= 500)"""                                           # = etapa6_07 (linhas 62–65)
SX = "upper(trim(CAST(SEXO AS VARCHAR)))"
SEXO_ANTES = "TRY_CAST(trim(CAST(SEXO AS VARCHAR)) AS INT)"                                            # = etapa6_07 (linha 87), v1
SEXO_DEPOIS = f"CASE WHEN {SX} IN ('1', 'M') THEN 1 WHEN {SX} IN ('2', 'F') THEN 2 ELSE NULL END"     # 7c.2
con = duckdb.connect()
src = f"read_parquet('{SIM}', hive_partitioning=true, union_by_name=true)"

# (a)
tab = []
for univ, filtro in [("todos os registros DOFET", "TRUE"), ("óbitos fetais (critério da Etapa 1.6)", FET)]:
    x = con.sql(f"""SELECT CAST(ano AS INT) ano, COALESCE(trim(CAST(SEXO AS VARCHAR)), 'nulo') codigo, count(*) n FROM {src}
      WHERE CAST(ano AS INT) BETWEEN 2015 AND 2024 AND {filtro} GROUP BY ALL""").df()
    tab.append(x.assign(universo=univ))
T = pd.concat(tab)
T.to_csv(TB / f"tab_e7c2_01_sexo_sim_v1_{S}.csv", index=False)
for univ, x in T.groupby("universo", sort=False):
    log(f"SEXO no SIM-DOFET 2015–2024, {univ}:\n" + x.pivot(index="ano", columns="codigo", values="n").fillna(0).astype(int).to_string())
letras = T[T.codigo.str.upper().isin(["M", "F", "I"])].n.sum()
log(f"registros com SEXO em letra (M/F/I): {int(letras)}")
e16 = pd.read_csv(TB / f"tab_e1_06_sim_obitos_ano_regiao_v1_{S}.csv").query("componente == 'obito_fetal'")
assert int(T[T.universo.str.startswith("óbitos")].n.sum()) == int(e16.n.sum())   # = Etapa 1.6

# (b)
g = str(L.PROC / f"pig_grade_intergrowth_v1_{S}.parquet")
Q = []
for rot, sexo in [("antes (TRY_CAST, etapa6_07)", SEXO_ANTES), ("depois (M→1, F→2; I/0/9 → ausente)", SEXO_DEPOIS)]:
    q, n = con.sql(f"""WITH o AS (SELECT {SEM} SEMAGESTAC, {sexo} SEXO, TRY_CAST(trim(CAST(PESO AS VARCHAR)) AS INT) PESO FROM {src}
      WHERE CAST(ano AS INT) BETWEEN 2015 AND 2024 AND {FET} AND TRY_CAST(trim(CAST(GRAVIDEZ AS VARCHAR)) AS INT) = 1)
      SELECT avg(CASE WHEN g.centil_k3 < 0.10 THEN 1.0 ELSE 0 END), count(*) FROM o JOIN read_parquet('{g}') g USING (SEMAGESTAC, SEXO, PESO)""").fetchone()
    Q.append(dict(versao=rot, q_pig=q, n_obitos_na_grade=n))
Q = pd.DataFrame(Q)
Q.to_csv(TB / f"tab_e7c2_01_q_pig_v1_{S}.csv", index=False)
log("q do PIG (proporção < P10 entre óbitos fetais únicos na grade 24–42 sem, sexo 1/2, peso 100–7000):\n" + Q.to_string(index=False))

# (c)
lim = pd.read_csv(TB / f"tab_e6_07b_limites_v1_{S}.csv")
q_pub = lim[(lim.desfecho == "pig") & (lim.q < 1)].q.unique()
assert len(q_pub) == 1 and abs(q_pub[0] - Q.q_pig[0]) < 1e-15, (q_pub, Q.q_pig[0])     # o q "antes" = o publicado


def limites(t, q_pig_novo=None):
    t = t.copy()
    if q_pig_novo is not None:
        t.loc[(t.desfecho == "pig") & (t.q < 1), "q"] = q_pig_novo
    f = t.f_nacional_por_1000 / 1000
    odds = lambda k: k * f / (1 - f)
    pb, pi = t.p_branca / 100, t.p_indigena / 100
    t["RP_bruta_corrigida"] = ((pi + odds(t.k_indigena) * t.q) / (1 + odds(t.k_indigena))) / ((pb + odds(1.0) * t.q) / (1 + odds(1.0)))
    t["fator"] = t.RP_bruta_corrigida / t.RP_bruta
    m2 = pd.read_csv(TB / f"tab_e6_01a_m2_v1_{S}.csv").query("cluster == 'regsaude' and raca == 'Indigena'").set_index("desfecho")  # = etapa6_07
    assert np.allclose(t.RP_M2.to_numpy(), m2.RP.reindex(t.desfecho).to_numpy(), rtol=0, atol=0)
    t["RP_M2_corrigida"] = t.RP_M2 * t.fator
    t["RP_M2_lo_corrigido"] = m2.RP_lo.reindex(t.desfecho).to_numpy() * t.fator
    t["RP_M2_hi_corrigido"] = m2.RP_hi.reindex(t.desfecho).to_numpy() * t.fator
    return t


rep = limites(lim)
cols = ["RP_bruta_corrigida", "fator", "RP_M2_corrigida", "RP_M2_lo_corrigido", "RP_M2_hi_corrigido"]
dmax = float(np.abs(rep[cols].to_numpy() / lim[cols].to_numpy() - 1).max())
assert dmax < 1e-12, dmax
log(f"conferência: limites publicados reproduzidos com o q antigo (máx dif relativa {dmax:.1e})")
novo = limites(lim, Q.q_pig[1])
novo.to_csv(TB / f"tab_e7c2_01_limites_v1_{S}.csv", index=False)
cmp = lim[["desfecho", "q", "k_indigena", "RP_M2_corrigida"]].rename(columns={"q": "q_antes", "RP_M2_corrigida": "RP_M2_corrigida_antes"})
cmp["q_depois"], cmp["RP_M2_corrigida_depois"] = novo.q, novo.RP_M2_corrigida
cmp["dif"] = cmp.RP_M2_corrigida_depois - cmp.RP_M2_corrigida_antes
log("limites antes × depois:\n" + cmp.to_string(index=False))
log(f"máx |Δ RP M2 corrigida| = {cmp.dif.abs().max():.3g}; Δq do PIG = {Q.q_pig[1] - Q.q_pig[0]:.3g}")
