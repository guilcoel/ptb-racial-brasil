# 5.2–5.3 e 5.5 MAIHDA do PIG (lme4::glmer, logístico, intercepto aleatório de estrato, dados agregados
# cbind(casos, não casos) — verossimilhança binomial idêntica à individual).
# Fórmulas (docs/referencias/maihda_formulas_fonte_v1_20261008.md; Evans et al. 2024, PMC11059336):
#   VPC = σ²_u / (σ²_u + π²/3)                       [Evans 2024, "The VPC, AUC and PCV in logistic models"]
#   PCV = (σ²_u,M1 − σ²_u,M2) / σ²_u,M1              [Evans 2024, "...attributable to interaction effects"]
#   AUC = P(p̂_caso > p̂_não caso) + ½ P(empate), p̂ = prob. prevista do estrato   [Evans 2024, idem]
#   π^B_j = logit⁻¹(Xβ + u_j) − logit⁻¹(Xβ)           [Evans 2024, Fig. 4C]
#   IC das predições: simulação β ~ N(β̂, V̂), u_j ~ N(û_j, condVar_j), independentes   [Evans 2024, MLE]
# IC das variâncias e VPC: perfil de verossimilhança (confint, method = "profile").
# IC da AUC: DeLong (ver auc_ci). IC da PCV (e das variâncias, secundário): bootstrap paramétrico de 500 réplicas simuladas do Modelo 2
# (seed 42), reajustando Modelos 1 e 2 em cada réplica.
suppressPackageStartupMessages({library(lme4); library(data.table)})
PROJ <- Sys.getenv("PTB_PROJ", getwd()); S <- "20261008"  # 9a: raiz do projeto (rodar da raiz ou definir PTB_PROJ)
PROC <- file.path(PROJ, "data/processed"); TAB <- file.path(PROJ, "outputs/tables")
LOG <- file.path(PROJ, "outputs/logs", paste0("etapa5_", S, ".log"))
log <- function(...) { m <- paste0("[", format(Sys.time(), "%Y-%m-%d %H:%M:%S"), "] [02_maihda] ", paste0(...))
  cat(m, "\n"); cat(m, "\n", file = LOG, append = TRUE) }
set.seed(42)
E2 <- pi^2 / 3
REF <- "Branca|ge12|20a34|SE|T3"
NBOOT <- as.integer(Sys.getenv("NBOOT", "500")); NSIM <- 2000

prep <- function(f) {
  a <- fread(file.path(PROC, f))
  a[, `:=`(raca = relevel(factor(raca), "Branca"), esc3 = relevel(factor(esc3), "ge12"),
           idade3 = relevel(factor(idade3), "20a34"), regiao = relevel(factor(regiao), "SE"),
           tercil = relevel(factor(tercil), "T3"), estrato = factor(estrato), nc = n - casos)]
  a
}
CTL <- glmerControl(optimizer = "bobyqa", optCtrl = list(maxfun = 1e5))
F1 <- cbind(casos, nc) ~ 1 + (1 | estrato)
F2 <- cbind(casos, nc) ~ raca + esc3 + idade3 + regiao + tercil + (1 | estrato)
ajusta <- function(f, a) glmer(f, data = a, family = binomial, control = CTL)
s2 <- function(m) as.numeric(VarCorr(m)$estrato)
vpc <- function(v) v / (v + E2)
auc <- function(p, cas, nc) {           # Mann–Whitney ponderado, empates = 1/2
  o <- order(p); p <- p[o]; cas <- as.numeric(cas[o]); nc <- as.numeric(nc[o])
  g <- split(seq_along(p), p)          # agrupa empates exatos
  cumNC <- 0; s <- 0
  for (ix in g) { cj <- sum(cas[ix]); nj <- sum(nc[ix]); s <- s + cj * (cumNC + 0.5 * nj); cumNC <- cumNC + nj }
  s / (sum(cas) * sum(nc))
}
auc_m <- function(m, a) auc(fitted(m), a$casos, a$nc)
# IC da AUC: DeLong (valores de colocação ponderados; p̂ dos estratos tratados como escores fixos). O percentil do
# bootstrap paramétrico NÃO é usado para a AUC: cada réplica sorteia u_j novos, sem shrinkage, e a AUC das réplicas
# fica deslocada para cima (o IC percentil não contém a estimativa).
auc_ci <- function(p, cas, nc) {
  cas <- as.numeric(cas); nc <- as.numeric(nc); m <- sum(cas); n <- sum(nc)
  v10 <- sapply(p, function(x) (sum(nc[p < x]) + 0.5 * sum(nc[p == x])) / n)   # por caso no estrato
  v01 <- sapply(p, function(x) (sum(cas[p > x]) + 0.5 * sum(cas[p == x])) / m)  # por não caso
  A <- sum(cas * v10) / m
  s10 <- sum(cas * (v10 - A)^2) / (m - 1); s01 <- sum(nc * (v01 - A)^2) / (n - 1)
  se <- sqrt(s10 / m + s01 / n)
  c(A - 1.959964 * se, A + 1.959964 * se)
}
auc_cim <- function(m, a) auc_ci(fitted(m), a$casos, a$nc)
perfil <- function(m) { ci <- confint(m, parm = "theta_", method = "profile", oldNames = FALSE)^2; as.numeric(ci[1, ]) }

