"""
6.7 Tempo e condicionamento em nascidos vivos.
 (a) ig_metodo por ano × raça (amostra analítica); M2 para PTB e PIG com raça × período (2015–2019 ref., 2020–2021,
     2022–2024; período ⊂ ano: padronização dentro do período, como na 3.5), estratificado por ig_metodo (DUM / outro
     método); etapa3_lib.knol, EP por região de saúde.
 (b) Óbitos fetais (SIM-DOFET; TIPOBITO 1 e SEMAGESTAC ≥ 22, ou GESTACAO 2–6 se a IG faltar, ou PESO ≥ 500 g; critério da
     Etapa 1.6) por região × ano; razão de óbito fetal por 1,000 nascimentos totais = OF / (OF + NV) × 1,000, NV = todos os
     nascidos vivos residentes do SINASC (sem a cascata).
     Limites (fórmula de seleção simples, documentada): o SIM-DOFET não tem raça da mãe. Para a raça g,
       P*_g = (NV_g·p_g + OF_g·q) / (NV_g + OF_g),  com OF_g/NV_g = k_g · f/(1 − f)
     p_g = prevalência observada em nascidos vivos (bruta, Brasil); f = razão de óbito fetal nacional por nascimento total;
     q = proporção do desfecho entre os óbitos fetais (PTB: % < 37 sem entre os OF com IG; PIG: % < P10 INTERGROWTH-21st,
     grade gigs +3 dias, entre OF únicos 24–42 sem com sexo e peso válidos; e o limite q = 1).
     Brancas: k = 1. Indígenas: k = 1, 1.5, 2. Pretas e pardas: k = 1.
     RP*_bruta = P*_I / P*_B. Fator de viés = RP*_bruta / RP_bruta; RP M2 corrigida ≈ RP_M2 × fator (aproximação: o
     fator bruto é aplicado à RP ajustada).
Saídas: tab_e6_07a_igmetodo_ano_raca, tab_e6_07a_periodo_{interacao,dentro,wald}, tab_e6_07b_obito_fetal, tab_e6_07b_limites.
"""
import duckdb
import numpy as np
import pandas as pd

import etapa1_lib as E
import etapa3_lib as T
import etapa4_lib as S4
import etapa6_lib as E6
import etapa0_lib as L

log = E6.logger("07_tempo_nv")
TB, S = L.TAB, L.STAMP
d = S4.carrega()
d["periodo"] = pd.Categorical(T.load(["periodo"]).periodo.astype(str).to_numpy(), categories=["2015-2019", "2020-2021", "2022-2024"])
assert d.periodo.notna().all()
# (a)
x = d.groupby(["ano", "raca", "ig_metodo"], observed=True).size().rename("n").reset_index()
x["pct"] = 100 * x.n / x.groupby(["ano", "raca"], observed=True).n.transform("sum")
x.to_csv(TB / f"tab_e6_07a_igmetodo_ano_raca_v1_{S}.csv", index=False)
log("% DUM por ano × raça:\n" + x[x.ig_metodo == "DUM"].pivot(index="ano", columns="raca", values="pct").round(1).to_string())
res = {k: [] for k in ("interacao", "dentro", "wald")}
for met in ["DUM", "outro_metodo"]:
    sub = d[d.ig_metodo == met]
    for desf in ["ptb", "pig"]:
        s = sub[sub[desf].notna()]
        c = E.agrega(s, desf, ["raca", "idade_cat", "ano", "regiao", "periodo"])
        c["CODMUNRES"] = c.CODMUNRES.astype(str)
        assert int(c.n.sum()) == len(s)
        r = T.knol(E6.para_rs(c), "periodo", ["2015-2019", "2020-2021", "2022-2024"], "2015-2019", within=True, rotulo="periodo")
        for k in res:
            res[k].append(r[k].assign(ig_metodo=met, desfecho=desf))
        w = r["wald"].iloc[0]
        log(f"raça × período, {desf}, {met}: Wald χ² = {w.chi2:.1f} ({w.gl} gl), p = {w.p:.2e}; N = {w.N:,}")
for k, v in res.items():
    pd.concat(v).to_csv(TB / f"tab_e6_07a_periodo_{k}_v1_{S}.csv", index=False)
dn = pd.concat(res["dentro"])
log("RP Indígena por período (dentro do período):\n" + dn[dn.raca == "Indigena"][["ig_metodo", "desfecho", "nivel", "RP", "RP_lo", "RP_hi"]]
    .round(3).to_string(index=False))

# (b)
SIM = __import__("os").environ.get("SIM_DOFET_PARQUET", "/Volumes/Forja/Doc/dados_artigos_perinatais_clima/02_sim/_dofet/parquet/ano=*/uf=*.parquet")  # 9a: caminho local por variável de ambiente
REG = "CASE substr(trim(CAST(CODMUNRES AS VARCHAR)),1,1) WHEN '1' THEN 'N' WHEN '2' THEN 'NE' WHEN '3' THEN 'SE' WHEN '4' THEN 'S' WHEN '5' THEN 'CO' ELSE 'ign' END"
SEM = "TRY_CAST(trim(CAST(SEMAGESTAC AS VARCHAR)) AS INT)"
FET = f"""TRIM(CAST(TIPOBITO AS VARCHAR))='1' AND (
  ({SEM} IS NOT NULL AND {SEM} NOT IN (9,99) AND {SEM} >= 22)
  OR (({SEM} IS NULL OR {SEM} IN (9,99)) AND TRY_CAST(trim(CAST(GESTACAO AS VARCHAR)) AS INT) BETWEEN 2 AND 6)
  OR TRY_CAST(trim(CAST(PESO AS VARCHAR)) AS INT) >= 500)"""
