# Auditoria independente etapa 7b1 - Tarefa B (excluidos pela cascata com SEMAGESTAC 22-44)
library(DBI); library(data.table)
con <- dbConnect(duckdb::duckdb())
dbExecute(con, "CREATE VIEW f AS SELECT * FROM read_parquet('data/processed/sinasc_brasil_2015_2024_v1_20261008/ano=*/*.parquet', hive_partitioning=true)")
q <- "
WITH c AS (
 SELECT SEMAGESTAC, regiao, RACACORMAE,
  CASE WHEN NOT coalesce(RACACORMAE IN (1,2,4,5), false) THEN 1
       WHEN NOT coalesce(SEMAGESTAC BETWEEN 22 AND 44, false) THEN 2
       WHEN NOT coalesce(ESCMAE BETWEEN 1 AND 5, false) THEN 3
       WHEN NOT coalesce(IDADEMAE BETWEEN 10 AND 60, false) THEN 4
       ELSE 0 END AS passo
 FROM f)
SELECT passo, count(*) n,
  sum(CASE WHEN SEMAGESTAC BETWEEN 22 AND 44 THEN 1 ELSE 0 END) n_ig_valida,
  sum(CASE WHEN SEMAGESTAC BETWEEN 22 AND 36 THEN 1 ELSE 0 END) n_ptb
FROM c GROUP BY passo ORDER BY passo"
x <- as.data.table(dbGetQuery(con, q)); print(x)
cat("total:", sum(x$n), "\n")
exc <- x[passo > 0, .(n=sum(n), n_ig=sum(n_ig_valida), n_ptb=sum(n_ptb))]
inc <- x[passo == 0]
cat(sprintf("Excluidos: %d; com SEMAGESTAC 22-44: %d; <37: %d (%.4f%%)\n", exc$n, exc$n_ig, exc$n_ptb, 100*exc$n_ptb/exc$n_ig))
cat(sprintf("Incluidos: %d; PTB: %d (%.4f%%)\n", inc$n, inc$n_ptb, 100*inc$n_ptb/inc$n))
# por motivo e raca entre excluidos com IG valida
y <- as.data.table(dbGetQuery(con, "
SELECT CASE WHEN NOT coalesce(RACACORMAE IN (1,2,4,5), false) THEN CASE WHEN RACACORMAE IS NULL THEN '1_raca_nula' WHEN RACACORMAE=3 THEN '1_raca_amarela' ELSE '1_raca_outro' END
            WHEN NOT coalesce(ESCMAE BETWEEN 1 AND 5, false) THEN '3_escmae'
            WHEN NOT coalesce(IDADEMAE BETWEEN 10 AND 60, false) THEN '4_idade' ELSE '0_incl' END motivo,
 count(*) n, sum(CASE WHEN SEMAGESTAC < 37 THEN 1 ELSE 0 END) ptb
FROM f WHERE SEMAGESTAC BETWEEN 22 AND 44 GROUP BY 1 ORDER BY 1"))
y[, pct := 100*ptb/n]; print(y)
fwrite(rbind(x[, .(item=paste0("passo_",passo), n, n_ig_valida, n_ptb)]), "audit_independente/etapa7b1/auditor_B_cascata_v1_20261009.csv")
fwrite(y, "audit_independente/etapa7b1/auditor_B_motivo_v1_20261009.csv")