# ---- 5.2 modelos principais
a <- prep(paste0("maihda_estratos_v1_", S, ".csv"))
stopifnot(nrow(a) == 540, sum(a$n) == 25028320)
m1 <- ajusta(F1, a); m2 <- ajusta(F2, a)
# Etapa 6.6: o RDS guarda os modelos serializados ANTES de qualquer confint(profile), que altera o estado interno
LIMPO <- list(m1 = serialize(m1, NULL), m2 = serialize(m2, NULL))
re2 <- ranef(m2, condVar = TRUE)$estrato  # ANTES do perfil: confint(method = "profile") altera o estado interno (pp) e muda ranef() (lme4 1.1.37)
v1 <- s2(m1); v2 <- s2(m2)
p1 <- perfil(m1); p2 <- perfil(m2)
log(sprintf("M1: σ² = %.4f (perfil %.4f–%.4f); VPC = %.2f%%; AUC = %.4f", v1, p1[1], p1[2], 100 * vpc(v1), auc_m(m1, a)))
log(sprintf("M2: σ² = %.4f (perfil %.4f–%.4f); VPC = %.3f%%; PCV = %.2f%%; AUC = %.4f", v2, p2[1], p2[2], 100 * vpc(v2),
            100 * (v1 - v2) / v1, auc_m(m2, a)))
# checagem Laplace × quadratura adaptativa (um único efeito aleatório escalar)
q1 <- s2(glmer(F1, data = a, family = binomial, control = CTL, nAGQ = 25))
q2 <- s2(glmer(F2, data = a, family = binomial, control = CTL, nAGQ = 25))
log(sprintf("nAGQ = 25: σ² M1 = %.6f (Laplace %.6f); M2 = %.6f (Laplace %.6f)", q1, v1, q2, v2))

# bootstrap paramétrico do Modelo 2
log(sprintf("bootstrap paramétrico: %d réplicas do Modelo 2, seed 42", NBOOT))
sims <- simulate(m2, nsim = NBOOT, seed = 42)
bt <- rbindlist(lapply(seq_len(NBOOT), function(b) {
  y <- sims[[b]]; ab <- copy(a); ab[, `:=`(casos = y[, 1], nc = y[, 2])]
  r1 <- suppressWarnings(refit(m1, newresp = y)); r2 <- suppressWarnings(refit(m2, newresp = y))
  w1 <- s2(r1); w2 <- s2(r2)
  data.table(rep = b, s2_m1 = w1, s2_m2 = w2, vpc_m1 = vpc(w1), vpc_m2 = vpc(w2), pcv = (w1 - w2) / w1,
             auc_m1 = auc_m(r1, ab), auc_m2 = auc_m(r2, ab),
             conv = is.null(r1@optinfo$conv$lme4$messages) && is.null(r2@optinfo$conv$lme4$messages))
}))
fwrite(bt, file.path(TAB, paste0("tab_e5_02_bootstrap_v1_", S, ".csv")))
qq <- function(x) as.numeric(quantile(x, c(.025, .975)))
log(sprintf("bootstrap: %d/%d sem aviso de convergência", sum(bt$conv), NBOOT))

linha <- function(modelo, v, pf, bs2, bvpc, pcv, bpcv, au, bau, N, K)
  data.table(modelo = modelo, N = N, estratos = K, s2 = v, s2_lo_perfil = pf[1], s2_hi_perfil = pf[2],
             s2_lo_boot = bs2[1], s2_hi_boot = bs2[2], VPC_pct = 100 * vpc(v), VPC_lo = 100 * vpc(pf[1]),
             VPC_hi = 100 * vpc(pf[2]), PCV_pct = pcv, PCV_lo = bpcv[1], PCV_hi = bpcv[2], AUC = au, AUC_lo = bau[1], AUC_hi = bau[2])
