# Auditoria independente etapa 7b1 - modelos Poisson agregados com sanduiche por cluster
# Escrito sem consulta aos scripts/tabelas do autor. seed 42.
library(data.table)
set.seed(42)
ag <- readRDS("/private/tmp/claude-501/-Users-guilherme/e1c712c9-85af-4f6d-89f1-cb28b034e571/scratchpad/ag_v3.rds")
ag[, raca := factor(raca, levels=c("Branca","Preta","Parda","Indigena"))]
ag[, idade_cat := factor(idade_cat, levels=c("20-34","<20",">=35"))]
ag[, regiao := factor(regiao, levels=c("SE","N","NE","S","CO"))]
ag[, tercil := factor(tercil_reg, levels=c("T3","T1","T2"))]
for (v in c("ptb_ind","ptb_esp")) set(ag, which(is.na(ag[[v]])), v, 0)  # celulas so com sem_classif
stopifnot(!anyNA(ag[, .(n, ptb, n_ind, ptb_ind, n_esp, ptb_esp, semclass, raca, idade_cat, regiao, ano)]))

fit_pois <- function(d, yv, nv, f) {
  d <- d[get(nv) > 0]
  d[, `:=`(Y = get(yv), E = get(nv))]
  stopifnot(!anyNA(d$Y))
  d[, ano_f := factor(ano)]
  fit <- glm(f, family=poisson(link="log"), data=d, offset=log(E), control=glm.control(epsilon=1e-12, maxit=100))
  X <- model.matrix(fit)
  mu <- as.vector(exp(X %*% coef(fit))) * d$E
  A <- crossprod(X * sqrt(mu))
  Ainv <- solve(A)
  U <- rowsum(X * (d$Y - mu), d$cluster)
  G <- nrow(U); N <- sum(d$E); K <- ncol(X)
  V <- Ainv %*% crossprod(U) %*% Ainv * (G/(G-1)) * ((N-1)/(N-K))
  list(fit=fit, d=d, V=V, G=G, N=N, K=K, Y=sum(d$Y))
}
# P(g,t): media ponderada (por n) de exp(eta) com raca=g, tercil=t; gradiente
Pgt <- function(m, g, t) {
  cf <- copy(m$d); cf[, raca := factor(g, levels=levels(m$d$raca))]; cf[, tercil := factor(t, levels=levels(m$d$tercil))]
  Xc <- model.matrix(delete.response(terms(m$fit)), cf)
  stopifnot(identical(colnames(Xc), names(coef(m$fit))))
  p <- as.vector(exp(Xc %*% coef(m$fit)))
  list(P = sum(cf$E * p)/sum(cf$E), g = colSums(Xc * (cf$E * p))/sum(cf$E))
}
icr <- function(m, g, tk) {
  a <- Pgt(m, g, tk); b <- Pgt(m, "Branca", tk); c <- Pgt(m, g, "T3"); e <- Pgt(m, "Branca", "T3")
  est <- 100*((a$P - b$P) - (c$P - e$P)); gr <- 100*(a$g - b$g - c$g + e$g)
  se <- sqrt(as.numeric(t(gr) %*% m$V %*% gr))
  data.table(icr=est, se=se, lo=est-1.96*se, hi=est+1.96*se, p=2*pnorm(-abs(est/se)))
}
wald_int <- function(m) {
  b <- coef(m$fit); ix <- grep(":", names(b))
  stopifnot(length(ix) == 6)
  W <- as.numeric(t(b[ix]) %*% solve(m$V[ix, ix]) %*% b[ix])
  data.table(wald=W, df=6, p=pchisq(W, 6, lower.tail=FALSE))
}
pr_ind <- function(m) {
  b <- coef(m$fit)["racaIndigena"]; se <- sqrt(m$V["racaIndigena","racaIndigena"])
  data.table(pr=exp(b), lo=exp(b-1.96*se), hi=exp(b+1.96*se), logse=se)
}
f32 <- Y ~ raca + idade_cat + ano_f + regiao + tercil + raca:tercil
fM2 <- Y ~ raca + idade_cat + ano_f + regiao
s32 <- ag[tem_rs == TRUE]   # amostra com CO_REGSAUD

res <- list()
add <- function(tarefa, item, valor, extra="") res[[length(res)+1]] <<- data.table(tarefa=tarefa, item=item, valor=valor, extra=extra)

## ---------- Tarefa A ----------
subs <- list(completa = s32, DUM = s32[ig_metodo=="DUM"], outro_metodo = s32[ig_metodo=="outro_metodo"],
             sem_CE_DF = s32[!uf %in% c("CE","DF")], sem_2024 = s32[ano != 2024])
for (nm in names(subs)) {
  m <- fit_pois(subs[[nm]], "ptb", "n_ptb", f32)
  r <- icr(m, "Indigena", "T1"); w <- wald_int(m)
  cat(sprintf("A %-13s N=%d Y=%d G=%d ICR=%.4f [%.4f;%.4f] se=%.4f | Wald=%.3f p=%.4g\n", nm, m$N, m$Y, m$G, r$icr, r$lo, r$hi, r$se, w$wald, w$p))
  add("A", paste0(nm,"_N"), m$N); add("A", paste0(nm,"_G"), m$G)
  add("A", paste0(nm,"_ICR_Ind_T1"), r$icr); add("A", paste0(nm,"_ICR_Ind_T1_lo"), r$lo); add("A", paste0(nm,"_ICR_Ind_T1_hi"), r$hi)
  add("A", paste0(nm,"_Wald_chi2"), w$wald); add("A", paste0(nm,"_Wald_p"), w$p)
}

