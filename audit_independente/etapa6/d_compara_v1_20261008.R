# Comparacao auditor x autor (executado DEPOIS de gravar resultados proprios)
suppressMessages(library(data.table))
OUT <- "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa6"
TB <- "/Volumes/Forja/ptb-racial-brasil/outputs/tables"
cmp <- list()
## A
me <- fread(file.path(OUT, "a_icr_v1_20261008.csv"))[nivel == "T1"]
au <- fread(file.path(TB, "tab_e6_01a_interacao_v1_20261008.csv"))[nivel == "T1" & desfecho %in% c("pig", "ptb_esp") & sensibilidade == "3.2_regsaude"]
aw <- fread(file.path(TB, "tab_e6_01a_wald_v1_20261008.csv"))[desfecho %in% c("pig", "ptb_esp")]
mw <- fread(file.path(OUT, "a_wald_v1_20261008.csv"))
m <- merge(me, au[, .(desfecho, raca, aut_ICR = ICR_pp, aut_lo = ICR_lo, aut_hi = ICR_hi, aut_n = n_individual)], by = c("desfecho", "raca"))
for (i in seq_len(nrow(m))) for (v in c("ICR", "lo", "hi")) {
  a <- m[[c(ICR = "ICR_pp", lo = "ICR_lo", hi = "ICR_hi")[v]]][i]; b <- m[[paste0("aut_", v)]][i]
  cmp[[length(cmp) + 1]] <- data.frame(tarefa = "A", item = paste(m$desfecho[i], m$raca[i], "T1", v), auditor = a, autor = b, dif = a - b)
}
for (dz in c("pig", "ptb_esp")) {
  cmp[[length(cmp) + 1]] <- data.frame(tarefa = "A", item = paste(dz, "N"), auditor = mw[desfecho == dz]$N, autor = aw[desfecho == dz]$N, dif = mw[desfecho == dz]$N - aw[desfecho == dz]$N)
  cmp[[length(cmp) + 1]] <- data.frame(tarefa = "A", item = paste(dz, "G"), auditor = mw[desfecho == dz]$G, autor = aw[desfecho == dz]$G, dif = mw[desfecho == dz]$G - aw[desfecho == dz]$G)
  cmp[[length(cmp) + 1]] <- data.frame(tarefa = "A", item = paste(dz, "Wald chi2"), auditor = mw[desfecho == dz]$wald_chi2, autor = aw[desfecho == dz]$chi2, dif = mw[desfecho == dz]$wald_chi2 - aw[desfecho == dz]$chi2)
}
## B
mb <- fread(file.path(OUT, "b_concordancia_v1_20261008.csv"))[cod != "Total"]
ab <- fread(file.path(TB, "tab_e6_02a_concordancia_v1_20261008.csv"))[sub == "todas validas"]
ab[, cod := fifelse(tp == 9, "9/nulo", as.character(tp))]
mb2 <- merge(mb, ab, by = "cod")
for (i in seq_len(nrow(mb2))) for (v in list(c("n", "n_total"), c("n_validas", "n_dum_valida"), c("pct_dum_valida.x", "pct_dum_valida.y"),
                                             c("pct_exata.x", "pct_exata.y"), c("pct_pm1.x", "pct_pm1.y"), c("media_dif", "dif_media"), c("dp_dif", "dif_dp")))
  cmp[[length(cmp) + 1]] <- data.frame(tarefa = "B", item = paste("cod", mb2$cod[i], sub("\\.x$", "", v[1])),
                                       auditor = mb2[[v[1]]][i], autor = mb2[[v[2]]][i], dif = mb2[[v[1]]][i] - mb2[[v[2]]][i])
## C
mc <- fread(file.path(OUT, "c_rrr_v1_20261008.csv"))[raca == "Indigena"]
ac <- fread(file.path(TB, "tab_e6_03b_rrr_v1_20261008.csv"))[raca == "Indigena" & analise != "razao_RRR_T1_vs_T3"]
ac[, nivel := tercil]
mc2 <- merge(mc, ac[, .(categoria, nivel, aR = RRR, alo = lo, ahi = hi, aN = N, aG = G)], by = c("categoria", "nivel"))
for (i in seq_len(nrow(mc2))) for (v in list(c("RRR", "aR"), c("lo", "alo"), c("hi", "ahi"), c("N", "aN"), c("G", "aG")))
  cmp[[length(cmp) + 1]] <- data.frame(tarefa = "C", item = paste("Indigena", mc2$categoria[i], mc2$nivel[i], v[1]),
                                       auditor = mc2[[v[1]]][i], autor = mc2[[v[2]]][i], dif = mc2[[v[1]]][i] - mc2[[v[2]]][i])
res <- rbindlist(cmp)
res[, dif_rel := ifelse(autor != 0, dif / abs(autor), NA_real_)]
fwrite(res, file.path(OUT, "d_comparacao_v1_20261008.csv"))
options(width = 200); print(res, nrows = 200)
cat("\nmax |dif| relativa:", max(abs(res$dif_rel), na.rm = TRUE), "\n")
