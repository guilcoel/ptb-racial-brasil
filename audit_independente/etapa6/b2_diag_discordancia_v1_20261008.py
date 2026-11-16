# Diagnostico agregado da discordancia SEMAGESTAC x floor(dias/7) (codigo 8): resto dias%7 e ano bissexto
import duckdb
OUT = "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa6"
R = "/Volumes/Forja/CliMaterna/01_data/raw/SINASC/sinasc_{y}.parquet"
c = duckdb.connect()
num = lambda col: f"TRY_CAST(TRY_CAST(TRIM(CAST({col} AS VARCHAR)) AS DOUBLE) AS INTEGER)"
dt = lambda col: f"TRY_STRPTIME(LPAD(TRIM(CAST({col} AS VARCHAR)),8,'0'), '%d%m%Y')::DATE"
parts = [f"""select {y} ano, {num('RACACORMAE')} rc, {num('SEMAGESTAC')} sg, {num('ESCMAE')} esc, {num('IDADEMAE')} id,
  {num('TPMETESTIM')} tp, {dt('DTNASC')} dn, {dt('DTULTMENST')} dum from read_parquet('{R.format(y=y)}')""" for y in range(2015, 2025)]
c.sql("create view raw as " + " union all ".join(parts))
c.sql("""create table v as select ano, sg, datediff('day',dum,dn) d, dum, dn from raw
  where rc in (1,2,4,5) and sg between 22 and 44 and esc between 1 and 5 and id between 10 and 60
  and tp=8 and dum<dn and datediff('day',dum,dn)<=365""")
r = c.sql("""select d%7 resto, count(*) n, avg((sg=floor(d/7))::int)*100 pct_floor, avg((sg=round(d/7))::int)*100 pct_round,
   avg((sg=floor(d/7)+1)::int)*100 pct_floor_mais1, avg((sg=floor(d/7)-1)::int)*100 pct_floor_menos1
   from v group by 1 order by 1""").df()
print(r.to_string()); r.to_csv(f"{OUT}/b2_diag_resto7_v1_20261008.csv", index=False)
# intervalo atravessa 29/fev?
r2 = c.sql("""select (ano in (2016,2020,2024)) bissexto_nasc,
   (exists_feb29) atravessa_29fev, count(*) n, avg((sg=floor(d/7))::int)*100 pct_exata, avg(sg-floor(d/7)) media_dif,
   avg((sg=floor((d-1)/7))::int)*100 pct_exata_se_d_menos1
   from (select *, ((dum < date '2016-02-29' and dn >= date '2016-02-29') or (dum < date '2020-02-29' and dn >= date '2020-02-29')
          or (dum < date '2024-02-29' and dn >= date '2024-02-29')) exists_feb29 from v)
   group by all order by all""").df()
print(r2.to_string()); r2.to_csv(f"{OUT}/b2_diag_bissexto_v1_20261008.csv", index=False)
