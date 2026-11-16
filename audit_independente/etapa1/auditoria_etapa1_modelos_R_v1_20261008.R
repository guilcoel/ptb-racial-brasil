# Auditoria independente etapa 1 - modelos em R (glm + sandwich). Sem statsmodels.
suppressPackageStartupMessages({library(sandwich); library(arrow); library(data.table)})
OUT <- "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa1/"
f3 <- function(x) sprintf("%.3f", x)
lab <- c(`1`="Branca",`2`="Preta",`4`="Parda",`5`="Indigena")
## ---------- B: RP bruta Brasil, Poisson agregado raca x municipio, cluster CODMUNRES ----------
ag <- fread(paste0(OUT,"agreg_raca_municipio_v1_20261008.csv"), colClasses=list(character="mun"))
ag[, raca := relevel(factor(raca), ref="1")]
resB <- list()
for (d in c("ptb","lbw","pig")) {
  dd <- ag[get(paste0(d,"_n")) > 0]; dd[, y := get(paste0(d,"_y"))]; dd[, n := get(paste0(d,"_n"))]
  m <- glm(y ~ raca + offset(log(n)), family=poisson, data=dd)
  N <- sum(dd$n); k <- length(coef(m))
  # sandwich por cluster: escore de Poisson agregado = soma dos escores individuais (exato);
  # HC1 do nivel individual = HC0*G/(G-1) [cadjust] * (N-1)/(N-k) com N = n individual
  V <- vcovCL(m, cluster=~mun, type="HC0", cadjust=TRUE) * (N-1)/(N-k)
  se <- sqrt(diag(V)); b <- coef(m)
  p <- dd[, .(p=sum(y)/sum(n)), by=raca]; pb <- p[raca=="1", p]
  for (r in c("2","4","5")) { nm <- paste0("raca",r)
    resB[[length(resB)+1]] <- data.table(desfecho=d, raca=lab[r], RP=f3(exp(b[nm])), li=f3(exp(b[nm]-1.959964*se[nm])),
      ls=f3(exp(b[nm]+1.959964*se[nm])), dif_pp=sprintf("%.3f",100*(p[raca==r,p]-pb)), G=length(unique(dd$mun)), N=N) }
}
resB <- rbindlist(resB); print(resB); fwrite(resB, paste0(OUT,"tabB_rp_bruta_brasil_cluster_v1_20261008.csv"))
## ---------- C: Centro-Oeste, nivel individual ----------
co <- as.data.table(read_parquet(paste0(OUT,"co_individual_C_v1_20261008.parquet")))
co[, raca := relevel(factor(raca), ref="1")]
co[, idcat := factor(fifelse(idade<20,"<20",fifelse(idade<=34,"20-34",">=35")), levels=c("20-34","<20",">=35"))]
co[, esc := factor(esc)]; co[, ano := factor(ano)]; co[, uf := factor(uf)]
cat("n CO =", nrow(co), " casos ptb =", sum(co$ptb), " municipios =", uniqueN(co$mun), "\n")
fm <- list(M1 = ptb ~ raca, M5 = ptb ~ raca + idcat + esc + ano + uf)
ci <- function(b,se,nm) sprintf("%s (%s-%s)", f3(exp(b[nm])), f3(exp(b[nm]-1.959964*se[nm])), f3(exp(b[nm]+1.959964*se[nm])))
resC <- list()
for (mn in names(fm)) {
  ml <- glm(fm[[mn]], family=binomial, data=co); mp <- glm(fm[[mn]], family=poisson, data=co)
  se_or  <- sqrt(diag(vcov(ml)))
  se_orc <- sqrt(diag(vcovCL(ml, cluster=~mun, type="HC1")))
  se_rp0 <- sqrt(diag(vcovHC(mp, type="HC0")))
  se_rpc <- sqrt(diag(vcovCL(mp, cluster=~mun, type="HC1")))
  for (r in c("2","4","5")) { nm <- paste0("raca",r)
    resC[[length(resC)+1]] <- data.table(modelo=mn, raca=lab[r], OR_modelo=ci(coef(ml),se_or,nm), OR_cluster=ci(coef(ml),se_orc,nm),
      RP_HC0=ci(coef(mp),se_rp0,nm), RP_cluster=ci(coef(mp),se_rpc,nm)) }
  if (mn=="M1") { # checagem: RP cluster agregado (metodo B) == individual
    a2 <- co[, .(y=sum(ptb), n=.N), by=.(raca,mun)]; ma <- glm(y ~ raca + offset(log(n)), family=poisson, data=a2)
    Va <- vcovCL(ma, cluster=~mun, type="HC0", cadjust=TRUE)*(nrow(co)-1)/(nrow(co)-4)
    cat("checagem agregado vs individual (EP cluster raca5):", sqrt(Va["raca5","raca5"]), se_rpc["raca5"], "\n") }
}
resC <- rbindlist(resC); print(resC); fwrite(resC, paste0(OUT,"tabC_validacao_centro_oeste_v1_20261008.csv"))
## ---------- D: 20 casos PIG vs growthstandards e gigs ----------
library(growthstandards); library(gigs)
d <- fread(paste0(OUT,"D_amostra20_pig_v1_20261008.csv"))
d[, sx := fifelse(sexo==1,"Male","Female")]
d[, cent_gs := igb_wtkg2centile(gagebrth=ig_dias, wtkg=peso/1000, sex=sx)]
d[, p10_gs := igb_centile2value(gagebrth=ig_dias, p=10, var="wtkg", sex=sx)]
d[, cent_gigs := value2centile(peso/1000, ig_dias, fifelse(sexo==1,"M","F"), family="ig_nbs", acronym="wfga")*100]
d[, p10_gigs := centile2value(0.10, ig_dias, fifelse(sexo==1,"M","F"), family="ig_nbs", acronym="wfga")]
d[, pig_gs := as.integer(cent_gs < 10)]; d[, pig_gigs := as.integer(cent_gigs < 10)]
fwrite(d, paste0(OUT,"D_amostra20_pig_classificada_v1_20261008.csv"))
cat("D: concordancia oficial x growthstandards =", sum(d$pig_oficial==d$pig_gs,na.rm=TRUE), "/", nrow(d),
    "; NAs gs =", sum(is.na(d$pig_gs)), "\n")
cat("D: concordancia oficial x gigs =", sum(d$pig_oficial==d$pig_gigs,na.rm=TRUE), "/", nrow(d), "; NAs gigs =", sum(is.na(d$pig_gigs)), "\n")
cat("D: max |P10 oficial - P10 gs| (g) =", 1000*max(abs(d$p10_oficial-d$p10_gs),na.rm=TRUE),
    "; max |P10 oficial - P10 gigs| (g) =", 1000*max(abs(d$p10_oficial-d$p10_gigs),na.rm=TRUE), "\n")
cat("D: n PIG oficial =", sum(d$pig_oficial), "; faixa IG (sem) =", range(d$semagestac), "\n")
