# 6b.2 AUC (IC DeLong) do MAIHDA do PIG com efeitos aleatórios cruzados estrato × região de saúde (modelos A1 e A2 da 6.6).
# Reajuste idêntico ao de etapa6_06_maihda_area.R (mesmos dados, fórmulas e controle); confere σ² com tab_e6_06.
# AUC = P(p̂ caso > p̂ não caso) + ½ P(empate), p̂ = probabilidade prevista da célula estrato × região (fixos + ambos os
# efeitos aleatórios) [Evans 2024; BMJ Open 2020, PMC7590346]. IC: DeLong com valores de colocação ponderados (mesma
# função da Etapa 5, etapa5_02_maihda.R). Sem confint(profile) aqui; RDS dos dois modelos gravado logo após o ajuste.
suppressPackageStartupMessages({library(lme4); library(data.table)})
PROJ <- Sys.getenv("PTB_PROJ", getwd()); S <- "20261008"  # 9a: raiz do projeto (rodar da raiz ou definir PTB_PROJ)
PROC <- file.path(PROJ, "data/processed"); TAB <- file.path(PROJ, "outputs/tables")
LOG <- file.path(PROJ, "outputs/logs", paste0("etapa6_", S, ".log"))
log <- function(...) { m <- paste0("[", format(Sys.time(), "%Y-%m-%d %H:%M:%S"), "] [6b_02_auc_area] ", paste0(...))
  cat(m, "\n"); cat(m, "\n", file = LOG, append = TRUE) }
set.seed(42)
auc <- function(p, cas, nc) {
  o <- order(p); p <- p[o]; cas <- as.numeric(cas[o]); nc <- as.numeric(nc[o])
  g <- split(seq_along(p), p); cumNC <- 0; s <- 0
  for (ix in g) { cj <- sum(cas[ix]); nj <- sum(nc[ix]); s <- s + cj * (cumNC + 0.5 * nj); cumNC <- cumNC + nj }
  s / (sum(cas) * sum(nc))
}
auc_ci <- function(p, cas, nc) {
  cas <- as.numeric(cas); nc <- as.numeric(nc); m <- sum(cas); n <- sum(nc)
  o <- order(p); ps <- p[o]; cs <- cas[o]; ns <- nc[o]
  # valores de colocação por célula, vetorizados (equivalente ao sapply da Etapa 5)
  u <- unique(ps); k <- match(ps, u)
  nc_u <- tapply(ns, k, sum); cs_u <- tapply(cs, k, sum)
  below_nc <- c(0, cumsum(nc_u))[seq_along(u)]; above_cs <- rev(c(0, cumsum(rev(cs_u))))[-1]
  v10 <- ((below_nc + 0.5 * nc_u) / n)[k]; v01 <- ((above_cs + 0.5 * cs_u) / m)[k]
  A <- sum(cs * v10) / m
  se <- sqrt(sum(cs * (v10 - A)^2) / (m - 1) / m + sum(ns * (v01 - A)^2) / (n - 1) / n)
  c(A, A - 1.959964 * se, A + 1.959964 * se)
}
a <- fread(file.path(PROC, paste0("maihda_estratos_regsaude_v1_", S, ".csv")), colClasses = list(character = "CO_REGSAUD"))
a[, `:=`(raca = relevel(factor(raca), "Branca"), esc3 = relevel(factor(esc3), "ge12"), idade3 = relevel(factor(idade3), "20a34"),
         regiao = relevel(factor(regiao), "SE"), tercil = relevel(factor(tercil), "T3"), estrato = factor(estrato),
         rs = factor(CO_REGSAUD), nc = n - casos)]
CTL <- glmerControl(optimizer = "bobyqa", optCtrl = list(maxfun = 2e5))
A1 <- glmer(cbind(casos, nc) ~ 1 + (1 | estrato) + (1 | rs), data = a, family = binomial, control = CTL)
A2 <- glmer(cbind(casos, nc) ~ raca + esc3 + idade3 + regiao + tercil + (1 | estrato) + (1 | rs), data = a, family = binomial, control = CTL)
saveRDS(list(A1 = A1, A2 = A2), file.path(PROC, paste0("maihda_area_modelos_v1_", S, ".rds")))   # antes de qualquer perfil
t6 <- fread(file.path(TAB, paste0("tab_e6_06_maihda_area_v1_", S, ".csv")))
v <- function(m, g) as.numeric(VarCorr(m)[[g]])
stopifnot(abs(v(A1, "estrato") - t6$s2_estrato[1]) < 1e-8, abs(v(A2, "estrato") - t6$s2_estrato[2]) < 1e-8,
          abs(v(A2, "rs") - t6$s2_regsaude[2]) < 1e-8)
# conferência da função DeLong vetorizada contra a da Etapa 5 (M1 da Etapa 5)
e5 <- fread(file.path(TAB, paste0("tab_e5_02_modelos_v1_", S, ".csv")))
M5 <- readRDS(file.path(PROC, paste0("maihda_modelos_v1_", S, ".rds")))
d5 <- M5$m1@frame; y5 <- d5[[1]]
c5 <- auc_ci(fitted(M5$m1), y5[, 1], y5[, 2])
stopifnot(abs(c5[1] - e5$AUC[1]) < 1e-9, abs(c5[2] - e5$AUC_lo[1]) < 1e-9, abs(c5[3] - e5$AUC_hi[1]) < 1e-9)
r1 <- auc_ci(fitted(A1), a$casos, a$nc); r2 <- auc_ci(fitted(A2), a$casos, a$nc)
stopifnot(abs(r1[1] - auc(fitted(A1), a$casos, a$nc)) < 1e-12)
out <- data.table(modelo = c("A1 nulo (estrato + região de saúde)", "A2 efeitos principais (estrato + região de saúde)"),
                  AUC = c(r1[1], r2[1]), AUC_lo = c(r1[2], r2[2]), AUC_hi = c(r1[3], r2[3]), celulas = nrow(a), N = sum(a$n))
fwrite(out, file.path(TAB, paste0("tab_e6b_02_auc_area_v1_", S, ".csv")))
log("AUC do MAIHDA cruzado (DeLong; σ² conferidos com tab_e6_06; DeLong vetorizado = Etapa 5 no M1):\n",
    paste(capture.output(print(out)), collapse = "\n"))
