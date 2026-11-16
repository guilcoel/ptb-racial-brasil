# P97 INTERGROWTH-21st pela equação (pacote growthstandards, NÃO gigs) para comparar com a tabela oficial.
suppressMessages(library(growthstandards))
OUT <- "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa4b"
tab <- read.csv(file.path(OUT, "p97_intergrowth_tabela_v1_20261008.csv"))
tab$p97_eq_kg <- mapply(function(s, d) igb_centile2value(d, 97, var = "wtkg", sex = ifelse(s == 1, "Male", "Female")),
                        tab$sexo, tab$dias)
tab$dif_g <- 1000 * (tab$p97_kg - tab$p97_eq_kg)
write.csv(tab, file.path(OUT, "p97_tabela_vs_equacao_v1_20261008.csv"), row.names = FALSE)
cat("Todos os dias 168-300: |tabela - equação| máx (g) =", round(max(abs(tab$dif_g)), 2), "\n")
for (rng in list(c(168, 230), c(231, 300))) {
  s <- tab[tab$dias >= rng[1] & tab$dias <= rng[2], ]
  cat(sprintf("dias %d-%d: máx |dif| = %.2f g; n dias |dif|>5 g = %d\n", rng[1], rng[2], max(abs(s$dif_g)), sum(abs(s$dif_g) > 5)))
}
u <- tab[tab$dias %in% (7 * (24:36) + 3), ]
u$sg <- (u$dias - 3) / 7
print(u[, c("sexo", "sg", "dias", "p97_kg", "p97_eq_kg", "dif_g")], row.names = FALSE, digits = 6)
