suppressMessages(library(data.table))
T <- "/Volumes/Forja/ptb-racial-brasil/outputs/tables/"
a1 <- fread("tab_aud_e6b_modelos_v1_20261009.csv"); u1 <- fread(paste0(T,"tab_e6b_01_modelos_m1m3_v1_20261008.csv"))
a2 <- fread("tab_aud_e6b_m2_cenarios_v1_20261009.csv"); u2 <- fread(paste0(T,"tab_e6b_01_m2_cenarios_v1_20261008.csv"))[desfecho=="ptb"]
a3 <- fread("tab_aud_e6b_ptb_raca_metodo_v1_20261009.csv"); u3 <- fread(paste0(T,"tab_e6b_01_ptb_raca_metodo_v1_20261008.csv"))[desfecho=="ptb"]
L <- list()
lg <- function(t, a, u, ks, vs) { m <- merge(a, u, by = ks, suffixes = c(".a",".u"))
  for (v in vs) L[[length(L)+1]] <<- m[, .(tarefa=t, item=paste(do.call(paste, c(.SD, sep="|")), v, sep="|"),
     auditor=get(paste0(v,".a")), autor=get(paste0(v,".u"))), .SDcols=ks]
  cat(t, "linhas casadas:", nrow(m), "\n") }
lg("T1", a1, u1, c("modelo","desfecho","raca"), c("PR","PR_lo","PR_hi","N","casos","G"))
lg("T2", a2, u2, c("cenario","desfecho","raca"), c("PR","PR_lo","PR_hi","N","casos","G"))
lg("T3", a3, u3, c("raca","ig_metodo"), c("n","casos","pct"))
cmp <- rbindlist(L)[, `:=`(dif = auditor - autor, dif_rel = (auditor - autor)/autor)]
fwrite(cmp, "comparacao_v1_20261009.csv")
cat("itens:", nrow(cmp), " max|dif_rel|:", signif(max(abs(cmp$dif_rel)),3), "\n")
print(cmp[order(-abs(dif_rel))][1:5])
