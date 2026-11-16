"""
7b.1 Análises que fecham as pendências da 7b (autorizadas por Guilherme no prompt da 7b.1). Estimadores validados, EP por região
de saúde (etapa6_lib.para_rs), seed 42 (não há sorteio aqui).
 (1) ICR Indígena×T1 (e demais) + Wald da PTB TOTAL nos cenários só DUM, só outro método, sem CE/DF, sem 2024
     (etapa4_lib.roda_32 com remap) → tab_e7b1_01_cenarios_{interacao,wald}
 (2) S1 restrito: PTB (<37 sem) entre excluídos com SEMAGESTAC 22–44, por passo da cascata e região (mesma base e cascata
     da Etapa 0: etapa0_04_fluxograma.py, L.BASE_DIR, L.cascade_flags) → tab_e7b1_02_s1_restrito
 (4) PTB não classificados (sem_classif): cenário (i) todos indicados; (ii) todos espontâneos. PR M2 (3 raças, amostra analítica)
     de ptb_ind e ptb_esp; 3.2 (ICR, Wald) de ptb_ind e ptb_esp (amostra com região de saúde) → tab_e7b1_04_{m2,interacao,wald};
     contagem de não classificados por raça nas duas amostras → tab_e7b1_04_naoclass
 (5) RERI recodificado (referência = estrato conjunto de menor risco em cada 2×2; Knol et al. 2011; Knol & VanderWeele 2012)
     para PTB indicado, IC pelo método delta com os gradientes de etapa3_lib._pred (os mesmos usados pelo knol)
     → tab_e7b1_05_reri_recod
"""
import numpy as np
import pandas as pd

import etapa1_lib as E
import etapa3_lib as T
import etapa4_lib as S4
import etapa6_lib as E6
import etapa0_lib as L

log = L.Logger("7b1_01_analises", etapa="etapa7b1")
TB, S = L.TAB, L.STAMP
d = S4.carrega().reset_index(drop=True)

# ---------- (1)
res = {k: [] for k in ("interacao", "wald")}
for rot, mask in [("so_DUM", d.ig_metodo == "DUM"), ("so_outro_metodo", d.ig_metodo == "outro_metodo"),
                  ("sem_CE_DF", ~d.uf.isin(["CE", "DF"])), ("sem_2024", d.ano != 2024)]:
    r = S4.roda_32(d[mask.fillna(False).to_numpy(bool)], "ptb", rot, remap=E6.para_rs)
    for k in res:
        res[k].append(r[k])
    w, it = r["wald"].iloc[0], r["interacao"].query("raca == 'Indigena' and nivel == 'T1'").iloc[0]
    log(f"(1) {rot}: ICR Indígena×T1 PTB = {it.ICR_pp:.2f} ({it.ICR_lo:.2f} a {it.ICR_hi:.2f}); Wald χ² = {w.chi2:.1f}, p = {w.p:.3g}; N = {w.N:,}; G = {w.G}")
for k, v in res.items():
    pd.concat(v).to_csv(TB / f"tab_e7b1_01_cenarios_{k}_v1_{S}.csv", index=False)

# ---------- (4)
st = d.ptb_tipo.astype(str)
nc = (st == "sem_classif").to_numpy()
for cen, alvo in [("i_todos_indicados", "ptb_ind"), ("ii_todos_espontaneos", "ptb_esp")]:
    for desf in ("ptb_ind", "ptb_esp"):
        x = d[desf].astype("Float64").copy()
        x[nc] = 1.0 if desf == alvo else 0.0
        d[f"{desf}__{cen}"] = x.astype("Int8")
assert all(d[c].notna().sum() == d.ptb.notna().sum() for c in d.columns if "__" in c)
cnt = []
for amostra, s in [("analitica", d), ("com_regiao_saude", d[d.CO_REGSAUD.notna()])]:
    for g, x in s.groupby("raca", observed=True):
        ptb_n = int((x.ptb == 1).sum())
        cnt.append(dict(amostra=amostra, raca=g, ptb=ptb_n, nao_classificados=int((x.ptb_tipo.astype(str) == "sem_classif").sum())))
