# Auditoria independente — Etapa 7b2 (TPMETESTIM 1 vs 2; P97; reclassificação)
# Auditor independente, 2026-10-09. Somente leitura nos dados; saídas só agregadas.
# Estratégia: agregação exata em células (cluster × raça × idade × ano × região × tercil),
# Poisson log por IRLS ponderado (MLE idêntico ao individual), sanduíche agrupado com
# correção G/(G-1)·(N-1)/(N-K), N = nº de indivíduos.
import duckdb, numpy as np, pandas as pd, os, sys, json
from scipy import stats

np.random.seed(42)
ROOT = '/Volumes/Forja/ptb-racial-brasil'
OUT = f'{ROOT}/audit_independente/etapa7b2'
SP = sys.argv[1] if len(sys.argv) > 1 else '/tmp'
TAG = 'v1_20261009'

con = duckdb.connect()
con.sql("SET threads=8")
con.sql(f"""create view b as select * from read_parquet('{ROOT}/data/processed/sinasc_brasil_2015_2024_v3_20261008/ano=*/part-0.parquet', hive_partitioning=true) where incl""")
con.sql(f"""create table terc as select CAST(CO_REGSAUD AS VARCHAR) CO_REGSAUD, CAST(ano AS BIGINT) ano, tercil_reg
            from read_csv('{ROOT}/data/processed/tercil_reg_regsaude_ano_v1_20261008.csv', all_varchar=true)""")
# P97 oficial (tabela): peso_kg -> g
con.sql(f"""create table p97t as select case sexo when 'M' then 1 when 'F' then 2 end SEXO, CAST(gest_days AS INTEGER) gest_days,
            round(CAST(peso_kg AS DOUBLE)*1000) p97_tab_g
            from read_csv('{ROOT}/docs/referencias/intergrowth21_bw_centis_oficial.csv') where centil=97""")
con.sql(f"create table p97e as select CAST(SEXO AS INTEGER) SEXO, CAST(gest_days AS INTEGER) gest_days, p97_eq_g from read_csv('{SP}/p97_gigs.csv')")
chk = con.sql("select count(*), count(distinct (SEXO, gest_days)) from p97t").fetchall()
print('p97 tabela linhas/chaves:', chk)

con.sql("""
create table d as
select
  case when TPMETESTIM=1 then '1' when TPMETESTIM=2 then '2' else 'outro' end tpm,
  coalesce(b.CO_REGSAUD, 'UF_' || substr(b.CODMUNRES,1,2)) cl,
  (b.CO_REGSAUD is not null) has_reg,
  t.tercil_reg tercil,
  raca, idade_cat, b.ano, regiao,
  ptb, pig, ptb_ind, ptb_esp,
  (b.unica=1 and b.SEMAGESTAC between 24 and 36 and b.SEXO in (1,2) and b.PESO between 100 and 7000) elig,
  pt.p97_tab_g, pe.p97_eq_g, PESO
from b
left join terc t on t.CO_REGSAUD=b.CO_REGSAUD and t.ano=b.ano
left join p97t pt on pt.SEXO=b.SEXO and pt.gest_days=7*b.SEMAGESTAC+3
left join p97e pe on pe.SEXO=b.SEXO and pe.gest_days=7*b.SEMAGESTAC+3
""")
print(con.sql("select count(*), sum(has_reg and tercil is null), sum(elig and ptb=1), sum(elig and ptb=1 and p97_tab_g is null), sum(elig and ptb=1 and p97_eq_g is null) from d").fetchall())

con.sql("""
create table d2 as select *,
  coalesce(elig and ptb=1 and PESO > p97_tab_g, false) gt_tab,
  coalesce(elig and ptb=1 and PESO > p97_eq_g, false) gt_eq
from d""")

cells = con.sql("""
select tpm, cl, has_reg, tercil, raca, idade_cat, ano, regiao,
  count(*) n, sum(ptb) y_ptb,
  count(pig) n_pig, sum(pig) y_pig,
  count(ptb_ind) n_ind, sum(ptb_ind) y_ind,
  count(ptb_esp) n_esp, sum(ptb_esp) y_esp,
  sum(case when gt_tab then 0 else ptb end) y_ptb_rc,
  sum(case when gt_tab and ptb_esp=1 then 0 else ptb_esp end) y_esp_rc,
  sum(case when gt_eq then 0 else ptb end) y_ptb_rceq,
  sum(case when gt_eq and ptb_esp=1 then 0 else ptb_esp end) y_esp_rceq
from d2 group by all
""").df()
for c in cells.columns:
    if c.startswith('n') or c.startswith('y_'):
        cells[c] = cells[c].fillna(0).astype(float)
cells.to_parquet(f'{SP}/cells_7b2.parquet')

# B: P97 por raça e TPM (agregados)
B = con.sql("""
select tpm, raca, sum((elig and ptb=1)::int) n_elig_ptb, sum(gt_tab::int) n_gt97_tab, sum(gt_eq::int) n_gt97_eq
from d2 group by all order by all""").df()
B.to_csv(f'{SP}/B_raw.csv', index=False)
recl = con.sql("""
select sum(gt_tab::int) ptb_rc_tab, sum((gt_tab and ptb_esp=1)::int) esp_rc_tab,
       sum((gt_tab and ptb_ind=1)::int) ind_rc_tab, sum((gt_tab and ptb_esp is null)::int) naoclass_rc_tab,
       sum(gt_eq::int) ptb_rc_eq, sum((gt_eq and ptb_esp=1)::int) esp_rc_eq,
       sum((gt_tab and not gt_eq)::int) so_tab, sum((gt_eq and not gt_tab)::int) so_eq,
       sum((gt_tab and not gt_eq and ptb_esp=1)::int) so_tab_esp, sum((gt_eq and not gt_tab and ptb_esp=1)::int) so_eq_esp
from d2""").df()
recl.to_csv(f'{SP}/recl_raw.csv', index=False)
print(recl.T)
