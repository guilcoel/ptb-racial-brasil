# Consolida os valores do auditor em formato longo (tarefa,item,valor) — antes de abrir arquivos do autor.
suppressMessages(library(data.table))
OUT <- "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa7b3"
rd <- function(x) fread(file.path(OUT, sprintf("tab_aud_e7b3_%s_v1_20261009.csv", x)))
A_m2 <- rd("A_m2"); A_icr <- rd("A_icr"); A_w <- rd("A_w"); B_w <- rd("B_w"); C_w <- rd("C_w"); C_icr <- rd("C_icr"); B_icr <- rd("B_icr")
L <- list()
add <- function(tarefa, item, valor) L[[length(L) + 1]] <<- data.table(tarefa = tarefa, item = item, auditor = valor)
for (i in seq_len(nrow(A_m2))) with(A_m2[i], {
  add("A", sprintf("ptb_esp|%s|M2|PR_%s", amostra, raca), PR)
  add("A", sprintf("ptb_esp|%s|M2|PR_%s_lo", amostra, raca), PR_lo)
  add("A", sprintf("ptb_esp|%s|M2|PR_%s_hi", amostra, raca), PR_hi)
  if (raca == "Preta") { add("A", sprintf("ptb_esp|%s|M2|N", amostra), N); add("A", sprintf("ptb_esp|%s|M2|casos", amostra), casos)
                         add("A", sprintf("ptb_esp|%s|M2|G", amostra), G) }
})
for (i in seq_len(nrow(A_icr))) with(A_icr[i], {
  add("A", sprintf("ptb_esp|%s|3.2|ICR_%s_%s", amostra, raca, tercil), ICR_pp)
  add("A", sprintf("ptb_esp|%s|3.2|ICR_%s_%s_lo", amostra, raca, tercil), ICR_lo)
  add("A", sprintf("ptb_esp|%s|3.2|ICR_%s_%s_hi", amostra, raca, tercil), ICR_hi)
})
for (i in seq_len(nrow(A_w))) with(A_w[i], {
  add("A", sprintf("ptb_esp|%s|3.2|N", amostra), N); add("A", sprintf("ptb_esp|%s|3.2|G", amostra), G)
  add("A", sprintf("ptb_esp|%s|3.2|wald6_chi2", amostra), wald6_chi2); add("A", sprintf("ptb_esp|%s|3.2|wald6_p", amostra), wald6_p)
  add("A", sprintf("ptb_esp|%s|3.2|waldInd2_chi2", amostra), waldInd2_chi2); add("A", sprintf("ptb_esp|%s|3.2|waldInd2_p", amostra), waldInd2_p)
})
for (i in seq_len(nrow(B_w))) with(B_w[i], {
  add("B", sprintf("%s|%s|3.2|N", desfecho, amostra), N); add("B", sprintf("%s|%s|3.2|casos", desfecho, amostra), casos)
  add("B", sprintf("%s|%s|3.2|waldInd2_chi2", desfecho, amostra), waldInd2_chi2); add("B", sprintf("%s|%s|3.2|waldInd2_p", desfecho, amostra), waldInd2_p)
  add("B", sprintf("%s|%s|3.2|wald6_chi2", desfecho, amostra), wald6_chi2); add("B", sprintf("%s|%s|3.2|wald6_p", desfecho, amostra), wald6_p)
})
for (i in seq_len(nrow(B_icr[raca == "Indigena" & tercil == "T1"]))) with(B_icr[raca == "Indigena" & tercil == "T1"][i], {
  add("B", sprintf("%s|%s|3.2|ICR_Indigena_T1", desfecho, amostra), ICR_pp)
})
for (i in seq_len(nrow(C_w))) with(C_w[i], {
  add("C", sprintf("%s|%s|3.2|N", desfecho, amostra), N); add("C", sprintf("%s|%s|3.2|casos", desfecho, amostra), casos)
  add("C", sprintf("%s|%s|3.2|waldInd2_chi2", desfecho, amostra), waldInd2_chi2); add("C", sprintf("%s|%s|3.2|waldInd2_p", desfecho, amostra), waldInd2_p)
  add("C", sprintf("%s|%s|3.2|wald6_chi2", desfecho, amostra), wald6_chi2); add("C", sprintf("%s|%s|3.2|wald6_p", desfecho, amostra), wald6_p)
})
for (i in seq_len(nrow(C_icr[raca == "Indigena" & tercil == "T1"]))) with(C_icr[raca == "Indigena" & tercil == "T1"][i], {
  add("C", sprintf("%s|%s|3.2|ICR_Indigena_T1", desfecho, amostra), ICR_pp)
})
res <- rbindlist(L); res[, carimbo := format(Sys.time(), "%Y-%m-%d %H:%M:%S %Z")]
fwrite(res, file.path(OUT, "valores_auditor_v1_20261009.csv"))
cat(nrow(res), "linhas gravadas\n")
