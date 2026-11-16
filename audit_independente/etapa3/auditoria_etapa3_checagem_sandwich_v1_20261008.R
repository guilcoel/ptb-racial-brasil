# Checagem cruzada: sandwich::vcovCL (HC0, ajuste G/(G-1)) x (N-1)/(N-k), e P padronizada ponderada por n total
suppressMessages({library(arrow); library(sandwich)})
OUT <- "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa3"
d <- as.data.frame(read_parquet(file.path(OUT, "cel_interacao_v1_20261008.parquet")))
d$raca <- factor(d$raca, levels=c(1,2,4,5), labels=c("Branca","Preta","Parda","Indigena"))
d$ida <- factor(d$ida, levels=c("20_34","lt20","ge35")); d$ano <- factor(d$ano, levels=2015:2024)
d$mr <- factor(d$mr, levels=c(3,1,2,4,5)); d$terc <- factor(d$terc, levels=c(3,1,2))
d <- d[d$n_esp>0,]
fit <- glm(y_esp ~ raca+ida+ano+mr+terc+raca:terc+offset(log(n_esp)), family=poisson(), data=d, control=glm.control(epsilon=1e-12))
N <- sum(d$n_esp); k <- length(coef(fit))
V <- vcovCL(fit, cluster=~mun, type="HC0", cadjust=TRUE) * (N-1)/(N-k)
se <- sqrt(diag(V))
print(round(cbind(b=coef(fit), se=se)[c("racaIndigena","terc1","racaIndigena:terc1","racaPreta:terc1"),], 6))
ag <- aggregate(n ~ raca+ida+ano+mr+terc, data=d, FUN=sum)
P <- function(g,m){nd<-ag; nd$raca<-factor(g,levels=levels(d$raca)); nd$terc<-factor(m,levels=levels(d$terc))
  sum(nd$n*exp(drop(model.matrix(~raca+ida+ano+mr+terc+raca:terc,nd)%*%coef(fit))))/sum(nd$n)}
for (g in c("Indigena","Preta")) cat(g, "ICR (pesos n total) =", 100*((P(g,"1")-P("Branca","1"))-(P(g,"3")-P("Branca","3"))), "\n")