C = pd.DataFrame(cnt)
C["pct_dos_ptb"] = 100 * C.nao_classificados / C.ptb
C.to_csv(TB / f"tab_e7b1_04_naoclass_v1_{S}.csv", index=False)
tot = C.groupby("amostra").nao_classificados.sum()
log(f"(4) não classificados: analítica {tot['analitica']:,}; com região de saúde {tot['com_regiao_saude']:,}\n" + C.round(2).to_string(index=False))
assert tot["analitica"] == 131809 and tot["com_regiao_saude"] == 131801
R_ = T.R
rows = []
for cen in ("i_todos_indicados", "ii_todos_espontaneos"):
    for desf in ("ptb_ind", "ptb_esp"):
        col = f"{desf}__{cen}"
        s = d[d[col].notna()]
        c = E6.para_rs(E.agrega(s, col, ["raca", "idade_cat", "ano", "regiao"]).assign(CODMUNRES=lambda z: z.CODMUNRES.astype(str)))
        assert int(c.n.sum()) == len(s)
        f = E.fit_agg(c, T.M2, "poisson")
        for t in E.termos(f, R_ + "[T."):
            g = t["termo"].split("[T.")[1].rstrip("]")
            rows.append(dict(cenario=cen, desfecho=desf, raca=g, N=len(s), casos=int(s[col].sum()), G=f["G"], PR=t["est"], PR_lo=t["lo"], PR_hi=t["hi"]))
M = pd.DataFrame(rows)
M.to_csv(TB / f"tab_e7b1_04_m2_v1_{S}.csv", index=False)
log("(4) PR M2 (EP região de saúde):\n" + M.round(3).to_string(index=False))
res = {k: [] for k in ("interacao", "wald")}
for cen in ("i_todos_indicados", "ii_todos_espontaneos"):
    for desf in ("ptb_ind", "ptb_esp"):
        r = S4.roda_32(d, f"{desf}__{cen}", cen, remap=E6.para_rs)
        for k in res:
            res[k].append(r[k])
for k, v in res.items():
    pd.concat(v).to_csv(TB / f"tab_e7b1_04_{k}_v1_{S}.csv", index=False)
it = pd.concat(res["interacao"]).query("raca == 'Indigena' and nivel == 'T1'")
log("(4) ICR Indígena×T1:\n" + it[["sensibilidade", "desfecho", "ICR_pp", "ICR_lo", "ICR_hi", "ICR_p"]].round(3).to_string(index=False))

# ---------- (5) RERI recodificado, PTB indicado (amostra e modelo da 3.2 / 6.1a)
s = d[d.ptb_ind.notna() & d.CO_REGSAUD.notna()]
c = E.agrega(s, "ptb_ind", ["raca", "idade_cat", "ano", "regiao", "tercil_reg"])
c["CODMUNRES"] = c.CODMUNRES.astype(str)
c = E6.para_rs(c)
NIV = ["T1", "T2", "T3"]
r = T.knol(c, "tercil_reg", NIV, "T3", mod_main="C(tercil_reg, Treatment('T3'))", rotulo="tercil_reg")
fit, V = r["fit"], r["fit"]["cov"]["cluster"]
c2 = c.copy()
ix = T._ix(c2, "tercil_reg", NIV, "T3")
P, Gd = {}, {}
for g in T.RACAS:
    for m in NIV:
        P[g, m], Gd[g, m] = T._pred(fit, c2, {"raca": g, "tercil_reg": m}, ix, "tercil_reg")
        assert abs(P[g, m] - r["P"][g, m]) < 1e-12
