# Auditoria independente etapa 4b - R (glm Poisson; sandwich). Sem statsmodels/gigs.
# A: IC Wilson; B: ICR Indígena x T1 (modelo 3.2) para PTB espontâneo plausível (b); C: RP M5 Centro-Oeste por ig_metodo.
suppressMessages({library(arrow); library(sandwich)})
OUT <- "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa4b"
rg <- c("Branca", "Preta", "Parda", "Indigena")

## A ---------------------------------------------------------------
a <- read.csv(file.path(OUT, "A_contagens_critb_v1_20261008.csv"))
wil <- function(x, n, z = qnorm(0.975)) {
  p <- x / n; den <- 1 + z^2 / n; ctr <- (p + z^2 / (2 * n)) / den
  h <- z * sqrt(p * (1 - p) / n + z^2 / (4 * n^2)) / den; cbind(ctr - h, ctr + h)
}
for (s in c("tab", "eq")) {
  x <- a[[paste0("n_b_", s)]]; w <- wil(x, a$n_eleg)
  a[[paste0("pct_", s)]] <- round(100 * x / a$n_eleg, 4)
  a[[paste0("LI_", s)]] <- round(100 * w[, 1], 4); a[[paste0("LS_", s)]] <- round(100 * w[, 2], 4)
}
chk <- prop.test(a$n_b_tab[1], a$n_eleg[1], correct = FALSE)$conf.int
stopifnot(abs(100 * chk[1] - a$LI_tab[1]) < 1e-4)
a <- a[order(match(a$raca_nome, rg), match(a$igm, c("DUM", "outro", "ign", "TOTAL"))), ]
write.csv(a, file.path(OUT, "A_pct_critb_raca_igmetodo_v1_20261008.csv"), row.names = FALSE)
cat("== A ==\n"); print(a[, c("raca_nome", "igm", "n_eleg", "n_b_tab", "pct_tab", "LI_tab", "LS_tab", "pct_eq", "so_equacao")], row.names = FALSE)

## B ---------------------------------------------------------------
fac <- function(d) {
  d$raca <- factor(d$raca, levels = c(1, 2, 4, 5), labels = rg)
  d$ida <- factor(d$ida, levels = c("20_34", "lt20", "ge35")); d$ano <- factor(d$ano, levels = 2015:2024)
  d$mr <- factor(d$mr, levels = c(3, 1, 2, 4, 5)); d$terc <- factor(d$terc, levels = c(3, 1, 2)); d
}
icr_fit <- function(d, y, rotulo) {
  d$yy <- d[[y]]; d$dd <- d$n_esp
  fit <- glm(yy ~ raca + ida + ano + mr + terc + raca:terc + offset(log(dd)), family = poisson(), data = d,
             control = glm.control(epsilon = 1e-12, maxit = 100))
  stopifnot(fit$converged); b <- coef(fit); k <- length(b); N <- sum(d$dd); G <- length(unique(d$mun))
  V <- vcovCL(fit, cluster = ~mun, type = "HC0", cadjust = TRUE) * (N - 1) / (N - k)   # = HC1 individual por cluster
  ag <- aggregate(dd ~ raca + ida + ano + mr + terc, data = d, FUN = sum)
  Pf <- function(g, m) {
    nd <- ag; nd$raca <- factor(g, levels = rg); nd$terc <- factor(m, levels = c(3, 1, 2))
    X <- model.matrix(~ raca + ida + ano + mr + terc + raca:terc, nd); stopifnot(identical(colnames(X), names(b)))
    r <- exp(drop(X %*% b)); c(sum(nd$dd * r) / sum(nd$dd), colSums(X * nd$dd * r) / sum(nd$dd))
  }
  out <- list()
  for (g in rg[-1]) {
    v <- (Pf(g, "1") - Pf("Branca", "1")) - (Pf(g, "3") - Pf("Branca", "3"))
    se <- sqrt(drop(t(v[-1]) %*% V %*% v[-1]))
    out[[g]] <- data.frame(desfecho = rotulo, grupo = g, N = N, G = G, k = k, casos = sum(d$yy),
                           ICR_pp = 100 * v[1], LI = 100 * (v[1] - 1.96 * se), LS = 100 * (v[1] + 1.96 * se), EP_pp = 100 * se)
  }
  do.call(rbind, out)
}
cel <- fac(as.data.frame(read_parquet(file.path(OUT, "B_cel_v1_20261008.parquet"))))
cel <- aggregate(cbind(n_esp, y_esp, y_esp_b_tab, y_esp_b_eq) ~ raca + ida + ano + mr + terc + mun, data = cel, FUN = sum)
resB <- rbind(icr_fit(cel, "y_esp", "ptb_esp (checagem; etapa3 = 2,022854)"),
              icr_fit(cel, "y_esp_b_tab", "ptb_esp plausível (b) - P97 tabela oficial"),
              icr_fit(cel, "y_esp_b_eq", "ptb_esp plausível (b) - P97 equação growthstandards"))
