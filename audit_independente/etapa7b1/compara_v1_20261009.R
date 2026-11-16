# Auditoria 7b1 - comparacao auditor x autor
library(data.table)
T <- "outputs/tables/"; D <- "audit_independente/etapa7b1/"
au <- fread(paste0(D,"auditor_valores_v1_20261009.csv")); ex <- fread(paste0(D,"auditor_extras_pos_leitura_v1_20261009.csv"))
bc <- fread(paste0(D,"auditor_B_cascata_v1_20261009.csv")); cc <- fread(paste0(D,"auditor_C_auc_v1_20261009.csv"))
A <- function(it) au[item==it, valor]; X <- function(it) ex[item==it, valor]
i01 <- fread(paste0(T,"tab_e7b1_01_cenarios_interacao_v1_20261008.csv")); w01 <- fread(paste0(T,"tab_e7b1_01_cenarios_wald_v1_20261008.csv"))
s02 <- fread(paste0(T,"tab_e7b1_02_s1_restrito_v1_20261008.csv")); c03 <- fread(paste0(T,"tab_e7b1_03_auc_fixa_v1_20261008.csv"))
i04 <- fread(paste0(T,"tab_e7b1_04_interacao_v1_20261008.csv")); m04 <- fread(paste0(T,"tab_e7b1_04_m2_v1_20261008.csv"))
n04 <- fread(paste0(T,"tab_e7b1_04_naoclass_v1_20261008.csv")); w04 <- fread(paste0(T,"tab_e7b1_04_wald_v1_20261008.csv"))
r05 <- fread(paste0(T,"tab_e7b1_05_reri_recod_v1_20261008.csv"))
L <- list(); cmp <- function(tar, it, a, b) L[[length(L)+1]] <<- data.table(tarefa=tar, item=it, auditor=a, autor=b)
mapA <- c(DUM="so_DUM", outro_metodo="so_outro_metodo", sem_CE_DF="sem_CE_DF", sem_2024="sem_2024")
for (k in names(mapA)) { r <- i01[sensibilidade==mapA[k] & raca=="Indigena" & nivel=="T1"]; w <- w01[sensibilidade==mapA[k]]
  cmp("A", paste0(k,"_N"), A(paste0(k,"_N")), w$N); cmp("A", paste0(k,"_G"), A(paste0(k,"_G")), w$G)
  cmp("A", paste0(k,"_ICR_Ind_T1"), A(paste0(k,"_ICR_Ind_T1")), r$ICR_pp)
  cmp("A", paste0(k,"_ICR_Ind_T1_lo"), A(paste0(k,"_ICR_Ind_T1_lo")), r$ICR_lo); cmp("A", paste0(k,"_ICR_Ind_T1_hi"), A(paste0(k,"_ICR_Ind_T1_hi")), r$ICR_hi)
  cmp("A", paste0(k,"_Wald_chi2"), A(paste0(k,"_Wald_chi2")), w$chi2); cmp("A", paste0(k,"_Wald_p"), A(paste0(k,"_Wald_p")), w$p)
  for (g in c("Parda","Preta","Indigena")) for (tk in c("T1","T2")) if (!(g=="Indigena" & tk=="T1"))
    cmp("A_extra", paste0(k,"_ICR_",g,"_",tk), X(paste0("A_",k,"_ICR_",g,"_",tk)), i01[sensibilidade==mapA[k] & raca==g & nivel==tk, ICR_pp]) }
br <- s02[regiao=="Brasil"]; ex_ <- bc[item!="passo_0"]
cmp("B","excl_total", sum(ex_$n), br[grupo=="excluidos", n]); cmp("B","excl_ig22_44", sum(ex_$n_ig_valida), br[grupo=="excluidos", n_ig_22_44])
cmp("B","excl_ig22_44_lt37", sum(ex_$n_ptb), br[grupo=="excluidos", n_ptb_22_44]); cmp("B","excl_pct_lt37", A("excl_pct_lt37"), br[grupo=="excluidos", ptb_pct_22_44])
cmp("B","incl_n", A("incl_n"), br[grupo=="incluidos", n]); cmp("B","incl_ptb", A("incl_ptb"), br[grupo=="incluidos", n_ptb_22_44]); cmp("B","incl_pct_ptb", A("incl_pct_ptb"), br[grupo=="incluidos", ptb_pct_22_44])
for (p in 1:4) { g <- c("excluidos_1_raca","excluidos_2_ig","excluidos_3_esc","excluidos_4_idade")[p]
  cmp("B_extra", paste0(g,"_n"), bc[item==paste0("passo_",p), n], br[grupo==g, n]); cmp("B_extra", paste0(g,"_ig22_44"), bc[item==paste0("passo_",p), n_ig_valida], br[grupo==g, n_ig_22_44]); cmp("B_extra", paste0(g,"_lt37"), bc[item==paste0("passo_",p), n_ptb], br[grupo==g, n_ptb_22_44]) }
