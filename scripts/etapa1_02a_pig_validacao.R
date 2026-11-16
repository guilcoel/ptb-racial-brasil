# 1.2 PIG (INTERGROWTH-21st) — validação da implementação contra as tabelas oficiais.
#
# Implementação: pacote R gigs (LSHTM, github.com/lshtm-gigs/gigs, v0.5.2.9000),
#   família "ig_nbs", acrônimo "wfga" (peso para IG), 168–300 dias (24+0 a 42+6 sem),
#   incluindo o padrão de muito prematuro (Villar 2016) e o padrão de RN (Villar 2014).
# Cruzamento: growthstandards (ki-tools, v0.1.7), igb_centile2wtkg.
# Referência externa: tabelas oficiais de centis de peso ao nascer (kg, 2 casas), intergrowth21.com,
#   baixadas em 2026-10-08 para docs/referencias/ e convertidas em intergrowth21_bw_centis_oficial.csv.
# Saídas: tab_e1_pig_validacao_oficial (todos os pontos), tab_e1_pig_validacao_amostra20 (20 sorteados, seed 42).
set.seed(42)
suppressMessages({library(gigs); library(growthstandards)})
proj <- Sys.getenv("PTB_PROJ", getwd())  # 9a: raiz do projeto (rodar da raiz ou definir PTB_PROJ)
stamp <- "20261008"
logf <- file.path(proj, "outputs/logs", paste0("etapa1_", stamp, ".log"))
log <- function(m) { l <- sprintf("[%s] [02a_pig_validacao] %s", format(Sys.time(), "%Y-%m-%d %H:%M:%S"), m)
  cat(l, "\n"); cat(l, "\n", file = logf, append = TRUE) }

ref <- read.csv(file.path(proj, "docs/referencias/intergrowth21_bw_centis_oficial.csv"))
log(sprintf("tabela oficial: %d pontos, IG %d–%d dias", nrow(ref), min(ref$gest_days), max(ref$gest_days)))

ref$gigs_kg <- gigs::centile2value(p = ref$centil / 100, x = ref$gest_days, sex = ref$sexo,
                                   family = "ig_nbs", acronym = "wfga")
ref$gs_kg <- igb_centile2wtkg(ref$gest_days, ref$centil, sex = ifelse(ref$sexo == "M", "Male", "Female"))
ref$gigs_kg_2c <- round(ref$gigs_kg, 2)
ref$dif_kg <- round(ref$gigs_kg_2c - ref$peso_kg, 2)
ref$bate <- ref$dif_kg == 0
ref$dif_gigs_vs_gs <- abs(ref$gigs_kg - ref$gs_kg)
# centil devolvido pelo gigs no peso oficial (o peso oficial está arredondado a 10 g)
ref$gigs_centil_no_peso_oficial <- 100 * gigs::value2centile(y = ref$peso_kg, x = ref$gest_days, sex = ref$sexo,
                                                             family = "ig_nbs", acronym = "wfga")
write.csv(ref, file.path(proj, "outputs/tables", paste0("tab_e1_pig_validacao_oficial_v1_", stamp, ".csv")), row.names = FALSE)

log(sprintf("gigs = oficial (2 casas): %d/%d; |dif| máx = %.2f kg", sum(ref$bate), nrow(ref), max(abs(ref$dif_kg))))
log(sprintf("gigs vs growthstandards: |dif| máx = %.2e kg", max(ref$dif_gigs_vs_gs)))
nb <- ref[!ref$bate, ]
if (nrow(nb) > 0) log(sprintf("não batem: %s", paste(sprintf("%s %d+%d c%d of=%.2f gigs=%.4f",
  nb$sexo, nb$semanas, nb$dias, nb$centil, nb$peso_kg, nb$gigs_kg), collapse = "; ")))

am <- ref[sample(nrow(ref), 20), c("sexo", "semanas", "dias", "gest_days", "centil", "peso_kg",
                                    "gigs_kg", "gigs_kg_2c", "bate", "gigs_centil_no_peso_oficial")]
write.csv(am, file.path(proj, "outputs/tables", paste0("tab_e1_pig_validacao_amostra20_v1_", stamp, ".csv")), row.names = FALSE)
log(sprintf("amostra de 20 (seed 42): %d/20 batem", sum(am$bate)))
