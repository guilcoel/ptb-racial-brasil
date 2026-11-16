"""
6.2 Validação do código 8 de TPMETESTIM (DuckDB sobre os brutos, somente leitura).
Amostra: cascata da RSP refeita em SQL (raça 1/2/4/5; SEMAGESTAC 22–44; ESCMAE 1–5; IDADEMAE 10–60) = 25,808,740.
 (a) DTULTMENST válida = data DDMMAAAA que existe e é anterior a DTNASC, com intervalo ≤ 365 dias.
     IG pela DUM = floor((DTNASC − DTULTMENST)/7), em semanas completas. Por código de TPMETESTIM: % de
     DTULTMENST válida; concordância exata e ±1 semana com SEMAGESTAC; Bland–Altman (dif = SEMAGESTAC − IG_DUM:
     média, DP, limites média ± 1.96 DP, P1/P99). Também no subconjunto plausível (IG_DUM 22–44).
 (b) TPMETESTIM por ano e por UF de residência; 1º ano com o código 8.
Saídas: tab_e6_02a_concordancia, tab_e6_02b_tpmetestim_ano, tab_e6_02b_tpmetestim_uf.
"""
import duckdb

import etapa6_lib as E6
import etapa0_lib as L

log = E6.logger("02_tpmetestim")
con = duckdb.connect()
partes = []
for y in range(2015, 2025):
    f = L.RAW / f"sinasc_{y}.parquet"
    partes.append(f"""SELECT {y} AS ano, CAST(TRY_CAST(RACACORMAE AS DOUBLE) AS INTEGER) rc, TRY_CAST(SEMAGESTAC AS DOUBLE) sg,
        TRY_CAST(ESCMAE AS DOUBLE) esc, TRY_CAST(IDADEMAE AS DOUBLE) idm, CAST(TPMETESTIM AS VARCHAR) tp,
        CAST(DTNASC AS VARCHAR) dn, CAST(DTULTMENST AS VARCHAR) du, LEFT(CAST(CODMUNRES AS VARCHAR), 2) cuf
        FROM read_parquet('{f}')""")
con.sql("CREATE TEMP VIEW bruto AS " + " UNION ALL ".join(partes))
con.sql("""CREATE TEMP TABLE a AS
  SELECT ano, rc, sg, COALESCE(CAST(CAST(TRY_CAST(tp AS DOUBLE) AS INTEGER) AS VARCHAR), 'nulo') tp, cuf,
         try_strptime(lpad(dn, 8, '0'), '%d%m%Y')::DATE dnasc, try_strptime(lpad(du, 8, '0'), '%d%m%Y')::DATE dum
  FROM bruto
  WHERE rc IN (1, 2, 4, 5) AND sg BETWEEN 22 AND 44 AND esc BETWEEN 1 AND 5 AND idm BETWEEN 10 AND 60""")
n = con.sql("SELECT count(*) FROM a").fetchone()[0]
log(f"amostra (cascata em SQL): {n:,}")
assert n == 25808740
con.sql("""CREATE TEMP TABLE b AS SELECT *, date_diff('day', dum, dnasc) dias,
  CASE WHEN dum IS NOT NULL AND dnasc IS NOT NULL AND dum < dnasc AND date_diff('day', dum, dnasc) <= 365 THEN 1 ELSE 0 END valida
  FROM a""")
q = """SELECT tp, {sub} sub, count(*) n_total, sum(valida) n_dum_valida, 100.0 * avg(valida) pct_dum_valida,
  count(*) FILTER (WHERE valida = 1 {extra}) n_comp,
  100.0 * avg(CASE WHEN floor(dias / 7.0) = sg THEN 1 ELSE 0 END) FILTER (WHERE valida = 1 {extra}) pct_exata,
  100.0 * avg(CASE WHEN abs(sg - floor(dias / 7.0)) <= 1 THEN 1 ELSE 0 END) FILTER (WHERE valida = 1 {extra}) pct_pm1,
  avg(sg - floor(dias / 7.0)) FILTER (WHERE valida = 1 {extra}) dif_media,
  stddev_samp(sg - floor(dias / 7.0)) FILTER (WHERE valida = 1 {extra}) dif_dp,
  quantile_cont(sg - floor(dias / 7.0), 0.01) FILTER (WHERE valida = 1 {extra}) dif_p1,
  quantile_cont(sg - floor(dias / 7.0), 0.99) FILTER (WHERE valida = 1 {extra}) dif_p99
  FROM b GROUP BY tp ORDER BY tp"""
A = con.sql(q.format(sub="'todas validas'", extra="")).df()
B = con.sql(q.format(sub="'IG_DUM 22-44'", extra="AND floor(dias / 7.0) BETWEEN 22 AND 44")).df()
import pandas as pd