## ---------- Tarefa D ----------
cat("D: sem_classif amostra analitica =", sum(ag$semclass), "; com CO_REGSAUD =", sum(s32$semclass), "\n")
add("D", "semclass_analitica", sum(ag$semclass)); add("D", "semclass_com_regsaud", sum(s32$semclass))
for (cen in c("i_todos_indicados","ii_todos_espontaneos")) {
  a2 <- copy(ag)
  if (cen == "i_todos_indicados") { a2[, `:=`(y_ind = ptb_ind + semclass, y_esp = ptb_esp)] } else { a2[, `:=`(y_ind = ptb_ind, y_esp = ptb_esp + semclass)] }
  for (o in c("ind","esp")) {
    m <- fit_pois(a2, paste0("y_",o), "n", fM2); p <- pr_ind(m)
    cat(sprintf("D %s PR M2 ptb_%s Ind vs Branca: %.4f [%.4f;%.4f] N=%d Y=%d G=%d\n", cen, o, p$pr, p$lo, p$hi, m$N, m$Y, m$G))
    add("D", paste0(cen,"_PR_M2_ptb_",o), p$pr); add("D", paste0(cen,"_PR_M2_ptb_",o,"_lo"), p$lo); add("D", paste0(cen,"_PR_M2_ptb_",o,"_hi"), p$hi)
  }
  m <- fit_pois(a2[tem_rs == TRUE], "y_ind", "n", f32); r <- icr(m, "Indigena", "T1")
  cat(sprintf("D %s ICR Ind T1 ptb_ind: %.4f [%.4f;%.4f] N=%d\n", cen, r$icr, r$lo, r$hi, m$N))
  add("D", paste0(cen,"_ICR_Ind_T1_ptb_ind"), r$icr); add("D", paste0(cen,"_ICR_Ind_T1_ptb_ind_lo"), r$lo); add("D", paste0(cen,"_ICR_Ind_T1_ptb_ind_hi"), r$hi)
}
# referencia sem cenario
for (o in c("ind","esp")) { m <- fit_pois(ag, paste0("ptb_",o), paste0("n_",o), fM2); p <- pr_ind(m)
  cat(sprintf("D original PR M2 ptb_%s: %.4f [%.4f;%.4f] N=%d\n", o, p$pr, p$lo, p$hi, m$N)); add("D", paste0("original_PR_M2_ptb_",o), p$pr) }

## ---------- Tarefa E ----------
m <- fit_pois(s32, "ptb_ind", "n_ind", f32)
cat("E: N =", m$N, " Y =", m$Y, " G =", m$G, "\n")
r0 <- icr(m, "Indigena", "T1"); cat(sprintf("E (ref) ICR Ind T1 ptb_ind original: %.4f [%.4f;%.4f]\n", r0$icr, r0$lo, r0$hi))
add("E", "ICR_Ind_T1_ptb_ind_original", r0$icr)
for (pp in list(c("Indigena","T1"), c("Indigena","T2"), c("Parda","T1"))) {
  g <- pp[1]; tk <- pp[2]
  cells <- list(B_T3 = Pgt(m,"Branca","T3"), B_Tk = Pgt(m,"Branca",tk), g_T3 = Pgt(m,g,"T3"), g_Tk = Pgt(m,g,tk))
  Ps <- sapply(cells, `[[`, "P")
  ref <- names(which.min(Ps))
  opp <- c(B_T3="g_Tk", g_Tk="B_T3", B_Tk="g_T3", g_T3="B_Tk")[ref]
  simp <- setdiff(names(cells), c(ref, opp))
  num <- Ps[opp] - Ps[simp[1]] - Ps[simp[2]]
  reri <- num/Ps[ref] + 1
  gr <- (cells[[opp]]$g - cells[[simp[1]]]$g - cells[[simp[2]]]$g)/Ps[ref] - num/Ps[ref]^2 * cells[[ref]]$g
  se <- sqrt(as.numeric(t(gr) %*% m$V %*% gr))
  cat(sprintf("E %s x %s: P[B_T3,B_Tk,g_T3,g_Tk]=%s ref=%s RERI=%.4f [%.4f;%.4f] se=%.4f\n", g, tk,
              paste(sprintf("%.5f", Ps), collapse=","), ref, reri, reri-1.96*se, reri+1.96*se, se))
  key <- paste0(g,"_",tk)
  add("E", paste0(key,"_ref"), NA, ref)
  add("E", paste0(key,"_RERI"), reri, ref); add("E", paste0(key,"_RERI_lo"), reri-1.96*se); add("E", paste0(key,"_RERI_hi"), reri+1.96*se)
  for (cn in names(Ps)) add("E", paste0(key,"_P_",cn), Ps[cn])
}
out <- rbindlist(res)
fwrite(out, "audit_independente/etapa7b1/auditor_ADE_v1_20261009.csv")