ref61 = pd.read_csv(TB / f"tab_e6_01a_interacao_v1_{S}.csv").query("desfecho == 'ptb_ind'").set_index(["raca", "nivel"])
rows = []
for g in T.RACAS[1:]:
    for m in ("T1", "T2"):
        cel = {("Branca", "T3"): ("Branca", "T3"), ("Branca", m): ("Branca", m), (g, "T3"): (g, "T3"), (g, m): (g, m)}
        Pc = {k: P[k] for k in cel}
        rk = min(Pc, key=Pc.get)                                  # estrato conjunto de menor risco
        dupla = (g if rk[0] == "Branca" else "Branca", "T3" if rk[1] == m else m)
        s1, s2 = (dupla[0], rk[1]), (rk[0], dupla[1])               # um fator trocado em relação à referência
        val = (P[dupla] - P[s1] - P[s2]) / P[rk] + 1
        num = P[dupla] - P[s1] - P[s2]
        grad = (Gd[dupla] - Gd[s1] - Gd[s2]) / P[rk] - num * Gd[rk] / P[rk] ** 2
        se = float(np.sqrt(grad @ V @ grad))
        icr = 100 * ((P[g, m] - P["Branca", m]) - (P[g, "T3"] - P["Branca", "T3"]))
        assert abs(icr - ref61.loc[(g, m)].ICR_pp) < 1e-8          # mesmo modelo da Tabela 3
        rows.append(dict(raca=g, nivel=m, referencia=f"{rk[0]}-{rk[1]}", RERI_recod=val, lo=val - E.Z * se, hi=val + E.Z * se, se=se,
                         RERI_original=ref61.loc[(g, m)].RERI))
RR = pd.DataFrame(rows)
for (g, m), alvo in {("Indigena", "T1"): -0.59, ("Indigena", "T2"): -0.67, ("Parda", "T1"): -0.17}.items():
    v = RR.query("raca == @g and nivel == @m").RERI_recod.iloc[0]
    assert abs(v - alvo) <= 0.02, (g, m, v)
RR.to_csv(TB / f"tab_e7b1_05_reri_recod_v1_{S}.csv", index=False)
log("(5) RERI recodificado, PTB indicado (asserts −0.59 / −0.67 / −0.17 ± 0.02 OK):\n" + RR.round(3).to_string(index=False))

# ---------- (2) S1 restrito a 22–44 semanas (base e cascata da Etapa 0)
b = pd.read_parquet(L.BASE_DIR, columns=["RACACORMAE", "SEMAGESTAC", "ESCMAE", "IDADEMAE", "regiao"])
fl = L.cascade_flags(b)
assert int(fl.incluido.sum()) == 25808740
b["etapa"] = fl.etapa_exclusao.to_numpy()
b["ig2244"] = b.SEMAGESTAC.between(22, 44).fillna(False).to_numpy(bool)
b["ptb"] = (b.SEMAGESTAC < 37).fillna(False).to_numpy(bool)
rows = []
for reg, x in [("Brasil", b)] + [(r_, b[b.regiao == r_]) for r_ in L.REGIOES]:
    for grupo, y in [("incluidos", x[x.etapa == "incluido"]), ("excluidos", x[x.etapa != "incluido"])] + \
                    [(f"excluidos_{k}", x[x.etapa == k]) for k, _ in L.CASCADE]:
        yy = y[y.ig2244]
        rows.append(dict(regiao=reg, grupo=grupo, n=len(y), n_ig_22_44=len(yy), n_ptb_22_44=int(yy.ptb.sum()),
                         ptb_pct_22_44=100 * yy.ptb.mean() if len(yy) else np.nan,
                         n_ig_definida=int(y.SEMAGESTAC.notna().sum()), n_ptb_qualquer_ig=int(y.ptb.sum())))
S1 = pd.DataFrame(rows)
e8 = pd.read_csv(TB / f"tab08_ptb_incluidos_excluidos_v1_{S}.csv").set_index(["regiao", "grupo"])
chk = S1.set_index(["regiao", "grupo"]).join(e8, rsuffix="_e0")
assert (chk.n == chk.n_e0).all() and (chk.n_ig_definida == chk.n_ig_definida_e0).all() and (chk.n_ptb_qualquer_ig == chk.n_ptb).all()
S1.to_csv(TB / f"tab_e7b1_02_s1_restrito_v1_{S}.csv", index=False)
x = S1.query("regiao == 'Brasil' and grupo == 'excluidos'").iloc[0]
log(f"(2) S1 restrito: excluídos com IG 22–44: {x.n_ptb_22_44:,}/{x.n_ig_22_44:,} = {x.ptb_pct_22_44:.2f}% (auditor 7b: 143,071/1,239,937 = 11.54%); "
    f"n, IG definida e PTB sem restrição = tab08 da Etapa 0")
assert (int(x.n_ptb_22_44), int(x.n_ig_22_44)) == (143071, 1239937)
