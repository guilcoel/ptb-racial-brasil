# Auditoria independente — Etapa 7b3 (ptb-racial-brasil)
# Auditor independente, 2026-10-09. Somente leitura nos dados; saídas só em audit_independente/etapa7b3/.
# Escrito SEM consultar scripts/arquivos do autor (etapa7b3_*, etapa*_lib.py, tab_e7b3_*, manuscrito, flags).
#
# Estratégia: DuckDB agrega a base em células (cluster x raça x idade x ano x região x tercil x TPMETESTIM),
# com contagens n/y para cada desfecho; Poisson log em células (y, offset log n) é equivalente exato ao
# ajuste individual (covariáveis todas categóricas). Sanduíche agrupado: escores somados por cluster,
# correção G/(G-1)*(N-1)/(N-K) com N = nº de indivíduos no modelo.
# Cluster = CO_REGSAUD; sem região -> "UF_" + 2 primeiros dígitos de CODMUNRES (só afeta M2; o 3.2 exige CO_REGSAUD).
# ICR(g,t) = 100*{[P(g,t)-P(Br,t)] - [P(g,T3)-P(Br,T3)]}, P = média sobre as obs. do modelo da prob. prevista
# com raça=g e tercil=t (interações acompanham), IC pelo método delta com a mesma V.
# Tarefa C: P97 INTERGROWTH-21st pela TABELA oficial (gramas = round(1000*peso_kg)), dia = 7*SEMAGESTAC+3;
#           também pela EQUAÇÃO (gigs::centile2value, p=0.97) só para quantificar tabela x equação.
set.seed(42)
suppressMessages({library(DBI); library(data.table); library(gigs)})
OUT  <- "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa7b3"
BASE <- "/Volumes/Forja/ptb-racial-brasil/data/processed/sinasc_brasil_2015_2024_v3_20261008/ano=*/part-0.parquet"
TERC <- "/Volumes/Forja/ptb-racial-brasil/data/processed/tercil_reg_regsaude_ano_v1_20261008.csv"
REFP <- "/Volumes/Forja/ptb-racial-brasil/docs/referencias/intergrowth21_bw_centis_oficial.csv"
cellf <- file.path(OUT, "cel_e7b3_v1_20261009.parquet")
logf  <- file.path(OUT, "log_auditoria_v1_20261009.txt")
stamp <- function() format(Sys.time(), "%Y-%m-%d %H:%M:%S %Z")
lg <- function(...) { s <- paste0("[", stamp(), "] ", sprintf(...)); cat(s, "\n"); cat(s, "\n", file = logf, append = TRUE) }
lg("início; R %s; data.table %s; duckdb %s; gigs %s", R.version.string, packageVersion("data.table"),
   packageVersion("duckdb"), packageVersion("gigs"))

# ---------------- P97: tabela oficial e equação ----------------
ref <- fread(REFP)
p97t <- ref[centil == 97, .(sexo = fifelse(sexo == "M", 1L, 2L), dias = as.integer(gest_days),
                            p97_tab_g = as.integer(round(1000 * peso_kg)))]
stopifnot(!anyDuplicated(p97t[, .(sexo, dias)]))
need <- CJ(sexo = 1:2, sg = 24:36)[, dias := 7L * sg + 3L]
p97 <- merge(need, p97t, by = c("sexo", "dias"), all.x = TRUE)
stopifnot(!anyNA(p97$p97_tab_g))
p97[, p97_eq_g := 1000 * centile2value(p = rep(0.97, .N), x = as.numeric(dias),
                                       sex = fifelse(sexo == 1L, "M", "F"), family = "ig_nbs", acronym = "wfga")]
p97[, dif_g := p97_tab_g - p97_eq_g]
lg("P97 tabela - equação (g), dias 7*sg+3, sg 24-36: min %.1f, max %.1f, média |dif| %.1f",
   min(p97$dif_g), max(p97$dif_g), mean(abs(p97$dif_g)))
fwrite(p97, file.path(OUT, "p97_tabela_equacao_v1_20261009.csv"))

