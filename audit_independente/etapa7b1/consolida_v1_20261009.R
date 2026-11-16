library(data.table)
a <- fread("auditor_ADE_v1_20261009.csv")
b <- fread("auditor_B_cascata_v1_20261009.csv")
cc <- fread("auditor_C_auc_v1_20261009.csv")
exc <- b[item != "passo_0"]
B <- data.table(tarefa="B", item=c("excl_total","excl_ig22_44","excl_ig22_44_lt37","excl_pct_lt37","incl_n","incl_ptb","incl_pct_ptb"),
  valor=c(sum(exc$n), sum(exc$n_ig_valida), sum(exc$n_ptb), 100*sum(exc$n_ptb)/sum(exc$n_ig_valida), b[item=="passo_0",n], b[item=="passo_0",n_ptb], 100*b[item=="passo_0",n_ptb]/b[item=="passo_0",n]), extra="")
cc[, tp := fifelse(tipo=="fixa","fixa","fixa_aleat")]
C <- cc[modelo=="m2", .(tarefa="C", item=c(paste0("m2_AUC_",tp), paste0("m2_AUC_",tp,"_lo"), paste0("m2_AUC_",tp,"_hi")), valor=c(auc,lo,hi), extra="desfecho do m2 = PIG (casos 2,347,145)")]
v <- rbind(a, B, C, fill=TRUE)
v[, gravado_em := format(Sys.time(), "%Y-%m-%d %H:%M:%S")]
fwrite(v, "auditor_valores_v1_20261009.csv")
print(v[, .(tarefa, item, valor=format(valor, digits=8), extra)], nrows=200)
