# Auditoria independente — Etapa 7b — recálculo de modelos (itens 4, 6, 7, 9, 10)
# Somente leitura nos dados; grava apenas em audit_independente/etapa7b/.
# Estratégia: todas as covariáveis são categóricas => agregação exata por
# (padrão de covariáveis × cluster). Escores e Hessianas agregadas são idênticos
# aos do ajuste individual, logo β e sanduíche agrupado são exatos.
set.seed(42)
suppressMessages({library(DBI); library(duckdb); library(lme4)})
setwd("/Volumes/Forja/ptb-racial-brasil")
out <- "audit_independente/etapa7b"

con <- dbConnect(duckdb())
dbExecute(con, "CREATE VIEW b AS SELECT * FROM read_parquet('data/processed/sinasc_brasil_2015_2024_v3_20261008/ano=*/part-0.parquet', hive_partitioning=true) WHERE incl")
dbExecute(con, "CREATE TABLE t AS SELECT CAST(CO_REGSAUD AS VARCHAR) rs, CAST(ano AS BIGINT) ano, tercil_reg FROM read_csv_auto('data/processed/tercil_reg_regsaude_ano_v1_20261008.csv', all_varchar=true)")
dbExecute(con, "CREATE TABLE m AS SELECT CAST(CODMUNRES AS VARCHAR) cm, CAST(CO_REGSAUD AS VARCHAR) rs FROM read_csv_auto('data/processed/municipio_regsaude_dez24_v1_20261008.csv', all_varchar=true)")

