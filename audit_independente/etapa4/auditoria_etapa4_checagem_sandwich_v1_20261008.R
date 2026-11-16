# Checagem cruzada do EP do ICR com sandwich::vcovCL (HC0, cadjust) x (N-1)/(N-k), PIG ig_metodo=outro e ptb_esp ig_metodo=outro
suppressMessages({library(arrow); library(sandwich)})
OUT <- "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa4"
d0 <- as.data.frame(read_parquet(file.path(OUT, "cel_A_v1_20261008.parquet")))
d0 <- d0[d0$igm == "outro", ]
d0$raca <- factor(d0$raca, levels=c(1,2,4,5), labels=c("Branca","Preta","Parda","Indigena"))
d0$ida <- factor(d0$ida, levels=c("20_34","lt20","ge35")); d0$ano <- factor(d0$ano, levels=2015:2024)
d0$mr <- factor(d0$mr, levels=c(3,1,2,4,5)); d0$terc <- factor(d0$terc, levels=c(3,1,2))
for (oc in list(c("y_pig","n_pig"), c("y_esp","n_esp"))) {
  d <- aggregate(cbind(y=d0[[oc[1]]], den=d0[[oc[2]]]) ~ raca+ida+ano+mr+terc+mun, data=d0, FUN=sum)
  d <- d[d$den>0,]
  fit <- glm(y ~ raca+ida+ano+mr+terc+raca:terc+offset(log(den)), family=poisson(), data=d, control=glm.control(epsilon=1e-12))
  N <- sum(d$den); k <- length(coef(fit))
  V <- vcovCL(fit, cluster=~mun, type="HC0", cadjust=TRUE) * (N-1)/(N-k)
  ag <- aggregate(den ~ raca+ida+ano+mr+terc, data=d, FUN=sum)
  Pf <- function(g,m){nd<-ag; nd$raca<-factor(g,levels=levels(d$raca)); nd$terc<-factor(m,levels=levels(d$terc))
    X<-model.matrix(~raca+ida+ano+mr+terc+raca:terc,nd); r<-exp(drop(X%*%coef(fit)))
    c(sum(nd$den*r)/sum(nd$den), colSums(X*nd$den*r)/sum(nd$den))}
  v <- (Pf("Indigena","1")-Pf("Branca","1"))-(Pf("Indigena","3")-Pf("Branca","3"))
  se <- sqrt(drop(t(v[-1])%*%V%*%v[-1]))
  cat(oc[1], "outro: ICR =", sprintf("%.6f", 100*v[1]), " IC =", sprintf("%.6f", 100*(v[1]+c(-1,1)*1.96*se)), "\n")
}
