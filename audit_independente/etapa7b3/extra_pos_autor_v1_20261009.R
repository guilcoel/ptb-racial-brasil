# Cálculos complementares feitos DEPOIS de abrir as tabelas do autor (para explicar divergências):
# (1) ptb_esp reclassificado pela EQUAÇÃO com variante B (PTB não classificado reclassificado continua nulo);
# (2) cenários extras do autor com definição inferível: TPMETESTIM em {1,2}; sem 2024.
source_lines <- readLines("/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa7b3/auditoria_etapa7b3_v1_20261009.R")
cut <- grep("^# ---------------- Tarefa A", source_lines)
eval(parse(text = source_lines[1:(cut - 1)]))   # reaproveita leitura das células e funções (células já existem)
d[, `:=`(n_espB_e = n_esp, y_espB_e = y_esp - rc_eq_esp1)]
res <- list()
add <- function(nm, dd, y, n) { f <- fit_32(dd, y, n); x <- f$wald[, cenario := nm]; x[, desfecho := y]; res[[length(res)+1]] <<- x
  lg("extra %s %s: N=%s W6=%.6f Wind2=%.6f", nm, y, format(f$wald$N, big.mark=","), f$wald$wald6_chi2, f$wald$waldInd2_chi2) }
add("reclass_eq_varB", d, "y_espB_e", "n_espB_e")
add("tpm_1_2", d[tpm %in% c(1L, 2L)], "y_ptb", "n")
# robusta à datação (definição lida no script do autor após a gravação): TPMETESTIM em {1,2} e EXCLUI PTB > P97 (equação)
dr <- d[tpm %in% c(1L, 2L)][, `:=`(n_r = n - rc_eq, y_r = y_ptb - rc_eq)]
add("robusta_datacao", dr, "y_r", "n_r")
# sem CE/DF: UF de residência = 2 primeiros dígitos de CO_REGSAUD (23 = CE, 53 = DF)
add("sem_CE_DF", d[!substr(cl, 1, 2) %in% c("23", "53")], "y_ptb", "n")
monta_X0 <- monta_X; monta_X <- function(...) { X <- monta_X0(...); X[, setdiff(colnames(X), "a2024"), drop = FALSE] }
add("sem_2024", d[ano != 2024L], "y_ptb", "n")
x <- rbindlist(res); x[, carimbo := stamp()]
fwrite(x, file.path(OUT, "tab_aud_e7b3_extra_pos_autor_v1_20261009.csv"))