write.csv(resB, file.path(OUT, "B_icr_ptb_esp_plausivel_b_v1_20261008.csv"), row.names = FALSE)
cat("== B ==\n"); print(format(resB, digits = 7), row.names = FALSE)

## C ---------------------------------------------------------------
cc <- as.data.frame(read_parquet(file.path(OUT, "C_cel_co_v1_20261008.parquet")))
resC <- list()
for (m in c("DUM", "outro", "ign", "TODOS")) {
  s <- if (m == "TODOS") cc else cc[cc$igm == m, ]
  s <- aggregate(cbind(n, y) ~ raca + ida + esc + ano + uf + mun, data = s, FUN = sum)
  # expansão individual (necessária para HC0 individual): uma linha por nascimento, y 0/1
  i <- rep(seq_len(nrow(s)), s$n); yi <- unlist(mapply(function(n, y) c(rep(1L, y), rep(0L, n - y)), s$n, s$y), use.names = FALSE)
  ind <- s[i, c("raca", "ida", "esc", "ano", "uf", "mun")]; ind$y <- yi
  ind$raca <- factor(ind$raca, levels = c(1, 2, 4, 5), labels = rg); ind$ida <- factor(ind$ida, levels = c("20_34", "lt20", "ge35"))
  ind$esc <- factor(ind$esc, levels = 1:5); ind$ano <- factor(ind$ano, levels = 2015:2024); ind$uf <- factor(ind$uf)
  fit <- glm(y ~ raca + ida + esc + ano + uf, family = poisson(), data = ind, control = glm.control(epsilon = 1e-12, maxit = 100))
  stopifnot(fit$converged, !anyNA(coef(fit)))
  b <- coef(fit)["racaIndigena"]
  se0 <- sqrt(vcovHC(fit, type = "HC0")["racaIndigena", "racaIndigena"])
  se1 <- sqrt(vcovCL(fit, cluster = ~mun, type = "HC1", cadjust = TRUE)["racaIndigena", "racaIndigena"])
  resC[[m]] <- data.frame(ig_metodo = m, N = nrow(ind), casos = sum(ind$y), n_indigena = sum(ind$raca == "Indigena"),
                          casos_indigena = sum(ind$y[ind$raca == "Indigena"]), G = length(unique(ind$mun)), k = length(coef(fit)),
                          RP = exp(b), LI_HC0 = exp(b - 1.96 * se0), LS_HC0 = exp(b + 1.96 * se0),
                          LI_cl = exp(b - 1.96 * se1), LS_cl = exp(b + 1.96 * se1), EP_HC0 = se0, EP_cl = se1)
  cat(m, "ok\n"); rm(ind, fit); gc()
}
resC <- do.call(rbind, resC)
write.csv(resC, file.path(OUT, "C_rp_m5_co_indigena_por_igmetodo_v1_20261008.csv"), row.names = FALSE)
cat("== C ==\n"); print(format(resC, digits = 6), row.names = FALSE)
