# -*- coding: utf-8 -*-
"""Auditoria independente - etapa 2 (DuckDB SQL; sem pandas/statsmodels).
A. indice de acesso (1o tri) por regiao de saude x ano, 2014-2024 + sorteio de 10 pares
B. tercis do indice t-1 ponderados por nascimentos da amostra
C. agregados para o modelo M2 (ajustado em R)
Somente leitura nos dados; grava apenas agregados nesta pasta."""
import duckdb, numpy as np, csv, os

OUT = "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa2"
RAW = "/Volumes/Forja/CliMaterna/01_data/raw/SINASC/sinasc_{}.parquet"
REG = "/Volumes/Forja/ptb-racial-brasil/docs/referencias/territorio_dez24/rl_municip_regsaud.csv"
V3 = "/Volumes/Forja/ptb-racial-brasil/data/processed/sinasc_brasil_2015_2024_v3_20261008/*/part-0.parquet"

con = duckdb.connect()
con.sql("SET threads=8")
con.sql(f"""CREATE TABLE reg AS SELECT lpad(CAST(CO_MUNICIP AS VARCHAR),6,'0') AS mun,
                CAST(CO_REGSAUD AS VARCHAR) AS rs FROM read_csv('{REG}', all_varchar=true)""")
print("municipios na tabela:", con.sql("select count(*), count(distinct mun), count(distinct rs) from reg").fetchone())

# ---------- A. indice ----------
parts = []
for y in range(2014, 2025):
    parts.append(f"""SELECT {y} AS ano, TRIM(CAST(CODMUNRES AS VARCHAR)) AS mun,
        TRY_CAST(NULLIF(TRIM(CAST(MESPRENAT AS VARCHAR)),'') AS DOUBLE) AS mp
        FROM read_parquet('{RAW.format(y)}')""")
con.sql("CREATE TABLE raw AS " + " UNION ALL ".join(parts))
print("brutos por ano:", con.sql("select ano,count(*) from raw group by 1 order by 1").fetchall())
print("brutos sem regiao (nao mapeados) por ano:",
      con.sql("select ano,count(*) from raw r anti join reg g on r.mun=g.mun group by 1 order by 1").fetchall())
print("MESPRENAT nao inteiro 1-9 nem 99/nulo:",
      con.sql("select count(*) from raw where mp is not null and mp<>99 and not (mp between 1 and 9 and mp=floor(mp))").fetchone())
con.sql("""CREATE TABLE idx AS
  SELECT g.rs, r.ano, COUNT(*) AS n_res,
         SUM(CASE WHEN mp BETWEEN 1 AND 9 AND mp=floor(mp) THEN 1 ELSE 0 END) AS n_valido,
         SUM(CASE WHEN mp BETWEEN 1 AND 3 AND mp=floor(mp) THEN 1 ELSE 0 END) AS n_1tri
  FROM raw r JOIN reg g ON r.mun=g.mun GROUP BY 1,2""")
con.sql("ALTER TABLE idx ADD COLUMN indice DOUBLE")
con.sql("UPDATE idx SET indice = 100.0*n_1tri/n_valido")
con.sql(f"COPY (SELECT * FROM idx ORDER BY rs, ano) TO '{OUT}/indice_regsaud_ano_2014_2024.csv' (HEADER)")
print("pares (rs,ano):", con.sql("select count(*), count(distinct rs), min(indice), max(indice), sum(n_valido=0::int) from idx").fetchone())

