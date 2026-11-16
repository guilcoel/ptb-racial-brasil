"""
4b.4 Centro-Oeste (replicação da RSP) por método de estimação da IG.
M1 = raça; M5 = raça + idade_cat + ESCMAE (5 cat.) + ano + UF (RSP, lib_baseB/02_build_baseB). Desfecho PTB.
Logística (OR) e Poisson (RP); EP do modelo (OR), HC0 (RP) — como na Tabela 2 publicada — e clusterizado por município.
Primeiro: sem estratificar, deve reproduzir a Tabela 2 (OR M5 Indígena 1.504 (1.461–1.549); RP 1.41 (1.38–1.45)).
Depois: estratificado por ig_metodo (DUM / outro_metodo / ignorado). Wald de raça × ig_metodo no CO
(Poisson, M5 + ig_metodo + raça×ig_metodo, etapa3_lib.knol, EP clusterizado).
Saídas: tab_e4b_04_co_estratos, tab_e4b_04_co_wald.
Etapa 6b: com --rs, o EP "cluster" passa a ser agrupado por região de saúde (etapa6_lib.para_rs); saídas com sufixo _rs.
"""
import sys

import pandas as pd

import etapa1_lib as E
import etapa3_lib as T
import etapa0_lib as L

RS = "--rs" in sys.argv
SUF = "_rs" if RS else ""
if RS:
    import etapa6_lib as E6
log = E6.logger("6b_co_metodo_rs") if RS else L.Logger("04_co_metodo", etapa="etapa4b")
d = T.load(["raca", "idade_cat", "esc_cat", "uf", "regiao", "CODMUNRES", "ig_metodo", "ptb"])
d = d[d.regiao == "CO"].copy()
d["uf"] = d.uf.astype(str).astype("category")
d["ig_metodo"] = pd.Categorical(d.ig_metodo.astype(str), categories=["DUM", "outro_metodo", "ignorado"])
log("CO incluídos", len(d))
R = "C(raca, Treatment('Branca'))"
RHS = {"M1": R, "M5": f"{R} + C(idade_cat) + C(esc_cat) + C(ano) + C(uf)"}
EP = {"OR": [("modelo", "logit"), ("cluster", "logit")], "RP": [("hc0", "poisson"), ("cluster", "poisson")]}
rows = []
for estrato in ["todos", "DUM", "outro_metodo", "ignorado"]:
    s = d if estrato == "todos" else d[d.ig_metodo == estrato]
    c = E.agrega(s, "ptb", ["raca", "idade_cat", "esc_cat", "ano", "uf"])
    c["CODMUNRES"] = c.CODMUNRES.astype(str)
    if RS:
        c = E6.para_rs(c)
    assert int(c.n.sum()) == len(s)
    for m, rhs in RHS.items():
        fits = {fam: E.fit_agg(c, rhs, fam) for fam in ("logit", "poisson")}
        for med, lst in EP.items():
            for ep, fam in lst:
                for t in E.termos(fits[fam], R + "[T.", cov=ep):
                    rows.append(dict(estrato=estrato, modelo=m, medida=med, ep=ep, raca=t["termo"].split("[T.")[1].rstrip("]"),
                                     est=t["est"], lo=t["lo"], hi=t["hi"], N=len(s), casos=int(s.ptb.sum())))
    log(f"estrato {estrato}: N = {len(s):,}; casos = {int(s.ptb.sum()):,}")
X = pd.DataFrame(rows)
X.to_csv(L.TAB / f"tab_e4b_04_co_estratos{SUF}_v1_{L.STAMP}.csv", index=False)
v = X[(X.estrato == "todos") & (X.raca == "Indigena") & (X.modelo == "M5")]
orm = v[(v.medida == "OR") & (v.ep == "modelo")].iloc[0]
rph = v[(v.medida == "RP") & (v.ep == "hc0")].iloc[0]
ok = (round(orm.est, 3), round(orm.lo, 3), round(orm.hi, 3)) == (1.504, 1.461, 1.549) and \
     (round(rph.est, 2), round(rph.lo, 2), round(rph.hi, 2)) == (1.41, 1.38, 1.45)
log(f"validação RSP (M5 Indígena): OR {orm.est:.3f} ({orm.lo:.3f}–{orm.hi:.3f}); RP {rph.est:.2f} ({rph.lo:.2f}–{rph.hi:.2f}); bate = {ok}")

c = E.agrega(d, "ptb", ["raca", "idade_cat", "esc_cat", "ano", "uf", "ig_metodo"])
c["CODMUNRES"] = c.CODMUNRES.astype(str)
if RS:
    c = E6.para_rs(c)
r = T.knol(c, "ig_metodo", ["DUM", "outro_metodo", "ignorado"], "DUM", base=RHS["M5"], mod_main="C(ig_metodo, Treatment('DUM'))",
           rotulo="ig_metodo_CO")
r["wald"].to_csv(L.TAB / f"tab_e4b_04_co_wald{SUF}_v1_{L.STAMP}.csv", index=False)
w = r["wald"].iloc[0]
log(f"Wald raça × ig_metodo no CO (Poisson, M5, EP cluster): χ² = {w.chi2:.1f} ({w.gl} gl), p = {w.p:.2e}")
