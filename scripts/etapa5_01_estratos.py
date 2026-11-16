"""
5.1 Estratos interseccionais para o MAIHDA do PIG.
Amostra: PIG elegível (pig não nulo = única, 24–42 sem, sexo e peso válidos; INTERGROWTH gigs, IG = sem×7+3), menos os
sem região de saúde (sem tercil; mesmo recorte da 3.2).
Estrato = raça (4) × escolaridade (≤7: ESCMAE 1–3; 8–11: 4; ≥12: 5) × idade (<20, 20–34, ≥35) × macrorregião (5)
× tercil de acesso dentro da região (T1–T3, ano t−1) → até 540.
Saídas (só agregados): maihda_estratos (estrato), maihda_estratos_ano (estrato × ano), maihda_estratos_outro
(ig_metodo = outro_metodo), tab_e5_01_estratos_tamanho, tab_e5_01_estratos_pequenos.
"""
import numpy as np
import pandas as pd

import etapa3_lib as T
import etapa0_lib as L

log = L.Logger("01_estratos", etapa="etapa5")
d = T.anexa_acesso(T.load(["raca", "idade_cat", "esc_cat", "regiao", "CO_REGSAUD", "pig", "ig_metodo"]))
d = d[d.pig.notna()]
log(f"PIG elegível: {len(d):,}; casos {int(d.pig.sum()):,}")
d = d[d.tercil_reg.notna()].copy()
log(f"com tercil (região de saúde): {len(d):,}; casos {int(d.pig.sum()):,}")
ESC = {"1_nenhuma": "le7", "2_1a3anos": "le7", "3_4a7anos": "le7", "4_8a11anos": "8a11", "5_12mais": "ge12"}
IDA = {"<20": "lt20", "20-34": "20a34", ">=35": "ge35"}
d["esc3"] = d.esc_cat.astype(str).map(ESC)
d["idade3"] = d.idade_cat.astype(str).map(IDA)
assert d.esc3.notna().all() and d.idade3.notna().all()
d["raca"] = d.raca.astype(str)
d["regiao"] = d.regiao.astype(str)
d["tercil"] = d.tercil_reg.astype(str)
d["ig_metodo"] = d.ig_metodo.astype(str)
K = ["raca", "esc3", "idade3", "regiao", "tercil"]
d["estrato"] = d[K].agg("|".join, axis=1)
d["pig"] = d.pig.astype(int)


def agg(x, by):
    a = x.groupby(by, observed=True).pig.agg(n="size", casos="sum").reset_index()
    a[K] = a.estrato.str.split("|", expand=True)
    return a


S = L.STAMP
a = agg(d, ["estrato"])
a.to_csv(L.PROC / f"maihda_estratos_v1_{S}.csv", index=False)
agg(d, ["estrato", "ano"]).to_csv(L.PROC / f"maihda_estratos_ano_v1_{S}.csv", index=False)
o = agg(d[d.ig_metodo == "outro_metodo"], ["estrato"])
o.to_csv(L.PROC / f"maihda_estratos_outro_v1_{S}.csv", index=False)
assert int(a.n.sum()) == len(d) and int(a.casos.sum()) == int(d.pig.sum())

q = a.n.quantile([0, .1, .25, .5, .75, .9, 1]).round().astype(int)
tam = pd.DataFrame(dict(estatistica=["n_estratos", "n_possiveis", "min", "P10", "P25", "mediana", "P75", "P90", "max",
                                     "n_lt100", "casos_lt10", "N", "casos"],
                        valor=[len(a), 540, *q.tolist(), int((a.n < 100).sum()), int((a.casos < 10).sum()), len(d), int(d.pig.sum())]))
tam.to_csv(L.TAB / f"tab_e5_01_estratos_tamanho_v1_{S}.csv", index=False)
pq = a[(a.n < 100) | (a.casos < 10)].sort_values("n")
pq.assign(pct=lambda x: 100 * x.casos / x.n).to_csv(L.TAB / f"tab_e5_01_estratos_pequenos_v1_{S}.csv", index=False)
log("tamanho dos estratos:\n" + tam.to_string(index=False))
log(f"estratos com n < 100 ou casos < 10: {len(pq)}\n" + pq.to_string(index=False))
log(f"ig_metodo outro: {len(o)} estratos; N = {int(o.n.sum()):,}; casos = {int(o.casos.sum()):,}; min n = {o.n.min()}")
