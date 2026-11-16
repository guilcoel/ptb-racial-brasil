# Checagens extras (fora dos 10 itens) — somente agregados
set.seed(42)
suppressMessages({library(DBI); library(duckdb); library(lme4)})
setwd("/Volumes/Forja/ptb-racial-brasil")
L <- readRDS("data/processed/maihda_modelos_v1_20261008.rds")
aucw <- function(m) { y <- model.frame(m)[[1]]; cs <- as.numeric(y[,1]); nc <- as.numeric(y[,2]); p <- fitted(m)
  pp <- outer(p, p, function(a,b) (a>b) + 0.5*(a==b)); sum(outer(cs,nc)*pp)/(sum(cs)*sum(nc)) }
obs <- function(m) { y <- model.frame(m)[[1]]; cs <- as.numeric(y[,1]); nc <- as.numeric(y[,2]); p <- cs/(cs+nc)
  pp <- outer(p, p, function(a,b) (a>b) + 0.5*(a==b)); sum(outer(cs,nc)*pp)/(sum(cs)*sum(nc)) }
cat("AUC condicional m1 =", aucw(L$m1), " m2 =", aucw(L$m2), " AUC taxas observadas =", obs(L$m2), "\n")
cat("cor(fitted m1, fitted m2) =", cor(fitted(L$m1), fitted(L$m2)), "\n")
con <- dbConnect(duckdb())
print(dbGetQuery(con, "SELECT ig_metodo, TPMETESTIM, count(*) n FROM read_parquet('data/processed/sinasc_brasil_2015_2024_v3_20261008/ano=*/part-0.parquet', hive_partitioning=true) WHERE incl GROUP BY ALL ORDER BY ALL"))
u <- paste(sprintf("SELECT TRY_CAST(trim(CAST(RACACORMAE AS VARCHAR)) AS DOUBLE) rac, TRY_CAST(trim(CAST(SEMAGESTAC AS VARCHAR)) AS DOUBLE) sem, TRY_CAST(trim(CAST(ESCMAE AS VARCHAR)) AS DOUBLE) esc FROM read_parquet('/Volumes/Forja/CliMaterna/01_data/raw/SINASC/sinasc_%d.parquet')", 2015:2024), collapse=" UNION ALL ")
print(dbGetQuery(con, paste0("WITH r AS (", u, ") SELECT
  count(*) FILTER (WHERE rac IN (1,2,4,5) AND NOT coalesce(sem BETWEEN 22 AND 44,false) AND sem < 22) ig_lt22,
  count(*) FILTER (WHERE rac IN (1,2,4,5) AND NOT coalesce(sem BETWEEN 22 AND 44,false) AND sem > 44) ig_gt44,
  count(*) FILTER (WHERE rac IN (1,2,4,5) AND NOT coalesce(sem BETWEEN 22 AND 44,false) AND sem BETWEEN 37 AND 44) ig_termo_dentro_faixa,
  count(*) FILTER (WHERE rac IN (1,2,4,5) AND sem BETWEEN 22 AND 44 AND esc = 9) esc_9,
  count(*) FILTER (WHERE rac IN (1,2,4,5) AND sem BETWEEN 22 AND 44 AND esc IS NULL) esc_nulo,
  count(*) FILTER (WHERE rac IN (1,2,4,5) AND sem BETWEEN 22 AND 44 AND NOT coalesce(esc BETWEEN 1 AND 5,false) AND esc IS NOT NULL AND esc <> 9) esc_outro
  FROM r")))
dbDisconnect(con, shutdown=TRUE)
