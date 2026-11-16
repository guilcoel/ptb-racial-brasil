# Auditoria independente etapa 3 - contagens em DuckDB SQL (sem pandas)
# Saídas: apenas agregados.
import duckdb, os
OUT = '/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa3'
V3 = "/Volumes/Forja/ptb-racial-brasil/data/processed/sinasc_brasil_2015_2024_v3_20261008/ano=*/[!.]*.parquet"
RAW = "/Volumes/Forja/CliMaterna/01_data/raw/SINASC/sinasc_{y}.parquet"
REL = "/Volumes/Forja/ptb-racial-brasil/docs/referencias/territorio_dez24/rl_municip_regsaud.csv"
c = duckdb.connect()
c.sql("SET threads=8")

# 1. amostra analítica
c.sql(f"""
CREATE TABLE a AS
SELECT ano::INT ano, TRIM(CODMUNRES) mun, RACACORMAE::INT raca, SEMAGESTAC::INT sg,
       ESCMAE::INT esc, IDADEMAE::INT idade, ESTCIVMAE::INT estciv,
       STTRABPART::INT trab, STCESPARTO::INT cesp, PARTO::INT parto
FROM read_parquet('{V3}', hive_partitioning=true)
WHERE RACACORMAE IN (1,2,4,5) AND SEMAGESTAC BETWEEN 22 AND 44
  AND ESCMAE BETWEEN 1 AND 5 AND IDADEMAE BETWEEN 10 AND 60
""")
print('n amostra', c.sql("select count(*) from a").fetchone())
print('mun 0000', c.sql("select count(*) from a where mun like '%0000'").fetchone())
print('G clusters', c.sql("select count(distinct mun) from a").fetchone())

# 2. índice de acesso 2014-2024 a partir do bruto
c.sql(f"CREATE TABLE rel AS SELECT lpad(CAST(CO_MUNICIP AS VARCHAR),6,'0') mun, CAST(CO_REGSAUD AS VARCHAR) rs FROM read_csv('{REL}', all_varchar=true)")
parts = []
for y in range(2014, 2025):
    parts.append(f"""SELECT {y} ano, TRIM(CAST(CODMUNRES AS VARCHAR)) mun,
       TRY_CAST(TRIM(CAST(MESPRENAT AS VARCHAR)) AS DOUBLE)::INT mp
       FROM read_parquet('{RAW.format(y=y)}')""")
c.sql("CREATE TABLE raw AS " + " UNION ALL ".join(parts))
print('raw sem match rel', c.sql("select count(*), count(distinct mun) from raw left join rel using(mun) where rel.rs is null").fetchall())
c.sql("""CREATE TABLE idx AS
SELECT rs, ano, 100.0*SUM(CASE WHEN mp BETWEEN 1 AND 3 THEN 1 ELSE 0 END)/SUM(CASE WHEN mp BETWEEN 1 AND 9 THEN 1 ELSE 0 END) ind,
       SUM(CASE WHEN mp BETWEEN 1 AND 9 THEN 1 ELSE 0 END) den
FROM raw JOIN rel USING(mun) GROUP BY rs, ano""")
print('idx linhas', c.sql("select count(*), min(den) from idx").fetchall())

# 3. amostra de acesso + índice t-1
c.sql("""CREATE TABLE ac AS
SELECT a.*, rel.rs, CAST(substr(a.mun,1,1) AS INT) mr, idx.ind
FROM a JOIN rel USING(mun) JOIN idx ON idx.rs=rel.rs AND idx.ano=a.ano-1""")
print('n acesso', c.sql("select count(*) from ac").fetchone(),
      'n analitica sem rs', c.sql("select count(*) from a left join rel using(mun) where rel.rs is null").fetchone())