# ---------------- Agregação (DuckDB) ----------------
if (!file.exists(cellf)) {
  con <- dbConnect(duckdb::duckdb())
  dbExecute(con, "SET threads=8")
  duckdb::duckdb_register(con, "p97", as.data.frame(p97[, .(SEMAGESTAC = sg, SEXO = sexo, p97_tab_g, p97_eq_g)]))
  dbExecute(con, sprintf("create view b as select * from read_parquet('%s', hive_partitioning=true) where incl", BASE))
  dbExecute(con, sprintf("create table t as select CO_REGSAUD::varchar CO_REGSAUD, ano::int ano, tercil_reg
                          from read_csv('%s', all_varchar=true)", TERC))
  dbExecute(con, sprintf("copy (
    with x as (
      select coalesce(b.CO_REGSAUD, 'UF_' || substr(b.CODMUNRES,1,2)) cl,
             (b.CO_REGSAUD is not null)::int has_rs,
             b.raca, b.idade_cat, b.ano::int ano, b.regiao, t.tercil_reg, b.TPMETESTIM::int tpm,
             b.ptb, b.pig, b.ptb_ind, b.ptb_esp,
             (b.ptb = 1 and b.unica = 1 and b.SEMAGESTAC between 24 and 36 and b.SEXO in (1,2)
                and b.PESO between 100 and 7000 and b.PESO > p.p97_tab_g)::int rc_tab,
             (b.ptb = 1 and b.unica = 1 and b.SEMAGESTAC between 24 and 36 and b.SEXO in (1,2)
                and b.PESO between 100 and 7000 and b.PESO > p.p97_eq_g)::int rc_eq
      from b
      left join t on b.CO_REGSAUD = t.CO_REGSAUD and b.ano::int = t.ano
      left join p97 p on b.SEMAGESTAC = p.SEMAGESTAC and b.SEXO = p.SEXO)
    select cl, has_rs, raca, idade_cat, ano, regiao, tercil_reg, tpm,
           count(*) n, sum(ptb) y_ptb,
           count(pig) n_pig, sum(pig) y_pig,
           count(ptb_ind) n_ind, sum(ptb_ind) y_ind,
           count(ptb_esp) n_esp, sum(ptb_esp) y_esp,
           sum(coalesce(rc_tab,0)) rc_tab, sum(coalesce(rc_eq,0)) rc_eq,
           sum(case when coalesce(rc_tab,0)=1 and ptb_esp = 1 then 1 else 0 end) rc_tab_esp1,
           sum(case when coalesce(rc_tab,0)=1 and ptb_ind = 1 then 1 else 0 end) rc_tab_ind1,
           sum(case when coalesce(rc_tab,0)=1 and ptb_esp is null then 1 else 0 end) rc_tab_nc,
           sum(case when coalesce(rc_eq,0)=1 and ptb_esp = 1 then 1 else 0 end) rc_eq_esp1,
           sum(case when coalesce(rc_eq,0)=1 and ptb_esp is null then 1 else 0 end) rc_eq_nc
    from x group by all) to '%s' (format parquet)", cellf))
  dbDisconnect(con, shutdown = TRUE)
  lg("células gravadas em %s", cellf)
}
d <- as.data.table(arrow::read_parquet(cellf))
for (v in names(d)) if (inherits(d[[v]], "integer64")) d[[v]] <- as.numeric(d[[v]])
# sum() do DuckDB devolve NULL quando todos os valores da célula são nulos (n_* = 0): zera
for (v in grep("^(y_|rc_)", names(d), value = TRUE)) set(d, which(is.na(d[[v]])), v, 0)
lg("N total %s; células %d; clusters %d (UF_: %d); N sem CO_REGSAUD %s; sem tercil c/ regsaud %s",
   format(sum(d$n), big.mark = ","), nrow(d), uniqueN(d$cl), uniqueN(d$cl[grepl("^UF_", d$cl)]),
   sum(d$n[d$has_rs == 0]), sum(d$n[d$has_rs == 1 & is.na(d$tercil_reg)]))
# desfechos reclassificados
d[, `:=`(y_ptb_rct = y_ptb - rc_tab, y_ptb_rce = y_ptb - rc_eq,
         # variante A (principal): PTB reclassificado vira não caso também em ptb_esp (inclui os não classificados)
         n_espA_t = n_esp + rc_tab_nc, y_espA_t = y_esp - rc_tab_esp1,
         n_espA_e = n_esp + rc_eq_nc,  y_espA_e = y_esp - rc_eq_esp1,
         # variante B: não classificados reclassificados continuam nulos em ptb_esp
         n_espB_t = n_esp, y_espB_t = y_esp - rc_tab_esp1)]
rcs <- d[, .(n = sum(n), ptb = sum(y_ptb), rc_tab = sum(rc_tab), rc_eq = sum(rc_eq),
             rc_tab_esp1 = sum(rc_tab_esp1), rc_tab_ind1 = sum(rc_tab_ind1), rc_tab_nc = sum(rc_tab_nc)), by = raca]
rcs <- rbind(rcs, rcs[, lapply(.SD, sum), .SDcols = -"raca"][, raca := "Total"])
rcs[, `:=`(pct_ptb_rc_tab = 100 * rc_tab / ptb, pct_ptb_rc_eq = 100 * rc_eq / ptb)]
print(rcs); fwrite(rcs, file.path(OUT, "tab_aud_e7b3_reclass_contagens_v1_20261009.csv"))

# ---------------- Funções de ajuste ----------------
RACAS <- c("Preta", "Parda", "Indigena")
monta_X <- function(a, raca = NULL, terc = NULL, inter = TRUE) {
  r <- if (is.null(raca)) a$raca else rep(raca, nrow(a))
  X <- cbind("(Intercept)" = 1,
             rPreta = r == "Preta", rParda = r == "Parda", rIndigena = r == "Indigena",
             "i<20" = a$idade_cat == "<20", "i>=35" = a$idade_cat == ">=35",
             sapply(2016:2024, function(y) a$ano == y),
             gN = a$regiao == "N", gNE = a$regiao == "NE", gS = a$regiao == "S", gCO = a$regiao == "CO")
  colnames(X)[7:15] <- paste0("a", 2016:2024)
  if (inter) {
    t <- if (is.null(terc)) a$tercil_reg else rep(terc, nrow(a))
    X <- cbind(X, tT1 = t == "T1", tT2 = t == "T2")
    for (rr in RACAS) for (tt in c("T1", "T2"))
      X <- cbind(X, setNames(data.frame((r == rr) & (t == tt)), paste0("r", rr, ":t", tt)))
  }
  X <- as.matrix(X); storage.mode(X) <- "double"; X
}
ajusta <- function(a, inter) {
  X <- monta_X(a, inter = inter)
  stopifnot(all(colSums(X[, -1, drop = FALSE] * a$n) > 0))      # nenhum nível vazio
  f <- glm.fit(X, a$y, offset = log(a$n), family = poisson(), control = list(epsilon = 1e-12, maxit = 100))
  b <- f$coefficients; mu <- f$fitted.values                       # = n * p
  B <- solve(crossprod(X * sqrt(mu)))
  Ug <- rowsum(X * (a$y - mu), a$cl)
  G <- nrow(Ug); N <- sum(a$n); K <- ncol(X)
  V <- (G / (G - 1)) * ((N - 1) / (N - K)) * B %*% crossprod(Ug) %*% B
  dimnames(V) <- list(names(b), names(b))
  list(b = b, V = V, N = N, casos = sum(a$y), G = G, K = K, conv = f$converged, iter = f$iter,
       maxscore = max(abs(colSums(X * (a$y - mu)))), a = a)
}
prep <- function(dd, ycol, ncol, m32) {
  dd <- dd[get(ncol) > 0]
  if (m32) dd <- dd[has_rs == 1]
  by <- c("cl", "raca", "idade_cat", "ano", "regiao", if (m32) "tercil_reg")
  a <- dd[, .(y = sum(get(ycol)), n = sum(get(ncol))), by = by]
  if (m32) stopifnot(!anyNA(a$tercil_reg))
  a
}
fit_m2 <- function(dd, ycol, ncol) {
  m <- ajusta(prep(dd, ycol, ncol, FALSE), inter = FALSE)
  se <- sqrt(diag(m$V))
  data.table(raca = RACAS, beta = m$b[paste0("r", RACAS)], se = se[paste0("r", RACAS)])[
    , `:=`(PR = exp(beta), PR_lo = exp(beta - qnorm(.975) * se), PR_hi = exp(beta + qnorm(.975) * se),
           N = m$N, casos = m$casos, G = m$G, K = m$K, conv = m$conv)][]
}
fit_32 <- function(dd, ycol, ncol) {
  m <- ajusta(prep(dd, ycol, ncol, TRUE), inter = TRUE)
  a <- m$a; b <- m$b; V <- m$V; N <- m$N
  P <- list(); gr <- list()
  for (g in c("Branca", RACAS)) for (t in c("T1", "T2", "T3")) {
    Xg <- monta_X(a, g, t); pr <- exp(drop(Xg %*% b))
    P[[paste(g, t)]] <- sum(a$n * pr) / N
    gr[[paste(g, t)]] <- colSums(Xg * (a$n * pr)) / N
  }
  icr <- rbindlist(lapply(RACAS, function(g) rbindlist(lapply(c("T1", "T2"), function(t) {
    est <- 100 * ((P[[paste(g, t)]] - P[[paste("Branca", t)]]) - (P[[paste(g, "T3")]] - P[[paste("Branca", "T3")]]))
    gv  <- 100 * ((gr[[paste(g, t)]] - gr[[paste("Branca", t)]]) - (gr[[paste(g, "T3")]] - gr[[paste("Branca", "T3")]]))
    se <- sqrt(drop(t(gv) %*% V %*% gv))
    data.table(raca = g, tercil = t, ICR_pp = est, ICR_se = se,
               ICR_lo = est - qnorm(.975) * se, ICR_hi = est + qnorm(.975) * se,
               P_g_t = 100 * P[[paste(g, t)]], P_B_t = 100 * P[[paste("Branca", t)]],
               P_g_T3 = 100 * P[[paste(g, "T3")]], P_B_T3 = 100 * P[[paste("Branca", "T3")]])
  }))))
  wald <- function(ii) { W <- drop(t(b[ii]) %*% solve(V[ii, ii]) %*% b[ii])
                         c(chi2 = W, df = length(ii), p = pchisq(W, length(ii), lower.tail = FALSE)) }
  i6 <- grep(":t", names(b)); i2 <- c("rIndigena:tT1", "rIndigena:tT2")
  w6 <- wald(i6); w2 <- wald(i2)
  se <- sqrt(diag(V))
  list(icr = icr,
       wald = data.table(N = N, casos = m$casos, G = m$G, K = m$K, conv = m$conv, iter = m$iter,
                         maxscore = m$maxscore,
                         wald6_chi2 = w6[["chi2"]], wald6_p = w6[["p"]],
                         waldInd2_chi2 = w2[["chi2"]], waldInd2_p = w2[["p"]],
                         b_IndT1 = b[["rIndigena:tT1"]], se_IndT1 = se[["rIndigena:tT1"]],
                         b_IndT2 = b[["rIndigena:tT2"]], se_IndT2 = se[["rIndigena:tT2"]],
                         cov_IndT1T2 = V["rIndigena:tT1", "rIndigena:tT2"]),
       coef = data.table(termo = names(b), beta = b, se = se))
}
amostras <- list(completa = NULL, tpm1 = 1L, tpm2 = 2L, tpm8 = 8L)
subam <- function(k) if (is.null(amostras[[k]])) d else d[tpm == amostras[[k]]]

# ---------------- Tarefa A ----------------
lg("Tarefa A: ptb_esp por TPMETESTIM")
A_m2 <- list(); A_icr <- list(); A_w <- list()
for (k in c("tpm1", "tpm2", "tpm8")) {
  r <- fit_m2(subam(k), "y_esp", "n_esp"); r[, amostra := k]; A_m2[[k]] <- r; print(r)
  f <- fit_32(subam(k), "y_esp", "n_esp")
  A_icr[[k]] <- f$icr[, amostra := k]; A_w[[k]] <- f$wald[, amostra := k]
  print(f$icr[raca == "Indigena"]); print(f$wald)
}
A_m2 <- rbindlist(A_m2); A_icr <- rbindlist(A_icr); A_w <- rbindlist(A_w)

# ---------------- Tarefa B ----------------
lg("Tarefa B: Wald 2 gl indígena e 6 gl, 4 desfechos x 4 amostras")
DZ <- list(ptb = c("y_ptb", "n"), pig = c("y_pig", "n_pig"), ptb_ind = c("y_ind", "n_ind"), ptb_esp = c("y_esp", "n_esp"))
B_w <- list(); B_icr <- list(); B_coef <- list()
for (dz in names(DZ)) for (k in names(amostras)) {
  f <- fit_32(subam(k), DZ[[dz]][1], DZ[[dz]][2])
  B_w[[paste(dz, k)]] <- f$wald[, `:=`(desfecho = dz, amostra = k)]
  B_icr[[paste(dz, k)]] <- f$icr[, `:=`(desfecho = dz, amostra = k)]
  B_coef[[paste(dz, k)]] <- f$coef[, `:=`(desfecho = dz, amostra = k)]
  lg("B %s/%s: N=%s G=%d conv=%s W6=%.3f (p=%.4g) Wind2=%.3f (p=%.4g)", dz, k, format(f$wald$N, big.mark = ","),
     f$wald$G, f$wald$conv, f$wald$wald6_chi2, f$wald$wald6_p, f$wald$waldInd2_chi2, f$wald$waldInd2_p)
}
B_w <- rbindlist(B_w); B_icr <- rbindlist(B_icr); B_coef <- rbindlist(B_coef)

# ---------------- Tarefa C ----------------
lg("Tarefa C: reclassificação P97 (tabela oficial; equação gigs como sensibilidade)")
DZC <- list(ptb_rc_tab = c("y_ptb_rct", "n"), ptb_esp_rcA_tab = c("y_espA_t", "n_espA_t"),
            ptb_esp_rcB_tab = c("y_espB_t", "n_espB_t"),
            ptb_rc_eq = c("y_ptb_rce", "n"), ptb_esp_rcA_eq = c("y_espA_e", "n_espA_e"))
C_w <- list(); C_icr <- list()
for (dz in names(DZC)) for (k in names(amostras)) {
  f <- fit_32(subam(k), DZC[[dz]][1], DZC[[dz]][2])
  C_w[[paste(dz, k)]] <- f$wald[, `:=`(desfecho = dz, amostra = k)]
  C_icr[[paste(dz, k)]] <- f$icr[, `:=`(desfecho = dz, amostra = k)]
  lg("C %s/%s: N=%s casos=%s W6=%.3f (p=%.4g) Wind2=%.3f (p=%.4g)", dz, k, format(f$wald$N, big.mark = ","),
     format(f$wald$casos, big.mark = ","), f$wald$wald6_chi2, f$wald$wald6_p, f$wald$waldInd2_chi2, f$wald$waldInd2_p)
}
C_w <- rbindlist(C_w); C_icr <- rbindlist(C_icr)

# ---------------- Gravação com carimbo ----------------
ts <- stamp()
for (nm in c("A_m2", "A_icr", "A_w", "B_w", "B_icr", "B_coef", "C_w", "C_icr")) {
  x <- get(nm); x[, carimbo := ts]
  fwrite(x, file.path(OUT, sprintf("tab_aud_e7b3_%s_v1_20261009.csv", nm)))
}
lg("resultados gravados (carimbo %s)", ts)
