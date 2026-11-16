"""
7b.2 Diagnóstico final da datação (viés de mensuração, não modificação de efeito). Estimadores validados, EP por região de
saúde (etapa6_lib.para_rs), seed 42 (sem sorteio).
 (1) "Outro método" separado em TPMETESTIM 1 (exame físico/Capurro) e 2 (outro método; o manual da DN inclui o ultrassom):
     n e % por raça; % por raça × tercil entre indígenas (e demais raças); PR M2 (3 raças) de ptb, pig, ptb_ind; ICR (3.2) e Wald
     de ptb, pig, ptb_ind; % de prematuros únicos 24–36 sem com peso > P97 por raça (flags da 4b.1); casos indígenas por tercil
     (< 30 = instável). → tab_e7b2_01_{dist,dist_tercil,m2,interacao,wald,p97,casos_ind}
 (2) Reclassificação na amostra completa: todo PTB único 24–36 sem com peso > P97 (INTERGROWTH, critério b da 4b) vira não caso
     (denominador inalterado), em todos os métodos. PR M2 (3 raças) e 3.2 (ICR, Wald) de ptb e ptb_esp.
     → tab_e7b2_02_reclass_{m2,interacao,wald}
"""
import numpy as np
import pandas as pd

import etapa1_lib as E
import etapa3_lib as T
import etapa4_lib as S4
import etapa6_lib as E6
import etapa0_lib as L

log = L.Logger("7b2_01_datacao", etapa="etapa7b2")
TB, S = L.TAB, L.STAMP
d = S4.carrega().reset_index(drop=True)
x = T.load(["TPMETESTIM", "ig_metodo"])
assert len(x) == len(d) and (x.ig_metodo.astype(str).to_numpy() == d.ig_metodo.astype(str).to_numpy()).all()
d["tp"] = x.TPMETESTIM.to_numpy()
fl = pd.read_parquet(L.PROC / f"implausivel_flags_v1_{S}.parquet")
assert len(fl) == len(d)
d["imp_b"] = fl.imp_b.to_numpy()                       # NA = não elegível (não é prematuro único 24–36 sem válido)
assert int((d.tp.isin([1, 2])).sum()) == 10650839 and int((d.tp == 1).sum()) == 5085119 and int((d.tp == 2).sum()) == 5565720
R_ = T.R


def m2(s, desf, rot):
    s = s[s[desf].notna()]
    c = E6.para_rs(E.agrega(s, desf, ["raca", "idade_cat", "ano", "regiao"]).assign(CODMUNRES=lambda z: z.CODMUNRES.astype(str)))
    assert int(c.n.sum()) == len(s)
    f = E.fit_agg(c, T.M2, "poisson")
    return [dict(cenario=rot, desfecho=desf, raca=t["termo"].split("[T.")[1].rstrip("]"), N=len(s), casos=int(s[desf].sum()), G=f["G"],
                 PR=t["est"], PR_lo=t["lo"], PR_hi=t["hi"]) for t in E.termos(f, R_ + "[T.")]


# ---------- (1)
dist, dter, mrows, p97, cind = [], [], [], [], []
res = {k: [] for k in ("interacao", "wald")}
tot_r = d.groupby("raca", observed=True).size()
for cod in (1, 2):
    sub = d[d.tp == cod]
    rot = f"codigo_{cod}"
    for g, n in sub.groupby("raca", observed=True).size().items():
        dist.append(dict(codigo=cod, raca=g, n=int(n), pct_da_raca=100 * n / tot_r[g]))
    acc = d[d.CO_REGSAUD.notna()]
    for (g, t), y in acc.groupby(["raca", "tercil_reg"], observed=True):
        dter.append(dict(codigo=cod, raca=g, tercil=str(t), n_codigo=int((y.tp == cod).sum()), n_total=len(y), pct=100 * (y.tp == cod).mean()))
    for desf in ("ptb", "pig", "ptb_ind"):
        mrows += m2(sub, desf, rot)
        r = S4.roda_32(sub, desf, rot, remap=E6.para_rs)
        for k in res:
            res[k].append(r[k])
        sa = sub[sub[desf].notna() & sub.CO_REGSAUD.notna() & (sub.raca == "Indigena")]
        for t, y in sa.groupby("tercil_reg", observed=True):
            cind.append(dict(codigo=cod, desfecho=desf, tercil=str(t), n=len(y), casos=int(y[desf].sum()), instavel=bool(y[desf].sum() < 30)))
    el = sub[sub.imp_b.notna()]
    for g, y in el.groupby("raca", observed=True):
        p97.append(dict(codigo=cod, raca=g, n_prematuros=len(y), casos_p97=int(y.imp_b.sum()), pct=100 * y.imp_b.astype(float).mean(),
                        ic_lo=float(E.wilson(int(y.imp_b.sum()), len(y))[1]) * 100, ic_hi=float(E.wilson(int(y.imp_b.sum()), len(y))[2]) * 100))
    log(f"(1) código {cod}: n = {len(sub):,}; PR, ICR e Wald de ptb, pig, ptb_ind feitos")
