# Auditoria independente Etapa 6 - Tarefa C: logit multinomial (base = termo; 1 = espontaneo; 2 = indicado)
# Ajuste proprio por Newton-Raphson em celulas agregadas (R base) + checagem com nnet::multinom (pesos).
# EP sanduiche agrupado por regiao de saude (nulos -> cluster UF), correcao G/(G-1)*(N-1)/(N-K).
set.seed(42)
suppressMessages({library(data.table); library(nnet)})
OUT <- "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa6"
d0 <- fread(file.path(OUT, "cel_C_v1_20261008.csv"), colClasses = list(character = c("clus", "CO_REGSAUD")))
# soma de booleano nulo vira NA no DuckDB quando a celula nao tem nenhum ptb_tipo nao-nulo -> 0
d0[is.na(y1), y1 := 0L][is.na(y2), y2 := 0L]
stopifnot(all(d0$y0 + d0$y1 + d0$y2 == d0$n))

monta_X <- function(d, inter = FALSE) {
  r <- d$raca; t <- d$tercil_reg
  X <- cbind("(Intercept)" = 1, rPreta = r == "Preta", rParda = r == "Parda", rIndigena = r == "Indigena",
             "i<20" = d$idade_cat == "<20", "i>=35" = d$idade_cat == ">=35",
             sapply(2016:2024, function(a) d$ano == a),
             gN = d$regiao == "N", gNE = d$regiao == "NE", gS = d$regiao == "S", gCO = d$regiao == "CO")
  colnames(X)[7:15] <- paste0("a", 2016:2024)
  if (inter) {
    X <- cbind(X, tT1 = t == "T1", tT2 = t == "T2")
    for (rr in c("Preta", "Parda", "Indigena")) for (tt in c("T1", "T2")) {
      X <- cbind(X, (r == rr) & (t == tt)); colnames(X)[ncol(X)] <- paste0("r", rr, ":t", tt)
    }
  }
  storage.mode(X) <- "double"; X
}

ajusta <- function(d, X) {
  K <- ncol(X); Y <- cbind(d$y1, d$y2); n <- d$n
  th <- c(log(sum(d$y1) / sum(d$y0)), rep(0, K - 1), log(sum(d$y2) / sum(d$y0)), rep(0, K - 1))
  for (it in 1:50) {
    b1 <- th[1:K]; b2 <- th[K + 1:K]
    e1 <- exp(drop(X %*% b1)); e2 <- exp(drop(X %*% b2)); den <- 1 + e1 + e2
    p1 <- e1 / den; p2 <- e2 / den
    g <- c(colSums(X * (Y[, 1] - n * p1)), colSums(X * (Y[, 2] - n * p2)))
    H11 <- crossprod(X * (n * p1 * (1 - p1)), X); H22 <- crossprod(X * (n * p2 * (1 - p2)), X)
    H12 <- -crossprod(X * (n * p1 * p2), X)
    I <- rbind(cbind(H11, H12), cbind(t(H12), H22))
    step <- solve(I, g); th <- th + step
    if (max(abs(step)) < 1e-10) break
  }
  b1 <- th[1:K]; b2 <- th[K + 1:K]
  e1 <- exp(drop(X %*% b1)); e2 <- exp(drop(X %*% b2)); den <- 1 + e1 + e2
  p1 <- e1 / den; p2 <- e2 / den
  H11 <- crossprod(X * (n * p1 * (1 - p1)), X); H22 <- crossprod(X * (n * p2 * (1 - p2)), X)
  H12 <- -crossprod(X * (n * p1 * p2), X)
  Bread <- solve(rbind(cbind(H11, H12), cbind(t(H12), H22)))
  S <- cbind(X * (Y[, 1] - n * p1), X * (Y[, 2] - n * p2))
  U <- rowsum(S, d$clus); G <- nrow(U); N <- sum(n); P <- 2 * K
  cc <- G / (G - 1) * (N - 1) / (N - P)
  V <- cc * Bread %*% crossprod(U) %*% Bread
  nm <- c(paste0("esp:", colnames(X)), paste0("ind:", colnames(X)))
  names(th) <- nm; dimnames(V) <- list(nm, nm)
  cat(sprintf("iter=%d N=%d G=%d P=%d max|score|=%.2e cc=%.6f\n", it, N, G, P, max(abs(colSums(S))), cc))
  list(th = th, V = V, N = N, G = G, Vmodel = Bread)
}
rrr <- function(f, nm, a = NULL) { # exp(sum de coeficientes) com IC delta (na escala log)
  gv <- setNames(rep(0, length(f$th)), names(f$th)); gv[nm] <- 1
  est <- sum(f$th[nm]); se <- sqrt(drop(t(gv) %*% f$V %*% gv))
  data.frame(RRR = exp(est), lo = exp(est - 1.959964 * se), hi = exp(est + 1.959964 * se), se_log = se)
}

