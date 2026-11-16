#!/usr/bin/env python3
"""Auditoria independente SINASC 2015-2024 (DuckDB SQL).

Implementacao independente: nao le scripts/ nem outputs/ do projeto.
Brutos: somente leitura. Saidas: apenas contagens agregadas em CSV.
"""
import duckdb

RAW = "/Volumes/Forja/CliMaterna/01_data/raw/SINASC/sinasc_{y}.parquet"
PROC = "/Volumes/Forja/ptb-racial-brasil/data/processed/sinasc_brasil_2015_2024_v1_20261008/*/*.parquet"
OUT = "/Volumes/Forja/ptb-racial-brasil/audit_independente/"
ANOS = range(2015, 2025)

con = duckdb.connect()
con.sql("SET preserve_insertion_order=false")


def wcsv(rel_sql, nome):
    con.sql(f"COPY ({rel_sql}) TO '{OUT}{nome}' (HEADER, DELIMITER ',')")
    return con.sql(rel_sql)


# inteiro robusto: VARCHAR com zeros/brancos ou DOUBLE (2023). Nao-integral -> nulo.
con.sql("""
CREATE MACRO toint(x) AS (
  CASE WHEN TRY_CAST(NULLIF(TRIM(CAST(x AS VARCHAR)), '') AS DOUBLE) IS NOT NULL
        AND TRY_CAST(NULLIF(TRIM(CAST(x AS VARCHAR)), '') AS DOUBLE)
            = FLOOR(TRY_CAST(NULLIF(TRIM(CAST(x AS VARCHAR)), '') AS DOUBLE))
       THEN CAST(TRY_CAST(NULLIF(TRIM(CAST(x AS VARCHAR)), '') AS DOUBLE) AS INTEGER)
  END)
""")

# Tabela de trabalho a partir dos brutos (somente variaveis necessarias)
partes = []
for y in ANOS:
    partes.append(f"""
    SELECT {y} AS ano_arq,
           TRY_CAST(RIGHT(TRIM(CAST(DTNASC AS VARCHAR)), 4) AS INTEGER) AS ano_dt,
           SUBSTR(TRIM(CAST(CODMUNRES AS VARCHAR)), 1, 2) AS cod_uf,
           toint(RACACORMAE) AS raca, toint(SEMAGESTAC) AS sg,
           toint(ESCMAE) AS esc, toint(IDADEMAE) AS idade,
           toint(STTRABPART) AS sttrab, toint(PARTO) AS parto,
           toint(STCESPARTO) AS stces
    FROM read_parquet('{RAW.format(y=y)}')""")
con.sql("CREATE TABLE w AS " + " UNION ALL ".join(partes))
con.sql("""
CREATE TABLE b AS
SELECT *,
  CASE SUBSTR(cod_uf,1,1) WHEN '1' THEN 'N' WHEN '2' THEN 'NE' WHEN '3' THEN 'SE'
       WHEN '4' THEN 'S' WHEN '5' THEN 'CO' ELSE 'IGN' END AS regiao,
  (raca IN (1,2,4,5)) IS TRUE AS p1,
  (sg BETWEEN 22 AND 44) IS TRUE AS p2,
  (esc BETWEEN 1 AND 5) IS TRUE AS p3,
  (idade BETWEEN 10 AND 60) IS TRUE AS p4
FROM w""")
con.sql("CREATE VIEW p AS SELECT * FROM read_parquet('" + PROC + "', hive_partitioning=true)")

# ---------------- A ----------------
print("== A: n por ano ==")
print(wcsv("""
WITH r AS (SELECT ano_arq AS ano, COUNT(*) n_bruto,
                  SUM((ano_dt <> ano_arq)::INT) n_ano_dtnasc_difere
           FROM b GROUP BY 1),
     q AS (SELECT CAST(ano AS INTEGER) ano, COUNT(*) n_proc FROM p GROUP BY 1)
SELECT COALESCE(r.ano,q.ano) ano, n_bruto, n_proc, n_bruto - n_proc AS dif,
       n_ano_dtnasc_difere
FROM r FULL JOIN q ON r.ano=q.ano
UNION ALL
SELECT 9999, (SELECT COUNT(*) FROM b), (SELECT COUNT(*) FROM p),
       (SELECT COUNT(*) FROM b)-(SELECT COUNT(*) FROM p),
       (SELECT SUM((ano_dt<>ano_arq)::INT) FROM b)
ORDER BY 1""", "A_n_ano.csv"))

