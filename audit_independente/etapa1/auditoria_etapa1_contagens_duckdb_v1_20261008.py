# Auditoria independente etapa 1 - contagens em DuckDB SQL (sem pandas/statsmodels).
# Usa somente colunas brutas + particao ano; deriva tudo aqui.
import duckdb, numpy as np, csv
OUT='/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa1/'
SRC='/Volumes/Forja/ptb-racial-brasil/data/processed/sinasc_brasil_2015_2024_v2_20261008/**/*.parquet'
c=duckdb.connect(); c.sql("SET threads=8; SET memory_limit='16GB'")
c.sql(f"""create view raw as select CODMUNRES,RACACORMAE,SEMAGESTAC,ESCMAE,IDADEMAE,GRAVIDEZ,PESO,SEXO,
  STTRABPART,STCESPARTO,PARTO,ano, filename, file_row_number
  from read_parquet('{SRC}', hive_partitioning=true, filename=true, file_row_number=true)""")
# cascata
casc=[('total','true'),('raca','RACACORMAE in (1,2,4,5)'),('ig22_44','SEMAGESTAC between 22 and 44'),
      ('esc1_5','ESCMAE between 1 and 5'),('idade10_60','IDADEMAE between 10 and 60')]
cond=[]; cascata=[]
for nome,cc in casc:
    cond.append(cc); n=c.sql('select count(*) from raw where '+' and '.join(cond)).fetchone()[0]; cascata.append((nome,n)); print(nome,n)
c.sql('create temp table ig as select * from read_csv_auto(\''+OUT+'ig21_bw_centis_extraidos_pdf_v1_20261008.csv\')')
c.sql("""create temp table a as
select CODMUNRES mun, substr(CODMUNRES,1,2) uf, substr(CODMUNRES,1,1)::int reg, RACACORMAE raca, ano, ESCMAE esc, IDADEMAE idade,
  SEMAGESTAC ig, PESO peso, SEXO sexo, GRAVIDEZ grav, filename fn, file_row_number frn,
  (SEMAGESTAC<37)::int ptb, (SEMAGESTAC<28)::int ptb_lt28, (SEMAGESTAC between 28 and 31)::int ptb_28_31, (SEMAGESTAC between 32 and 36)::int ptb_32_36,
  case when SEMAGESTAC between 37 and 41 and PESO between 100 and 7000 then (PESO<2500)::int end lbw_termo,
  (GRAVIDEZ=1 and SEMAGESTAC between 24 and 42 and SEXO in (1,2) and PESO between 100 and 7000) pig_eleg,
  case when SEMAGESTAC<37 then
    case when coalesce(STTRABPART,-1)=1 or (coalesce(PARTO,-1)=2 and coalesce(STCESPARTO,-1)=1) then 'indicado'
         when coalesce(STTRABPART,-1)=2 and (coalesce(PARTO,-1)=1 or (coalesce(PARTO,-1)=2 and coalesce(STCESPARTO,-1)=2)) then 'espontaneo'
         else 'sem_class' end end ptb_tipo
from raw where RACACORMAE in (1,2,4,5) and SEMAGESTAC between 22 and 44 and ESCMAE between 1 and 5 and IDADEMAE between 10 and 60""")
c.sql("""create temp table b as select a.*,
  case when pig_eleg then (peso/1000.0 < g.p10)::int end pig, g.p10 p10_oficial
  from a left join ig g on pig_eleg and g.ig_dias = 7*a.ig+3 and g.sexo = case a.sexo when 1 then 'M' else 'F' end""")
print('n amostra', c.sql('select count(*) from b').fetchone()[0])
print('pig elegiveis sem p10 (deve ser 0):', c.sql('select count(*) from b where pig_eleg and p10_oficial is null').fetchone()[0])
# Tabela A longa
desf=['ptb','ptb_lt28','ptb_28_31','ptb_32_36','lbw_termo','pig']
parts=[]
for d in desf:
    parts.append(f"select '{d}' desfecho, raca, reg, sum({d}) casos, count({d}) denom from b group by grouping sets ((raca,reg),(raca),(reg),())")
for t in ['indicado','espontaneo','sem_class']:
    parts.append(f"select 'ptbtipo_{t}' desfecho, raca, reg, sum((ptb_tipo='{t}')::int) casos, count(ptb_tipo) denom from b group by grouping sets ((raca,reg),(raca),(reg),())")
q=' union all '.join(parts)
tabA=c.sql(f"select desfecho, coalesce(raca::varchar,'Todas') raca, coalesce(reg::varchar,'Brasil') regiao, casos, denom, round(100.0*casos/denom,3) pct from ({q}) order by 1,2,3").fetchall()
with open(OUT+'tabA_desfechos_raca_regiao_v1_20261008.csv','w',newline='') as fh:
    w=csv.writer(fh); w.writerow(['desfecho','raca','regiao','casos','denom','pct']); w.writerows(tabA)
with open(OUT+'cascata_amostra_v1_20261008.csv','w',newline='') as fh:
    w=csv.writer(fh); w.writerow(['etapa','n']); w.writerows(cascata)
# agregados raca x municipio p/ B (R)
c.sql(f"""copy (select raca, mun, sum(ptb) ptb_y, count(*) ptb_n, sum(lbw_termo) lbw_y, count(lbw_termo) lbw_n, sum(pig) pig_y, count(pig) pig_n
  from b group by raca, mun order by mun, raca) to '{OUT}agreg_raca_municipio_v1_20261008.csv' (header)""")
# nivel individual CO p/ C (fica no disco, na pasta de auditoria)
c.sql(f"""copy (select raca, ptb, idade, esc, ano, uf, mun from b where reg=5) to '{OUT}co_individual_C_v1_20261008.parquet' (format parquet)""")
# D: amostra de 20 elegiveis ao PIG. Metodo: ordenar elegiveis por (filename, file_row_number), numerar 0..N-1,
# indices = numpy.random.default_rng(42).choice(N, 20, replace=False)
c.sql("create temp table el as select row_number() over (order by fn, frn)-1 idx, ig, sexo, peso, p10_oficial, pig from b where pig_eleg")
N=c.sql('select count(*) from el').fetchone()[0]; idx=sorted(np.random.default_rng(42).choice(N,20,replace=False).tolist())
print('N elegiveis PIG',N)
c.sql(f"copy (select idx, ig semagestac, 7*ig+3 ig_dias, sexo, peso, p10_oficial, pig pig_oficial from el where idx in ({','.join(map(str,idx))}) order by idx) to '{OUT}D_amostra20_pig_v1_20261008.csv' (header)")
