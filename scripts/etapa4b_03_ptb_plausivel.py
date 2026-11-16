"""
4b.3 PTB "plausível": prematuros (únicas, 24–36 sem, sexo e peso válidos) com peso implausível para a IG passam
a NÃO CASO (denominador inalterado).
  critério b (principal): centil gigs (IG = semanas×7+3) > 0.97;  critério a (sensibilidade): PESO ≥ 2,500 g
Desfechos: ptb e ptb_esp. Modelos: M2 Brasil (RP e DR marginal; fit_agg/marginal da Etapa 1–2) e 3.2
(etapa4_lib.roda_32 → etapa3_lib.knol). Comparação com os originais e classificação (etapa4_lib.classifica).
Saídas: tab_e4b_03_m2, tab_e4b_03_{conjunto,interacao,wald}, tab_e4b_03_quadro.
"""
import numpy as np
import pandas as pd

import etapa1_lib as E
import etapa3_lib as T
import etapa4_lib as S4
import etapa0_lib as L

log = L.Logger("03_ptb_plausivel", etapa="etapa4b")
d = S4.carrega()
g = pd.read_parquet(L.PROC / f"pig_grade_intergrowth_v1_{L.STAMP}.parquet", columns=["SEMAGESTAC", "SEXO", "PESO", "centil_k3"])
v = pd.read_parquet(T.V3, columns=["incl", "SEMAGESTAC", "SEXO", "PESO"], filters=[("incl", "==", True)])
assert len(v) == len(d)  # mesma leitura da v3 (incl) e mesma ordem que T.load; anexa_acesso preserva a ordem
d = d.reset_index(drop=True)
v = v.reset_index(drop=True)
assert (v.SEMAGESTAC.to_numpy() == pd.read_parquet(T.V3, columns=["incl", "SEMAGESTAC"], filters=[("incl", "==", True)]).SEMAGESTAC.to_numpy()).all()
el = ((d.unica == 1) & v.SEMAGESTAC.between(24, 36) & v.SEXO.isin([1, 2]) & v.PESO.between(100, 7000)).fillna(False).to_numpy(bool)
k = v.loc[el, ["SEMAGESTAC", "SEXO", "PESO"]].astype("int32")
c = k.merge(g.astype({"SEMAGESTAC": "int32", "SEXO": "int32", "PESO": "int32"}), on=["SEMAGESTAC", "SEXO", "PESO"], how="left")
assert c.centil_k3.notna().all()
imp_b = np.zeros(len(d), bool)
imp_a = np.zeros(len(d), bool)
imp_b[np.where(el)[0]] = c.centil_k3.to_numpy() > 0.97
imp_a[np.where(el)[0]] = k.PESO.to_numpy() >= 2500
for crit, imp in [("b", imp_b), ("a", imp_a)]:
    for desf in ("ptb", "ptb_esp"):
        x = d[desf].astype("Float64").copy()
        x[imp & (x == 1).fillna(False).to_numpy(bool)] = 0.0
        d[f"{desf}_plaus_{crit}"] = x.astype("Int8")
    log(f"critério {crit}: PTB reclassificados = {int((imp & (d.ptb == 1).to_numpy(bool)).sum()):,}; "
        f"PTB espontâneo reclassificados = {int((imp & (d.ptb_esp == 1).fillna(False).to_numpy(bool)).sum()):,}")

R = "C(raca, Treatment('Branca'))"
M2 = f"{R} + C(idade_cat, Treatment('20-34')) + C(ano) + C(regiao, Treatment('SE'))"
m2 = []
res = {k_: [] for k_ in ("conjunto", "interacao", "wald")}
for desf in ["ptb", "ptb_esp", "ptb_plaus_b", "ptb_esp_plaus_b", "ptb_plaus_a", "ptb_esp_plaus_a"]:
    s = d[d[desf].notna()]
    cells = E.agrega(s, desf, ["raca", "idade_cat", "ano", "regiao"])
    cells["CODMUNRES"] = cells.CODMUNRES.astype(str)
    assert int(cells.n.sum()) == len(s)
    f = E.fit_agg(cells, M2, "poisson")
    mg = {r["nivel"]: r for r in E.marginal(f, cells, "raca", T.RACAS, "Branca")}
    for t in E.termos(f, R + "[T."):
        gr = t["termo"].split("[T.")[1].rstrip("]")
        m2.append(dict(desfecho=desf, raca=gr, N=len(s), casos=int(s[desf].sum()), RP=t["est"], RP_lo=t["lo"], RP_hi=t["hi"],
                       DR_pp=100 * mg[gr]["dif"], DR_lo=100 * mg[gr]["dif_lo"], DR_hi=100 * mg[gr]["dif_hi"]))
    r = S4.roda_32(d, desf, "4b.3")
    for k_ in res:
        res[k_].append(r[k_])
    log(f"{desf}: M2 e 3.2 feitos (N = {len(s):,}; casos = {int(s[desf].sum()):,})")
M = pd.DataFrame(m2)
M.to_csv(L.TAB / f"tab_e4b_03_m2_v1_{L.STAMP}.csv", index=False)
for k_, vv in res.items():
    pd.concat(vv).to_csv(L.TAB / f"tab_e4b_03_{k_}_v1_{L.STAMP}.csv", index=False)

it = pd.concat(res["interacao"])
it = it[it.nivel == "T1"]
rows = []
for ach, base in [("C", "ptb_esp"), ("D", "ptb")]:
    o = it[(it.desfecho == base) & (it.raca == "Indigena")].iloc[0]
    row = dict(achado=ach, desfecho=base, original=f"{o.ICR_pp:.2f} ({o.ICR_lo:.2f} a {o.ICR_hi:.2f})")
    for crit in ("b", "a"):
        x = it[(it.desfecho == f"{base}_plaus_{crit}") & (it.raca == "Indigena")].iloc[0]
        row[f"plaus_{crit}"] = f"{x.ICR_pp:.2f} ({x.ICR_lo:.2f} a {x.ICR_hi:.2f}) {S4.classifica(ach, o, x)}"
    for crit in ("orig", "b", "a"):
        nm = base if crit == "orig" else f"{base}_plaus_{crit}"
        mm = M[(M.desfecho == nm) & (M.raca == "Indigena")].iloc[0]
        row[f"M2_RP_Indigena_{crit}"] = f"{mm.RP:.2f} ({mm.RP_lo:.2f}–{mm.RP_hi:.2f}); DR {mm.DR_pp:.2f}"
    rows.append(row)
Q = pd.DataFrame(rows)
Q.to_csv(L.TAB / f"tab_e4b_03_quadro_v1_{L.STAMP}.csv", index=False)
log("quadro 4b.3:\n" + Q.to_string(index=False))
