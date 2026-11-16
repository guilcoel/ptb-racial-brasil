# Auditoria independente etapa 4 - contagens em DuckDB SQL (sem pandas). Saídas: apenas agregados.
# Reaproveita a lógica de índice/tercis da etapa 3 (auditor independente).
import duckdb
OUT = '/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa4'
V3 = "/Volumes/Forja/ptb-racial-brasil/data/processed/sinasc_brasil_2015_2024_v3_20261008/ano=*/[!.]*.parquet"
RAW = "/Volumes/Forja/CliMaterna/01_data/raw/SINASC/sinasc_{y}.parquet"
REL = "/Volumes/Forja/ptb-racial-brasil/docs/referencias/territorio_dez24/rl_municip_regsaud.csv"
CEN = "/Volumes/Forja/ptb-racial-brasil/docs/referencias/censo2022/sidra_9605_n6_2022.json"
c = duckdb.connect()
c.sql("SET threads=8")

# 0. base: raça 1-5 ou nula, demais critérios; só colunas brutas
c.sql(f"""
CREATE TABLE b AS
SELECT ano::INT ano, TRIM(CODMUNRES) mun, RACACORMAE::INT raca, SEMAGESTAC::INT sg,
       ESCMAE::INT esc, IDADEMAE::INT idade, ESTCIVMAE::INT estciv,
       STTRABPART::INT trab, STCESPARTO::INT cesp, PARTO::INT parto,
       PESO::INT peso, SEXO::INT sexo, GRAVIDEZ::INT grav, TPMETESTIM::INT tpm
FROM read_parquet('{V3}', hive_partitioning=true)
WHERE (RACACORMAE BETWEEN 1 AND 5 OR RACACORMAE IS NULL) AND SEMAGESTAC BETWEEN 22 AND 44
  AND ESCMAE BETWEEN 1 AND 5 AND IDADEMAE BETWEEN 10 AND 60
""")
print('base por raça', c.sql("select raca, count(*) from b group by 1 order by 1").fetchall())

# 1. índice de acesso 2014-2024 (bruto, todos os residentes)
c.sql(f"CREATE TABLE rel AS SELECT lpad(CAST(CO_MUNICIP AS VARCHAR),6,'0') mun, CAST(CO_REGSAUD AS VARCHAR) rs FROM read_csv('{REL}', all_varchar=true)")
parts = [f"""SELECT {y} ano, TRIM(CAST(CODMUNRES AS VARCHAR)) mun,
       TRY_CAST(TRIM(CAST(MESPRENAT AS VARCHAR)) AS DOUBLE)::INT mp FROM read_parquet('{RAW.format(y=y)}')"""
         for y in range(2014, 2025)]
c.sql("CREATE TABLE raw AS " + " UNION ALL ".join(parts))
c.sql("""CREATE TABLE idx AS
SELECT rs, ano, 100.0*SUM(CASE WHEN mp BETWEEN 1 AND 3 THEN 1 ELSE 0 END)/SUM(CASE WHEN mp BETWEEN 1 AND 9 THEN 1 ELSE 0 END) ind
FROM raw JOIN rel USING(mun) GROUP BY rs, ano""")

# 2. derivadas
c.sql("""CREATE TABLE d AS
SELECT b.*, rel.rs, CAST(substr(b.mun,1,1) AS INT) mr, idx.ind,
  CASE WHEN idade<20 THEN 'lt20' WHEN idade<=34 THEN '20_34' ELSE 'ge35' END ida,
  CASE WHEN estciv IN (2,5) THEN 'com' WHEN estciv IN (1,3,4) THEN 'sem' ELSE 'aus' END conj,
  CASE WHEN sg>=37 THEN 'termo'
       WHEN trab=1 OR (parto=2 AND cesp=1) THEN 'ind'
       WHEN trab=2 AND (parto=1 OR (parto=2 AND cesp=2)) THEN 'esp'
       ELSE 'semclass' END ptbt,
  CASE WHEN tpm=8 THEN 'DUM' WHEN tpm IN (1,2) THEN 'outro' ELSE 'ign' END igm
FROM b LEFT JOIN rel USING(mun) LEFT JOIN idx ON idx.rs=rel.rs AND idx.ano=b.ano-1""")
# PIG pela tabela oficial (P10 em kg -> gramas inteiros)
c.sql(f"CREATE TABLE p10 AS SELECT sexo, dias, CAST(round(p10_kg*1000) AS INT) p10g FROM '{OUT}/p10_intergrowth_tabela_v1_20261008.csv'")
c.sql("""CREATE TABLE d2 AS
SELECT d.*, CASE WHEN grav=1 AND sg BETWEEN 24 AND 42 AND d.sexo IN (1,2) AND peso BETWEEN 100 AND 7000
                 THEN CASE WHEN peso < p10.p10g THEN 1 ELSE 0 END END pig
FROM d LEFT JOIN p10 ON p10.sexo=d.sexo AND p10.dias=7*d.sg+3""")
print('pig elegível sem P10 (deve ser 0)', c.sql("select count(*) from d2 where grav=1 and sg between 24 and 42 and sexo in (1,2) and peso between 100 and 7000 and pig is null").fetchone())

# 3. tercis dentro da macrorregião (amostra analítica completa: raça 1,2,4,5 com índice)
c.sql("""CREATE TABLE pares AS SELECT mr, rs, ano, ind, COUNT(*) n FROM d2
         WHERE raca IN (1,2,4,5) AND ind IS NOT NULL GROUP BY ALL""")