# tercis ponderados dentro da macrorregião
c.sql("""CREATE TABLE pares AS SELECT mr, rs, ano, ind, COUNT(*) n FROM ac GROUP BY ALL""")
c.sql("""CREATE TABLE cum AS SELECT *, SUM(n) OVER (PARTITION BY mr ORDER BY ind, rs, ano ROWS UNBOUNDED PRECEDING)*1.0
        / SUM(n) OVER (PARTITION BY mr) f FROM pares""")
c.sql("""CREATE TABLE cortes AS SELECT mr,
   MIN(ind) FILTER (WHERE f >= 1.0/3) c1, MIN(ind) FILTER (WHERE f >= 2.0/3) c2 FROM cum GROUP BY mr""")
c.sql(f"COPY (SELECT * FROM cortes ORDER BY mr) TO '{OUT}/A_cortes_tercis_v1_20261008.csv' (HEADER)")
c.sql("""CREATE TABLE ac2 AS SELECT ac.*, CASE WHEN ind<=c1 THEN 1 WHEN ind<=c2 THEN 2 ELSE 3 END terc
        FROM ac JOIN cortes USING(mr)""")
c.sql(f"""COPY (WITH t AS (SELECT mr, terc, COUNT(*) n FROM ac2 GROUP BY mr, terc)
        SELECT mr, terc, n, 100.0*n/SUM(n) OVER (PARTITION BY mr) pct_macro, 100.0*n/SUM(n) OVER () pct_total FROM t
        UNION ALL SELECT 0, terc, SUM(n), NULL, 100.0*SUM(n)/(SELECT SUM(n) FROM t) FROM t GROUP BY terc
        ORDER BY 1,2) TO '{OUT}/A_pct_tercis_v1_20261008.csv' (HEADER)""")
print(c.sql("select * from cortes order by mr"))
print(c.sql(f"select * from '{OUT}/A_pct_tercis_v1_20261008.csv'"))

# células para modelo de interação
c.sql(f"""COPY (
SELECT raca, CASE WHEN idade<20 THEN 'lt20' WHEN idade<=34 THEN '20_34' ELSE 'ge35' END ida,
  ano, mr, terc, mun,
  COUNT(*) n, SUM(CASE WHEN sg<37 THEN 1 ELSE 0 END) y_ptb,
  SUM(CASE WHEN sg>=37 OR (trab=1 OR (parto=2 AND cesp=1)) OR (trab=2 AND (parto=1 OR (parto=2 AND cesp=2))) THEN 1 ELSE 0 END) n_esp,
  SUM(CASE WHEN sg<37 AND NOT (trab=1 OR (parto=2 AND cesp=1)) AND (trab=2 AND (parto=1 OR (parto=2 AND cesp=2))) THEN 1 ELSE 0 END) y_esp
FROM ac2 GROUP BY ALL) TO '{OUT}/cel_interacao_v1_20261008.parquet' (FORMAT parquet)""")
# Nota: PTB "indicado" tem precedência se ambas as regras casassem (impossível: trab=1 vs trab=2; parto=2&cesp=1 vs cesp=2 exclusivos).

# células para bootstrap (analítica com ESTCIV 1-5)
c.sql(f"""COPY (
SELECT raca, CASE WHEN idade<20 THEN 'lt20' WHEN idade<=34 THEN '20_34' ELSE 'ge35' END ida,
  ano, CAST(substr(mun,1,1) AS INT) mr, esc, CASE WHEN estciv IN (2,5) THEN 0 ELSE 1 END semcomp, mun,
  COUNT(*) n, SUM(CASE WHEN sg<37 THEN 1 ELSE 0 END) y
FROM a WHERE estciv IN (1,2,3,4,5) GROUP BY ALL) TO '{OUT}/cel_boot_v1_20261008.parquet' (FORMAT parquet)""")
c.sql(f"COPY (SELECT DISTINCT mun FROM a ORDER BY mun) TO '{OUT}/clusters_boot_v1_20261008.csv' (HEADER)")
print('n boot', c.sql("select count(*) from a where estciv in (1,2,3,4,5)").fetchone())