wcsv("""
WITH r AS (SELECT ano_arq ano, cod_uf, COUNT(*) n_bruto FROM b GROUP BY 1,2),
     q AS (SELECT CAST(ano AS INTEGER) ano, cod_uf, COUNT(*) n_proc FROM p GROUP BY 1,2)
SELECT COALESCE(r.ano,q.ano) ano, COALESCE(r.cod_uf,q.cod_uf) cod_uf,
       COALESCE(n_bruto,0) n_bruto, COALESCE(n_proc,0) n_proc,
       COALESCE(n_bruto,0)-COALESCE(n_proc,0) dif
FROM r FULL JOIN q ON r.ano=q.ano AND r.cod_uf=q.cod_uf ORDER BY 1,2""", "A_n_uf_ano.csv")
print(con.sql(f"""SELECT COUNT(*) celulas, SUM((dif<>0)::INT) celulas_diferentes,
                  SUM(ABS(dif)) soma_abs_dif FROM read_csv('{OUT}A_n_uf_ano.csv')"""))
# conferencia do ano do DTNASC na base processada
print(con.sql("SELECT SUM((YEAR(DTNASC)<>ano)::INT) proc_ano_dtnasc_difere, "
              "SUM((_ano_arquivo<>ano)::INT) proc_anoarq_difere, "
              "SUM((SUBSTR(CODMUNRES,1,2)<>cod_uf)::INT) proc_coduf_difere FROM p"))

# ---------------- B ----------------
print("== B: duplicatas ==")
linhas = []
for y in ANOS:
    f = RAW.format(y=y)
    cols = [r[0] for r in con.sql(f"DESCRIBE SELECT * FROM read_parquet('{f}')").fetchall()]
    sem_cont = [c for c in cols if c.lower() != "contador"]
    lst_all = ", ".join(f'"{c}"' for c in cols)
    lst_sc = ", ".join(f'"{c}"' for c in sem_cont)
    d_all = con.sql(f"SELECT COUNT(*) FROM (SELECT DISTINCT {lst_all} FROM read_parquet('{f}'))").fetchone()[0]
    n = con.sql(f"SELECT COUNT(*) FROM read_parquet('{f}')").fetchone()[0]
    d_sc = con.sql(f"SELECT COUNT(*) FROM (SELECT DISTINCT {lst_sc} FROM read_parquet('{f}'))").fetchone()[0]
    linhas.append((f"bruto_{y}", len(cols), n, n - d_all,
                   (n - d_sc) if len(sem_cont) < len(cols) else None))
pcols = [r[0] for r in con.sql("DESCRIBE SELECT * FROM p").fetchall()]
lst = ", ".join(f'"{c}"' for c in pcols)
n = con.sql("SELECT COUNT(*) FROM p").fetchone()[0]
d = con.sql(f"SELECT COUNT(*) FROM (SELECT DISTINCT {lst} FROM p)").fetchone()[0]
linhas.append(("processada_todas_colunas", len(pcols), n, n - d, None))
for y in ANOS:
    ny, dy = con.sql(f"SELECT COUNT(*), (SELECT COUNT(*) FROM (SELECT DISTINCT {lst} FROM p WHERE ano={y})) FROM p WHERE ano={y}").fetchone()
    linhas.append((f"processada_{y}", len(pcols), ny, ny - dy, None))
con.sql("CREATE TABLE dup(base VARCHAR, n_colunas INT, n BIGINT, excesso_todas_colunas BIGINT, excesso_sem_contador BIGINT)")
con.executemany("INSERT INTO dup VALUES (?,?,?,?,?)", linhas)
print(wcsv("SELECT * FROM dup", "B_duplicatas.csv"))

# ---------------- C ----------------
print("== C: fluxograma ==")
FLUXO = """
SELECT {g} AS grupo,
  COUNT(*) n0_fonte,
  COUNT(*) FILTER (WHERE NOT p1) exc1_raca,
  COUNT(*) FILTER (WHERE p1) n1,
  COUNT(*) FILTER (WHERE p1 AND NOT p2) exc2_ig,
  COUNT(*) FILTER (WHERE p1 AND p2) n2,
  COUNT(*) FILTER (WHERE p1 AND p2 AND NOT p3) exc3_esc,
  COUNT(*) FILTER (WHERE p1 AND p2 AND p3) n3,
  COUNT(*) FILTER (WHERE p1 AND p2 AND p3 AND NOT p4) exc4_idade,
  COUNT(*) FILTER (WHERE p1 AND p2 AND p3 AND p4) n4_final
FROM b {w} GROUP BY ALL"""
print(wcsv(FLUXO.format(g="'BR'", w="") + " UNION ALL " +
           FLUXO.format(g="regiao", w="") + " ORDER BY 1", "C_fluxograma.csv"))
