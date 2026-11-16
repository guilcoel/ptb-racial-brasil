# Auditoria independente etapa 4b - contagens em DuckDB SQL (sem pandas). Saídas: apenas agregados.
# Índice/tercis reaproveitam a lógica do auditor da etapa 3/4 (DuckDB). Critério (b) = PESO > P97 (tabela oficial).
import duckdb
OUT = '/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa4b'
V3 = "/Volumes/Forja/ptb-racial-brasil/data/processed/sinasc_brasil_2015_2024_v3_20261008/ano=*/[!.]*.parquet"
RAW = "/Volumes/Forja/CliMaterna/01_data/raw/SINASC/sinasc_{y}.parquet"
REL = "/Volumes/Forja/ptb-racial-brasil/docs/referencias/territorio_dez24/rl_municip_regsaud.csv"
c = duckdb.connect()
c.sql("SET threads=8")

# 0. amostra analítica (só colunas brutas)
c.sql(f"""
CREATE TABLE b AS
SELECT ano::INT ano, TRIM(CAST(CODMUNRES AS VARCHAR)) mun, RACACORMAE::INT raca, SEMAGESTAC::INT sg,
       ESCMAE::INT esc, IDADEMAE::INT idade, STTRABPART::INT trab, STCESPARTO::INT cesp, PARTO::INT parto,
       PESO::INT peso, SEXO::INT sexo, GRAVIDEZ::INT grav, TPMETESTIM::INT tpm
FROM read_parquet('{V3}', hive_partitioning=true)
WHERE RACACORMAE IN (1,2,4,5) AND SEMAGESTAC BETWEEN 22 AND 44
  AND ESCMAE BETWEEN 1 AND 5 AND IDADEMAE BETWEEN 10 AND 60
""")
print('amostra analítica por raça', c.sql("select raca, count(*) from b group by 1 order by 1").fetchall())

# 1. índice de acesso 2014-2024 (bruto, todos os residentes)
c.sql(f"CREATE TABLE rel AS SELECT lpad(CAST(CO_MUNICIP AS VARCHAR),6,'0') mun, CAST(CO_REGSAUD AS VARCHAR) rs FROM read_csv('{REL}', all_varchar=true)")
parts = [f"""SELECT {y} ano, TRIM(CAST(CODMUNRES AS VARCHAR)) mun,
       TRY_CAST(TRIM(CAST(MESPRENAT AS VARCHAR)) AS DOUBLE)::INT mp FROM read_parquet('{RAW.format(y=y)}')"""
         for y in range(2014, 2025)]
c.sql("CREATE TABLE raw AS " + " UNION ALL ".join(parts))
c.sql("""CREATE TABLE idx AS
SELECT rs, ano, 100.0*SUM(CASE WHEN mp BETWEEN 1 AND 3 THEN 1 ELSE 0 END)/SUM(CASE WHEN mp BETWEEN 1 AND 9 THEN 1 ELSE 0 END) ind
FROM raw JOIN rel USING(mun) GROUP BY rs, ano""")

# 2. P97 (tabela oficial em gramas; equação growthstandards em gramas contínuos)
c.sql(f"""CREATE TABLE p97 AS SELECT sexo, dias, CAST(round(p97_kg*1000) AS INT) p97g, p97_eq_kg*1000 p97eq
          FROM read_csv('{OUT}/p97_tabela_vs_equacao_v1_20261008.csv')""")

# 3. derivadas
c.sql("""CREATE TABLE d AS
SELECT b.*, rel.rs, CAST(substr(b.mun,1,1) AS INT) mr, CAST(substr(b.mun,1,2) AS INT) uf, idx.ind,
  CASE WHEN idade<20 THEN 'lt20' WHEN idade<=34 THEN '20_34' ELSE 'ge35' END ida,
  CASE WHEN sg>=37 THEN 'termo'
       WHEN trab=1 OR (parto=2 AND cesp=1) THEN 'ind'
       WHEN trab=2 AND (parto=1 OR (parto=2 AND cesp=2)) THEN 'esp'
       ELSE 'semclass' END ptbt,
  CASE WHEN tpm=8 THEN 'DUM' WHEN tpm IN (1,2) THEN 'outro' ELSE 'ign' END igm,
  (grav=1 AND sg BETWEEN 24 AND 36 AND b.sexo IN (1,2) AND peso BETWEEN 100 AND 7000) eleg,
  COALESCE(grav=1 AND sg BETWEEN 24 AND 36 AND b.sexo IN (1,2) AND peso BETWEEN 100 AND 7000 AND peso > p97.p97g, FALSE) cb_tab,
  COALESCE(grav=1 AND sg BETWEEN 24 AND 36 AND b.sexo IN (1,2) AND peso BETWEEN 100 AND 7000 AND peso > p97.p97eq, FALSE) cb_eq
FROM b LEFT JOIN rel USING(mun) LEFT JOIN idx ON idx.rs=rel.rs AND idx.ano=b.ano-1
       LEFT JOIN p97 ON p97.sexo=b.sexo AND p97.dias=7*b.sg+3""")
