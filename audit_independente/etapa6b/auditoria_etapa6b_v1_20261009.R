# Auditoria independente — Etapa 6b (ptb-racial-brasil)
# Auditor independente, 2026-10-09. Somente leitura dos dados; saídas só em audit_independente/etapa6b/.
# Poisson log em células agregadas (y = casos, offset log(n)) — equivalente exato ao ajuste individual;
# IC 95% com sanduíche agrupado (cluster = região de saúde do CSV; sem correspondência -> "UF_"+UF),
# correção G/(G-1)*(N-1)/(N-K) com N = nº de indivíduos.
set.seed(42)
suppressMessages({library(DBI); library(data.table)})
OUT <- "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa6b"
SCR <- Sys.getenv("SCR", tempdir())
cellf <- file.path(SCR, "cells_e6b.parquet")

if (!file.exists(cellf)) {
  con <- dbConnect(duckdb::duckdb())
  dbExecute(con, "SET threads=8")
  dbExecute(con, "create view b as select * from read_parquet('/Volumes/Forja/ptb-racial-brasil/data/processed/sinasc_brasil_2015_2024_v3_20261008/ano=*/part-0.parquet', hive_partitioning=true) where incl")
  dbExecute(con, "create table m as select * from read_csv('/Volumes/Forja/ptb-racial-brasil/data/processed/municipio_regsaude_dez24_v1_20261008.csv', all_varchar=true)")
  dbExecute(con, sprintf("copy (
    select b.raca, b.idade_cat, cast(b.ano as integer) ano, b.regiao, b.esc_cat, b.estciv_cat, b.ig_metodo,
           coalesce(m.CO_REGSAUD, 'UF_' || substr(b.CODMUNRES,1,2)) cl,
           count(*) n, sum(b.ptb) ptb,
           count(b.pig) n_pig, sum(b.pig) pig,
           sum(case when m.CO_REGSAUD is null then 1 else 0 end) n_semmap
    from b left join m on b.CODMUNRES = m.CODMUNRES
    group by all) to '%s' (format parquet)", cellf))
  dbDisconnect(con, shutdown = TRUE)
}
d <- as.data.table(arrow::read_parquet(cellf))
cat("N total:", sum(d$n), " sem mapa:", sum(d$n_semmap), " clusters:", uniqueN(d$cl), "\n")
cat("clusters UF_:", paste(sort(unique(d$cl[grepl('^UF_', d$cl)])), collapse=","), "\n")
d[, raca := factor(raca, c("Branca","Preta","Parda","Indigena"))]
d[, idade_cat := relevel(factor(idade_cat), "20-34")]
d[, regiao := relevel(factor(regiao), "SE")]
d[, esc_cat := relevel(factor(esc_cat), "5_12mais")]
d[, ano := factor(ano)]

fitpr <- function(dd, fml, ycol, ncol) {
  vars <- all.vars(fml)
  a <- dd[get(ncol) > 0, .(y = sum(get(ycol)), n = sum(get(ncol))), by = c(vars, "cl")]
  a <- a[n > 0]
  for (v in vars) if (is.factor(a[[v]])) a[[v]] <- droplevels(a[[v]])
  X <- model.matrix(fml, a)
  f <- glm.fit(X, a$y, offset = log(a$n), family = poisson(), control = list(epsilon = 1e-12, maxit = 100))
  b <- f$coefficients; mu <- f$fitted.values
  B <- solve(crossprod(X * sqrt(mu)))
  U <- X * (a$y - mu)
  Ug <- rowsum(U, a$cl)
  G <- nrow(Ug); N <- sum(a$n); K <- ncol(X)
  V <- (G/(G-1)) * ((N-1)/(N-K)) * B %*% crossprod(Ug) %*% B
  se <- sqrt(diag(V))
  r <- data.table(raca = c("Preta","Parda","Indigena"))
  r[, beta := b[paste0("raca", raca)]][, se := se[paste0("raca", raca)]]
  r[, `:=`(PR = exp(beta), PR_lo = exp(beta - qnorm(.975)*se), PR_hi = exp(beta + qnorm(.975)*se),
           N = N, casos = sum(a$y), G = G, K = K, conv = f$converged)]
  r
}
F1 <- ~ raca
F2 <- ~ raca + idade_cat + ano + regiao
F3 <- ~ raca + idade_cat + ano + regiao + esc_cat + estciv_cat

res <- list()
for (dz in c("ptb","pig")) {
  ncol <- if (dz == "ptb") "n" else "n_pig"
  for (m in c("M1","M2","M3")) {
    dd <- if (m == "M3") d[!is.na(estciv_cat)] else d
    fm <- switch(m, M1 = F1, M2 = F2, M3 = F3)
    r <- fitpr(dd, fm, dz, ncol); r[, `:=`(modelo = m, desfecho = dz)]
    res[[length(res)+1]] <- r; print(r)
  }
}
t1 <- rbindlist(res); setcolorder(t1, c("modelo","desfecho","raca"))
fwrite(t1, file.path(OUT, "tab_aud_e6b_modelos_v1_20261009.csv"))

res2 <- list()
for (cen in c("DUM","outro_metodo")) {
  r <- fitpr(d[ig_metodo == cen], F2, "ptb", "n"); r[, `:=`(cenario = paste0("so_", cen), modelo = "M2", desfecho = "ptb")]
  res2[[cen]] <- r; print(r)
}
t2 <- rbindlist(res2); setcolorder(t2, c("cenario","modelo","desfecho","raca"))
fwrite(t2, file.path(OUT, "tab_aud_e6b_m2_cenarios_v1_20261009.csv"))

t3 <- d[, .(n = sum(n), casos = sum(ptb)), by = .(raca, ig_metodo)][order(raca, ig_metodo)]
t3[, pct := 100 * casos / n]
print(t3)
fwrite(t3, file.path(OUT, "tab_aud_e6b_ptb_raca_metodo_v1_20261009.csv"))