tab <- rbind(
  linha("M1 nulo", v1, p1, qq(bt$s2_m1), NA, NA, c(NA, NA), auc_m(m1, a), auc_cim(m1, a), sum(a$n), nrow(a)),
  linha("M2 efeitos principais", v2, p2, qq(bt$s2_m2), NA, 100 * (v1 - v2) / v1, 100 * qq(bt$pcv), auc_m(m2, a), auc_cim(m2, a),
        sum(a$n), nrow(a)))

# sensibilidade: + ano (estrato × ano)
ay <- prep(paste0("maihda_estratos_ano_v1_", S, ".csv")); ay[, ano := factor(ano)]
stopifnot(sum(ay$n) == sum(a$n))
m1y <- ajusta(F1, ay); m2y <- ajusta(update(F2, . ~ . + ano), ay)
LIMPO$m1y <- serialize(m1y, NULL); LIMPO$m2y <- serialize(m2y, NULL)
v1y <- s2(m1y); v2y <- s2(m2y); p2y <- perfil(m2y); p1y <- perfil(m1y)
tab <- rbind(tab,
  linha("M1 nulo (estrato × ano)", v1y, p1y, c(NA, NA), NA, NA, c(NA, NA), auc_m(m1y, ay), auc_cim(m1y, ay), sum(ay$n), nlevels(ay$estrato)),
  linha("M2 + ano (estrato × ano)", v2y, p2y, c(NA, NA), NA, 100 * (v1y - v2y) / v1y, c(NA, NA), auc_m(m2y, ay), auc_cim(m2y, ay),
        sum(ay$n), nlevels(ay$estrato)))
log(sprintf("M2 + ano: σ² = %.4f (perfil %.4f–%.4f); VPC = %.3f%%; PCV vs M1 (estrato × ano) = %.2f%%", v2y, p2y[1], p2y[2],
            100 * vpc(v2y), 100 * (v1y - v2y) / v1y))

# efeitos fixos do M2 (OR, IC de Wald)
fe <- fixef(m2); se <- sqrt(diag(vcov(m2)))
fwrite(data.table(termo = names(fe), beta = fe, OR = exp(fe), OR_lo = exp(fe - 1.959964 * se), OR_hi = exp(fe + 1.959964 * se)),
       file.path(TAB, paste0("tab_e5_02_fixos_m2_v1_", S, ".csv")))

# ---- 5.3 predições por estrato (M2: fixos + aleatório), por simulação
X <- model.matrix(~ raca + esc3 + idade3 + regiao + tercil, data = a)
stopifnot(identical(colnames(X), names(fe)))
re <- re2
u <- re[as.character(a$estrato), 1]; pv <- as.numeric(attr(re, "postVar"))[match(as.character(a$estrato), rownames(re))]
set.seed(42)
B <- MASS::mvrnorm(NSIM, fe, vcov(m2))                 # NSIM × p
U <- matrix(rnorm(NSIM * nrow(a), rep(u, each = NSIM), rep(sqrt(pv), each = NSIM)), NSIM)   # NSIM × estratos
XB <- B %*% t(X)
P <- plogis(XB + U); PA <- plogis(XB)
r <- which(a$estrato == REF)
ci <- function(M) t(apply(M, 2, quantile, c(.025, .975)))
xb <- as.numeric(X %*% fe)
stopifnot(max(abs(plogis(xb + u) - fitted(m2))) < 1e-8)   # û coerente com o ajuste
pr <- data.table(a[, .(estrato, raca, esc3, idade3, regiao, tercil, n, casos)], obs_pct = 100 * a$casos / a$n,
                 p_pct = 100 * plogis(xb + u), ci(100 * P), u = u, u_se = sqrt(pv),
                 piB_pp = 100 * (plogis(xb + u) - plogis(xb)), ci(100 * (P - PA)),
                 razao = plogis(xb + u) / plogis(xb[r] + u[r]), ci(P / P[, r]),
                 dif_pp = 100 * (plogis(xb + u) - plogis(xb[r] + u[r])), ci(100 * (P - P[, r])))
setnames(pr, c("estrato", "raca", "esc3", "idade3", "regiao", "tercil", "n", "casos", "obs_pct", "p_pct", "p_lo", "p_hi",
               "u", "u_se", "piB_pp", "piB_lo", "piB_hi", "razao", "razao_lo", "razao_hi", "dif_pp", "dif_lo", "dif_hi"))
