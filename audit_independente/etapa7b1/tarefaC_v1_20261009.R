# Auditoria independente etapa 7b1 - Tarefa C: AUC da parte fixa do m2 (MAIHDA) com IC DeLong ponderado
suppressMessages(library(lme4)); library(data.table)
L <- readRDS("data/processed/maihda_modelos_v1_20261008.rds")
auc_w <- function(p, wpos, wneg) {
  Wp <- sum(wpos); Wn <- sum(wneg)
  # psi(p_i caso, p_j nao caso)
  psi <- outer(p, p, function(a, b) (a > b) + 0.5 * (a == b))
  V10 <- as.vector(psi %*% wneg) / Wn          # por estrato, como caso
  V01 <- as.vector(t(psi) %*% wpos) / Wp       # por estrato, como nao caso
  auc <- sum(wpos * V10) / Wp
  S10 <- sum(wpos * (V10 - auc)^2) / (Wp - 1); S01 <- sum(wneg * (V01 - auc)^2) / (Wn - 1)
  se <- sqrt(S10/Wp + S01/Wn)
  c(auc=auc, se=se, lo=auc-1.96*se, hi=auc+1.96*se, nties=sum(duplicated(p)))
}
out <- list()
for (nm in c("m1","m2")) {
  m <- L[[nm]]
  Y <- model.response(model.frame(m)); casos <- Y[, "casos"]; nc <- Y[, "nc"]
  X <- getME(m, "X"); pf <- as.vector(plogis(X %*% fixef(m)))
  pc <- as.vector(fitted(m))   # fixa + aleatorio (contexto)
  a1 <- auc_w(pf, casos, nc); a2 <- auc_w(pc, casos, nc)
  cat(sprintf("%s: estratos=%d casos=%d nc=%d | AUC fixa=%.4f [%.4f; %.4f] (empates=%d) | AUC fixa+aleat=%.4f [%.4f; %.4f]\n",
      nm, nrow(X), sum(casos), sum(nc), a1["auc"], a1["lo"], a1["hi"], a1["nties"], a2["auc"], a2["lo"], a2["hi"]))
  out[[nm]] <- data.table(modelo=nm, tipo=c("fixa","fixa+aleat"), auc=c(a1["auc"],a2["auc"]), lo=c(a1["lo"],a2["lo"]), hi=c(a1["hi"],a2["hi"]), se=c(a1["se"],a2["se"]))
}
fwrite(rbindlist(out), "audit_independente/etapa7b1/auditor_C_auc_v1_20261009.csv")
