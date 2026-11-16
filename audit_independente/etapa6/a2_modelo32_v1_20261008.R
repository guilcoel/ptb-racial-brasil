# Auditoria independente Etapa 6 - Tarefa A: modelo 3.2 (Poisson log, celulas agregadas)
# EP sanduiche agrupado por CO_REGSAUD com correcao G/(G-1)*(N-1)/(N-K); ICR por padronizacao + delta.
set.seed(42)
suppressMessages(library(data.table))
OUT <- "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa6"

monta_X <- function(d, raca = NULL, terc = NULL) {
  r <- if (is.null(raca)) d$raca else rep(raca, nrow(d))
  t <- if (is.null(terc)) d$tercil_reg else rep(terc, nrow(d))
  X <- cbind(
    "(Intercept)" = 1,
    rPreta = r == "Preta", rParda = r == "Parda", rIndigena = r == "Indigena",
    "i<20" = d$idade_cat == "<20", "i>=35" = d$idade_cat == ">=35",
    sapply(2016:2024, function(a) d$ano == a),
    gN = d$regiao == "N", gNE = d$regiao == "NE", gS = d$regiao == "S", gCO = d$regiao == "CO",
    tT1 = t == "T1", tT2 = t == "T2")
  colnames(X)[7:15] <- paste0("a", 2016:2024)
  for (rr in c("Preta", "Parda", "Indigena")) for (tt in c("T1", "T2"))
    X <- cbind(X, setNames(data.frame((r == rr) & (t == tt)), paste0("r", rr, ":t", tt)))
  X <- as.matrix(X); storage.mode(X) <- "double"; X
}

res_all <- list(); wald_all <- list()
for (dz in c("pig", "ptb_esp")) {
  d <- fread(file.path(OUT, sprintf("cel_A_%s_v1_20261008.csv", dz)), colClasses = list(character = "CO_REGSAUD"))
  X <- monta_X(d)
  fit <- glm.fit(X, d$y, offset = log(d$n), family = poisson())
  b <- fit$coefficients
  mu <- exp(drop(X %*% b))            # prob individual
  N <- sum(d$n); K <- ncol(X); G <- uniqueN(d$CO_REGSAUD)
  Bread <- solve(crossprod(X * sqrt(d$n * mu)))
  sc <- X * (d$y - d$n * mu)
  U <- rowsum(sc, d$CO_REGSAUD)
  cc <- G / (G - 1) * (N - 1) / (N - K)
  V <- cc * Bread %*% crossprod(U) %*% Bread
  cat(sprintf("\n== %s: N=%d casos=%d G=%d K=%d conv=%s iter=%d max|score|=%.2e\n",
              dz, N, sum(d$y), G, K, fit$converged, fit$iter, max(abs(colSums(sc)))))
  print(round(cbind(beta = b, se = sqrt(diag(V)), RR = exp(b)), 4))
  # probabilidades padronizadas
  P <- list(); gr <- list()
  for (g in c("Branca", "Preta", "Parda", "Indigena")) for (t in c("T1", "T2", "T3")) {
    Xg <- monta_X(d, g, t); m <- exp(drop(Xg %*% b))
    P[[paste(g, t)]] <- sum(d$n * m) / N
    gr[[paste(g, t)]] <- colSums(Xg * (d$n * m)) / N
  }
  for (g in c("Preta", "Parda", "Indigena")) for (t in c("T1", "T2")) {
    est <- 100 * ((P[[paste(g, t)]] - P[[paste("Branca", t)]]) - (P[[paste(g, "T3")]] - P[[paste("Branca", "T3")]]))
    gv <- 100 * ((gr[[paste(g, t)]] - gr[[paste("Branca", t)]]) - (gr[[paste(g, "T3")]] - gr[[paste("Branca", "T3")]]))
    se <- sqrt(drop(t(gv) %*% V %*% gv))
    res_all[[length(res_all) + 1]] <- data.frame(desfecho = dz, raca = g, nivel = t, N = N, casos = sum(d$y), G = G, K = K,
      P_g_t = 100 * P[[paste(g, t)]], P_B_t = 100 * P[[paste("Branca", t)]],
      P_g_T3 = 100 * P[[paste(g, "T3")]], P_B_T3 = 100 * P[[paste("Branca", "T3")]],
      ICR_pp = est, se = se, ICR_lo = est - 1.959964 * se, ICR_hi = est + 1.959964 * se)
  }
  # Wald conjunto das 6 interacoes
  ii <- grep(":t", names(b))
  W <- drop(t(b[ii]) %*% solve(V[ii, ii]) %*% b[ii])
  wald_all[[dz]] <- data.frame(desfecho = dz, N = N, G = G, K = K, wald_chi2 = W, df = length(ii), p = pchisq(W, length(ii), lower.tail = FALSE))
  pb <- data.frame(desfecho = dz, grupo = names(P), P_pct = 100 * unlist(P))
  fwrite(pb, file.path(OUT, sprintf("a_probpadr_%s_v1_20261008.csv", dz)))
  fwrite(data.frame(termo = names(b), beta = b, se = sqrt(diag(V))), file.path(OUT, sprintf("a_coef_%s_v1_20261008.csv", dz)))
}
res <- rbindlist(res_all); wd <- rbindlist(wald_all)
fwrite(res, file.path(OUT, "a_icr_v1_20261008.csv")); fwrite(wd, file.path(OUT, "a_wald_v1_20261008.csv"))
print(res[, .(desfecho, raca, nivel, ICR_pp = round(ICR_pp, 3), lo = round(ICR_lo, 3), hi = round(ICR_hi, 3))])
print(wd)
