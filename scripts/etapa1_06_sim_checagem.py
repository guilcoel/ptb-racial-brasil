"""
1.6 Checagem do SIM (somente leitura, sem análise, sem linkage). DuckDB SQL, só agregados.

Fonte: /Volumes/Forja/Doc/dados_artigos_perinatais_clima/02_sim/ (download definitivo de 02/10/2026;
diferença 0 por UF×ano contra CliMaterna/TabNet segundo o FONTE.md da pasta).
  SIM-DO   parquet/ano=AAAA/uf=XX.parquet   (óbitos não fetais)
  SIM-DOFET _dofet/parquet/ano=AAAA/uf=BR.parquet (óbitos fetais)
Dicionário: docs/referencias/Dicionario_SIM_2025.pdf (baixado em 2026-10-08).

Definições:
  óbito fetal: TIPOBITO = 1 e (SEMAGESTAC válido ≥ 22  OU  [SEMAGESTAC ausente/9/99 e GESTACAO 2–6]  OU  PESO ≥ 500)
  neonatal precoce: TIPOBITO = 2 e IDADE com 1º dígito 0 (minutos) ou 1 (horas), ou 2 (dias) com subcampo ≤ 06
    (codificação do dado, conferida no FONTE.md do 02_sim: o texto do dicionário de 2025 diverge)
  região: 1º dígito de CODMUNRES (ausente/inválido = 'ign')
NUMERODN: não existe nos parquets nem no DBF bruto (conferido em DOFET24 e DOAC2024) nem no dicionário.
Saídas: tab_e1_06_sim_obitos_ano_regiao, tab_e1_06_sim_completude_mae.
"""
import duckdb
import pandas as pd

import etapa1_lib as E

log = E.logger("06_sim")
SIM = __import__("os").environ.get("SIM_RAW", "/Volumes/Forja/Doc/dados_artigos_perinatais_clima/02_sim")  # 9a: caminho local por variável de ambiente
con = duckdb.connect()
src = {"DO": f"{SIM}/parquet/ano=*/uf=*.parquet", "DOFET": f"{SIM}/_dofet/parquet/ano=*/uf=*.parquet"}
REG = "CASE substr(trim(CODMUNRES),1,1) WHEN '1' THEN 'N' WHEN '2' THEN 'NE' WHEN '3' THEN 'SE' WHEN '4' THEN 'S' WHEN '5' THEN 'CO' ELSE 'ign' END"
SEM = "TRY_CAST(trim(SEMAGESTAC) AS INT)"
FET = f"""TRIM(TIPOBITO)='1' AND (
  ({SEM} IS NOT NULL AND {SEM} NOT IN (9,99) AND {SEM} >= 22)
  OR (({SEM} IS NULL OR {SEM} IN (9,99)) AND TRY_CAST(trim(GESTACAO) AS INT) BETWEEN 2 AND 6)
  OR TRY_CAST(trim(PESO) AS INT) >= 500)"""
NEO = """TRIM(TIPOBITO)='2' AND (substr(trim(IDADE),1,1) IN ('0','1')
  OR (substr(trim(IDADE),1,1)='2' AND TRY_CAST(substr(trim(IDADE),2,2) AS INT) <= 6))"""

rows, comp = [], []
for comp_name, crit, s in [("obito_fetal", FET, src["DOFET"]), ("neonatal_precoce_0a6d", NEO, src["DO"])]:
    q = f"""SELECT CAST(ano AS INT) ano, {REG} regiao, count(*) n
            FROM read_parquet('{s}', hive_partitioning=true, union_by_name=true)
            WHERE CAST(ano AS INT) BETWEEN 2015 AND 2024 AND {crit} GROUP BY ALL"""
    r = con.sql(q).df()
    r.insert(0, "componente", comp_name)
    rows.append(r)
    log(f"{comp_name}: total 2015–2024", int(r.n.sum()))
    q = f"""SELECT CAST(ano AS INT) ano, {REG} regiao, count(*) n,
              100*avg(CASE WHEN TRY_CAST(trim(IDADEMAE) AS INT) BETWEEN 10 AND 60 THEN 1 ELSE 0 END) pct_idademae_valida,
              100*avg(CASE WHEN TRY_CAST(trim(ESCMAE) AS INT) BETWEEN 1 AND 5 THEN 1 ELSE 0 END) pct_escmae_valida,
              100*avg(CASE WHEN TRY_CAST(trim(ESCMAE2010) AS INT) BETWEEN 0 AND 5 THEN 1 ELSE 0 END) pct_escmae2010_valida,
              100*avg(CASE WHEN trim(RACACOR) IN ('1','2','3','4','5') THEN 1 ELSE 0 END) pct_racacor_falecido_valida
            FROM read_parquet('{s}', hive_partitioning=true, union_by_name=true)
            WHERE CAST(ano AS INT) BETWEEN 2015 AND 2024 AND {crit} GROUP BY ALL"""
    c = con.sql(q).df()
    c.insert(0, "componente", comp_name)
    comp.append(c)

t = pd.concat(rows).sort_values(["componente", "ano", "regiao"])
t.to_csv(E.L.TAB / f"tab_e1_06_sim_obitos_ano_regiao_v1_{E.L.STAMP}.csv", index=False)
c = pd.concat(comp).sort_values(["componente", "ano", "regiao"])
for k in [x for x in c.columns if x.startswith("pct")]:
    c[k] = c[k].round(2)
c.to_csv(E.L.TAB / f"tab_e1_06_sim_completude_mae_v1_{E.L.STAMP}.csv", index=False)
for comp_name in ("obito_fetal", "neonatal_precoce_0a6d"):
    x = t[t.componente == comp_name].pivot_table(index="ano", columns="regiao", values="n", aggfunc="sum")
    log(f"{comp_name} por ano: " + ", ".join(f"{a}={int(v):,}" for a, v in x.sum(axis=1).items()))
cols = {r["column_name"] for r in con.sql(f"DESCRIBE SELECT * FROM read_parquet('{src['DO']}', union_by_name=true)").df().to_dict("records")}
log(f"NUMERODN no SIM-DO: {'NUMERODN' in cols}; RACACORMAE: {'RACACORMAE' in cols}")