R = pd.concat([A, B])
R["LoA_inf"] = R.dif_media - 1.96 * R.dif_dp
R["LoA_sup"] = R.dif_media + 1.96 * R.dif_dp
R.to_csv(L.TAB / f"tab_e6_02a_concordancia_v1_{L.STAMP}.csv", index=False)
log("concordância IG_DUM × SEMAGESTAC por TPMETESTIM:\n" + R.round(3).to_string(index=False))
# convenção: concordância exata por resto (dias mod 7) — o desvio de ±1 semana depende do resto, não é aleatório
M7 = con.sql("""SELECT dias % 7 resto, count(*) n, 100.0 * avg(CASE WHEN floor(dias / 7.0) = sg THEN 1 ELSE 0 END) pct_exata
  FROM b WHERE tp = '8' AND valida = 1 GROUP BY 1 ORDER BY 1""").df()
M7.to_csv(L.TAB / f"tab_e6_02a_resto7_v1_{L.STAMP}.csv", index=False)
log("código 8, concordância exata por resto (dias mod 7):\n" + M7.round(2).to_string(index=False))
# fronteira de 37 semanas (código 8): PTB por SEMAGESTAC × PTB pela DUM, por raça
F = con.sql("""SELECT CASE rc WHEN 1 THEN 'Branca' WHEN 2 THEN 'Preta' WHEN 4 THEN 'Parda' ELSE 'Indigena' END raca, count(*) n,
  count(*) FILTER (WHERE sg < 37) ptb_sinasc, count(*) FILTER (WHERE floor(dias / 7.0) < 37) ptb_dum,
  count(*) FILTER (WHERE sg < 37 AND floor(dias / 7.0) >= 37) sinasc_ptb_dum_termo,
  count(*) FILTER (WHERE sg >= 37 AND floor(dias / 7.0) < 37) sinasc_termo_dum_ptb
  FROM b WHERE tp = '8' AND valida = 1 GROUP BY 1 ORDER BY 1""").df()
F["pct_ptb_sinasc"] = 100 * F.ptb_sinasc / F.n
F["pct_ptb_dum"] = 100 * F.ptb_dum / F.n
F.to_csv(L.TAB / f"tab_e6_02a_fronteira37_v1_{L.STAMP}.csv", index=False)
log("código 8, fronteira de 37 semanas (SEMAGESTAC × floor(dias/7)):\n" + F.round(3).to_string(index=False))
# por ano, só o código 8 (estabilidade)
Y8 = con.sql("""SELECT ano, count(*) n, 100.0 * avg(valida) pct_valida,
  100.0 * avg(CASE WHEN floor(dias / 7.0) = sg THEN 1 ELSE 0 END) FILTER (WHERE valida = 1) pct_exata
  FROM b WHERE tp = '8' GROUP BY ano ORDER BY ano""").df()
log("código 8 por ano:\n" + Y8.round(3).to_string(index=False))

# (b)
Y = con.sql("SELECT ano, tp, count(*) n FROM a GROUP BY ALL").df()
Y["pct"] = 100 * Y.n / Y.groupby("ano").n.transform("sum")
Yw = Y.pivot(index="ano", columns="tp", values="pct").round(2)
Y.merge(Y8[["ano", "pct_valida", "pct_exata"]].assign(tp="8"), on=["ano", "tp"], how="left").to_csv(
    L.TAB / f"tab_e6_02b_tpmetestim_ano_v1_{L.STAMP}.csv", index=False)
log("TPMETESTIM por ano (% da amostra):\n" + Yw.to_string())
U = con.sql("SELECT cuf, tp, count(*) n FROM a GROUP BY ALL").df()
U["uf"] = U.cuf.map(L.UF_SIGLA) if isinstance(L.UF_SIGLA, dict) else U.cuf
U["pct"] = 100 * U.n / U.groupby("cuf").n.transform("sum")
U.to_csv(L.TAB / f"tab_e6_02b_tpmetestim_uf_v1_{L.STAMP}.csv", index=False)
Uw = U.pivot(index="uf", columns="tp", values="pct").round(1)
log("TPMETESTIM por UF (% da amostra):\n" + Uw.to_string())
prim = con.sql("SELECT min(ano) FROM a WHERE tp = '8'").fetchone()[0]
log(f"1º ano com código 8 na amostra 2015–2024: {prim} (a série começa em 2015; ver brutos anteriores no item (c))")
# 2010–2014 (fora do período; todos os registros, sem cascata): quando o código 8 aparece e a relação com DTULTMENST
pre = []
for y in range(2010, 2015):
    f = L.RAW / f"sinasc_{y}.parquet"
    cols = con.sql(f"SELECT * FROM read_parquet('{f}') LIMIT 0").columns
    if "TPMETESTIM" not in cols:
        pre.append(dict(ano=y, tp="(coluna ausente)", n=None, n_dtultmenst=None))
        continue
    du = "count(DTULTMENST)" if "DTULTMENST" in cols else "NULL"
    for tp, nn, nd in con.sql(f"SELECT CAST(TPMETESTIM AS VARCHAR), count(*), {du} FROM read_parquet('{f}') GROUP BY 1 ORDER BY 1").fetchall():
        pre.append(dict(ano=y, tp=tp, n=nn, n_dtultmenst=nd))
P = pd.DataFrame(pre)
P.to_csv(L.TAB / f"tab_e6_02b_tpmetestim_2010_2014_v1_{L.STAMP}.csv", index=False)
log("TPMETESTIM 2010–2014 (todos os registros; n e nº com DTULTMENST preenchida):\n" + P.to_string(index=False))