f2 <- cc[modelo=="m2" & tipo=="fixa"]; c2 <- cc[modelo=="m2" & tipo=="fixa+aleat"]; c1 <- cc[modelo=="m1" & tipo=="fixa+aleat"]
cmp("C","m2_AUC_fixa", f2$auc, c03[modelo=="m2", AUC_parte_fixa]); cmp("C","m2_AUC_fixa_lo", f2$lo, c03[modelo=="m2", AUC_fixa_lo]); cmp("C","m2_AUC_fixa_hi", f2$hi, c03[modelo=="m2", AUC_fixa_hi])
cmp("C_extra","m2_AUC_condicional", c2$auc, c03[modelo=="m2", AUC_condicional]); cmp("C_extra","m1_AUC_condicional", c1$auc, c03[modelo=="m1", AUC_condicional])
cmp("D","semclass_analitica", A("semclass_analitica"), n04[amostra=="analitica", sum(nao_classificados)]); cmp("D","semclass_com_regsaud", A("semclass_com_regsaud"), n04[amostra=="com_regiao_saude", sum(nao_classificados)])
cen <- c(i_todos_indicados="i", ii_todos_espontaneos="ii")
for (k in names(cen)) { for (o in c("ind","esp")) { r <- m04[cenario==k & desfecho==paste0("ptb_",o) & raca=="Indigena"]
    cmp("D", paste0(k,"_PR_M2_ptb_",o), A(paste0(k,"_PR_M2_ptb_",o)), r$PR); cmp("D", paste0(k,"_PR_M2_ptb_",o,"_lo"), A(paste0(k,"_PR_M2_ptb_",o,"_lo")), r$PR_lo); cmp("D", paste0(k,"_PR_M2_ptb_",o,"_hi"), A(paste0(k,"_PR_M2_ptb_",o,"_hi")), r$PR_hi)
    for (g in c("Parda","Preta")) cmp("D_extra", paste0(k,"_PR_M2_ptb_",o,"_",g), X(paste0("D_",cen[k],"_PR_M2_ptb_",o,"_",g)), m04[cenario==k & desfecho==paste0("ptb_",o) & raca==g, PR])
    cmp("D_extra", paste0(k,"_Wald_ptb_",o), X(paste0("D_",cen[k],"_wald_ptb_",o)), w04[sensibilidade==k & desfecho==paste0("ptb_",o,"__",k), chi2])
    for (g in c("Parda","Preta","Indigena")) for (tk in c("T1","T2")) if (!(o=="ind" & g=="Indigena" & tk=="T1"))
      cmp("D_extra", paste0(k,"_ICR_ptb_",o,"_",g,"_",tk), X(paste0("D_",cen[k],"_ICR_ptb_",o,"_",g,"_",tk)), i04[sensibilidade==k & desfecho==paste0("ptb_",o,"__",k) & raca==g & nivel==tk, ICR_pp]) }
  r <- i04[sensibilidade==k & desfecho==paste0("ptb_ind__",k) & raca=="Indigena" & nivel=="T1"]
  cmp("D", paste0(k,"_ICR_Ind_T1_ptb_ind"), A(paste0(k,"_ICR_Ind_T1_ptb_ind")), r$ICR_pp)
  cmp("D", paste0(k,"_ICR_Ind_T1_ptb_ind_lo"), A(paste0(k,"_ICR_Ind_T1_ptb_ind_lo")), r$ICR_lo); cmp("D", paste0(k,"_ICR_Ind_T1_ptb_ind_hi"), A(paste0(k,"_ICR_Ind_T1_ptb_ind_hi")), r$ICR_hi) }
for (pp in list(c("Indigena","T1"), c("Indigena","T2"), c("Parda","T1"))) { k <- paste0(pp[1],"_",pp[2]); r <- r05[raca==pp[1] & nivel==pp[2]]
  cmp("E", paste0(k,"_RERI"), A(paste0(k,"_RERI")), r$RERI_recod); cmp("E", paste0(k,"_RERI_lo"), A(paste0(k,"_RERI_lo")), r$lo); cmp("E", paste0(k,"_RERI_hi"), A(paste0(k,"_RERI_hi")), r$hi)
  cmp("E", paste0(k,"_ref_igual(1=sim)"), 1, as.numeric(r$referencia == paste0(pp[1],"-",pp[2]))) }
for (g in c("Parda","Preta","Indigena")) for (tk in c("T1","T2")) { r <- r05[raca==g & nivel==tk]
  if (!(paste0(g,tk) %in% c("IndigenaT1","IndigenaT2","PardaT1"))) cmp("E_extra", paste0(g,"_",tk,"_RERI_recod"), ex[grepl(paste0("E_RERIrecod_",g,"_",tk), item), valor], r$RERI_recod)
  cmp("E_extra", paste0(g,"_",tk,"_RERI_original"), X(paste0("E_RERIorig_",g,"_",tk)), r$RERI_original) }
out <- rbindlist(L)
out[, dif := auditor - autor]; out[, dif_rel := fifelse(autor != 0, dif/abs(autor), NA_real_)]
fwrite(out, paste0(D,"comparacao_7b1_v1_20261009.csv"))
cat("itens:", nrow(out), " max|dif_rel| estimativas pontuais (sem _lo/_hi):", out[!grepl("_lo$|_hi$", item), max(abs(dif_rel), na.rm=TRUE)],
    " max|dif_rel| limites IC:", out[grepl("_lo$|_hi$", item), max(abs(dif_rel), na.rm=TRUE)], "\n")
print(out[abs(dif_rel) > 1e-6 | is.na(dif_rel)], nrows=200)
# razao das meia-larguras (autor/auditor) nos IC: deve ser qnorm(.975)/1.96 se o autor usa z exato
hw <- merge(out[grepl("_hi$", item), .(base=sub("_hi$","",item), a_hi=auditor, b_hi=autor)], out[!grepl("_lo$|_hi$", item), .(base=item, a=auditor, b=autor)], by="base")
hw <- hw[!grepl("PR_M2", base)]; hw[, razao := (b_hi-b)/(a_hi-a)]
pr <- merge(out[grepl("PR_M2.*_hi$", item), .(base=sub("_hi$","",item), a_hi=auditor, b_hi=autor)], out[grepl("PR_M2", item) & !grepl("_lo$|_hi$", item), .(base=item, a=auditor, b=autor)], by="base")
pr[, razao := log(b_hi/b)/log(a_hi/a)]
print(rbind(hw[, .(base, razao)], pr[, .(base, razao)])); cat("qnorm(.975)/1.96 =", qnorm(.975)/1.96, "\n")
