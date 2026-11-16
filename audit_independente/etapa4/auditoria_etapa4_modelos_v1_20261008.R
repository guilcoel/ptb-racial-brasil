# Auditoria independente etapa 4 - modelos em R (glm Poisson; sandwich por cluster montado à mão; nnet::multinom)
# Uso: Rscript auditoria_etapa4_modelos_v1_20261008.R A   |   ... B
suppressMessages({library(arrow); library(nnet)})
OUT <- "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa4"
args <- commandArgs(TRUE); parte <- if (length(args)) args[1] else "A"
rg <- c("Branca", "Preta", "Parda", "Indigena")

fac <- function(d) {
  d$raca <- factor(d$raca, levels = c(1, 2, 4, 5), labels = rg)
  d$ida  <- factor(d$ida, levels = c("20_34", "lt20", "ge35"))
  d$ano  <- factor(d$ano, levels = 2015:2024)
  d$mr   <- factor(d$mr, levels = c(3, 1, 2, 4, 5))
  d$terc <- factor(d$terc, levels = c(3, 1, 2))
  d
}

# Ajusta Poisson y ~ raça*tercil + idade + ano + macro com offset log(den); EP cluster CODMUNRES
# (HC0 por cluster x G/(G-1) x (N-1)/(N-k)); ICR(g,T1) padronizado sobre todas as células, IC delta.
icr_fit <- function(d, y, den, rotulo) {
  d <- d[d[[den]] > 0, ]
  d$yy <- d[[y]]; d$dd <- d[[den]]
  fit <- glm(yy ~ raca + ida + ano + mr + terc + raca:terc + offset(log(dd)), family = poisson(),
             data = d, control = glm.control(epsilon = 1e-12, maxit = 100))
  X <- model.matrix(fit); b <- coef(fit); k <- length(b)
  stopifnot(!any(is.na(b)), fit$converged)
  mu <- fitted(fit); N <- sum(d$dd); cl <- d$mun; G <- length(unique(cl))
  Bread <- solve(crossprod(X * sqrt(mu)))
  S <- rowsum(X * (d$yy - mu), cl)
  V <- Bread %*% crossprod(S) %*% Bread * G / (G - 1) * (N - 1) / (N - k)
  ag <- aggregate(dd ~ raca + ida + ano + mr + terc, data = d, FUN = sum)
  Pfun <- function(g, m) {
    nd <- ag; nd$raca <- factor(g, levels = levels(d$raca)); nd$terc <- factor(m, levels = levels(d$terc))
    Xc <- model.matrix(~ raca + ida + ano + mr + terc + raca:terc, nd)
    stopifnot(identical(colnames(Xc), names(b)))
    r <- exp(drop(Xc %*% b))
    list(P = sum(nd$dd * r) / sum(nd$dd), grad = colSums(Xc * (nd$dd * r)) / sum(nd$dd))
  }
  g <- "Indigena"
  P <- list(g1 = Pfun(g, "1"), b1 = Pfun("Branca", "1"), g3 = Pfun(g, "3"), b3 = Pfun("Branca", "3"))
  est <- (P$g1$P - P$b1$P) - (P$g3$P - P$b3$P)
  gr <- (P$g1$grad - P$b1$grad) - (P$g3$grad - P$b3$grad)
  se <- sqrt(drop(t(gr) %*% V %*% gr))
  data.frame(modelo = rotulo, N = N, G = G, k = k, celulas = nrow(d), y = sum(d$yy),
             n_indigena = sum(d$dd[d$raca == "Indigena"]),
             ICR_pp = 100 * est, LI = 100 * (est - 1.96 * se), LS = 100 * (est + 1.96 * se), EP_pp = 100 * se)
}

cel <- fac(as.data.frame(read_parquet(file.path(OUT, "cel_A_v1_20261008.parquet"))))
colap <- function(d) aggregate(cbind(n_esp, y_esp, n_pig, y_pig) ~ raca + ida + ano + mr + terc + mun, data = d, FUN = sum)

