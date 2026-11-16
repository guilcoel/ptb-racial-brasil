# Bloco C (parte 2) — os modelos refeitos em R, por caminho independente do projeto:
#   células agregadas por DuckDB (R) direto do parquet v3 (incl = true, com região de saúde), tercis do auditor (c1),
#   glm Poisson com offset log(n), covariância agrupada por região de saúde com sandwich::vcovCL (HC0, ajuste G/(G−1)) vezes
#   (N−1)/(N−K) com N = nascimentos (correção documentada do projeto, adotada como definição do estimador; ver relatório),
#   padronização total (Knol & VanderWeele) e delta-método próprios. Saída: estimativas agregadas (sem contagens de células).
suppressMessages({library(duckdb); library(sandwich)})
AUD <- "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa8"
V3 <- "/Volumes/Forja/ptb-racial-brasil/data/processed/sinasc_brasil_2015_2024_v3_20261008"
con <- dbConnect(duckdb())
dbExecute(con, sprintf("SET temp_directory='%s/duck_tmp_v1_20261013'", AUD))
ter <- read.csv(file.path(AUD, "terc_auditor_v1_20261013.csv"), colClasses = c(CO_REGSAUD = "character"))
treg <- read.csv(file.path(AUD, "tercreg_auditor_v1_20261013.csv"), colClasses = c(CO_REGSAUD = "character"))
duckdb_register(con, "ter", ter); duckdb_register(con, "treg", treg)
RACAS <- c("Branca", "Parda", "Preta", "Indigena"); NIV <- c("T1", "T2", "T3")
Z <- qnorm(0.975)

celulas <- function(desf, mod, anos) {
  tb <- if (mod == "tercil_reg") "treg" else "ter"
  q <- sprintf("SELECT CAST(d.raca AS VARCHAR) raca, CAST(d.idade_cat AS VARCHAR) idade_cat, CAST(d.ano AS INT) ano, d.regiao, t.%s terc,
      d.CO_REGSAUD, sum(d.%s)::DOUBLE Y, count(*)::DOUBLE n
    FROM read_parquet('%s/*/*.parquet', hive_partitioning = true) d JOIN %s t ON d.CO_REGSAUD = t.CO_REGSAUD AND CAST(d.ano AS INT) = t.ano
    WHERE d.incl AND d.CO_REGSAUD IS NOT NULL AND d.%s IS NOT NULL AND CAST(d.ano AS INT) BETWEEN %d AND %d GROUP BY ALL",
    mod, desf, V3, tb, desf, anos[1], anos[2])
  c <- dbGetQuery(con, q)
  c$raca <- factor(c$raca, levels = RACAS)
  stopifnot(!anyNA(c$raca))
  c$idade_cat <- relevel(factor(c$idade_cat), ref = "20-34")
  c$ano <- factor(c$ano); c$regiao <- relevel(factor(c$regiao), ref = "SE")
  c$terc <- factor(c$terc, levels = c("T3", "T1", "T2"))
  c
}

ajusta <- function(desf, mod, anos) {
  c <- celulas(desf, mod, anos)
  f <- glm(Y ~ raca + idade_cat + ano + regiao + terc + raca:terc + offset(log(n)), family = poisson(), data = c,
           control = glm.control(epsilon = 1e-12, maxit = 100))
  N <- sum(c$n); K <- length(coef(f)); G <- length(unique(c$CO_REGSAUD))
  V <- vcovCL(f, cluster = c$CO_REGSAUD, type = "HC0", cadjust = TRUE) * (N - 1) / (N - K)
  b <- coef(f)
  tt <- delete.response(terms(f))
  P <- list(); Gd <- list()
  for (g in RACAS) for (m in NIV) {
    nd <- c; nd$raca <- factor(g, levels = RACAS); nd$terc <- factor(m, levels = c("T3", "T1", "T2"))
    X <- model.matrix(tt, model.frame(tt, nd, xlev = f$xlevels))
    mu <- as.vector(exp(X %*% b))
    P[[paste(g, m)]] <- sum(c$n * mu) / N
    Gd[[paste(g, m)]] <- colSums(X * (c$n * mu)) / N
  }
  out <- list()
  for (g in RACAS[-1]) for (m in c("T1", "T2")) {
    v <- (P[[paste(g, m)]] - P[[paste("Branca", m)]]) - (P[[paste(g, "T3")]] - P[[paste("Branca", "T3")]])
    gr <- (Gd[[paste(g, m)]] - Gd[[paste("Branca", m)]]) - (Gd[[paste(g, "T3")]] - Gd[[paste("Branca", "T3")]])
    se <- sqrt(as.numeric(t(gr) %*% V %*% gr))
    out[[length(out) + 1]] <- data.frame(raca = g, nivel = m, ICR_pp = 100 * v, ICR_lo = 100 * (v - Z * se), ICR_hi = 100 * (v + Z * se))
  }
  ix <- grep(":terc", names(b)); ii <- grep("^racaIndigena:terc", names(b))
  w6 <- as.numeric(t(b[ix]) %*% solve(V[ix, ix], b[ix])); w2 <- as.numeric(t(b[ii]) %*% solve(V[ii, ii], b[ii]))
  # sensibilidade do estimador: sem o fator (N−1)/(N−K) e com HC1 do sandwich (n = células) — diferença esperada desprezível/pequena
  V0 <- V * (N - K) / (N - 1)
  w2_0 <- as.numeric(t(b[ii]) %*% solve(V0[ii, ii], b[ii]))
  res <- do.call(rbind, out)
  res$exposicao <- mod; res$desfecho <- desf; res$N <- N; res$G <- G; res$K <- K; res$n_cel <- nrow(c)
  res$chi2_6gl <- w6; res$p_6gl <- pchisq(w6, 6, lower.tail = FALSE); res$chi2_ind_2gl <- w2; res$p_ind_2gl <- pchisq(w2, 2, lower.tail = FALSE)
  res$chi2_ind_2gl_semfator <- w2_0; res$conv <- f$converged; res$gl_ix <- length(ix)
  res
}

R <- list()
for (mod in c("tercil_aps", "tercil_ind21")) for (desf in c("ptb", "pig", "ptb_ind")) {
  cat(mod, desf, "\n"); R[[length(R) + 1]] <- ajusta(desf, mod, c(2015, 2021))
}
for (desf in c("ptb", "pig", "ptb_ind")) { cat("principal", desf, "\n"); R[[length(R) + 1]] <- ajusta(desf, "tercil_reg", c(2015, 2024)) }
R <- do.call(rbind, R)
write.csv(R, file.path(AUD, "modelos_auditor_v1_20261013.csv"), row.names = FALSE)
print(R[R$raca == "Indigena" & R$nivel == "T1", c("exposicao", "desfecho", "ICR_pp", "ICR_lo", "ICR_hi", "p_ind_2gl", "p_6gl", "N", "G")])
dbDisconnect(con, shutdown = TRUE)
