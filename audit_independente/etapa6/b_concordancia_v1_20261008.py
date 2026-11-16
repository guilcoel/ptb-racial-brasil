# Auditoria independente Etapa 6 - Tarefa B: concordancia IG(DUM) x SEMAGESTAC por TPMETESTIM
# Somente leitura nos brutos; saida apenas agregada.
import duckdb
OUT = "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa6"
R = "/Volumes/Forja/CliMaterna/01_data/raw/SINASC/sinasc_{y}.parquet"
c = duckdb.connect()
def num(col):  # texto ou double -> inteiro
    return f"TRY_CAST(TRY_CAST(TRIM(CAST({col} AS VARCHAR)) AS DOUBLE) AS INTEGER)"
def dt(col):   # texto DDMMAAAA -> date (lpad por seguranca)
    return f"TRY_STRPTIME(LPAD(TRIM(CAST({col} AS VARCHAR)),8,'0'), '%d%m%Y')::DATE"
parts = []
for y in range(2015, 2025):
    parts.append(f"""select {y} as ano, {num('RACACORMAE')} rc, {num('SEMAGESTAC')} sg, {num('ESCMAE')} esc,
       {num('IDADEMAE')} id, {num('TPMETESTIM')} tp, {dt('DTNASC')} dn, {dt('DTULTMENST')} dum,
       DTULTMENST is not null and TRIM(CAST(DTULTMENST AS VARCHAR))<>'' as dum_pre
       from read_parquet('{R.format(y=y)}')""")
c.sql("create view raw as " + " union all ".join(parts))
c.sql("""create table casc as select * from raw where rc in (1,2,4,5) and sg between 22 and 44
         and esc between 1 and 5 and id between 10 and 60""")
n = c.sql("select count(*) from casc").fetchone()[0]
print("N cascata:", n, "(esperado 25808740)")
print("DTNASC nao parseavel:", c.sql("select count(*) from casc where dn is null").fetchone())
print("TPMETESTIM:", c.sql("select tp, count(*) from casc group by 1 order by 1").fetchall())
c.sql("""create table v as select *, (dum is not null and dn is not null and dum < dn and datediff('day',dum,dn) <= 365) as val,
         case when dum is not null and dn is not null and dum < dn and datediff('day',dum,dn) <= 365
              then floor(datediff('day',dum,dn)/7.0)::int end as ig_dum,
         case when tp in (1,2,8) then tp::varchar else '9/nulo' end as cod from casc""")
q = """select {g} as cod, count(*) n, avg(val::int)*100 pct_dum_valida,
   sum(val::int) n_validas,
   avg(case when val then (sg=ig_dum)::int end)*100 pct_exata,
   avg(case when val then (abs(sg-ig_dum)<=1)::int end)*100 pct_pm1,
   avg(case when val then sg-ig_dum end) media_dif,
   stddev_samp(case when val then sg-ig_dum end) dp_dif
   from v {w} group by all"""
res = c.sql(q.format(g="cod", w="") + " union all " + q.format(g="'Total'", w="")).df().sort_values("cod")
print(res.to_string())
res.to_csv(f"{OUT}/b_concordancia_v1_20261008.csv", index=False)
# por ano para diagnostico
res2 = c.sql(q.format(g="ano, cod", w="")).df().sort_values(["ano","cod"])
res2.to_csv(f"{OUT}/b_concordancia_por_ano_v1_20261008.csv", index=False)
print(res2.to_string())
