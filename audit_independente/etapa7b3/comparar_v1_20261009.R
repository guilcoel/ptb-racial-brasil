# Comparação auditor x autor — Etapa 7b3 (executado DEPOIS do manifesto_pre_autor_v1_20261009.txt)
suppressMessages(library(data.table))
OUT <- "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa7b3"
TB  <- "/Volumes/Forja/ptb-racial-brasil/outputs/tables"
aud <- fread(file.path(OUT, "valores_auditor_v1_20261009.csv"))[, .(tarefa, item, auditor)]
ext <- fread(file.path(OUT, "tab_aud_e7b3_extra_pos_autor_v1_20261009.csv"))
am <- function(x) fcase(x == "principal", "completa", x == "codigo_1", "tpm1", x == "codigo_2", "tpm2", x == "codigo_8", "tpm8", default = x)

# --- autor em formato longo ---
L <- list(); add <- function(tarefa, item, v) L[[length(L) + 1]] <<- data.table(tarefa = tarefa, item = item, autor = as.numeric(v))
m2 <- fread(file.path(TB, "tab_e7b3_01_esp_m2_v1_20261008.csv"))
for (i in seq_len(nrow(m2))) with(m2[i], {
  k <- am(cenario)
  add("A", sprintf("ptb_esp|%s|M2|PR_%s", k, raca), PR); add("A", sprintf("ptb_esp|%s|M2|PR_%s_lo", k, raca), PR_lo)
  add("A", sprintf("ptb_esp|%s|M2|PR_%s_hi", k, raca), PR_hi)
  if (raca == "Preta") { add("A", sprintf("ptb_esp|%s|M2|N", k), N); add("A", sprintf("ptb_esp|%s|M2|casos", k), casos)
                         add("A", sprintf("ptb_esp|%s|M2|G", k), G) }
})
it <- fread(file.path(TB, "tab_e7b3_01_esp_interacao_v1_20261008.csv"))
for (i in seq_len(nrow(it))) with(it[i], {
  k <- am(cenario)
  add("A", sprintf("ptb_esp|%s|3.2|ICR_%s_%s", k, raca, nivel), ICR_pp)
  add("A", sprintf("ptb_esp|%s|3.2|ICR_%s_%s_lo", k, raca, nivel), ICR_lo)
  add("A", sprintf("ptb_esp|%s|3.2|ICR_%s_%s_hi", k, raca, nivel), ICR_hi)
})
wd <- fread(file.path(TB, "tab_e7b3_02_wald_ind_v1_20261008.csv"))
for (i in seq_len(nrow(wd))) with(wd[i], {
  k <- am(cenario)
  if (k %in% c("completa", "tpm1", "tpm2", "tpm8")) {
    if (desfecho == "ptb_esp" && k != "completa") {          # tarefa A (Wald do 3.2 de ptb_esp por código)
      add("A", sprintf("ptb_esp|%s|3.2|N", k), N); add("A", sprintf("ptb_esp|%s|3.2|G", k), G)
      add("A", sprintf("ptb_esp|%s|3.2|wald6_chi2", k), chi2_6gl); add("A", sprintf("ptb_esp|%s|3.2|wald6_p", k), p_6gl)
      add("A", sprintf("ptb_esp|%s|3.2|waldInd2_chi2", k), chi2_ind_2gl); add("A", sprintf("ptb_esp|%s|3.2|waldInd2_p", k), p_ind_2gl)
    }
    add("B", sprintf("%s|%s|3.2|N", desfecho, k), N)
    add("B", sprintf("%s|%s|3.2|waldInd2_chi2", desfecho, k), chi2_ind_2gl); add("B", sprintf("%s|%s|3.2|waldInd2_p", desfecho, k), p_ind_2gl)
    add("B", sprintf("%s|%s|3.2|wald6_chi2", desfecho, k), chi2_6gl); add("B", sprintf("%s|%s|3.2|wald6_p", desfecho, k), p_6gl)
  }
})
aut <- rbindlist(L)