pairs = con.sql("SELECT rs, ano, n_res, n_valido, n_1tri, indice FROM idx ORDER BY rs, ano").fetchall()
rng = np.random.default_rng(42)
sel = rng.choice(len(pairs), size=10, replace=False)
with open(f"{OUT}/sorteio_10_pares_seed42.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["ordem_sorteio", "posicao_0based", "CO_REGSAUD", "ano", "n_res", "n_mesprenat_valido", "n_1tri", "indice"])
    for k, i in enumerate(sel):
        p = pairs[i]; w.writerow([k + 1, int(i), p[0], p[1], p[2], p[3], p[4], f"{p[5]:.4f}"])
        print("SORTEIO", k + 1, int(i), p[0], p[1], p[2], p[3], p[4], f"{p[5]:.4f}")

# ---------- amostra analitica (v3, colunas brutas) ----------
con.sql(f"""CREATE TABLE v3 AS SELECT CAST(ano AS INTEGER) ano, TRIM(CODMUNRES) mun,
   CAST(RACACORMAE AS INTEGER) raca, CAST(SEMAGESTAC AS INTEGER) sg, CAST(ESCMAE AS INTEGER) esc,
   CAST(IDADEMAE AS INTEGER) idade, CAST(STTRABPART AS INTEGER) stt, CAST(STCESPARTO AS INTEGER) stc,
   CAST(PARTO AS INTEGER) parto
   FROM read_parquet('{V3}', hive_partitioning=true, hive_types={{'ano':BIGINT}})""")
cas = con.sql("""SELECT count(*),
  count(*) FILTER (WHERE raca IN (1,2,4,5)),
  count(*) FILTER (WHERE raca IN (1,2,4,5) AND sg BETWEEN 22 AND 44),
  count(*) FILTER (WHERE raca IN (1,2,4,5) AND sg BETWEEN 22 AND 44 AND esc BETWEEN 1 AND 5),
  count(*) FILTER (WHERE raca IN (1,2,4,5) AND sg BETWEEN 22 AND 44 AND esc BETWEEN 1 AND 5 AND idade BETWEEN 10 AND 60)
  FROM v3""").fetchone()
print("CASCATA total/raca/IG/esc/idade:", cas)
con.sql("""CREATE TABLE am AS SELECT v.*, g.rs,
   CASE WHEN sg<37 THEN 1 ELSE 0 END AS ptb,
   CASE WHEN sg>=37 THEN 0
        WHEN stt=1 OR (parto=2 AND stc=1) THEN 0
        WHEN stt=2 AND (parto=1 OR (parto=2 AND stc=2)) THEN 1
        ELSE NULL END AS ptb_esp,
   CASE WHEN idade<20 THEN 'lt20' WHEN idade<=34 THEN '20_34' ELSE 'ge35' END AS faixa,
   substr(v.mun,1,1) AS macro
   FROM v3 v LEFT JOIN reg g ON v.mun=g.mun
   WHERE raca IN (1,2,4,5) AND sg BETWEEN 22 AND 44 AND esc BETWEEN 1 AND 5 AND idade BETWEEN 10 AND 60""")
print("amostra n:", con.sql("select count(*) from am").fetchone())
print("sem regiao de saude:", con.sql("select count(*), count(*) filter (where mun like '%0000') from am where rs is null").fetchone())
print("ptb_esp: n_nao_nulo, soma, ptb_sem_class:", con.sql("select count(ptb_esp), sum(ptb_esp), count(*) filter (where ptb=1 and ptb_esp is null) from am").fetchone())
print("macro distintos:", con.sql("select macro,count(*) from am group by 1 order by 1").fetchall())

# ---------- B. tercis ----------
con.sql("""CREATE TABLE par AS SELECT a.rs, a.ano, COUNT(*) AS nb, i.indice AS ind_lag
   FROM am a LEFT JOIN idx i ON i.rs=a.rs AND i.ano=a.ano-1
   WHERE a.rs IS NOT NULL GROUP BY a.rs, a.ano, i.indice""")
print("pares amostra / sem indice t-1:", con.sql("select count(*), count(*) filter (where ind_lag is null), sum(nb) filter (where ind_lag is null) from par").fetchone())
cuts = con.sql("""WITH s AS (SELECT ind_lag, SUM(nb) nb FROM par WHERE ind_lag IS NOT NULL GROUP BY 1),
   c AS (SELECT ind_lag, SUM(nb) OVER (ORDER BY ind_lag) / SUM(nb) OVER () AS cf FROM s)
   SELECT MIN(ind_lag) FILTER (WHERE cf >= 1.0/3), MIN(ind_lag) FILTER (WHERE cf >= 2.0/3) FROM c""").fetchone()
c1, c2 = cuts
print(f"CORTES: c1={c1:.4f} c2={c2:.4f} (raw {c1!r} {c2!r})")
ter = con.sql(f"""SELECT CASE WHEN ind_lag <= {c1!r} THEN 'T1' WHEN ind_lag <= {c2!r} THEN 'T2' ELSE 'T3' END t,
   SUM(nb) n, COUNT(*) npares FROM par WHERE ind_lag IS NOT NULL GROUP BY 1 ORDER BY 1""").fetchall()
tot = sum(r[1] for r in ter)
with open(f"{OUT}/tercis_cortes_e_distribuicao.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["tercil", "n_nasc", "pct_nasc", "n_pares", "corte1", "corte2"])
    for r in ter:
        w.writerow([r[0], r[1], f"{100*r[1]/tot:.4f}", r[2], f"{c1:.4f}", f"{c2:.4f}"])
        print("TERCIL", r[0], r[1], f"{100*r[1]/tot:.4f}%", r[2])
print("total com tercil:", tot)

# ---------- C. agregados para R ----------
con.sql(f"""COPY (SELECT raca, faixa, ano, macro, mun, COUNT(*) n, SUM(ptb) y_ptb,
     COUNT(ptb_esp) n_esp, SUM(ptb_esp) y_esp
   FROM am GROUP BY ALL ORDER BY ALL) TO '{OUT}/agregado_m2_raca_idade_ano_macro_mun.csv' (HEADER)""")
print("OK")
