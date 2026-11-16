"""
7b.3 PTB espontâneo por código de datação e Wald só dos termos indígenas. Estimadores validados (fit_agg; o ajuste da 3.2 é o de
etapa4_lib.roda_32, replicado aqui só para expor o objeto `fit` do knol), EP por região de saúde (etapa6_lib.para_rs).
 (1) ptb_esp nos códigos TPMETESTIM 1, 2 e 8: PR M2 (3 raças) e 3.2 (ICR, Wald 6 gl). → tab_e7b3_01_esp_{m2,interacao}
 (2) Wald dos termos indígenas (ix__Indigena__T1, ix__Indigena__T2; 2 gl), mesma covariância por cluster do Wald de 6 gl, para
     ptb, pig, ptb_ind, ptb_esp na análise principal, nos códigos 1, 2 e 8 e na reclassificação > P97 (ptb, ptb_esp); e, só
     para ptb, nos demais cenários da Tabela 4 (outro método 1–2, robusta à datação, sem CE/DF, sem 2024), para completar a
     coluna. O Wald de 6 gl é conferido contra as tabelas já publicadas no pacote. → tab_e7b3_02_wald_ind
 (3) ICR Parda×T1 e Black×T1 da PTB total reclassificada: já em tab_e7b2_02_reclass_interacao (lido no pacote).
"""
import numpy as np
import pandas as pd
from scipy import stats

import etapa1_lib as E
import etapa3_lib as T
import etapa4_lib as S4
import etapa6_lib as E6
import etapa0_lib as L

log = L.Logger("7b3_01_esp_wald", etapa="etapa7b3")
TB, S = L.TAB, L.STAMP
d = S4.carrega().reset_index(drop=True)
x = T.load(["TPMETESTIM"])
assert len(x) == len(d)
d["tp"] = x.TPMETESTIM.to_numpy()
fl = pd.read_parquet(L.PROC / f"implausivel_flags_v1_{S}.parquet")
assert len(fl) == len(d)
imp = fl.imp_b.fillna(0).to_numpy().astype(bool)
for desf in ("ptb", "ptb_esp"):
    y = d[desf].astype("Float64").copy()
    y[imp & (y == 1).fillna(False).to_numpy(bool)] = 0.0
    d[f"{desf}_reclass"] = y.astype("Int8")
assert int((imp & (d.ptb == 1).to_numpy(bool)).sum()) == 410747
R_ = T.R
IND = ["ix__Indigena__T1", "ix__Indigena__T2"]


def ajuste_32(sub, desf):
    """= etapa4_lib.roda_32(sub, desf, rot, remap=para_rs), devolvendo também o fit do knol."""
    s = sub[sub[desf].notna() & sub.CO_REGSAUD.notna()]
    c = E.agrega(s, desf, ["raca", "idade_cat", "ano", "regiao", "tercil_reg"])
    assert int(c.n.sum()) == len(s) and int(c.Y.sum()) == int(s[desf].sum())
    c["CODMUNRES"] = c.CODMUNRES.astype(str)
    c["raca"] = c.raca.cat.remove_unused_categories() if c.raca.cat.categories.size > 4 else c.raca
    c = E6.para_rs(c)
    return T.knol(c, "tercil_reg", ["T1", "T2", "T3"], "T3", mod_main="C(tercil_reg, Treatment('T3'))", rotulo="tercil_reg")


def wald_ind(r):
    f, V = r["fit"], r["fit"]["cov"]["cluster"]
    idx = [f["names"].index(n) for n in IND]
    b = f["params"].to_numpy()[idx]
    w = float(b @ np.linalg.solve(V[np.ix_(idx, idx)], b))
    return w, stats.chi2.sf(w, 2)


def m2(s, desf, rot):
    s = s[s[desf].notna()]
    c = E6.para_rs(E.agrega(s, desf, ["raca", "idade_cat", "ano", "regiao"]).assign(CODMUNRES=lambda z: z.CODMUNRES.astype(str)))
    f = E.fit_agg(c, T.M2, "poisson")
    return [dict(cenario=rot, desfecho=desf, raca=t["termo"].split("[T.")[1].rstrip("]"), N=len(s), casos=int(s[desf].sum()), G=f["G"],
                 PR=t["est"], PR_lo=t["lo"], PR_hi=t["hi"]) for t in E.termos(f, R_ + "[T.")]


# Wald de 6 gl já publicados (conferência)
pub = {}
for _, w in pd.read_csv(TB / f"tab_e6_01a_wald_v1_{S}.csv").iterrows():
    pub[("principal", w.desfecho)] = w.chi2
for _, w in pd.read_csv(TB / f"tab_e7b2_01_wald_v1_{S}.csv").iterrows():
    pub[(w.sensibilidade, w.desfecho)] = w.chi2
