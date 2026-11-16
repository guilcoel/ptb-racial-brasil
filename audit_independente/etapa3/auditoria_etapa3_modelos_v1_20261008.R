# Auditoria independente etapa 3 - modelos em R (glm Poisson; sandwich por cluster montado à mão)
suppressMessages(library(arrow))
OUT <- "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa3"
args <- commandArgs(TRUE); parte <- if (length(args)) args[1] else "BC"

fac <- function(d) {
  d$raca <- factor(d$raca, levels = c(1, 2, 4, 5), labels = c("Branca", "Preta", "Parda", "Indigena"))
  d$ida  <- factor(d$ida, levels = c("20_34", "lt20", "ge35"))
  d$ano  <- factor(d$ano, levels = 2015:2024)
  d$mr   <- factor(d$mr, levels = c(3, 1, 2, 4, 5))
  d
}

if (grepl("B", parte)) {
  d <- as.data.frame(read_parquet(file.path(OUT, "cel_interacao_v1_20261008.parquet")))
  d <- fac(d); d$terc <- factor(d$terc, levels = c(3, 1, 2))
  d <- d[d$n_esp > 0, ]
  fit <- glm(y_esp ~ raca + ida + ano + mr + terc + raca:terc + offset(log(n_esp)),
             family = poisson(), data = d, control = glm.control(epsilon = 1e-12, maxit = 100))
  X <- model.matrix(fit); b <- coef(fit); k <- length(b)
  mu <- fitted(fit)                      # = n_esp * taxa
  N <- sum(d$n_esp); cl <- d$mun; G <- length(unique(cl))
  Bread <- solve(crossprod(X * sqrt(mu)))
  S <- rowsum(X * (d$y_esp - mu), cl)
  V <- Bread %*% crossprod(S) %*% Bread * G / (G - 1) * (N - 1) / (N - k)
  cat("N =", N, " G =", G, " k =", k, " celulas =", nrow(d), "\n")

  # RP conjuntas vs Branca-T3
  rg <- c("Branca", "Preta", "Parda", "Indigena"); tm <- c("1", "2", "3")
  L <- function(g, m) {
    l <- setNames(rep(0, k), names(b))
    if (g != "Branca") l[paste0("raca", g)] <- 1
    if (m != "3") l[paste0("terc", m)] <- 1
    if (g != "Branca" && m != "3") l[paste0("raca", g, ":terc", m)] <- 1
    l
  }
  rp <- do.call(rbind, lapply(rg, function(g) do.call(rbind, lapply(tm, function(m) {
    l <- L(g, m); e <- sum(l * b); se <- sqrt(drop(t(l) %*% V %*% l))
    data.frame(raca = g, tercil = paste0("T", m), RP = exp(e), LI = exp(e - 1.96 * se), LS = exp(e + 1.96 * se))
  }))))

  # Probabilidades padronizadas: colapsa células sobre município (mesmo n_esp e covariáveis)
  ag <- aggregate(n_esp ~ raca + ida + ano + mr + terc, data = d, FUN = sum)
  Pfun <- function(g, m) {
    nd <- ag; nd$raca <- factor(g, levels = levels(d$raca)); nd$terc <- factor(m, levels = levels(d$terc))
    Xc <- model.matrix(~ raca + ida + ano + mr + terc + raca:terc, nd)
    stopifnot(identical(colnames(Xc), names(b)))
    r <- exp(drop(Xc %*% b))
    list(P = sum(nd$n_esp * r) / sum(nd$n_esp), grad = colSums(Xc * (nd$n_esp * r)) / sum(nd$n_esp))
  }
  PP <- list(); for (g in rg) for (m in tm) PP[[paste(g, m)]] <- Pfun(g, m)
  rp$P_pct <- sapply(seq_len(nrow(rp)), function(i) 100 * PP[[paste(rp$raca[i], sub("T", "", rp$tercil[i]))]]$P)
  write.csv(rp, file.path(OUT, "B_rp_conjuntas_prob_ptb_esp_v1_20261008.csv"), row.names = FALSE)
  print(format(rp, digits = 6))

  icr <- do.call(rbind, lapply(c("Indigena", "Preta", "Parda"), function(g) {
    est <- (PP[[paste(g, 1)]]$P - PP[[paste("Branca", 1)]]$P) - (PP[[paste(g, 3)]]$P - PP[[paste("Branca", 3)]]$P)
    gr <- (PP[[paste(g, 1)]]$grad - PP[[paste("Branca", 1)]]$grad) - (PP[[paste(g, 3)]]$grad - PP[[paste("Branca", 3)]]$grad)
    se <- sqrt(drop(t(gr) %*% V %*% gr))
    data.frame(raca = g, ICR_pp = 100 * est, LI = 100 * (est - 1.96 * se), LS = 100 * (est + 1.96 * se), EP_pp = 100 * se)
  }))
  write.csv(icr, file.path(OUT, "C_icr_ptb_esp_v1_20261008.csv"), row.names = FALSE)
  print(format(icr, digits = 6))
}

if (grepl("D", parte)) {
  d <- as.data.frame(read_parquet(file.path(OUT, "cel_boot_v1_20261008.parquet")))
  d <- fac(d)
  d$esc <- factor(d$esc, levels = c(5, 1, 2, 3, 4)); d$semcomp <- factor(d$semcomp, levels = c(0, 1))
  kk <- read.csv(file.path(OUT, "boot_contagens_r1a20_v1_20261008.csv"), colClasses = c("integer", "character", "integer"))
  X2 <- model.matrix(~ raca + ida + ano + mr, d)
  X3 <- model.matrix(~ raca + ida + ano + mr + esc + semcomp, d)
  res <- list()
  for (r in 1:20) {
    kr <- kk[kk$replica == r, ]
    w <- kr$k[match(d$mun, kr$mun)]; w[is.na(w)] <- 0
    s <- w > 0
    y <- d$y[s] * w[s]; off <- log(d$n[s] * w[s])
    f2 <- glm.fit(X2[s, ], y, offset = off, family = poisson(), control = glm.control(epsilon = 1e-12, maxit = 100))
    f3 <- glm.fit(X3[s, ], y, offset = off, family = poisson(), control = glm.control(epsilon = 1e-12, maxit = 100))
    for (g in c("Parda", "Preta", "Indigena"))
      res[[length(res) + 1]] <- data.frame(replica = r, raca = g,
        RP_M2cc = sprintf("%.6f", exp(f2$coefficients[paste0("raca", g)])),
        RP_M3 = sprintf("%.6f", exp(f3$coefficients[paste0("raca", g)])))
    cat("replica", r, "conv", f2$converged, f3$converged, "\n")
  }
  res <- do.call(rbind, res)
  write.csv(res, file.path(OUT, "D_bootstrap_r1a20_v1_20261008.csv"), row.names = FALSE, quote = FALSE)
  print(res)
}
