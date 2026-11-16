"""
1.5b Validação do estimador AGREGADO no Centro-Oeste.

Referências (RSP 2026;60:e44, Base B; arquivos do projeto Racial-PTB-SINASC):
  publicado (Tabela 2):  OR com EP do modelo; RP com sandwich HC0 individual (sem cluster)
  or_vs_rr_comparison.csv: as mesmas OR/RP com EP clusterizado por CODMUNRES (3 casas)
Modelos: M1 = raça; M5 = raça + idade_cat + esc_cat (ESCMAE 1–5) + ano + UF.
Também ajusta no nível individual (statsmodels, 2,156,674 linhas) e compara com o agregado.
Saída: tab_e1_05b_validacao_co.
"""
import numpy as np
import pandas as pd
import patsy
import statsmodels.api as sm

import etapa1_lib as E

log = E.logger("05a_valid_co")
RACE = "C(raca, Treatment('Branca'))"
RHS = {"M1": RACE, "M5": RACE + " + C(idade_cat) + C(esc_cat) + C(ano) + C(uf)"}
PREF = RACE + "[T."
PUB = {  # (modelo, medida, raça): (est, lo, hi, casas)
    ("M1", "OR", "Indigena"): (1.709, 1.663, 1.757, 3), ("M1", "OR", "Preta"): (1.053, 1.032, 1.074, 3),
    ("M1", "OR", "Parda"): (0.991, 0.981, 1.000, 3), ("M1", "RP", "Indigena"): (1.58, 1.55, 1.62, 2),
    ("M5", "OR", "Indigena"): (1.504, 1.461, 1.549, 3), ("M5", "RP", "Indigena"): (1.41, 1.38, 1.45, 2)}
CLU = {  # or_vs_rr_comparison.csv (cluster por CODMUNRES)
    ("M1", "OR", "Parda"): (0.991, 0.962, 1.020), ("M1", "OR", "Preta"): (1.053, 1.019, 1.088),
    ("M1", "OR", "Indigena"): (1.709, 1.403, 2.083), ("M5", "OR", "Parda"): (0.989, 0.960, 1.019),
    ("M5", "OR", "Preta"): (1.035, 1.006, 1.064), ("M5", "OR", "Indigena"): (1.504, 1.248, 1.813),
    ("M1", "RP", "Parda"): (0.992, 0.966, 1.017), ("M1", "RP", "Preta"): (1.047, 1.017, 1.077),
    ("M1", "RP", "Indigena"): (1.584, 1.346, 1.864), ("M5", "RP", "Parda"): (0.990, 0.965, 1.016),
    ("M5", "RP", "Preta"): (1.031, 1.006, 1.057), ("M5", "RP", "Indigena"): (1.414, 1.213, 1.648)}
FAM = {"OR": "logit", "RP": "poisson"}

d = E.load(["raca", "idade_cat", "esc_cat", "ano", "uf", "CODMUNRES", "ptb", "regiao"], [("regiao", "==", "CO")])
d["raca"] = d["raca"].cat.remove_unused_categories()
log("CO incluídos", len(d))
cells = E.agrega(d, "ptb", ["raca", "idade_cat", "esc_cat", "ano", "uf"])
log(f"células (padrão × município): {len(cells):,}; Σn = {int(cells.n.sum()):,}; ΣY = {int(cells.Y.sum()):,}")
assert int(cells.n.sum()) == len(d) and int(cells.Y.sum()) == int(d.ptb.sum())

rows = []
for m in ("M1", "M5"):
    for med in ("OR", "RP"):
        fa = E.fit_agg(cells, RHS[m], FAM[med])
        # individual
        X = patsy.dmatrix(RHS[m], d, return_type="dataframe")
        y = d["ptb"].astype(float).to_numpy()
        fam = sm.families.Binomial() if med == "OR" else sm.families.Poisson()
        ind = {"modelo": sm.GLM(y, X, family=fam).fit()}
        ind["hc0"] = sm.GLM(y, X, family=fam).fit(cov_type="HC0")
        ind["cluster"] = sm.GLM(y, X, family=fam).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.CODMUNRES)[0]})
        log(f"{m} {med}: ajustes agregado e individual feitos")
        for cov in ("modelo", "hc0", "cluster"):
            for t in E.termos(fa, PREF, cov=cov):
                g = t["termo"].split("[T.")[1].rstrip("]")
                ri = ind[cov]
                j = list(ri.params.index).index(t["termo"])
                b, se = ri.params.iloc[j], ri.bse.iloc[j]
                row = dict(modelo=m, medida=med, raca=g, ep=cov, agg_est=t["est"], agg_lo=t["lo"], agg_hi=t["hi"],
                           ind_est=np.exp(b), ind_lo=np.exp(b - E.Z * se), ind_hi=np.exp(b + E.Z * se))
                row["max_absdif_agg_ind"] = max(abs(row["agg_est"] - row["ind_est"]), abs(row["agg_lo"] - row["ind_lo"]),
                                                abs(row["agg_hi"] - row["ind_hi"]))
                ref, casas = None, 3
                if cov == ("modelo" if med == "OR" else "hc0") and (m, med, g) in PUB:
                    *ref, casas = PUB[(m, med, g)]
                    row["referencia"] = "publicado (Tabela 2)"
                elif cov == "cluster" and (m, med, g) in CLU:
                    ref = CLU[(m, med, g)]
                    row["referencia"] = "or_vs_rr_comparison (cluster)"
                if ref:
                    obt = tuple(round(row[k], casas) for k in ("agg_est", "agg_lo", "agg_hi"))
                    row.update(ref_est=ref[0], ref_lo=ref[1], ref_hi=ref[2], casas=casas,
                               agg_arred=f"{obt[0]} ({obt[1]}–{obt[2]})", bate=obt == tuple(ref))
                rows.append(row)

t = pd.DataFrame(rows)
t.to_csv(E.L.TAB / f"tab_e1_05b_validacao_co_v1_{E.L.STAMP}.csv", index=False)
r = t[t.referencia.notna()]
for _, x in r.iterrows():
    log(f"{x.modelo} {x.medida} {x.raca} [{x.ep}] agg={x.agg_arred} ref={x.ref_est} ({x.ref_lo}–{x.ref_hi}) bate={x.bate}")
log(f"comparações com referência: {int(r.bate.sum())}/{len(r)} batem; "
    f"máx |agregado − individual| = {t.max_absdif_agg_ind.max():.2e}")
