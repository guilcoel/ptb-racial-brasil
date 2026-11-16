"""
6.1(d) Quadro: ICR-chave com IC por município (Etapas 3, 4, 4b) × IC por região de saúde (Etapa 6.1), com a classificação
de etapa4_lib.classifica (mantém / enfraquece / inverte; achado D: mantém se o IC inclui 0, senão muda), aplicada ao resultado
por região de saúde em relação ao por município.
Saída: tab_e6_01d_quadro.
"""
import pandas as pd

import etapa4_lib as S4
import etapa6_lib as E6
import etapa0_lib as L

log = E6.logger("01d_quadro")
TB, S = L.TAB, L.STAMP
rd = lambda f: pd.read_csv(TB / f"{f}_v1_{S}.csv")
ACH = {"pig": "A", "pig_k0": "A", "pig_k6": "A", "ptb_ind": "B", "ptb_esp": "C", "ptb_esp_plaus_b": "C", "ptb_esp_plaus_a": "C",
       "ptb": "D", "ptb_plaus_b": "D", "ptb_plaus_a": "D"}
K = ["desfecho", "raca", "nivel"]
pares = []
o = rd("tab_e3_02_interacao").query("analise == '3.2_tercil_reg' and estrato == 'Brasil'")
pares.append(("3.2 principal", o, rd("tab_e6_01a_interacao")))
orig = pd.concat([rd("tab_e4_01b_interacao"), rd("tab_e4_02_interacao"),
                  rd("tab_e4b_03_interacao").replace({"sensibilidade": {"4b.3": "4b.3_plausivel"}})])
nb = rd("tab_e6_01b_interacao")
for sens in nb.sensibilidade.unique():
    pares.append((sens, orig[orig.sensibilidade == sens], nb[nb.sensibilidade == sens]))
pares.append(("4.6_imputacao_multipla", rd("tab_e4_06_mi_rubin"), rd("tab_e4_06_mi_rubin_rs")))
rows = []
for rot, a, b in pares:
    m = a.merge(b, on=K, suffixes=("_mun", "_rs"))
    m = m[(m.nivel == "T1") & ((m.raca == "Indigena") | ((m.raca == "Parda") & (m.desfecho == "ptb_ind")))]
    for _, r in m.iterrows():
        if r.desfecho not in ACH:
            continue
        ach = ACH[r.desfecho]
        om = dict(ICR_pp=r.ICR_pp_mun, ICR_lo=r.ICR_lo_mun, ICR_hi=r.ICR_hi_mun)
        nr = dict(ICR_pp=r.ICR_pp_rs, ICR_lo=r.ICR_lo_rs, ICR_hi=r.ICR_hi_rs)
        rows.append(dict(achado=ach, analise=rot, desfecho=r.desfecho, termo=f"{r.raca}×T1",
                         ICR_municipio=f"{r.ICR_pp_mun:.2f} ({r.ICR_lo_mun:.2f} a {r.ICR_hi_mun:.2f})",
                         ICR_regsaude=f"{r.ICR_pp_rs:.2f} ({r.ICR_lo_rs:.2f} a {r.ICR_hi_rs:.2f})",
                         razao_largura=(r.ICR_hi_rs - r.ICR_lo_rs) / (r.ICR_hi_mun - r.ICR_lo_mun),
                         classe_municipio=S4.classifica(ach, om, om) if ach == "D" else ("IC exclui 0" if r.ICR_lo_mun > 0 or r.ICR_hi_mun < 0 else "IC inclui 0"),
                         classe_regsaude_vs_municipio=S4.classifica(ach, om, nr)))
Q = pd.DataFrame(rows).sort_values(["achado", "analise", "desfecho", "termo"])
Q.to_csv(TB / f"tab_e6_01d_quadro_v1_{S}.csv", index=False)
log("quadro 6.1(d):\n" + Q.round(2).to_string(index=False))
log("contagem: " + Q.groupby(["achado", "classe_regsaude_vs_municipio"]).size().to_string().replace("\n", " | "))