# --- tarefa C: autor (equação gigs; ptb_esp com não classificados mantidos nulos) x auditor (tabela; variantes) ---
cw <- fread(file.path(OUT, "tab_aud_e7b3_C_w_v1_20261009.csv"))[amostra == "completa"]
rc <- wd[cenario == "reclass_p97"]
LC <- list()
addc <- function(item, a, b) LC[[length(LC) + 1]] <<- data.table(tarefa = "C", item = item, auditor = a, autor = b)
mapC <- list(ptb = list(c("ptb_rc_tab", "auditor_TABELA (principal)"), c("ptb_rc_eq", "auditor_EQUACAO")),
             ptb_esp = list(c("ptb_esp_rcA_tab", "auditor_TABELA_varA (reclassificado vira 0 mesmo se nao classificado; principal)"),
                            c("ptb_esp_rcB_tab", "auditor_TABELA_varB (nao classificado continua nulo)"),
                            c("ptb_esp_rcA_eq", "auditor_EQUACAO_varA")))
for (dz in names(mapC)) for (v in mapC[[dz]]) {
  a <- cw[desfecho == v[1]]; b <- rc[desfecho == dz]
  addc(sprintf("%s|reclass_p97|%s|N", dz, v[2]), a$N, b$N)
  addc(sprintf("%s|reclass_p97|%s|waldInd2_chi2", dz, v[2]), a$waldInd2_chi2, b$chi2_ind_2gl)
  addc(sprintf("%s|reclass_p97|%s|waldInd2_p", dz, v[2]), a$waldInd2_p, b$p_ind_2gl)
  addc(sprintf("%s|reclass_p97|%s|wald6_chi2", dz, v[2]), a$wald6_chi2, b$chi2_6gl)
  addc(sprintf("%s|reclass_p97|%s|wald6_p", dz, v[2]), a$wald6_p, b$p_6gl)
}
# extras calculados após abrir o autor (definição lida do script do autor)
mapE <- list(c("reclass_eq_varB", "reclass_p97", "ptb_esp", "auditor_EQUACAO_varB (= definicao do autor)"),
             c("tpm_1_2", "outro_metodo_1_2", "ptb", "extra"), c("robusta_datacao", "robusta_datacao", "ptb", "extra"),
             c("sem_CE_DF", "sem_CE_DF", "ptb", "extra"), c("sem_2024", "sem_2024", "ptb", "extra"))
for (v in mapE) {
  a <- ext[cenario == v[1]]; b <- wd[cenario == v[2] & desfecho == v[3]]
  tf <- if (v[1] == "reclass_eq_varB") "C" else "extra"
  for (s in list(c("N", "N"), c("G", "G"), c("waldInd2_chi2", "chi2_ind_2gl"), c("waldInd2_p", "p_ind_2gl"),
                 c("wald6_chi2", "chi2_6gl"), c("wald6_p", "p_6gl")))
    LC[[length(LC) + 1]] <- data.table(tarefa = tf, item = sprintf("%s|%s|%s|%s", v[3], v[2], v[4], s[1]),
                                       auditor = a[[s[1]]], autor = b[[s[2]]])
}
cmp <- rbind(merge(aud[tarefa %in% c("A", "B")], aut, by = c("tarefa", "item"), all = FALSE), rbindlist(LC))
cmp[, dif := auditor - autor][, dif_rel := fifelse(autor != 0, dif / abs(autor), NA_real_)]
setorder(cmp, tarefa, item)
fwrite(cmp, file.path(OUT, "comparacao_7b3_v1_20261009.csv"))
# itens do autor sem par no auditor e vice-versa (A/B)
so_aut <- aut[!aud, on = c("tarefa", "item")]; so_aud <- aud[tarefa %in% c("A", "B")][!aut, on = c("tarefa", "item")]
cat("linhas comparadas:", nrow(cmp), "| só autor:", nrow(so_aut), "| só auditor (A/B):", nrow(so_aud), "\n")
if (nrow(so_aut)) print(so_aut)
cat("\nmax |dif_rel| por tarefa (A/B/extra; excluindo variantes de C):\n")
print(cmp[!grepl("TABELA|EQUACAO_varA|EQUACAO\\|", item), .(n = .N, max_abs_dif_rel = max(abs(dif_rel), na.rm = TRUE),
                                                          max_abs_dif = max(abs(dif), na.rm = TRUE)), by = tarefa])
cat("\nTarefa C:\n"); print(cmp[tarefa == "C", .(item, auditor = signif(auditor, 7), autor = signif(autor, 7), dif = signif(dif, 3), dif_rel = signif(dif_rel, 3))])
cat("\nMaiores |dif_rel| em A/B:\n"); print(cmp[tarefa %in% c("A", "B")][order(-abs(dif_rel))][1:8])