c.sql("""CREATE TABLE cum AS SELECT *, SUM(n) OVER (PARTITION BY mr ORDER BY ind, rs, ano ROWS UNBOUNDED PRECEDING)*1.0
        / SUM(n) OVER (PARTITION BY mr) f FROM pares""")
c.sql("""CREATE TABLE cortes AS SELECT mr, MIN(ind) FILTER (WHERE f >= 1.0/3) c1, MIN(ind) FILTER (WHERE f >= 2.0/3) c2
         FROM cum GROUP BY mr""")
c.sql(f"COPY (SELECT * FROM cortes ORDER BY mr) TO '{OUT}/A_cortes_tercis_v1_20261008.csv' (HEADER)")
print(c.sql("select * from cortes order by mr").fetchall())
c.sql("""CREATE TABLE e AS SELECT d2.*, CASE WHEN ind IS NULL THEN 0 WHEN ind<=c1 THEN 1 WHEN ind<=c2 THEN 2 ELSE 3 END terc
         FROM d2 LEFT JOIN cortes USING(mr)""")
print('terc x raça nula', c.sql("select terc, raca is null, count(*) from e group by all order by all").fetchall())

# 4. células da amostra de acesso (raça 1,2,4,5, terc 1-3) para os modelos, com ig_metodo
c.sql(f"""COPY (
SELECT raca, ida, ano, mr, terc, mun, igm,
  SUM(CASE WHEN ptbt<>'semclass' THEN 1 ELSE 0 END) n_esp,
  SUM(CASE WHEN ptbt='esp' THEN 1 ELSE 0 END) y_esp,
  SUM(CASE WHEN pig IS NOT NULL THEN 1 ELSE 0 END) n_pig,
  SUM(COALESCE(pig,0)) y_pig, COUNT(*) n
FROM e WHERE raca IN (1,2,4,5) AND terc>0 GROUP BY ALL) TO '{OUT}/cel_A_v1_20261008.parquet' (FORMAT parquet)""")
print('N acesso / por igm', c.sql(f"select igm, sum(n), sum(n_esp), sum(n_pig) from '{OUT}/cel_A_v1_20261008.parquet' group by rollup(igm) order by 1").fetchall())

# 5. faixas de composição racial do município (Censo 2022, SIDRA 9605)
c.sql(f"""CREATE TABLE cen AS
WITH j AS (SELECT substr(D1C,1,6) mun, D4C cat, COALESCE(TRY_CAST(V AS BIGINT),0) v
           FROM read_json_auto('{CEN}') WHERE D4C IN ('95251','2776','2780'))
SELECT mun, 100.0*SUM(v) FILTER (WHERE cat='2776')/SUM(v) FILTER (WHERE cat='95251') pb,
            100.0*SUM(v) FILTER (WHERE cat='2780')/SUM(v) FILTER (WHERE cat='95251') pi
FROM j GROUP BY mun""")
c.sql("""CREATE TABLE fx AS SELECT mun,
  CASE WHEN pb<=20 THEN 'B1' WHEN pb<=40 THEN 'B2' WHEN pb<=60 THEN 'B3' WHEN pb<=80 THEN 'B4' ELSE 'B5' END ||
  CASE WHEN pi<=1 THEN 'I1' WHEN pi<=5 THEN 'I2' WHEN pi<=20 THEN 'I3' ELSE 'I4' END faixa FROM cen""")
print('municípios censo', c.sql("select count(*) from fx").fetchone())
c.sql("CREATE TABLE f AS SELECT e.*, COALESCE(fx.faixa,'semcenso') faixa FROM e LEFT JOIN fx USING(mun)")
print('registros sem censo', c.sql("select count(*), count(distinct mun) from f where faixa='semcenso'").fetchall())
print('faixa x raca nula', c.sql("select faixa, count(*) filter (where raca is null), count(*) from f group by 1 order by 1").fetchall())

# 6. padrões para imputação
patt = """mr, ano, ida, esc, conj, ptbt, CASE WHEN pig IS NULL THEN 'ne' ELSE CAST(pig AS VARCHAR) END pigc,
          CASE WHEN terc=0 THEN 'sem' ELSE 'T'||terc END tercc, faixa"""
c.sql(f"""COPY (SELECT {patt}, raca, COUNT(*) n FROM f WHERE raca IS NOT NULL GROUP BY ALL)
          TO '{OUT}/B_treino_padroes_v1_20261008.parquet' (FORMAT parquet)""")
# faltantes que entram no modelo PIG (elegível PIG, terc 1-3), com município para o cluster
c.sql(f"""COPY (SELECT {patt}, mun, terc, COUNT(*) n, SUM(pig) y_pig FROM f
          WHERE raca IS NULL AND pig IS NOT NULL AND terc>0 GROUP BY ALL)
          TO '{OUT}/B_faltantes_modelo_v1_20261008.parquet' (FORMAT parquet)""")
print('treino padrões/linhas', c.sql(f"select count(*), sum(n) from '{OUT}/B_treino_padroes_v1_20261008.parquet'").fetchall())
print('faltantes (todos) / no modelo PIG', c.sql("select count(*) from f where raca is null").fetchone(),
      c.sql(f"select count(*), sum(n), sum(y_pig) from '{OUT}/B_faltantes_modelo_v1_20261008.parquet'").fetchall())
