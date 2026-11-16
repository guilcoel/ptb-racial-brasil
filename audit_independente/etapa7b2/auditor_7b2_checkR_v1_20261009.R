suppressMessages({library(arrow); library(sandwich)})
d <- as.data.frame(read_parquet("cells_7b2.parquet"))
d <- d[d$has_reg & d$n_esp>0,]
d$raca <- relevel(factor(d$raca), "Branca"); d$idade_cat <- relevel(factor(d$idade_cat), "20-34")
d$ano <- factor(d$ano); d$regiao <- relevel(factor(d$regiao), "SE"); d$tercil <- relevel(factor(d$tercil), "T3")
d$r <- d$y_esp/d$n_esp
f <- suppressWarnings(glm(r ~ raca*tercil + idade_cat + ano + regiao, family=poisson, weights=n_esp, data=d))
N <- sum(d$n_esp); K <- length(coef(f))
V <- vcovCL(f, cluster=~cl, type="HC0", cadjust=TRUE) * (N-1)/(N-K)
tt <- grep(":", names(coef(f)), value=TRUE)
b <- coef(f)[tt]; W <- as.numeric(t(b) %*% solve(V[tt,tt]) %*% b)
cat("Wald chi2", W, "p", pchisq(W, 6, lower.tail=FALSE), "\n")
print(cbind(est=coef(f)[c("racaIndigena","racaIndigena:tercilT1")], se=sqrt(diag(V))[c("racaIndigena","racaIndigena:tercilT1")]))
# ICR by finite differences
P <- function(beta, g, t){ nd <- d; nd$raca <- factor(g, levels=levels(d$raca)); nd$tercil <- factor(t, levels=levels(d$tercil))
  X <- model.matrix(delete.response(terms(f)), nd); sum(d$n_esp*exp(X %*% beta))/N }
icr <- function(beta) 100*((P(beta,"Indigena","T1")-P(beta,"Branca","T1"))-(P(beta,"Indigena","T3")-P(beta,"Branca","T3")))
b0 <- coef(f); e0 <- icr(b0)
gr <- sapply(seq_along(b0), function(j){h<-1e-6; bb<-b0; bb[j]<-bb[j]+h; (icr(bb)-e0)/h})
se <- sqrt(as.numeric(t(gr) %*% V %*% gr)); cat("ICR", e0, "se", se, "IC", e0-1.96*se, e0+1.96*se, "\n")
