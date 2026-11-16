"""
4b.1 Plausibilidade peso × IG entre os prematuros e 4b.2 distribuição da IG por método.

4b.1 População: amostra analítica, gestação única (GRAVIDEZ 1), SEMAGESTAC 24–36, SEXO 1/2, PESO 100–7000.
  (a) PESO ≥ 2,500 g
  (b) centil INTERGROWTH-21st de peso para IG > 0.97  (c) > 0.90
  Centil = grade gigs da Etapa 1 (data/processed/pig_grade_intergrowth_v1, coluna centil_k3: IG em dias = semanas×7+3),
  a mesma do PIG; nenhuma equação reescrita.
  % com IC de Wilson por raça × ig_metodo (Brasil), × tercil_reg (amostra de acesso), × macrorregião.
4b.2 Amostra analítica (todas as gestações): frequência relativa das semanas 28–42 por raça × ig_metodo;
  % em 36–40; preferência digital = f(w) / média[f(w−1), f(w+1)] para w = 29–41.
Saídas: tab_e4b_01_implausivel_{brasil,tercil,regiao}, tab_e4b_02_dist_ig, tab_e4b_02_preferencia_digital;
        data/processed/implausivel_flags_v1 (flags por registro, para 4b.3).
"""
import numpy as np
import pandas as pd

import etapa1_lib as E
import etapa3_lib as T
import etapa0_lib as L

log = L.Logger("01_plausibilidade", etapa="etapa4b")
cols = ["raca", "regiao", "CO_REGSAUD", "ig_metodo", "unica", "SEMAGESTAC", "SEXO", "PESO", "ptb"]
d = T.anexa_acesso(T.load(cols))
d["ig_metodo"] = d.ig_metodo.astype(str)
g = pd.read_parquet(L.PROC / f"pig_grade_intergrowth_v1_{L.STAMP}.parquet", columns=["SEMAGESTAC", "SEXO", "PESO", "centil_k3"])
el = (d.unica == 1) & d.SEMAGESTAC.between(24, 36) & d.SEXO.isin([1, 2]) & d.PESO.between(100, 7000)
el = el.fillna(False).to_numpy(bool)
p = d[el].copy()
k = p[["SEMAGESTAC", "SEXO", "PESO"]].astype("int32")
p = p.join(k.merge(g.astype({"SEMAGESTAC": "int32", "SEXO": "int32", "PESO": "int32"}), on=["SEMAGESTAC", "SEXO", "PESO"],
                   how="left").set_index(p.index).centil_k3)
assert p.centil_k3.notna().all()
p["imp_a"] = (p.PESO >= 2500).astype(int)
p["imp_b"] = (p.centil_k3 > 0.97).astype(int)
p["imp_c"] = (p.centil_k3 > 0.90).astype(int)
log(f"prematuros elegíveis (únicas, 24–36 sem, sexo e peso válidos): {len(p):,}; "
    f"(a) {100 * p.imp_a.mean():.2f}%  (b) {100 * p.imp_b.mean():.2f}%  (c) {100 * p.imp_c.mean():.2f}%")


def tabula(s, keys):
    rows = []
    for key, x in s.groupby(keys, observed=True):
        key = key if isinstance(key, tuple) else (key,)
        for c in ["imp_a", "imp_b", "imp_c"]:
            k_, n_ = int(x[c].sum()), len(x)
            pp, lo, hi = E.wilson(k_, n_)
            rows.append({**dict(zip(keys, key)), "criterio": c[-1], "casos": k_, "n_prematuros": n_,
                         "pct": 100 * pp, "ic_lo": 100 * lo, "ic_hi": 100 * hi})
    return pd.DataFrame(rows)


tabula(p, ["raca", "ig_metodo"]).to_csv(L.TAB / f"tab_e4b_01_implausivel_brasil_v1_{L.STAMP}.csv", index=False)
tabula(p[p.tercil_reg.notna()], ["raca", "ig_metodo", "tercil_reg"]).to_csv(L.TAB / f"tab_e4b_01_implausivel_tercil_v1_{L.STAMP}.csv", index=False)
tabula(p, ["raca", "ig_metodo", "regiao"]).to_csv(L.TAB / f"tab_e4b_01_implausivel_regiao_v1_{L.STAMP}.csv", index=False)
fl = pd.DataFrame({"imp_a": pd.Series(pd.NA, index=d.index, dtype="Int8"), "imp_b": pd.Series(pd.NA, index=d.index, dtype="Int8")})
fl.loc[p.index, "imp_a"] = p.imp_a.astype("Int8")
fl.loc[p.index, "imp_b"] = p.imp_b.astype("Int8")
fl.to_parquet(L.PROC / f"implausivel_flags_v1_{L.STAMP}.parquet")  # alinhado à ordem de T.anexa_acesso(T.load(...))
log("tabelas 4b.1 gravadas")

# 4b.2
s = d[d.SEMAGESTAC.between(28, 42)]
ft = s.groupby(["raca", "ig_metodo", "SEMAGESTAC"], observed=True).size().rename("n").reset_index()
tot = d.groupby(["raca", "ig_metodo"], observed=True).size().rename("N").reset_index()
ft = ft.merge(tot, on=["raca", "ig_metodo"])
ft["pct"] = 100 * ft.n / ft.N  # % de todos os nascimentos do grupo (22–44 sem)
ft.to_csv(L.TAB / f"tab_e4b_02_dist_ig_v1_{L.STAMP}.csv", index=False)
pr = []
for (r, m), x in ft.groupby(["raca", "ig_metodo"], observed=True):
    f = x.set_index("SEMAGESTAC").pct
    for w in range(29, 42):
        pr.append(dict(raca=r, ig_metodo=m, semana=w, pct=f.get(w, 0), indice_pref=f.get(w, 0) / ((f.get(w - 1, 0) + f.get(w + 1, 0)) / 2)))
pd.DataFrame(pr).to_csv(L.TAB / f"tab_e4b_02_preferencia_digital_v1_{L.STAMP}.csv", index=False)
log("tabelas 4b.2 gravadas")
