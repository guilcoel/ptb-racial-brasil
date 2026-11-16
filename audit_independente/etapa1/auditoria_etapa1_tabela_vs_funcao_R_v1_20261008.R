# Compara P10 oficial (PDF) com growthstandards e gigs em todos os dias 168-300 (sem dados de caso)
suppressPackageStartupMessages({library(data.table); library(growthstandards); library(gigs)})
OUT <- "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa1/"
t <- fread(paste0(OUT,"ig21_bw_centis_extraidos_pdf_v1_20261008.csv"))
t[, p10_gs := igb_centile2value(ig_dias, p=10, var="wtkg", sex=fifelse(sexo=="M","Male","Female"))]
t[, p10_gigs := centile2value(0.10, ig_dias, sexo, family="ig_nbs", acronym="wfga")]
t[, d_gs := 1000*(p10_gs-p10)][, d_gigs := 1000*(p10_gigs-p10)]
print(t[, .(max_abs_gs=max(abs(d_gs),na.rm=T), na_gs=sum(is.na(d_gs)), max_abs_gigs=max(abs(d_gigs),na.rm=T), na_gigs=sum(is.na(d_gigs)),
            dias_gt5g_gs=sum(abs(d_gs)>5,na.rm=T), dias_gt5g_gigs=sum(abs(d_gigs)>5,na.rm=T)), by=tabela])
fwrite(t, paste0(OUT,"D_tabela_oficial_vs_funcoes_p10_v1_20261008.csv"))
