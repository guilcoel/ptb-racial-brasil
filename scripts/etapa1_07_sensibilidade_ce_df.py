"""
1.7 Sensibilidade sem CE e DF (as duas UFs com pior completude de RACACORMAE na Etapa 0).
Compara prevalências de 1.4(a) e RP brutas de 1.5(c) com e sem CE/DF.
Pré-requisito: etapa1_04_prevalencias.py e etapa1_05b_rp_brutas.py rodados com e sem --sem-ce-df.
Saídas: tab_e1_07_sens_prev, tab_e1_07_sens_rp.
"""
import pandas as pd

import etapa1_lib as E

log = E.logger("07_sens_ce_df")
T = E.L.TAB
S = E.L.STAMP
pa = pd.read_csv(T / f"tab_e1_04_prevalencias_v1_{S}.csv")
pb = pd.read_csv(T / f"tab_e1_04_prevalencias_semCEDF_v1_{S}.csv")
k = ["estrato", "nivel", "raca", "desfecho"]
p = pa[pa.estrato.isin(["regiao", "brasil"])].merge(pb, on=k, suffixes=("", "_sem"))
p["dif_pp"] = p.prev_pct_sem - p.prev_pct
p.to_csv(T / f"tab_e1_07_sens_prev_v1_{S}.csv", index=False)

ra = pd.read_csv(T / f"tab_e1_05c_rp_or_da_brutas_v1_{S}.csv")
rb = pd.read_csv(T / f"tab_e1_05c_rp_or_da_brutas_semCEDF_v1_{S}.csv")
r = ra[ra.medida == "RP"].merge(rb[rb.medida == "RP"], on=["desfecho", "regiao", "raca", "medida"], suffixes=("", "_sem"))
r["var_rel_pct"] = 100 * (r.est_sem / r.est - 1)
r.to_csv(T / f"tab_e1_07_sens_rp_v1_{S}.csv", index=False)

main = ["ptb", "lbw_termo", "pig"]
x = p[p.desfecho.isin(main)]
log(f"prevalências raça×região (ptb/lbw/pig): máx |Δ| = {x.dif_pp.abs().max():.2f} p.p. "
    f"({x.loc[x.dif_pp.abs().idxmax(), ['desfecho', 'nivel', 'raca']].tolist()})")
y = r[r.desfecho.isin(main)]
log(f"RP brutas (ptb/lbw/pig): máx |variação relativa| = {y.var_rel_pct.abs().max():.1f}% "
    f"({y.loc[y.var_rel_pct.abs().idxmax(), ['desfecho', 'regiao', 'raca']].tolist()})")
for _, z in y[y.regiao == "Brasil"].iterrows():
    log(f"Brasil {z.desfecho} {z.raca}: RP {z.est:.2f} ({z.lo:.2f}–{z.hi:.2f}) -> {z.est_sem:.2f} ({z.lo_sem:.2f}–{z.hi_sem:.2f})")