print('elegível sem P97 (deve ser 0)', c.sql("""select count(*) from d left join p97 on p97.sexo=d.sexo and p97.dias=7*d.sg+3
       where eleg and p97g is null""").fetchone())

# A. % critério (b) entre prematuros elegíveis, raça x ig_metodo (Brasil; amostra analítica, sem exigir tercil)
c.sql(f"""COPY (
SELECT CASE raca WHEN 1 THEN 'Branca' WHEN 2 THEN 'Preta' WHEN 4 THEN 'Parda' WHEN 5 THEN 'Indigena' END raca_nome,
       COALESCE(igm,'TOTAL') igm, COUNT(*) n_eleg, SUM(cb_tab::INT) n_b_tab, SUM(cb_eq::INT) n_b_eq,
       SUM((cb_tab AND NOT cb_eq)::INT) so_tabela, SUM((cb_eq AND NOT cb_tab)::INT) so_equacao
FROM d WHERE eleg GROUP BY GROUPING SETS ((raca, igm), (raca)) ORDER BY raca, igm) TO '{OUT}/A_contagens_critb_v1_20261008.csv' (HEADER)""")
print('reclassificação tabela x equação (todos elegíveis):', c.sql("""select count(*), sum(cb_tab::INT), sum(cb_eq::INT),
      sum((cb_tab and not cb_eq)::INT), sum((cb_eq and not cb_tab)::INT) from d where eleg""").fetchall())
print('reclassificação por sexo x sg (só onde há):', c.sql("""select sexo, sg, sum((cb_tab and not cb_eq)::INT) st, sum((cb_eq and not cb_tab)::INT) se
      from d where eleg group by all having st+se>0 order by all""").fetchall())

# B. tercis dentro da macrorregião (pares região de saúde x ano ponderados pela amostra analítica completa)
c.sql("""CREATE TABLE pares AS SELECT mr, rs, ano, ind, COUNT(*) n FROM d WHERE ind IS NOT NULL GROUP BY ALL""")
c.sql("""CREATE TABLE cum AS SELECT *, SUM(n) OVER (PARTITION BY mr ORDER BY ind, rs, ano ROWS UNBOUNDED PRECEDING)*1.0
        / SUM(n) OVER (PARTITION BY mr) f FROM pares""")
c.sql("""CREATE TABLE cortes AS SELECT mr, MIN(ind) FILTER (WHERE f >= 1.0/3) c1, MIN(ind) FILTER (WHERE f >= 2.0/3) c2
         FROM cum GROUP BY mr""")
c.sql(f"COPY (SELECT * FROM cortes ORDER BY mr) TO '{OUT}/B_cortes_tercis_v1_20261008.csv' (HEADER)")
print('cortes', c.sql("select * from cortes order by mr").fetchall())
c.sql("""CREATE TABLE e AS SELECT d.*, CASE WHEN ind IS NULL THEN 0 WHEN ind<=c1 THEN 1 WHEN ind<=c2 THEN 2 ELSE 3 END terc
         FROM d LEFT JOIN cortes USING(mr)""")
c.sql(f"""COPY (
SELECT raca, ida, ano, mr, terc, mun,
  COUNT(*) n_esp,
  SUM((ptbt='esp')::INT) y_esp,
  SUM((ptbt='esp' AND NOT cb_tab)::INT) y_esp_b_tab,
  SUM((ptbt='esp' AND NOT cb_eq)::INT) y_esp_b_eq
FROM e WHERE terc>0 AND ptbt<>'semclass' GROUP BY ALL) TO '{OUT}/B_cel_v1_20261008.parquet' (FORMAT parquet)""")
print('B N, y_esp, y_esp_b_tab, y_esp_b_eq', c.sql(f"select sum(n_esp), sum(y_esp), sum(y_esp_b_tab), sum(y_esp_b_eq) from '{OUT}/B_cel_v1_20261008.parquet'").fetchall())
print('B ptb esp reclassificados tab vs eq', c.sql("""select sum((ptbt='esp' and cb_tab and not cb_eq)::INT), sum((ptbt='esp' and cb_eq and not cb_tab)::INT)
      from e where terc>0 and ptbt<>'semclass'""").fetchall())

# C. Centro-Oeste (mr=5), amostra analítica completa (sem exigência de tercil), ptb = sg<37
c.sql(f"""COPY (
SELECT raca, ida, esc, ano, uf, mun, igm, COUNT(*) n, SUM((sg<37)::INT) y
FROM d WHERE mr=5 GROUP BY ALL) TO '{OUT}/C_cel_co_v1_20261008.parquet' (FORMAT parquet)""")
print('C por igm', c.sql(f"select igm, sum(n), sum(y), sum(n) filter (where raca=5), sum(y) filter (where raca=5) from '{OUT}/C_cel_co_v1_20261008.parquet' group by rollup(igm) order by 1").fetchall())
