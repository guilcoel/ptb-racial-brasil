# Auditoria independente - etapa 2 - Modelo M2 (Poisson log, EP cluster por CODMUNRES)
# Ajuste sobre dados agregados (raca x faixa x ano x macro x municipio) com offset log(n).
# Equivalencia com o nivel individual: escores e Hessiana somam exatamente dentro da celula
# (covariaveis constantes na celula, celulas aninhadas no cluster). A unica diferenca no
# vcovCL(type="HC1") e o fator (n-1)/(n-k), que usa n = n de linhas. Por isso calculamos
# HC0 com cadjust G/(G-1) e multiplicamos por (N_ind-1)/(N_ind-k). Conferido abaixo
# com expansao para nivel individual num subconjunto (UFs 11, 12, 14, 28).
suppressPackageStartupMessages(library(sandwich))
OUT <- "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa2"
d <- read.csv(file.path(OUT, "agregado_m2_raca_idade_ano_macro_mun.csv"),
              colClasses = c(raca="integer", faixa="character", ano="integer", macro="character",
                             mun="character", n="numeric", y_ptb="numeric", n_esp="numeric", y_esp="numeric"))
d$y_esp[is.na(d$y_esp)] <- 0
prep <- function(d) {
  d$raca  <- relevel(factor(d$raca), ref = "1")
  d$faixa <- relevel(factor(d$faixa), ref = "20_34")
  d$ano   <- relevel(factor(d$ano), ref = "2015")
  d$macro <- relevel(factor(d$macro), ref = "3")
  d
}
d <- prep(d)
fml <- y ~ raca + faixa + ano + macro

fit_agg <- function(dd, ycol, ncol) {
  dd <- dd[dd[[ncol]] > 0, ]
  dd$y <- dd[[ycol]]; dd$off <- log(dd[[ncol]])
  m <- glm(fml, family = poisson(), data = dd, offset = off)
  N <- sum(dd[[ncol]]); k <- length(coef(m))
  V <- vcovCL(m, cluster = dd$mun, type = "HC0", cadjust = TRUE) * (N - 1) / (N - k)
  list(m = m, V = V, N = N, G = length(unique(dd$mun)))
}

## --- conferencia de equivalencia (subconjunto expandido a nivel individual) ---
s <- droplevels(d[substr(d$mun, 1, 2) %in% c("11", "12", "14", "28"), ])  # UF 28 (NE) para ter 2 macros
for (oc in list(c("y_ptb", "n"), c("y_esp", "n_esp"))) {
  a <- fit_agg(s, oc[1], oc[2])
  ss <- s[s[[oc[2]]] > 0, ]
  idx <- rep(seq_len(nrow(ss)), ss[[oc[2]]])
  ind <- ss[idx, c("raca", "faixa", "ano", "macro", "mun")]
  ind$y <- unlist(mapply(function(y, n) c(rep(1, y), rep(0, n - y)), ss[[oc[1]]], ss[[oc[2]]]))
  mi <- glm(fml, family = poisson(), data = ind)
  Vi <- vcovCL(mi, cluster = ind$mun, type = "HC1")
  Vn <- vcovCL(a$m, cluster = ss$mun, type = "HC1")  # ingenuo sobre agregado
  cat(sprintf("CHECK %s: N=%d | max|dcoef|=%.2e | max rel dif EP (manual vs indiv)=%.2e | (vcovCL HC1 ingenuo agregado vs indiv)=%.2e\n",
              oc[1], nrow(ind), max(abs(coef(a$m) - coef(mi))),
              max(abs(sqrt(diag(a$V)) / sqrt(diag(Vi)) - 1)),
              max(abs(sqrt(diag(Vn)) / sqrt(diag(Vi)) - 1))))
}

## --- modelos completos ---
res <- NULL
for (oc in list(c("ptb", "y_ptb", "n"), c("ptb_esp", "y_esp", "n_esp"))) {
  a <- fit_agg(d, oc[2], oc[3])
  for (r in c("2", "4", "5")) {
    nm <- paste0("raca", r); b <- coef(a$m)[nm]; se <- sqrt(a$V[nm, nm])
    res <- rbind(res, data.frame(desfecho = oc[1], raca = c("2"="Preta","4"="Parda","5"="Indigena")[r],
      RP = exp(b), IC_inf = exp(b - qnorm(0.975) * se), IC_sup = exp(b + qnorm(0.975) * se),
      beta = b, ep_cluster = se, N = a$N, n_clusters = a$G, eventos = sum(d[[oc[2]]])))
  }
}
rownames(res) <- NULL
write.csv(res, file.path(OUT, "m2_rp_brasil.csv"), row.names = FALSE)
print(format(res, digits = 6))
for (i in seq_len(nrow(res)))
  cat(sprintf("%s %s RP=%.3f (%.3f-%.3f) N=%d\n", res$desfecho[i], res$raca[i], res$RP[i], res$IC_inf[i], res$IC_sup[i], res$N[i]))
