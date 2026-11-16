"""
6.4 Análise robusta à datação (sensibilidade principal da prematuridade).
Subamostra: ig_metodo = "outro método" (TPMETESTIM 1/2; o manual da DN manda registrar a ultrassonografia como
"outro método") E sem PTB implausível (prematuros únicos 24–36 sem com peso > P97 INTERGROWTH, critério b da 4b,
EXCLUÍDOS da subamostra; flags da 4b.1, NA = não elegível = mantido).
M2 (RP e DR marginal) para PTB, PTB espontâneo e PTB indicado; análise 3.2 (ICR Indígena×T1 e Parda×T1 e Wald);
EP agrupado por região de saúde (etapa6_lib.para_rs).
Saídas: tab_e6_04_m2, tab_e6_04_{conjunto,interacao,wald}.
"""
import pandas as pd

import etapa1_lib as E
import etapa3_lib as T
import etapa4_lib as S4
import etapa6_lib as E6
import etapa0_lib as L

log = E6.logger("04_robusta_datacao")
d = S4.carrega().reset_index(drop=True)
fl = pd.read_parquet(L.PROC / f"implausivel_flags_v1_{L.STAMP}.parquet")
assert len(fl) == len(d)
imp = fl.imp_b.fillna(0).to_numpy().astype(bool) & (d.ptb == 1).to_numpy(bool)
assert int(imp.sum()) == 410747  # = PTB reclassificados pelo critério b na 4b.3
om = (d.ig_metodo == "outro_metodo").to_numpy(bool)
s = d[om & ~imp]
log(f"outro método: {int(om.sum()):,}; excluídos PTB implausíveis (b) nele: {int((om & imp).sum()):,}; subamostra {len(s):,}")
R = "C(raca, Treatment('Branca'))"
OUT = ["ptb", "ptb_esp", "ptb_ind"]
m2 = []
for desf in OUT:
    x = s[s[desf].notna()]
    c = E6.para_rs(E.agrega(x, desf, ["raca", "idade_cat", "ano", "regiao"]).assign(CODMUNRES=lambda z: z.CODMUNRES.astype(str)))
    assert int(c.n.sum()) == len(x)
    f = E.fit_agg(c, T.M2, "poisson")
    mg = {r["nivel"]: r for r in E.marginal(f, c, "raca", T.RACAS, "Branca")}
    for t in E.termos(f, R + "[T."):
        g = t["termo"].split("[T.")[1].rstrip("]")
        m2.append(dict(desfecho=desf, raca=g, N=len(x), casos=int(x[desf].sum()), G=f["G"], RP=t["est"], RP_lo=t["lo"], RP_hi=t["hi"],
                       DR_pp=100 * mg[g]["dif"], DR_lo=100 * mg[g]["dif_lo"], DR_hi=100 * mg[g]["dif_hi"]))
M = pd.DataFrame(m2)
M.to_csv(L.TAB / f"tab_e6_04_m2_v1_{L.STAMP}.csv", index=False)
log("M2 (outro método, sem PTB implausível; EP região de saúde):\n" + M.round(3).to_string(index=False))
res = {k: [] for k in ("conjunto", "interacao", "wald")}
for desf in OUT:
    r = S4.roda_32(s, desf, "6.4_outro_sem_implausivel", remap=E6.para_rs)
    for k in res:
        res[k].append(r[k])
for k, v in res.items():
    pd.concat(v).to_csv(L.TAB / f"tab_e6_04_{k}_v1_{L.STAMP}.csv", index=False)
it = pd.concat(res["interacao"])
log("3.2, ICR T1:\n" + it[it.nivel == "T1"][["desfecho", "raca", "ICR_pp", "ICR_lo", "ICR_hi"]].round(3).to_string(index=False))
log("Wald:\n" + pd.concat(res["wald"])[["desfecho", "chi2", "gl", "p", "N", "G"]].to_string(index=False))
