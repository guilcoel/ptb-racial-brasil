# Auditoria independente etapa 7b1 - agregacao em celulas (somente leitura nos dados)
library(DBI); library(data.table)
set.seed(42)
con <- dbConnect(duckdb::duckdb())
dbExecute(con, "CREATE VIEW b AS SELECT * FROM read_parquet('data/processed/sinasc_brasil_2015_2024_v3_20261008/ano=*/part-0.parquet', hive_partitioning=true)")
ag <- as.data.table(dbGetQuery(con, "
SELECT COALESCE(CO_REGSAUD, 'UF_' || substr(CODMUNRES,1,2)) AS cluster,
       CO_REGSAUD IS NOT NULL AS tem_rs, CO_REGSAUD,
       CAST(ano AS INTEGER) ano, raca, idade_cat, regiao, uf, ig_metodo,
       count(*) n, sum(ptb) ptb, count(ptb) n_ptb,
       count(ptb_ind) n_ind, sum(ptb_ind) ptb_ind,
       count(ptb_esp) n_esp, sum(ptb_esp) ptb_esp,
       sum(CASE WHEN ptb_tipo='sem_classif' THEN 1 ELSE 0 END) semclass
FROM b WHERE incl GROUP BY ALL"))
ter <- fread("data/processed/tercil_reg_regsaude_ano_v1_20261008.csv", colClasses=list(character="CO_REGSAUD"))
cat("tercil dup:", ter[, .N, by=.(CO_REGSAUD, ano)][N>1, .N], "\n")
ag <- merge(ag, ter[, .(CO_REGSAUD, ano, tercil_reg)], by=c("CO_REGSAUD","ano"), all.x=TRUE)
cat("celulas:", nrow(ag), " n total:", sum(ag$n), "\n")
print(ag[, .(n=sum(n)), by=.(tem_rs, sem_tercil=is.na(tercil_reg))])
print(ag[, .(n=sum(n), ptb=sum(ptb)), by=tercil_reg][order(tercil_reg)])
saveRDS(ag, "/private/tmp/claude-501/-Users-guilherme/e1c712c9-85af-4f6d-89f1-cb28b034e571/scratchpad/ag_v3.rds")
