# Auditoria independente Etapa 6 - agregacao em celulas (somente leitura nos dados)
# Saidas: celulas agregadas (sem microdados) para os modelos A e C.
import duckdb, os
OUT = "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa6"
B = "/Volumes/Forja/ptb-racial-brasil/data/processed/sinasc_brasil_2015_2024_v3_20261008/ano=*/part-0.parquet"
T = "/Volumes/Forja/ptb-racial-brasil/data/processed/tercil_reg_regsaude_ano_v1_20261008.csv"
c = duckdb.connect()
c.sql(f"""create view b as select raca, idade_cat, regiao, CODMUNRES, CO_REGSAUD, pig, ptb_esp, ptb_tipo, ano::int as ano
          from read_parquet('{B}', hive_partitioning=true) where incl""")
c.sql(f"""create table t as select CO_REGSAUD::varchar as CO_REGSAUD, ano::int as ano, tercil_reg
          from read_csv('{T}', all_varchar=true)""")
print("N incl:", c.sql("select count(*) from b").fetchone())
print("dup tercil:", c.sql("select count(*) from (select CO_REGSAUD,ano,count(*) n from t group by all having n>1)").fetchone())
print("CO_REGSAUD nulo:", c.sql("select count(*) from b where CO_REGSAUD is null").fetchone())
print("sem tercil (com regsaud):", c.sql("""select count(*) from b left join t using (CO_REGSAUD, ano)
       where b.CO_REGSAUD is not null and t.tercil_reg is null""").fetchone())
print("distrib raca:", c.sql("select raca,count(*) from b group by 1 order by 1").fetchall())
print("distrib ptb_tipo:", c.sql("select ptb_tipo,count(*) from b group by 1 order by 1").fetchall())
# Modelo A: celulas por desfecho
for d in ["pig", "ptb_esp"]:
    c.sql(f"""copy (select b.CO_REGSAUD, raca, idade_cat, regiao, b.ano, t.tercil_reg,
                count(*) n, sum({d}) y
             from b join t using (CO_REGSAUD, ano)
             where {d} is not null and b.CO_REGSAUD is not null
             group by all) to '{OUT}/cel_A_{d}_v1_20261008.csv' (header)""")
    print(d, c.sql(f"select count(*), sum(n), sum(y), count(distinct CO_REGSAUD) from read_csv('{OUT}/cel_A_{d}_v1_20261008.csv')").fetchall())
# Modelo C: multinomial - cluster = regsaud ou UF (para nulos)
c.sql(f"""copy (select coalesce(b.CO_REGSAUD, 'UF'||substr(CODMUNRES,1,2)) as clus,
              b.CO_REGSAUD, raca, idade_cat, regiao, b.ano, t.tercil_reg,
              count(*) n,
              sum((ptb_tipo is null)::int) y0,
              sum((ptb_tipo='espontaneo')::int) y1,
              sum((ptb_tipo='indicado')::int) y2
           from b left join t using (CO_REGSAUD, ano)
           where ptb_tipo is null or ptb_tipo in ('espontaneo','indicado')
           group by all) to '{OUT}/cel_C_v1_20261008.csv' (header)""")
print("C", c.sql(f"select count(*), sum(n), sum(y0), sum(y1), sum(y2), count(distinct clus) from read_csv('{OUT}/cel_C_v1_20261008.csv')").fetchall())
