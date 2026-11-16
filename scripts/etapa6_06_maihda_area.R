# 6.6 MAIHDA do PIG com nível de área: logístico com efeitos aleatórios CRUZADOS de estrato (540) e região de saúde (433),
# dados agregados estrato × região (cbind(casos, não casos)); lme4::glmer (Laplace).
#   A1: 1 + (1|estrato) + (1|regsaude)
#   A2: raça + escolaridade + idade + região + tercil + (1|estrato) + (1|regsaude)
# Fórmulas (docs/referencias/maihda_formulas_fonte_v1_20261008.md):
#   VPC_k = σ²_k / (σ²_estrato + σ²_região + π²/3)   [BMJ Open 2020;10:e036130, PMC7590346, fórmulas 5–6]
#   PCV_estrato = (σ²_e,A1 − σ²_e,A2) / σ²_e,A1       [Evans 2024]
# ranef extraído ANTES de qualquer confint(profile) (lme4 1.1.37 altera o estado interno no perfil; Etapa 5).
# IC das variâncias: perfil de verossimilhança.
suppressPackageStartupMessages({library(lme4); library(data.table)})
PROJ <- Sys.getenv("PTB_PROJ", getwd()); S <- "20261008"  # 9a: raiz do projeto (rodar da raiz ou definir PTB_PROJ)
PROC <- file.path(PROJ, "data/processed"); TAB <- file.path(PROJ, "outputs/tables")
LOG <- file.path(PROJ, "outputs/logs", paste0("etapa6_", S, ".log"))
log <- function(...) { m <- paste0("[", format(Sys.time(), "%Y-%m-%d %H:%M:%S"), "] [06_maihda_area] ", paste0(...))
  cat(m, "\n"); cat(m, "\n", file = LOG, append = TRUE) }
set.seed(42)
E2 <- pi^2 / 3
a <- fread(file.path(PROC, paste0("maihda_estratos_regsaude_v1_", S, ".csv")), colClasses = list(character = "CO_REGSAUD"))
a[, `:=`(raca = relevel(factor(raca), "Branca"), esc3 = relevel(factor(esc3), "ge12"), idade3 = relevel(factor(idade3), "20a34"),
         regiao = relevel(factor(regiao), "SE"), tercil = relevel(factor(tercil), "T3"), estrato = factor(estrato),
         rs = factor(CO_REGSAUD), nc = n - casos)]
