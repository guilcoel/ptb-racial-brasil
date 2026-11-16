suppressMessages(library(gigs))
t <- read.csv("docs/referencias/intergrowth21_bw_centis_oficial.csv")
t$eq <- 1000*mapply(function(p,g,s) centile2value(p/100, g, s, family="ig_nbs", acronym="wfga"), t$centil, t$gest_days, t$sexo)
t$dif <- 1000*t$peso_kg - t$eq
cat("n linhas", nrow(t), " |dif|>5.01 g:", sum(abs(t$dif)>5.01, na.rm=TRUE), " max|dif|:", max(abs(t$dif), na.rm=TRUE), "\n")
print(t[abs(t$dif)>5.01, c("fonte","sexo","semanas","dias","centil","peso_kg","eq","dif")])
