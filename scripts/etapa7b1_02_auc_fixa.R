# 7b.1 (3) AUC do MAIHDA (PIG) só com a parte fixa do M2 (p̂ = plogis(Xβ), sem û), IC DeLong; e, para conferência, a AUC
# condicional (fitted, com û) do M1 e do M2 = tab_e5_02_modelos. Objetos: maihda_modelos_v1_20261008.rds (gravado antes do
# perfil, Etapa 6.6). Funções de AUC e DeLong idênticas às de etapa6b_02_auc_area.R (DeLong vetorizado conferido contra a
# Etapa 5). Saída: tab_e7b1_03_auc_fixa.
suppressPackageStartupMessages({library(lme4); library(data.table)})
PROJ <- Sys.getenv("PTB_PROJ", getwd()); S <- "20261008"  # 9a: raiz do projeto (rodar da raiz ou definir PTB_PROJ)
PROC <- file.path(PROJ, "data/processed"); TAB <- file.path(PROJ, "outputs/tables")
LOG <- file.path(PROJ, "outputs/logs", paste0("etapa7b1_", S, ".log"))
log <- function(...) { m <- paste0("[", format(Sys.time(), "%Y-%m-%d %H:%M:%S"), "] [7b1_02_auc_fixa] ", paste0(...))
  cat(m, "\n"); cat(m, "\n", file = LOG, append = TRUE) }
auc_ci <- function(p, cas, nc) {
  cas <- as.numeric(cas); nc <- as.numeric(nc); m <- sum(cas); n <- sum(nc)
  o <- order(p); ps <- p[o]; cs <- cas[o]; ns <- nc[o]
  u <- unique(ps); k <- match(ps, u)
  nc_u <- tapply(ns, k, sum); cs_u <- tapply(cs, k, sum)
  below_nc <- c(0, cumsum(nc_u))[seq_along(u)]; above_cs <- rev(c(0, cumsum(rev(cs_u))))[-1]
  v10 <- ((below_nc + 0.5 * nc_u) / n)[k]; v01 <- ((above_cs + 0.5 * cs_u) / m)[k]
  A <- sum(cs * v10) / m
  se <- sqrt(sum(cs * (v10 - A)^2) / (m - 1) / m + sum(ns * (v01 - A)^2) / (n - 1) / n)
  c(A, A - 1.959964 * se, A + 1.959964 * se)
}
M <- readRDS(file.path(PROC, paste0("maihda_modelos_v1_", S, ".rds")))
e5 <- fread(file.path(TAB, paste0("tab_e5_02_modelos_v1_", S, ".csv")))
out <- list()
for (k in c("m1", "m2")) {
  m <- M[[k]]; y <- m@frame[[1]]
  cond <- auc_ci(fitted(m), y[, 1], y[, 2])
  ref <- e5[modelo == c(m1 = "M1 nulo", m2 = "M2 efeitos principais")[[k]]]
  stopifnot(abs(cond[1] - ref$AUC) < 1e-9, abs(cond[2] - ref$AUC_lo) < 1e-9)   # = Etapa 5
  fixa <- auc_ci(plogis(as.numeric(getME(m, "X") %*% fixef(m))), y[, 1], y[, 2])
  out[[k]] <- data.table(modelo = k, AUC_condicional = cond[1], AUC_cond_lo = cond[2], AUC_cond_hi = cond[3],
                         AUC_parte_fixa = fixa[1], AUC_fixa_lo = fixa[2], AUC_fixa_hi = fixa[3])
}
R <- rbindlist(out)
R[modelo == "m1", `:=`(AUC_parte_fixa = NA, AUC_fixa_lo = NA, AUC_fixa_hi = NA)]   # M1 nulo: parte fixa = só intercepto (AUC 0.5)
fwrite(R, file.path(TAB, paste0("tab_e7b1_03_auc_fixa_v1_", S, ".csv")))
log("AUC (DeLong) condicional e só com a parte fixa:\n", paste(capture.output(print(R)), collapse = "\n"))
