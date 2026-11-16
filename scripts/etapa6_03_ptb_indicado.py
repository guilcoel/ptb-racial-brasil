"""
6.3 Validação da prematuridade indicada.
 (a) ptb_tipo (termo / espontâneo / indicado / sem classificação) × TPROBSON (grupo de Robson gerado pelo sistema; 11 não
     documentado na estrutura CGIAE) × raça: contagens e % dentro de ptb_tipo × raça.
 (b) Logit multinomial (base = termo; espontâneo; indicado) com o M2 (raça + idade + ano + região), excluídos os PTB sem
     classificação; etapa6_lib.fit_mnl (validado contra statsmodels MNLogit: β, EP do modelo e EP por cluster idênticos
     numa subamostra de 1%). EP agrupado por região de saúde (os 533 sem região: cluster por UF).
     Brasil: RRR de cada raça vs Branca. Por tercil (amostra de acesso): M2 + tercil + raça×tercil; RRR de cada raça
     dentro de cada tercil = exp(β_raça + β_raça×tercil), IC delta.
Saídas: tab_e6_03a_robson, tab_e6_03b_rrr.
"""
import numpy as np
import pandas as pd

import etapa1_lib as E
import etapa3_lib as T
import etapa6_lib as E6
import etapa0_lib as L

log = E6.logger("03_ptb_indicado")
d = T.anexa_acesso(T.load(["raca", "idade_cat", "regiao", "CODMUNRES", "CO_REGSAUD", "ptb_tipo", "TPROBSON"]))
d["tipo"] = d.ptb_tipo.astype(str).replace({"nan": "termo", "None": "termo"})
d["robson"] = d.TPROBSON.astype("Int64").astype(str).replace({"<NA>": "nulo"})
log(f"amostra {len(d):,}; tipo: {d.tipo.value_counts().to_dict()}")

# (a)
a = d.groupby(["raca", "tipo", "robson"], observed=True).size().rename("n").reset_index()
a["pct"] = 100 * a.n / a.groupby(["raca", "tipo"], observed=True).n.transform("sum")
a.to_csv(L.TAB / f"tab_e6_03a_robson_v1_{L.STAMP}.csv", index=False)
w = a[a.tipo.isin(["espontaneo", "indicado"])].pivot_table(index="robson", columns=["tipo", "raca"], values="pct", observed=True).round(1)
w = w.reindex(sorted(w.index, key=lambda s: (len(s), s)))
log("% por grupo de Robson dentro de tipo × raça (PTB):\n" + w.to_string())

# (b)
s = d[d.tipo != "sem_classif"].copy()
for k, t in enumerate(["termo", "espontaneo", "indicado"]):
    s[f"y{k}"] = (s.tipo == t).astype(float)
Y = ["y0", "y1", "y2"]
R = "C(raca, Treatment('Branca'))"
rows = []


def rrr(f, termos, rotulo, tercil):
    V = f["cov"]["cluster"]
    K = f["K"]
    for j, cat in enumerate(["espontaneo", "indicado"]):
        for g in T.RACAS[1:]:
            gr = np.zeros(K * f["J"])
            for nm in termos(g):
                gr[j * K + f["names"].index(nm)] = 1
            v = float(gr @ f["params"].to_numpy().T.reshape(-1))
            se = float(np.sqrt(gr @ V @ gr))
            rows.append(dict(analise=rotulo, tercil=tercil, categoria=cat, raca=g, RRR=np.exp(v), lo=np.exp(v - E.Z * se),
                             hi=np.exp(v + E.Z * se), N=int(f["N"]), G=f["G"]))


c = s.groupby(["raca", "idade_cat", "ano", "regiao", "CODMUNRES"], observed=True)[Y].sum().reset_index()
assert int(c[Y].to_numpy().sum()) == len(s)
f = E6.fit_mnl(E6.para_rs(c), T.M2, Y)
log(f"multinomial Brasil: N = {int(f['N']):,}; G = {f['G']}; {f['iter']} iterações")
rrr(f, lambda g: [f"{R}[T.{g}]"], "Brasil", "todos")

sa = s[s.CO_REGSAUD.notna()]
ca = sa.groupby(["raca", "idade_cat", "ano", "regiao", "tercil_reg", "CODMUNRES"], observed=True)[Y].sum().reset_index()
assert int(ca[Y].to_numpy().sum()) == len(sa)
rhs = T.M2 + " + C(tercil_reg, Treatment('T3')) + " + R + ":C(tercil_reg, Treatment('T3'))"
fa = E6.fit_mnl(E6.para_rs(ca), rhs, Y)
log(f"multinomial por tercil: N = {int(fa['N']):,}; G = {fa['G']}; {fa['iter']} iterações")
for t in ["T1", "T2", "T3"]:
    rrr(fa, lambda g, t=t: [f"{R}[T.{g}]"] + ([f"{R}[T.{g}]:C(tercil_reg, Treatment('T3'))[T.{t}]"] if t != "T3" else []),
        "por_tercil", t)
# razão de RRR T1 vs T3 (interação multiplicativa), Indígena e Parda
for j, cat in enumerate(["espontaneo", "indicado"]):
    for g in T.RACAS[1:]:
        nm = f"{R}[T.{g}]:C(tercil_reg, Treatment('T3'))[T.T1]"
        i = j * fa["K"] + fa["names"].index(nm)
        b, se = fa["params"].iloc[:, j][nm], np.sqrt(fa["cov"]["cluster"][i, i])
        rows.append(dict(analise="razao_RRR_T1_vs_T3", tercil="T1/T3", categoria=cat, raca=g, RRR=np.exp(b),
                         lo=np.exp(b - E.Z * se), hi=np.exp(b + E.Z * se), N=int(fa["N"]), G=fa["G"]))
X = pd.DataFrame(rows)
X.to_csv(L.TAB / f"tab_e6_03b_rrr_v1_{L.STAMP}.csv", index=False)
log("RRR (EP por região de saúde):\n" + X.round(3).to_string(index=False))