stopifnot(sum(a$n) == 25028320, nlevels(a$estrato) == 540, nlevels(a$rs) == 433)
CTL <- glmerControl(optimizer = "bobyqa", optCtrl = list(maxfun = 2e5))
t0 <- Sys.time()
A1 <- glmer(cbind(casos, nc) ~ 1 + (1 | estrato) + (1 | rs), data = a, family = binomial, control = CTL)
A2 <- glmer(cbind(casos, nc) ~ raca + esc3 + idade3 + regiao + tercil + (1 | estrato) + (1 | rs), data = a, family = binomial, control = CTL)
log(sprintf("ajustes: %.1f min; células %d", as.numeric(difftime(Sys.time(), t0, units = "mins")), nrow(a)))
for (m in list(A1, A2)) if (!is.null(m@optinfo$conv$lme4$messages)) log("aviso de convergência: ", paste(m@optinfo$conv$lme4$messages, collapse = "; "))
# ranef ANTES do perfil
reA2 <- ranef(A2, condVar = TRUE); reA1 <- ranef(A1)
uA2 <- data.table(estrato = rownames(reA2$estrato), u_area = reA2$estrato[, 1], u_area_se = sqrt(as.numeric(attr(reA2$estrato, "postVar"))))
uA1 <- data.table(estrato = rownames(reA1$estrato), u_area_m1 = reA1$estrato[, 1])
urs <- data.table(CO_REGSAUD = rownames(reA2$rs), u_rs = reA2$rs[, 1])
vc <- function(m) { v <- as.data.frame(VarCorr(m)); setNames(v$vcov, v$grp) }
v1 <- vc(A1); v2 <- vc(A2)
vpc <- function(v, k) v[[k]] / (v[["estrato"]] + v[["rs"]] + E2)
prf <- function(m) { ci <- confint(m, parm = "theta_", method = "profile", oldNames = FALSE)^2; ci }
c1 <- prf(A1); c2 <- prf(A2)
log("perfil A1:\n", paste(capture.output(print(c1)), collapse = "\n"))
log("perfil A2:\n", paste(capture.output(print(c2)), collapse = "\n"))
lin <- function(nome, v, ci) {
  ie <- grep("estrato", rownames(ci)); ir <- grep("rs", rownames(ci))
  data.table(modelo = nome, s2_estrato = v[["estrato"]], s2_estrato_lo = ci[ie, 1], s2_estrato_hi = ci[ie, 2],
             s2_regsaude = v[["rs"]], s2_regsaude_lo = ci[ir, 1], s2_regsaude_hi = ci[ir, 2],
             VPC_estrato_pct = 100 * vpc(v, "estrato"), VPC_regsaude_pct = 100 * vpc(v, "rs"))
}
tab <- rbind(lin("A1 nulo (estrato + região de saúde)", v1, c1), lin("A2 efeitos principais (estrato + região de saúde)", v2, c2))
tab[, PCV_estrato_pct := c(NA, 100 * (v1[["estrato"]] - v2[["estrato"]]) / v1[["estrato"]])]
tab[, PCV_regsaude_pct := c(NA, 100 * (v1[["rs"]] - v2[["rs"]]) / v1[["rs"]])]
# comparação com a Etapa 5 (modelos sem área; RDS regravado antes do perfil)
M5 <- readRDS(file.path(PROC, paste0("maihda_modelos_v1_", S, ".rds")))
u5 <- data.table(estrato = rownames(ranef(M5$m2)$estrato), u_e5 = ranef(M5$m2)$estrato[, 1])
u51 <- data.table(estrato = rownames(ranef(M5$m1)$estrato), u_e5_m1 = ranef(M5$m1)$estrato[, 1])
p5 <- fread(file.path(TAB, paste0("tab_e5_03_predicoes_v1_", S, ".csv")))
stopifnot(max(abs(u5[match(p5$estrato, estrato)]$u_e5 - p5$u)) < 1e-8)   # RDS limpo = tabela da Etapa 5
U <- Reduce(function(x, y) merge(x, y, by = "estrato"), list(uA2, uA1, u5, u51))
r2 <- cor(U$u_area, U$u_e5); r1 <- cor(U$u_area_m1, U$u_e5_m1)
s2 <- cor(U$u_area, U$u_e5, method = "spearman")
top15 <- function(x, col) x[order(-get(col))][1:15]$estrato
ov <- length(intersect(top15(U, "u_area"), top15(U, "u_e5")))
tab[, `:=`(cor_u_estrato_vs_E5 = c(r1, r2), spearman_vs_E5 = c(cor(U$u_area_m1, U$u_e5_m1, method = "spearman"), s2),
           top15_u_comuns_E5 = c(NA, ov), s2_estrato_E5 = c(as.numeric(VarCorr(M5$m1)$estrato), as.numeric(VarCorr(M5$m2)$estrato)))]
fwrite(tab, file.path(TAB, paste0("tab_e6_06_maihda_area_v1_", S, ".csv")))
fwrite(U[order(-u_area)], file.path(TAB, paste0("tab_e6_06_u_estrato_v1_", S, ".csv")))
fwrite(urs[order(-u_rs)], file.path(TAB, paste0("tab_e6_06_u_regsaude_v1_", S, ".csv")))
log("MAIHDA com área:\n", paste(capture.output(print(tab)), collapse = "\n"))
log("10 maiores û de estrato (A2) com área × Etapa 5:\n", paste(capture.output(print(U[order(-u_area)][1:10])), collapse = "\n"))
log(sprintf("fim (%.1f min)", as.numeric(difftime(Sys.time(), t0, units = "mins"))))