for _, w in pd.read_csv(TB / f"tab_e7b1_01_cenarios_wald_v1_{S}.csv").iterrows():
    pub[({"so_DUM": "codigo_8", "so_outro_metodo": "outro_metodo_1_2"}.get(w.sensibilidade, w.sensibilidade), "ptb")] = w.chi2
for _, w in pd.read_csv(TB / f"tab_e6_01b_wald_v1_{S}.csv").query("sensibilidade == '4.1_DUM'").iterrows():
    pub[("codigo_8", w.desfecho)] = w.chi2
for _, w in pd.read_csv(TB / f"tab_e7b2_02_reclass_wald_v1_{S}.csv").iterrows():
    pub[("reclass_p97", w.desfecho.replace("_reclass", ""))] = w.chi2
for _, w in pd.read_csv(TB / f"tab_e6_04_wald_v1_{S}.csv").iterrows():
    pub[("robusta_datacao", w.desfecho)] = w.chi2

robusta = (d.tp.isin([1, 2]) & ~(imp & (d.ptb == 1).to_numpy(bool))).to_numpy(bool)
CEN = [("principal", np.ones(len(d), bool), ["ptb", "pig", "ptb_ind", "ptb_esp"]),
       ("codigo_1", (d.tp == 1).to_numpy(), ["ptb", "pig", "ptb_ind", "ptb_esp"]),
       ("codigo_2", (d.tp == 2).to_numpy(), ["ptb", "pig", "ptb_ind", "ptb_esp"]),
       ("codigo_8", (d.tp == 8).to_numpy(), ["ptb", "pig", "ptb_ind", "ptb_esp"]),
       ("reclass_p97", np.ones(len(d), bool), ["ptb", "ptb_esp"]),
       ("outro_metodo_1_2", d.tp.isin([1, 2]).to_numpy(), ["ptb"]),
       ("robusta_datacao", robusta, ["ptb"]),
       ("sem_CE_DF", (~d.uf.isin(["CE", "DF"])).to_numpy(), ["ptb"]),
       ("sem_2024", (d.ano != 2024).to_numpy(), ["ptb"])]
assert int(robusta.sum()) == 10607946
W, IT, M = [], [], []
for cen, mask, outs in CEN:
    sub = d[mask]
    for desf in outs:
        col = f"{desf}_reclass" if cen == "reclass_p97" else desf
        r = ajuste_32(sub, col)
        w6 = r["wald"].iloc[0]
        w2, p2 = wald_ind(r)
        ref = pub.get((cen, desf))
        conf = None if ref is None else abs(w6.chi2 - ref)
        assert conf is None or conf < 1e-6, (cen, desf, w6.chi2, ref)
        W.append(dict(cenario=cen, desfecho=desf, N=int(w6.N), G=int(w6.G), chi2_6gl=w6.chi2, p_6gl=w6.p, chi2_ind_2gl=w2, p_ind_2gl=p2,
                      wald6_conferido=ref is not None))
        if desf == "ptb_esp" and cen.startswith("codigo"):
            IT.append(r["interacao"].assign(cenario=cen, desfecho=desf))
            M.extend(m2(sub, desf, cen))
        log(f"{cen} {desf}: Wald 6 gl χ² = {w6.chi2:.2f} (p = {w6.p:.3g}){' [= publicado]' if ref is not None else ''}; "
            f"Wald indígena 2 gl χ² = {w2:.2f} (p = {p2:.3g})")
Wd = pd.DataFrame(W)
Wd.to_csv(TB / f"tab_e7b3_02_wald_ind_v1_{S}.csv", index=False)
pd.concat(IT).to_csv(TB / f"tab_e7b3_01_esp_interacao_v1_{S}.csv", index=False)
Md = pd.DataFrame(M)
Md.to_csv(TB / f"tab_e7b3_01_esp_m2_v1_{S}.csv", index=False)
# conferência: ICR de ptb_esp no código 8 = 4.1_DUM da 6.1b
it8 = pd.concat(IT).query("cenario == 'codigo_8'").set_index(["raca", "nivel"]).ICR_pp
ib = pd.read_csv(TB / f"tab_e6_01b_interacao_v1_{S}.csv").query("sensibilidade == '4.1_DUM' and desfecho == 'ptb_esp'").set_index(["raca", "nivel"]).ICR_pp
assert float((it8 - ib.reindex(it8.index)).abs().max()) < 1e-9
log(f"Wald de 6 gl conferidos com o publicado: {int(Wd.wald6_conferido.sum())}/{len(Wd)}")
log("PTB espontâneo por código, PR M2:\n" + Md.round(3).to_string(index=False))
ii = pd.concat(IT).query("nivel == 'T1'")[["cenario", "raca", "ICR_pp", "ICR_lo", "ICR_hi", "ICR_p"]]
log("PTB espontâneo por código, ICR ×T1:\n" + ii.round(3).to_string(index=False))
log("Wald (6 gl e indígena 2 gl):\n" + Wd.round(4).to_string(index=False))
