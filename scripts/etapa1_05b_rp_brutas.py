"""
1.5c RP, OR e diferença absoluta (p.p.) BRUTAS de cada raça vs Branca, por estimação agregada
(raça × município; etapa1_lib.fit_agg, validada no CO em etapa1_05a), EP clusterizado por CODMUNRES.
Desfechos: ptb, ptb_extremo, ptb_muito, ptb_mod_tardio, lbw_termo, pig; Brasil e cada região.
Sensibilidade do PIG (Brasil): pig_k0, pig_k6, pig_tabela_oficial.
Argumento opcional --sem-ce-df (1.7).
Saídas: tab_e1_05c_rp_or_da_brutas (longa), tab_e1_05c_rp_brutas_fmt.
"""
import sys

import numpy as np
import pandas as pd

import etapa1_lib as E

SENS = "--sem-ce-df" in sys.argv
SUF = "_semCEDF" if SENS else ""
log = E.logger("05b_rp_brutas" + SUF)
d = E.load(["raca", "regiao", "uf", "CODMUNRES", "ptb", "ptb_sub", "lbw_termo", "pig", "pig_k0", "pig_k6",
            "pig_tabela_oficial"])
if SENS:
    d = d[~d.uf.isin(["CE", "DF"])]
d["raca"] = d.raca.cat.remove_unused_categories()
d["ptb_extremo"] = (d.ptb_sub == "1_extremo_lt28").astype(int)
d["ptb_muito"] = (d.ptb_sub == "2_muito_28a31").astype(int)
d["ptb_mod_tardio"] = (d.ptb_sub == "3_moderado_tardio_32a36").astype(int)
log("amostra", len(d))
RHS = "C(raca, Treatment('Branca'))"
PREF = RHS + "[T."
OUT = ["ptb", "ptb_extremo", "ptb_muito", "ptb_mod_tardio", "lbw_termo", "pig"]
JOBS = [(o, r) for o in OUT for r in ["Brasil"] + E.L.REGIOES] + \
       [(o, "Brasil") for o in ("pig_k0", "pig_k6", "pig_tabela_oficial")]

rows = []
for desf, reg in JOBS:
    s = d if reg == "Brasil" else d[d.regiao == reg]
    cells = E.agrega(s, desf, ["raca"])
    assert int(cells.n.sum()) == int(s[desf].notna().sum()) and int(cells.Y.sum()) == int(s[desf].sum())
    fits = {"RP": E.fit_agg(cells, RHS, "poisson"), "OR": E.fit_agg(cells, RHS, "logit"),
            "DA_pp": E.fit_agg(cells, RHS, "identity")}
    for med, fit in fits.items():
        for t in E.termos(fit, PREF, cov="cluster", expo=(med != "DA_pp")):
            k = 100 if med == "DA_pp" else 1
            rows.append(dict(desfecho=desf, regiao=reg, raca=t["termo"].split("[T.")[1].rstrip("]"), medida=med,
                             est=k * t["est"], lo=k * t["lo"], hi=k * t["hi"], p=t["p"],
                             n_celulas=fit["n_cells"], N=int(fit["N"]), n_municipios=fit["G"]))
    log(f"{desf} {reg}: N={int(fits['RP']['N']):,}, municípios={fits['RP']['G']:,}")

t = pd.DataFrame(rows)
t.to_csv(E.L.TAB / f"tab_e1_05c_rp_or_da_brutas{SUF}_v1_{E.L.STAMP}.csv", index=False)
t["valor"] = t.est.map(lambda v: E.fmt_f(v, 2)) + " (" + t.lo.map(lambda v: E.fmt_f(v, 2)) + "–" + \
             t.hi.map(lambda v: E.fmt_f(v, 2)) + ")"
w = t.pivot_table(index=["medida", "desfecho", "raca"], columns="regiao", values="valor", aggfunc="first")
w = w[["Brasil"] + E.L.REGIOES]
w.to_csv(E.L.TAB / f"tab_e1_05c_rp_brutas_fmt{SUF}_v1_{E.L.STAMP}.csv")
log("tabelas gravadas")