if (grepl("A", parte)) {
  res <- list()
  tot <- colap(cel)
  res[[1]] <- icr_fit(tot, "y_esp", "n_esp", "ptb_esp | amostra completa (checagem etapa3)")
  res[[2]] <- icr_fit(tot, "y_pig", "n_pig", "pig | amostra completa")
  for (m in c("outro", "DUM")) {
    s <- colap(cel[cel$igm == m, ])
    res[[length(res) + 1]] <- icr_fit(s, "y_pig", "n_pig", paste0("pig | ig_metodo=", m))
    res[[length(res) + 1]] <- icr_fit(s, "y_esp", "n_esp", paste0("ptb_esp | ig_metodo=", m))
  }
  res <- do.call(rbind, res)
  write.csv(res, file.path(OUT, "A_icr_indigena_T1_por_igmetodo_v1_20261008.csv"), row.names = FALSE)
  print(format(res, digits = 7), right = FALSE)
}

if (grepl("B", parte)) {
  SEED <- 20261008; set.seed(SEED); M <- 10
  tr <- as.data.frame(read_parquet(file.path(OUT, "B_treino_padroes_v1_20261008.parquet")))
  fa <- as.data.frame(read_parquet(file.path(OUT, "B_faltantes_modelo_v1_20261008.parquet")))
  key <- c("mr", "ano", "ida", "esc", "conj", "ptbt", "pigc", "tercc", "faixa")
  # largo: uma linha por padrão, colunas = contagens por raça 1..5
  tr$pid <- do.call(paste, c(tr[key], sep = "|"))
  pats <- tr[!duplicated(tr$pid), key]; pats$pid <- tr$pid[!duplicated(tr$pid)]
  Y <- matrix(0, nrow(pats), 5, dimnames = list(NULL, paste0("r", 1:5)))
  Y[cbind(match(tr$pid, pats$pid), tr$raca)] <- tr$n
  # mr x faixa: interação saturada codificada como um fator único (mesmo espaço de mr + faixa + mr:faixa, sem células vazias)
  prep <- function(p) {
    p$mr <- factor(p$mr, levels = c(3, 1, 2, 4, 5)); p$ano <- factor(p$ano, levels = 2015:2024)
    p$ida <- factor(p$ida, levels = c("20_34", "lt20", "ge35")); p$esc <- factor(p$esc, levels = 1:5)
    p$conj <- factor(p$conj, levels = c("com", "sem", "aus"))
    p$ptbt <- factor(p$ptbt, levels = c("termo", "esp", "ind", "semclass"))
    p$pigc <- factor(p$pigc, levels = c("0", "1", "ne")); p$tercc <- factor(p$tercc, levels = c("T3", "T1", "T2", "sem"))
    p$mrfx <- factor(paste(p$mr, p$faixa), levels = lv_mrfx)
    p
  }
  lv_mrfx <- sort(unique(paste(pats$mr, pats$faixa)))
  pats <- prep(pats); fa <- prep(fa)
  stopifnot(!anyNA(fa$mrfx))
  fml <- Y ~ ano + ida + esc + conj + ptbt * tercc + pigc * tercc + mrfx
  cat("padrões de treino:", nrow(pats), " registros:", sum(Y), "\n")

  fa$mun <- as.character(fa$mun)
  obs <- colap(cel)
  N_obs_pig <- sum(obs$n_pig)
  base <- icr_fit(obs, "y_pig", "n_pig", "pig | casos completos")
  res <- list(); wts <- NULL; amarela <- numeric(M); conv <- logical(M)
  rbinom_cascata <- function(n, P) {  # sorteio multinomial vetorizado por linha (binomiais condicionais)
    out <- matrix(0L, length(n), ncol(P)); rest <- n; prest <- rep(1, length(n))
    for (j in seq_len(ncol(P) - 1)) {
      pj <- pmin(1, pmax(0, P[, j] / prest)); pj[prest <= 0] <- 0
      out[, j] <- rbinom(length(n), rest, pj); rest <- rest - out[, j]; prest <- prest - P[, j]
    }
    out[, ncol(P)] <- rest; out
  }
  for (m in seq_len(M)) {
    pats$Ys <- matrix(rpois(length(Y), Y), nrow(Y), dimnames = dimnames(Y))   # bootstrap Poisson(n)
    fml_m <- Ys ~ ano + ida + esc + conj + ptbt * tercc + pigc * tercc + mrfx
    dsub <- pats[rowSums(pats$Ys) > 0, ]
    fit <- if (is.null(wts)) multinom(fml_m, data = dsub, maxit = 3000, MaxNWts = 5000, trace = FALSE, reltol = 1e-12, abstol = 1e-6)
           else multinom(fml_m, data = dsub, maxit = 3000, MaxNWts = 5000, trace = FALSE, reltol = 1e-12, abstol = 1e-6, Wts = wts)
    wts <- fit$wts; conv[m] <- fit$convergence == 0
    P <- predict(fit, newdata = fa, type = "probs")
    stopifnot(ncol(P) == 5, !anyNA(P))
    D <- rbinom_cascata(fa$n, P)
    amarela[m] <- sum(D[, 3])
    imp <- do.call(rbind, lapply(c(1, 2, 4, 5), function(r) {
      x <- fa[D[, r] > 0, c("ida", "ano", "mr", "terc", "mun", "pigc")]; nn <- D[D[, r] > 0, r]
      data.frame(raca = r, ida = as.character(x$ida), ano = as.integer(as.character(x$ano)),
                 mr = as.integer(as.character(x$mr)), terc = x$terc, mun = x$mun,
                 n_esp = 0, y_esp = 0, n_pig = nn, y_pig = ifelse(x$pigc == "1", nn, 0))
    }))
    imp <- fac(imp)
    dm <- colap(rbind(obs, imp))
    r <- icr_fit(dm, "y_pig", "n_pig", paste0("pig | imputação ", m))
    r$n_imputados_modelo <- sum(imp$n_pig); r$amarela_imputada <- amarela[m]
    r$imp_indigena <- sum(imp$n_pig[imp$raca == "Indigena"]); r$multinom_conv <- conv[m]; r$deviance <- fit$deviance
    res[[m]] <- r
    cat("m =", m, " conv =", conv[m], " ICR =", r$ICR_pp, " EP =", r$EP_pp, " ind imp =", r$imp_indigena, "\n")
  }
  res <- do.call(rbind, res)
  write.csv(res, file.path(OUT, "B_imputacoes_m1a10_v1_20261008.csv"), row.names = FALSE)
  # Rubin
  Q <- res$ICR_pp; U <- res$EP_pp^2
  Qb <- mean(Q); W <- mean(U); B <- var(Q); Tt <- W + (1 + 1 / M) * B
  rr <- (1 + 1 / M) * B / W; df <- (M - 1) * (1 + 1 / rr)^2
  lambda <- (1 + 1 / M) * B / Tt; fmi <- (rr + 2 / (df + 3)) / (rr + 1)
  tq <- qt(0.975, df)
  rub <- data.frame(seed = SEED, M = M, ICR_pp = Qb, EP_pp = sqrt(Tt), LI = Qb - tq * sqrt(Tt), LS = Qb + tq * sqrt(Tt),
                    LI_z = Qb - 1.96 * sqrt(Tt), LS_z = Qb + 1.96 * sqrt(Tt),
                    W_pp2 = W, B_pp2 = B, T_pp2 = Tt, r = rr, df_Rubin = df, lambda = lambda, FMI = fmi,
                    ICR_cc = base$ICR_pp, LI_cc = base$LI, LS_cc = base$LS, N_cc = base$N)
  write.csv(rub, file.path(OUT, "B_rubin_icr_indigena_T1_pig_v1_20261008.csv"), row.names = FALSE)
  print(format(res, digits = 6)); print(t(rub))
}
