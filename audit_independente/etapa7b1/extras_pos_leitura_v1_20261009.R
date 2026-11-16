# Auditoria 7b1 - verificacoes EXTRAS, rodadas APOS ler as tabelas do autor (itens nao pedidos)
library(DBI); library(data.table)
src <- readLines("audit_independente/etapa7b1/modelos_v1_20261009.R")
eval(parse(text = src[1:grep("^res <- list", src)]))   # reaproveita funcoes/dados
out <- list(); add <- function(it, v) out[[length(out)+1]] <<- data.table(item=it, valor=v)
# Wald cenarios D (ptb_ind e ptb_esp)
for (cen in c("i","ii")) { a2 <- copy(s32)
  if (cen=="i") a2[, `:=`(y_ind=ptb_ind+semclass, y_esp=ptb_esp)] else a2[, `:=`(y_ind=ptb_ind, y_esp=ptb_esp+semclass)]
  for (o in c("ind","esp")) { m <- fit_pois(a2, paste0("y_",o), "n", f32); w <- wald_int(m)
    add(paste0("D_",cen,"_wald_ptb_",o), w$wald)
    for (g in c("Parda","Preta","Indigena")) for (tk in c("T1","T2")) add(paste0("D_",cen,"_ICR_ptb_",o,"_",g,"_",tk), icr(m,g,tk)$icr) }
  for (o in c("ind","esp")) { m <- fit_pois(copy(ag)[, `:=`(y_ind=if (cen=="i") ptb_ind+semclass else ptb_ind, y_esp=if (cen=="i") ptb_esp else ptb_esp+semclass)], paste0("y_",o), "n", fM2)
    for (g in c("Parda","Preta")) add(paste0("D_",cen,"_PR_M2_ptb_",o,"_",g), exp(coef(m$fit)[paste0("raca",g)])) }
}
# A: demais ICR nas subamostras
subs <- list(DUM = s32[ig_metodo=="DUM"], outro_metodo = s32[ig_metodo=="outro_metodo"], sem_CE_DF = s32[!uf %in% c("CE","DF")], sem_2024 = s32[ano != 2024])
for (nm in names(subs)) { m <- fit_pois(subs[[nm]], "ptb", "n_ptb", f32)
  for (g in c("Parda","Preta","Indigena")) for (tk in c("T1","T2")) add(paste0("A_",nm,"_ICR_",g,"_",tk), icr(m,g,tk)$icr) }
# E: RERI recod para Parda T2, Preta T1/T2 e RERI original (ref Branca-T3)
m <- fit_pois(s32, "ptb_ind", "n_ind", f32)
for (g in c("Parda","Preta","Indigena")) for (tk in c("T1","T2")) {
  Ps <- c(B_T3=Pgt(m,"Branca","T3")$P, B_Tk=Pgt(m,"Branca",tk)$P, g_T3=Pgt(m,g,"T3")$P, g_Tk=Pgt(m,g,tk)$P)
  ref <- names(which.min(Ps)); opp <- c(B_T3="g_Tk", g_Tk="B_T3", B_Tk="g_T3", g_T3="B_Tk")[ref]; simp <- setdiff(names(Ps), c(ref,opp))
  add(paste0("E_RERIrecod_",g,"_",tk,"_ref_",ref), (Ps[opp]-Ps[simp[1]]-Ps[simp[2]])/Ps[ref]+1)
  add(paste0("E_RERIorig_",g,"_",tk), (Ps["g_Tk"]-Ps["B_Tk"]-Ps["g_T3"])/Ps["B_T3"]+1) }
res <- rbindlist(out); fwrite(res, "audit_independente/etapa7b1/auditor_extras_pos_leitura_v1_20261009.csv"); print(res, nrows=200)
# B: colunas extras (IG definida = SEMAGESTAC nao nulo?) e por regiao
con <- dbConnect(duckdb::duckdb())
dbExecute(con, "CREATE VIEW f AS SELECT * FROM read_parquet('data/processed/sinasc_brasil_2015_2024_v1_20261008/ano=*/*.parquet', hive_partitioning=true)")
print(dbGetQuery(con, "
WITH c AS (SELECT regiao, SEMAGESTAC,
  CASE WHEN NOT coalesce(RACACORMAE IN (1,2,4,5), false) THEN 1 WHEN NOT coalesce(SEMAGESTAC BETWEEN 22 AND 44, false) THEN 2
       WHEN NOT coalesce(ESCMAE BETWEEN 1 AND 5, false) THEN 3 WHEN NOT coalesce(IDADEMAE BETWEEN 10 AND 60, false) THEN 4 ELSE 0 END passo FROM f)
SELECT coalesce(regiao,'?') regiao, passo, count(*) n, sum((SEMAGESTAC BETWEEN 22 AND 44)::INT) n_ig, sum((SEMAGESTAC BETWEEN 22 AND 36)::INT) n_ptb,
  count(SEMAGESTAC) n_sem_nao_nulo, sum((SEMAGESTAC < 37)::INT) n_lt37, sum((SEMAGESTAC <= 44)::INT) n_le44, sum((SEMAGESTAC < 99)::INT) n_lt99
FROM c GROUP BY ALL ORDER BY 1,2"))