pr[, `:=`(u_lo = u - 1.959964 * u_se, u_hi = u + 1.959964 * u_se, p_m1_pct = 100 * fitted(m1))]
fwrite(pr, file.path(TAB, paste0("tab_e5_03_predicoes_v1_", S, ".csv")))
top <- rbind(pr[order(-p_pct)][1:15][, lista := "maior_risco"], pr[order(p_pct)][1:15][, lista := "menor_risco"],
             pr[order(-u)][1:15][, lista := "u_positivo"], pr[order(u)][1:15][, lista := "u_negativo"])
fwrite(top, file.path(TAB, paste0("tab_e5_03_top15_v1_", S, ".csv")))
log(sprintf("estrato de referência %s: p = %.2f%% (%.2f–%.2f)", REF, pr$p_pct[r], pr$p_lo[r], pr$p_hi[r]))
log("15 de maior risco:\n", paste(capture.output(print(pr[order(-p_pct)][1:15, .(estrato, n, obs_pct, p_pct, p_lo, p_hi, razao)])), collapse = "\n"))
log("15 com maior u positivo:\n", paste(capture.output(print(pr[order(-u)][1:15, .(estrato, n, u, u_lo, u_hi, piB_pp)])), collapse = "\n"))
log("15 com maior u negativo:\n", paste(capture.output(print(pr[order(u)][1:15, .(estrato, n, u, u_lo, u_hi, piB_pp)])), collapse = "\n"))

# ---- 5.5 sensibilidade: só ig_metodo = outro método
ao <- prep(paste0("maihda_estratos_outro_v1_", S, ".csv"))
m1o <- ajusta(F1, ao); m2o <- ajusta(F2, ao); v1o <- s2(m1o); v2o <- s2(m2o)
LIMPO$m1o <- serialize(m1o, NULL); LIMPO$m2o <- serialize(m2o, NULL)
reo <- ranef(m2o, condVar = TRUE)$estrato  # ANTES do perfil: confint(method = "profile") altera o estado interno (pp) e muda ranef() (lme4 1.1.37)
p1o <- perfil(m1o); p2o <- perfil(m2o)
tab <- rbind(tab,
  linha("M1 nulo — outro método", v1o, p1o, c(NA, NA), NA, NA, c(NA, NA), auc_m(m1o, ao), auc_cim(m1o, ao), sum(ao$n), nrow(ao)),
  linha("M2 — outro método", v2o, p2o, c(NA, NA), NA, 100 * (v1o - v2o) / v1o, c(NA, NA), auc_m(m2o, ao), auc_cim(m2o, ao), sum(ao$n), nrow(ao)))
uo <- data.table(estrato = rownames(reo), u = reo[, 1], u_se = sqrt(as.numeric(attr(reo, "postVar"))))
uo <- merge(uo, ao[, .(estrato = as.character(estrato), n, casos)], by = "estrato")
uo <- merge(uo, pr[, .(estrato = as.character(estrato), u_principal = u, rank_principal = frank(-u))], by = "estrato")
uo[, `:=`(u_lo = u - 1.959964 * u_se, u_hi = u + 1.959964 * u_se)]
fwrite(uo[order(-u)], file.path(TAB, paste0("tab_e5_05_outro_u_v1_", S, ".csv")))
log(sprintf("outro método: M1 σ² = %.4f; M2 σ² = %.4f (%.4f–%.4f); VPC M2 = %.3f%%; PCV = %.2f%%; cor(u, u principal) = %.3f",
            v1o, v2o, p2o[1], p2o[2], 100 * vpc(v2o), 100 * (v1o - v2o) / v1o, cor(uo$u, uo$u_principal)))
log("5 maiores u positivos (outro método):\n", paste(capture.output(print(uo[order(-u)][1:5])), collapse = "\n"))
fwrite(tab, file.path(TAB, paste0("tab_e5_02_modelos_v1_", S, ".csv")))
log("modelos:\n", paste(capture.output(print(tab[, .(modelo, s2, s2_lo_perfil, s2_hi_perfil, VPC_pct, VPC_lo, VPC_hi, PCV_pct, PCV_lo, PCV_hi, AUC, AUC_lo, AUC_hi)])), collapse = "\n"))
MODS <- lapply(LIMPO, unserialize)
stopifnot(max(abs(plogis(as.numeric(getME(MODS$m2, "X") %*% fixef(MODS$m2)) + ranef(MODS$m2)$estrato[as.character(MODS$m2@frame$estrato), 1]) - fitted(MODS$m2))) < 1e-8)
saveRDS(MODS, file.path(PROC, paste0("maihda_modelos_v1_", S, ".rds")))   # estado anterior ao perfil
log("fim")
