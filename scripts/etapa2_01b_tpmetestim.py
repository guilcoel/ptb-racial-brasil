"""
2.1 TPMETESTIM: distribuição de códigos e completude por ano e macrorregião (amostra analítica e todos os nascidos).
Válido = 1, 2 ou 8 (8 = IG pela DUM, ver etapa2_01_base_v3.py); incompleto = 9 ou nulo.
Saída: tab_e2_01_tpmetestim_ano_regiao.
"""
import pandas as pd

import etapa0_lib as L

log = L.Logger("01b_tpmetestim", etapa="etapa2")
d = pd.read_parquet(L.PROC / f"sinasc_brasil_2015_2024_v3_{L.STAMP}", columns=["incl", "ano", "regiao", "TPMETESTIM"])
d["cod"] = d.TPMETESTIM.astype("Int64").astype("string").fillna("nulo")
rows = []
for univ, s in [("todos", d), ("amostra", d[d.incl])]:
    for reg_name, ss in [("Brasil", s)] + [(r, s[s.regiao == r]) for r in L.REGIOES]:
        t = pd.crosstab(ss.ano, ss.cod)
        for c in ["1", "2", "8", "9", "nulo"]:
            if c not in t:
                t[c] = 0
        n = t.sum(axis=1)
        for y in t.index:
            rows.append(dict(universo=univ, regiao=reg_name, ano=y, n=int(n[y]),
                             **{f"pct_{c}": round(100 * t.loc[y, c] / n[y], 2) for c in ["1", "2", "8", "9", "nulo"]},
                             pct_completo=round(100 * (t.loc[y, "1"] + t.loc[y, "2"] + t.loc[y, "8"]) / n[y], 2)))
out = pd.DataFrame(rows)
out.to_csv(L.TAB / f"tab_e2_01_tpmetestim_ano_regiao_v1_{L.STAMP}.csv", index=False)
a = out[(out.universo == "amostra")]
log("completude TPMETESTIM (amostra), Brasil por ano: " + ", ".join(f"{r.ano}={r.pct_completo}" for r in a[a.regiao == "Brasil"].itertuples()))