out <- list()
## Modelo 1: amostra completa (sem sem_classif)
X1 <- monta_X(d0); f1 <- ajusta(d0, X1)
for (cat_ in c("esp", "ind")) for (g in c("Preta", "Parda", "Indigena"))
  out[[length(out) + 1]] <- cbind(modelo = "C1_sem_tercil", categoria = cat_, raca = g, nivel = "todos", N = f1$N, G = f1$G,
                                 rrr(f1, paste0(cat_, ":r", g)))
## checagem nnet::multinom (pontos) - formato longo ponderado
lg <- rbind(cbind(d0, cat = "0", w = d0$y0), cbind(d0, cat = "1", w = d0$y1), cbind(d0, cat = "2", w = d0$y2))[w > 0]
lg[, `:=`(raca = relevel(factor(raca), "Branca"), idade_cat = relevel(factor(idade_cat), "20-34"),
          regiao = relevel(factor(regiao), "SE"), anof = factor(ano), cat = factor(cat))]
mm <- multinom(cat ~ raca + idade_cat + anof + regiao, data = lg, weights = w, maxit = 500, reltol = 1e-12, trace = FALSE)
cf <- coef(mm)
cat("nnet check RRR Indigena esp/ind:", exp(cf["1", "racaIndigena"]), exp(cf["2", "racaIndigena"]),
    " | proprio:", exp(f1$th["esp:rIndigena"]), exp(f1$th["ind:rIndigena"]), "\n")

## Modelo 2: amostra com CO_REGSAUD, + tercil + raca x tercil
d2 <- d0[!is.na(CO_REGSAUD) & CO_REGSAUD != ""]
X2 <- monta_X(d2, inter = TRUE); f2 <- ajusta(d2, X2)
for (cat_ in c("esp", "ind")) for (g in c("Preta", "Parda", "Indigena")) for (t in c("T1", "T2", "T3")) {
  nm <- paste0(cat_, ":r", g); if (t != "T3") nm <- c(nm, paste0(cat_, ":r", g, ":t", t))
  out[[length(out) + 1]] <- cbind(modelo = "C2_raca_x_tercil", categoria = cat_, raca = g, nivel = t, N = f2$N, G = f2$G, rrr(f2, nm))
}
res <- rbindlist(out)
res[, categoria := fifelse(categoria == "esp", "espontaneo", "indicado")]
fwrite(res, file.path(OUT, "c_rrr_v1_20261008.csv"))
fwrite(data.frame(termo = names(f1$th), beta = f1$th, se = sqrt(diag(f1$V))), file.path(OUT, "c_coef_m1_v1_20261008.csv"))
fwrite(data.frame(termo = names(f2$th), beta = f2$th, se = sqrt(diag(f2$V))), file.path(OUT, "c_coef_m2_v1_20261008.csv"))
print(res[raca == "Indigena", .(modelo, categoria, nivel, N, G, RRR = round(RRR, 3), lo = round(lo, 3), hi = round(hi, 3))])
print(res[raca != "Indigena", .(modelo, categoria, raca, nivel, RRR = round(RRR, 3), lo = round(lo, 3), hi = round(hi, 3))])