con.sql("CREATE TABLE a AS SELECT * FROM b WHERE p1 AND p2 AND p3 AND p4")
RACA = """
SELECT {g} AS grupo, raca,
  CASE raca WHEN 1 THEN 'Branca' WHEN 2 THEN 'Preta' WHEN 4 THEN 'Parda' WHEN 5 THEN 'Indigena' END rotulo,
  COUNT(*) n, SUM((sg<37)::INT) n_ptb, ROUND(100.0*SUM((sg<37)::INT)/COUNT(*),4) ptb_pct
FROM a {w} GROUP BY ALL"""
print(wcsv(RACA.format(g="'BR'", w="") + " UNION ALL " +
           RACA.format(g="regiao", w="") + " ORDER BY 1,2", "C_raca_ptb.csv").limit(40))
print(con.sql("SELECT 'BR' grupo, COUNT(*) n, SUM((sg<37)::INT) ptb, ROUND(100.0*AVG((sg<37)::INT),4) pct FROM a"))

# ---------------- D ----------------
print("== D: Centro-Oeste ==")
print(wcsv(FLUXO.format(g="cod_uf", w="WHERE regiao='CO'") + " UNION ALL " +
           FLUXO.format(g="'CO'", w="WHERE regiao='CO'") + " ORDER BY 1", "D_fluxograma_CO.csv"))
print(wcsv("""
WITH pub(raca, n_pub, ptb_pub) AS (VALUES (1,610353,11.1),(4,1392713,11.0),(2,115766,11.7),(5,37842,17.6))
SELECT r.*, pub.n_pub, r.n - pub.n_pub dif_n, pub.ptb_pub
FROM (""" + RACA.format(g="'CO'", w="WHERE regiao='CO'") + """) r JOIN pub USING (raca)
ORDER BY raca""", "D_raca_ptb_CO.csv"))

# ---------------- E ----------------
print("== E: fenotipo entre PTB ==")
E = """
SELECT {g} AS grupo,
  COUNT(*) n_ptb,
  COUNT(*) FILTER (WHERE cls='indicada') n_indicada,
  COUNT(*) FILTER (WHERE cls='espontanea') n_espontanea,
  COUNT(*) FILTER (WHERE cls='sem_classificacao') n_sem_class,
  ROUND(100.0*COUNT(*) FILTER (WHERE cls='indicada')/COUNT(*),4) pct_indicada,
  ROUND(100.0*COUNT(*) FILTER (WHERE cls='espontanea')/COUNT(*),4) pct_espontanea,
  ROUND(100.0*COUNT(*) FILTER (WHERE cls='sem_classificacao')/COUNT(*),4) pct_sem_class
FROM (SELECT regiao,
        CASE WHEN (sttrab=1) IS TRUE OR (parto=2 AND stces=1) IS TRUE THEN 'indicada'
             WHEN (sttrab=2 AND (parto=1 OR (parto=2 AND stces=2))) IS TRUE THEN 'espontanea'
             ELSE 'sem_classificacao' END cls
      FROM a WHERE sg < 37) t
GROUP BY ALL"""
print(wcsv(E.format(g="'BR'") + " UNION ALL " + E.format(g="regiao") + " ORDER BY 1",
           "E_fenotipo_ptb.csv"))

# Diagnosticos de valores fora do dominio (agregados)
print(wcsv("""
SELECT 'raca' var, raca::VARCHAR valor, COUNT(*) n FROM b GROUP BY ALL
UNION ALL SELECT 'esc', esc::VARCHAR, COUNT(*) FROM b GROUP BY ALL
UNION ALL SELECT 'regiao', regiao, COUNT(*) FROM b GROUP BY ALL
UNION ALL SELECT 'sttrab_ptb', sttrab::VARCHAR, COUNT(*) FROM a WHERE sg<37 GROUP BY ALL
UNION ALL SELECT 'parto_ptb', parto::VARCHAR, COUNT(*) FROM a WHERE sg<37 GROUP BY ALL
UNION ALL SELECT 'stces_ptb', stces::VARCHAR, COUNT(*) FROM a WHERE sg<37 GROUP BY ALL
ORDER BY 1,2""", "Z_dominios.csv").limit(80))