pd.DataFrame(dist).to_csv(TB / f"tab_e7b2_01_dist_v1_{S}.csv", index=False)
pd.DataFrame(dter).to_csv(TB / f"tab_e7b2_01_dist_tercil_v1_{S}.csv", index=False)
pd.DataFrame(mrows).to_csv(TB / f"tab_e7b2_01_m2_v1_{S}.csv", index=False)
pd.DataFrame(p97).to_csv(TB / f"tab_e7b2_01_p97_v1_{S}.csv", index=False)
C = pd.DataFrame(cind)
C.to_csv(TB / f"tab_e7b2_01_casos_ind_v1_{S}.csv", index=False)
for k, v in res.items():
    pd.concat(v).to_csv(TB / f"tab_e7b2_01_{k}_v1_{S}.csv", index=False)
it = pd.concat(res["interacao"]).query("raca == 'Indigena' and nivel == 'T1'")
wd = pd.concat(res["wald"])
log("(1) distribuição por raça:\n" + pd.DataFrame(dist).round(2).to_string(index=False))
log("(1) PR M2 Indígena:\n" + pd.DataFrame(mrows).query("raca == 'Indigena'").round(3).to_string(index=False))
log("(1) ICR Indígena×T1 e Wald:\n" + it[["sensibilidade", "desfecho", "ICR_pp", "ICR_lo", "ICR_hi"]].merge(
    wd[["sensibilidade", "desfecho", "chi2", "p", "N", "G"]], on=["sensibilidade", "desfecho"]).round(4).to_string(index=False))
log("(1) % > P97:\n" + pd.DataFrame(p97).round(2).to_string(index=False))
log("(1) casos indígenas por tercil (< 30 = instável):\n" + C.to_string(index=False))

# ---------- (2)
imp = d.imp_b.fillna(0).to_numpy().astype(bool)
for desf in ("ptb", "ptb_esp"):
    y = d[desf].astype("Float64").copy()
    y[imp & (y == 1).fillna(False).to_numpy(bool)] = 0.0
    d[f"{desf}_reclass"] = y.astype("Int8")
nr = int((imp & (d.ptb == 1).to_numpy(bool)).sum())
ne = int((imp & (d.ptb_esp == 1).fillna(False).to_numpy(bool)).sum())
assert (nr, ne) == (410747, 244676)                    # = Etapa 4b.3, critério b
rows = []
res = {k: [] for k in ("interacao", "wald")}
for desf in ("ptb_reclass", "ptb_esp_reclass"):
    rows += m2(d, desf, "reclass_p97")
    r = S4.roda_32(d, desf, "reclass_p97", remap=E6.para_rs)
    for k in res:
        res[k].append(r[k])
M = pd.DataFrame(rows)
M.to_csv(TB / f"tab_e7b2_02_reclass_m2_v1_{S}.csv", index=False)
for k, v in res.items():
    pd.concat(v).to_csv(TB / f"tab_e7b2_02_reclass_{k}_v1_{S}.csv", index=False)
# coerência com a Etapa 6.1b (mesmo critério, mesma amostra): ICR idêntico
ib = pd.read_csv(TB / f"tab_e6_01b_interacao_v1_{S}.csv").query("sensibilidade == '4b.3_plausivel'")
it2 = pd.concat(res["interacao"])
for a, b in [("ptb_reclass", "ptb_plaus_b"), ("ptb_esp_reclass", "ptb_esp_plaus_b")]:
    x1 = it2[it2.desfecho == a].set_index(["raca", "nivel"]).ICR_pp
    x0 = ib[ib.desfecho == b].set_index(["raca", "nivel"]).ICR_pp
    assert float((x1 - x0.reindex(x1.index)).abs().max()) < 1e-9, a
pi = M.query("desfecho == 'ptb_reclass' and raca == 'Indigena'").iloc[0]
log(f"(2) reclassificados: PTB {nr:,}; espontâneos {ne:,}. PR M2 Indígena PTB = {pi.PR:.2f} ({pi.PR_lo:.2f}–{pi.PR_hi:.2f}) "
    f"(Etapa 4b, cluster por município: 1.05 (0.98–1.12)); ICR = 6.1b (asserção)\n" + M.round(3).to_string(index=False))
log("(2) ICR Indígena×T1 e Wald:\n" + it2.query("raca == 'Indigena' and nivel == 'T1'")[["desfecho", "ICR_pp", "ICR_lo", "ICR_hi"]].merge(
    pd.concat(res["wald"])[["desfecho", "chi2", "p"]], on="desfecho").round(4).to_string(index=False))
assert abs(pi.PR - 1.05) < 0.01                        # ordem de grandeza da Etapa 4b (ponto idêntico; só o EP muda)
