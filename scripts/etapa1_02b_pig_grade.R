# 1.2 PIG — grade de referência (não contém microdado): para cada SEMAGESTAC 24–42, SEXO (1 M, 2 F)
# e PESO 100–7000 g, o centil INTERGROWTH-21st de peso para IG (gigs::value2centile, ig_nbs/wfga).
#
# O SINASC só registra semanas completas. A IG em dias exigida pelo padrão é imputada como
#   dias = 7*SEMAGESTAC + k, com k = 3 (meio da semana; primária) e k = 0 / 6 (sensibilidade).
# Cobertura do padrão: 168–300 dias -> SEMAGESTAC 24–42 em todas as convenções; 22–23 e 43–44 ficam fora.
# Também grava o P10 oficial (tabela PDF interpolada no mesmo dia) para a sensibilidade "tabela oficial".
set.seed(42)
suppressMessages({library(gigs); library(arrow)})
proj <- Sys.getenv("PTB_PROJ", getwd())  # 9a: raiz do projeto (rodar da raiz ou definir PTB_PROJ)
stamp <- "20261008"
logf <- file.path(proj, "outputs/logs", paste0("etapa1_", stamp, ".log"))
log <- function(m) { l <- sprintf("[%s] [02b_pig_grade] %s", format(Sys.time(), "%Y-%m-%d %H:%M:%S"), m)
  cat(l, "\n"); cat(l, "\n", file = logf, append = TRUE) }

g <- expand.grid(SEMAGESTAC = 24:42, SEXO = 1:2, PESO = 100:7000)
sx <- ifelse(g$SEXO == 1, "M", "F")
for (k in c(0, 3, 6)) {
  g[[paste0("centil_k", k)]] <- gigs::value2centile(y = g$PESO / 1000, x = 7 * g$SEMAGESTAC + k, sex = sx,
                                                    family = "ig_nbs", acronym = "wfga")
}
ref <- read.csv(file.path(proj, "docs/referencias/intergrowth21_bw_centis_oficial.csv"))
p10 <- ref[ref$centil == 10, ]
p10$SEXO <- ifelse(p10$sexo == "M", 1L, 2L)
p10$SEMAGESTAC <- p10$semanas
p10 <- p10[p10$dias == 3, c("SEMAGESTAC", "SEXO", "peso_kg")]
names(p10)[3] <- "p10_oficial_kg_k3"
g <- merge(g, p10, by = c("SEMAGESTAC", "SEXO"), all.x = TRUE)
stopifnot(!anyNA(g$p10_oficial_kg_k3), !anyNA(g$centil_k3))
# limiar do gigs no P10 (k = 3) e checagem de monotonicidade: centil < 0.1  <=>  PESO < limiar
thr <- unique(data.frame(SEMAGESTAC = g$SEMAGESTAC, SEXO = g$SEXO))
thr$p10_gigs_kg_k3 <- gigs::centile2value(p = 0.1, x = 7 * thr$SEMAGESTAC + 3, sex = ifelse(thr$SEXO == 1, "M", "F"),
                                          family = "ig_nbs", acronym = "wfga")
g <- merge(g, thr, by = c("SEMAGESTAC", "SEXO"))
incons <- sum((g$centil_k3 < 0.1) != (g$PESO / 1000 < g$p10_gigs_kg_k3))
log(sprintf("grade: %d linhas; inconsistências centil<0.1 vs PESO<limiar: %d", nrow(g), incons))
write_parquet(g, file.path(proj, "data/processed", paste0("pig_grade_intergrowth_v1_", stamp, ".parquet")))
write.csv(thr[order(thr$SEXO, thr$SEMAGESTAC), ], file.path(proj, "outputs/tables",
          paste0("tab_e1_pig_limiares_p10_v1_", stamp, ".csv")), row.names = FALSE)
log("grade e limiares P10 gravados")