con = duckdb.connect()
of = con.sql(f"""SELECT CAST(ano AS INT) ano, {REG} regiao, count(*) obitos_fetais FROM read_parquet('{SIM}', hive_partitioning=true,
  union_by_name=true) WHERE CAST(ano AS INT) BETWEEN 2015 AND 2024 AND {FET} GROUP BY ALL""").df()
e16 = pd.read_csv(TB / f"tab_e1_06_sim_obitos_ano_regiao_v1_{S}.csv").query("componente == 'obito_fetal'")
assert int(of.obitos_fetais.sum()) == int(e16.n.sum())  # = Etapa 1.6
nv = []
for y in range(2015, 2025):
    f = L.RAW / f"sinasc_{y}.parquet"
    nv.append(con.sql(f"SELECT {y} ano, {REG} regiao, count(*) nascidos_vivos FROM read_parquet('{f}') GROUP BY ALL").df())
nv = pd.concat(nv)
B = nv.merge(of, on=["ano", "regiao"], how="outer").fillna(0)
B["razao_OF_por_1000_totais"] = 1000 * B.obitos_fetais / (B.obitos_fetais + B.nascidos_vivos)
B.to_csv(TB / f"tab_e6_07b_obito_fetal_v1_{S}.csv", index=False)
log("razão de óbito fetal por 1,000 nascimentos totais (região × ano):\n" +
    B[B.regiao != "ign"].pivot(index="ano", columns="regiao", values="razao_OF_por_1000_totais").round(2).to_string())
tot = B.sum(numeric_only=True)
fnac = tot.obitos_fetais / (tot.obitos_fetais + tot.nascidos_vivos)
# q: proporção do desfecho entre os óbitos fetais
qptb = con.sql(f"""SELECT avg(CASE WHEN {SEM} < 37 THEN 1.0 ELSE 0 END), count(*) FROM read_parquet('{SIM}', hive_partitioning=true,
  union_by_name=true) WHERE CAST(ano AS INT) BETWEEN 2015 AND 2024 AND {FET} AND {SEM} BETWEEN 22 AND 44""").fetchone()
g = str(L.PROC / f"pig_grade_intergrowth_v1_{S}.parquet")
# 7c.2: SEXO em letra (M/F) passa a ser recodificado (M → 1, F → 2; I/0/9 → ausente). No SIM-DOFET 2015–2024 só há 0/1/2, e o q do
# PIG e os limites são idênticos aos da versão anterior (TRY_CAST AS INT); ver etapa7c2_01_sexo_sim.py.
SEXO_SIM = "CASE WHEN upper(trim(CAST(SEXO AS VARCHAR))) IN ('1', 'M') THEN 1 WHEN upper(trim(CAST(SEXO AS VARCHAR))) IN ('2', 'F') THEN 2 ELSE NULL END"
qpig = con.sql(f"""WITH o AS (SELECT {SEM} SEMAGESTAC, {SEXO_SIM} SEXO,
  TRY_CAST(trim(CAST(PESO AS VARCHAR)) AS INT) PESO FROM read_parquet('{SIM}', hive_partitioning=true, union_by_name=true)
  WHERE CAST(ano AS INT) BETWEEN 2015 AND 2024 AND {FET} AND TRY_CAST(trim(CAST(GRAVIDEZ AS VARCHAR)) AS INT) = 1)
  SELECT avg(CASE WHEN g.centil_k3 < 0.10 THEN 1.0 ELSE 0 END), count(*) FROM o JOIN read_parquet('{g}') g USING (SEMAGESTAC, SEXO, PESO)""").fetchone()
log(f"f nacional = {1000 * fnac:.2f} por 1,000 totais; q_PTB = {100 * qptb[0]:.1f}% (n = {qptb[1]:,}); q_PIG = {100 * qpig[0]:.1f}% (n = {qpig[1]:,})")
m2 = pd.read_csv(TB / f"tab_e6_01a_m2_v1_{S}.csv").query("cluster == 'regsaude'")
rows = []
for desf, qs in [("ptb", [qptb[0], 1.0]), ("pig", [qpig[0], 1.0])]:
    s = d[d[desf].notna()]
    p = s.groupby("raca", observed=True)[desf].mean()
    for q in qs:
        for k in (1.0, 1.5, 2.0):
            def pstar(g, kk):
                odds = kk * fnac / (1 - fnac)  # OF_g / NV_g
                return (p[g] + odds * q) / (1 + odds)
            rp0 = p["Indigena"] / p["Branca"]
            rp1 = pstar("Indigena", k) / pstar("Branca", 1.0)
            mm = m2[(m2.desfecho == desf) & (m2.raca == "Indigena")].iloc[0]
            fat = rp1 / rp0
            rows.append(dict(desfecho=desf, q=q, k_indigena=k, f_nacional_por_1000=1000 * fnac, p_branca=100 * p["Branca"],
                             p_indigena=100 * p["Indigena"], RP_bruta=rp0, RP_bruta_corrigida=rp1, fator=fat, RP_M2=mm.RP,
                             RP_M2_corrigida=mm.RP * fat, RP_M2_lo_corrigido=mm.RP_lo * fat, RP_M2_hi_corrigido=mm.RP_hi * fat))
Lm = pd.DataFrame(rows)
Lm.to_csv(TB / f"tab_e6_07b_limites_v1_{S}.csv", index=False)
log("limites (nascidos vivos → nascimentos totais), Indígena vs Branca:\n" + Lm.round(4).to_string(index=False))