agg <- dbGetQuery(con, "
  SELECT b.raca, b.idade_cat, b.ano, b.regiao,
         coalesce(m.rs, 'UF_' || substr(b.CODMUNRES,1,2)) AS cl,
         t.tercil_reg,
         count(b.ptb_ind)                         AS n_nn,
         sum(b.ptb_ind)                           AS y_ind,
         sum(b.ptb_esp)                           AS y_esp,
         count(*) FILTER (WHERE b.ptb_tipo IS NULL)          AS k_termo,
         count(*) FILTER (WHERE b.ptb_tipo = 'espontaneo')   AS k_esp,
         count(*) FILTER (WHERE b.ptb_tipo = 'indicado')     AS k_ind
  FROM b
  LEFT JOIN m ON substr(b.CODMUNRES,1,6) = m.cm
  LEFT JOIN t ON b.CO_REGSAUD = t.rs AND b.ano = t.ano
  GROUP BY ALL")
dbDisconnect(con, shutdown = TRUE)

agg$raca      <- relevel(factor(agg$raca), "Branca")
agg$idade_cat <- relevel(factor(agg$idade_cat), "20-34")
agg$ano       <- factor(agg$ano)
agg$regiao    <- relevel(factor(agg$regiao), "SE")
agg$cl        <- factor(agg$cl)
cat("células agregadas:", nrow(agg), " G =", nlevels(agg$cl), " N(ptb nn) =", sum(agg$n_nn), "\n")

# ---------------- Poisson M2 com sanduíche agrupado ----------------
pois_cl <- function(yvar) {
  d <- agg[agg$n_nn > 0, ]
  X <- model.matrix(~ raca + idade_cat + ano + regiao, d)
  y <- d[[yvar]]; off <- log(d$n_nn)
  fit <- glm.fit(X, y, offset = off, family = poisson(), control = list(epsilon = 1e-12, maxit = 100))
  b <- fit$coefficients; mu <- as.vector(exp(X %*% b + off))
  bread <- solve(crossprod(X * mu, X))
  U <- rowsum(X * (y - mu), d$cl)              # escore por cluster
  meat <- crossprod(U)
  N <- sum(d$n_nn); K <- ncol(X); G <- nrow(U)
  adj <- G/(G-1) * (N-1)/(N-K)
  V <- adj * bread %*% meat %*% bread
  list(b = b, V = V, N = N, K = K, G = G, adj = adj, conv = fit$converged)
}
pr_row <- function(f, term) {
  est <- f$b[term]; se <- sqrt(f$V[term, term])
  c(PR = exp(est), lo = exp(est - qnorm(.975)*se), hi = exp(est + qnorm(.975)*se), se = se)
}
f_ind <- pois_cl("y_ind"); f_esp <- pois_cl("y_esp")
it4 <- pr_row(f_ind, "racaPreta"); it6 <- pr_row(f_esp, "racaIndigena")
cat("Poisson ind: N =", f_ind$N, " K =", f_ind$K, " G =", f_ind$G, " adj =", f_ind$adj, " conv =", f_ind$conv, "\n")
print(round(rbind(item4_ind_Preta = it4, item6_esp_Indigena = it6), 4))
# tabela completa de raça (para checagem cruzada)
racas <- c("racaPreta","racaParda","racaIndigena")
pois_tab <- rbind(
  data.frame(desfecho="ptb_ind", termo=racas, t(sapply(racas, function(r) pr_row(f_ind, r)))),
  data.frame(desfecho="ptb_esp", termo=racas, t(sapply(racas, function(r) pr_row(f_esp, r)))))
write.csv(pois_tab, file.path(out, "poisson_m2_raca_v1_20261009.csv"), row.names = FALSE)

# ---------------- Logit multinomial com interação raça × tercil ----------------
d <- agg[!is.na(agg$tercil_reg) & (agg$k_termo + agg$k_esp + agg$k_ind) > 0, ]
d$tercil_reg <- relevel(factor(d$tercil_reg), "T3")
X <- model.matrix(~ raca + idade_cat + ano + regiao + tercil_reg + raca:tercil_reg, d)
Y <- cbind(d$k_termo, d$k_esp, d$k_ind); Nr <- rowSums(Y)
p <- ncol(X); J <- 2
theta <- rep(0, p*J)
# chute inicial: interceptos = log-odds marginais
theta[1] <- log(sum(Y[,2])/sum(Y[,1])); theta[p+1] <- log(sum(Y[,3])/sum(Y[,1]))
probs <- function(th) {
  e1 <- exp(X %*% th[1:p]); e2 <- exp(X %*% th[(p+1):(2*p)])
  den <- 1 + e1 + e2; cbind(1/den, e1/den, e2/den)
}
for (it in 1:50) {
  P <- probs(theta)
  r1 <- Y[,2] - Nr*P[,2]; r2 <- Y[,3] - Nr*P[,3]
  g <- c(crossprod(X, r1), crossprod(X, r2))
  w11 <- Nr*P[,2]*(1-P[,2]); w22 <- Nr*P[,3]*(1-P[,3]); w12 <- -Nr*P[,2]*P[,3]
  H <- rbind(cbind(crossprod(X*w11, X), crossprod(X*w12, X)),
             cbind(crossprod(X*w12, X), crossprod(X*w22, X)))
  step <- solve(H, g); theta <- theta + step
  if (max(abs(step)) < 1e-10) break
}
cat("multinomial: iterações =", it, " max|passo| =", max(abs(step)), "\n")
P <- probs(theta)
r1 <- Y[,2] - Nr*P[,2]; r2 <- Y[,3] - Nr*P[,3]
w11 <- Nr*P[,2]*(1-P[,2]); w22 <- Nr*P[,3]*(1-P[,3]); w12 <- -Nr*P[,2]*P[,3]
H <- rbind(cbind(crossprod(X*w11, X), crossprod(X*w12, X)),
           cbind(crossprod(X*w12, X), crossprod(X*w22, X)))
bread <- solve(H)
U <- cbind(rowsum(X*r1, d$cl), rowsum(X*r2, d$cl))
meat <- crossprod(U)
Nm <- sum(Nr); Km <- p*J; Gm <- nrow(U)
adj_m <- Gm/(Gm-1) * (Nm-1)/(Nm-Km)
Vm_raw <- bread %*% meat %*% bread
nm <- c(paste0("esp:", colnames(X)), paste0("ind:", colnames(X)))
names(theta) <- nm; dimnames(Vm_raw) <- list(nm, nm)
cat("multinomial: N =", Nm, " K =", Km, " G =", Gm, " adj =", adj_m, "\n")

rrr_within <- function(cat, raca, terc, V) {
  a <- paste0(cat, ":raca", raca)
  terms <- a
  if (terc != "T3") terms <- c(a, paste0(cat, ":raca", raca, ":tercil_reg", terc))
  L <- setNames(rep(0, length(theta)), names(theta)); L[terms] <- 1
  est <- sum(L*theta); se <- sqrt(as.numeric(t(L) %*% V %*% L))
  c(RRR = exp(est), lo = exp(est - qnorm(.975)*se), hi = exp(est + qnorm(.975)*se), se = se)
}
mn_tab <- do.call(rbind, lapply(c("esp","ind"), function(cc)
  do.call(rbind, lapply(c("Preta","Parda","Indigena"), function(rr)
    do.call(rbind, lapply(c("T1","T2","T3"), function(tt)
      data.frame(categoria=cc, raca=rr, tercil=tt,
                 t(rrr_within(cc, rr, tt, adj_m*Vm_raw)),
                 se_sem_ajuste = rrr_within(cc, rr, tt, Vm_raw)["se"])))))))
write.csv(mn_tab, file.path(out, "multinomial_rrr_tercil_v1_20261009.csv"), row.names = FALSE)
it7     <- rrr_within("ind", "Indigena", "T1", adj_m*Vm_raw)
it7_raw <- rrr_within("ind", "Indigena", "T1", Vm_raw)
print(round(rbind(item7_ajustado = it7, item7_sem_ajuste = it7_raw), 4))

# ---------------- MAIHDA (RDS) ----------------
L <- readRDS("data/processed/maihda_modelos_v1_20261008.rds")
m2 <- L$m2
mf <- model.frame(m2); yy <- mf[[1]]
cs <- as.numeric(yy[, "casos"]); nc <- as.numeric(yy[, "nc"])
# p̂ = fitted(m2) (condicional, inclui û) ; checagem: igual a plogis(Xβ + Zû)
ph <- fitted(m2)
Xf <- getME(m2, "X"); u <- ranef(m2)$estrato
eta <- as.vector(Xf %*% fixef(m2)) + u[as.character(mf$estrato), 1]
p_man <- plogis(eta)
cat("max|fitted - plogis(Xb+u)| =", max(abs(ph - p_man)), "\n")

auc_w <- function(p, wc, wn) {
  o <- order(p); p <- p[o]; wc <- wc[o]; wn <- wn[o]
  C <- sum(wc); NC <- sum(wn)
  # para cada valor único de p: não casos abaixo, iguais; casos acima, iguais
  up <- unique(p); idx <- match(p, up)
  wn_u <- tapply(wn, idx, sum); wc_u <- tapply(wc, idx, sum)
  cum_n_below <- c(0, cumsum(wn_u))[seq_along(up)]
  cum_c_above <- C - cumsum(wc_u)
  V10 <- (cum_n_below + 0.5*wn_u) / NC     # placement de cada caso (por valor)
  V01 <- (cum_c_above + 0.5*wc_u) / C      # placement de cada não caso
  auc <- sum(wc_u * V10) / C
  S10 <- sum(wc_u * (V10 - auc)^2) / (C - 1)
  S01 <- sum(wn_u * (V01 - auc)^2) / (NC - 1)
  se <- sqrt(S10/C + S01/NC)
  c(AUC = auc, lo = auc - qnorm(.975)*se, hi = auc + qnorm(.975)*se, se = se)
}
it9 <- auc_w(ph, cs, nc)
# checagem por força bruta (O(540^2)) da AUC
pp <- outer(ph, ph, function(a, b) (a > b) + 0.5*(a == b))
auc_bf <- sum(outer(cs, nc) * pp) / (sum(cs)*sum(nc))
cat("AUC força bruta =", auc_bf, "\n")
# AUC do m2 só com efeitos fixos (para diagnóstico)
it9_fix <- auc_w(plogis(as.vector(Xf %*% fixef(m2))), cs, nc)
print(round(rbind(item9 = it9, item9_so_fixos = it9_fix), 5))

imax <- which.max(p_man)
it10 <- data.frame(estrato = as.character(mf$estrato[imax]), p = p_man[imax],
                   n = cs[imax] + nc[imax], casos = cs[imax], obs = cs[imax]/(cs[imax]+nc[imax]))
print(it10)
top <- data.frame(estrato = as.character(mf$estrato), p = p_man, obs = cs/(cs+nc), n = cs+nc)
top <- top[order(-top$p), ][1:5, ]
write.csv(top, file.path(out, "maihda_m2_top5_v1_20261009.csv"), row.names = FALSE)

res <- data.frame(
  item = c(4, 6, 7, 9, 10),
  valor_recalculado = c(
    sprintf("%.2f (%.2f-%.2f)", it4[1], it4[2], it4[3]),
    sprintf("%.2f (%.2f-%.2f)", it6[1], it6[2], it6[3]),
    sprintf("%.2f (%.2f-%.2f)", it7[1], it7[2], it7[3]),
    sprintf("%.3f (%.3f-%.3f)", it9[1], it9[2], it9[3]),
    sprintf("%s: %.1f%%", it10$estrato, 100*it10$p)),
  bruto = c(
    paste(signif(it4[1:3], 8), collapse = ";"), paste(signif(it6[1:3], 8), collapse = ";"),
    paste(signif(it7[1:3], 8), collapse = ";"), paste(signif(it9[1:3], 8), collapse = ";"),
    signif(100*it10$p, 8)))
print(res)
write.csv(res, file.path(out, "recalculo_modelos_v1_20261009.csv"), row.names = FALSE)
