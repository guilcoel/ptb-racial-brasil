"""
3.0(b) IC por bootstrap da atenuação M2→M3 e de ΔRP = RP_M2 − RP_M3 (Etapa 2, Brasil).

Bootstrap por município (reamostragem de clusters com reposição), 500 réplicas, seed 42, IC percentil 2.5–97.5.
  clusters = CODMUNRES distintos da amostra analítica, em ordem lexicográfica (G = 5,593)
  sorteio  = numpy.random.default_rng(42).integers(0, G, size=(500, G)); réplica b usa a linha b (0-based)
  peso de cada célula na réplica = nº de vezes que seu município foi sorteado (pesos de frequência)
Modelos (mesmas células e fórmulas da Etapa 2, amostra com estciv_cat completo):
  M2cc = raça + idade_cat + ano + região;  M3 = M2cc + esc_cat + estciv_cat
Ajuste: IRLS de Poisson próprio (log, offset log n, pesos de frequência), partida no beta da amostra completa,
  convergência max|Δβ| < 1e-10. Conferido: com pesos 1 reproduz o statsmodels/Etapa 2.
Atenuação por réplica = (RP_M2 − RP_M3)/(RP_M2 − 1) × 100; instável quando RP_M2 ≈ 1 (ver resumo).
Saídas: tab_e3_00b_bootstrap_replicas (RP por réplica), tab_e3_00b_atenuacao_ic.
Etapa 6b: com --rs, clusters = regiões de saúde (etapa6_lib.cluster_rs: 433 + um por UF para município ignorado),
  mesmo esquema de sorteio (default_rng(42), linha b da matriz 500 × G); saídas com sufixo _rs; log da etapa 6.
"""
import os
os.environ.update({k: "1" for k in ["OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"]})
import sys
import time
from multiprocessing import get_context

import numpy as np
import pandas as pd
import patsy

import etapa1_lib as E
import etapa0_lib as L

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
B = int(ARGS[0]) if ARGS else 500
RS = "--rs" in sys.argv
SUF = "_rs" if RS else ""
NPROC = 8
if RS:
    import etapa6_lib as E6
log = E6.logger("6b_bootstrap_atenuacao_rs") if RS else L.Logger("00b_bootstrap", etapa="etapa3")
V3 = L.PROC / f"sinasc_brasil_2015_2024_v3_{L.STAMP}"
OUT = ["ptb", "ptb_esp", "ptb_ind", "lbw_termo", "pig"]
R = "C(raca, Treatment('Branca'))"
RHS3 = (f"{R} + C(idade_cat, Treatment('20-34')) + C(ano) + C(regiao, Treatment('SE')) + "
        "C(esc_cat, Treatment('5_12mais')) + C(estciv_cat, Treatment('com_companheiro'))")
RACAS = ["Parda", "Preta", "Indigena"]


def irls(X, Y, n, w, b0, tol=1e-10, maxit=50):
    b = b0.copy()
    off = np.log(n)
    for _ in range(maxit):
        eta = X @ b + off
        mu = np.exp(eta)
        z = eta - off + (Y - mu) / mu
        W = w * mu
        XtW = X.T * W
        bn = np.linalg.solve(XtW @ X, XtW @ z)
        if np.max(np.abs(bn - b)) < tol:
            return bn
        b = bn
    raise RuntimeError("IRLS não convergiu")


G_ = {}


def replica(bi):
    w = np.bincount(G_["D"][bi], minlength=G_["G"]).astype(float)[G_["cidx"]]
    b3 = irls(G_["X3"], G_["Y"], G_["n"], w, G_["b3"])
    b2 = irls(G_["X2"], G_["Y"], G_["n"], w, G_["b2"])
    return bi, np.exp(b2[G_["j2"]]), np.exp(b3[G_["j3"]])


def main():
    d = pd.read_parquet(V3, columns=["incl", "ano", "raca", "idade_cat", "esc_cat", "estciv_cat", "regiao", "CODMUNRES"] + OUT,
                        filters=[("incl", "==", True)])
    d["ano"] = d.ano.astype(int)
    d["regiao"] = d.regiao.astype(str).astype("category")
    d["CODMUNRES"] = d.CODMUNRES.astype(str)
    d["raca"] = d.raca.cat.remove_unused_categories()
    if RS:
        d["CODMUNRES"] = E6.cluster_rs(d.CODMUNRES)  # identificador do cluster = região de saúde
    clusters = np.array(sorted(d.CODMUNRES.unique()))
    G = len(clusters)
    D = np.random.default_rng(42).integers(0, G, size=(500, G))[:B]
    log(f"amostra {len(d):,}; clusters G = {G:,}; réplicas = {B}")

    rows, reps = [], []
    t0 = time.time()
    for desf in OUT:
        s = d[d[desf].notna() & d.estciv_cat.notna()]
        c = E.agrega(s, desf, ["raca", "idade_cat", "ano", "regiao", "esc_cat", "estciv_cat"])
        X3 = patsy.dmatrix(RHS3, c, return_type="dataframe")
        keep2 = [i for i, nm in enumerate(X3.columns) if not nm.startswith(("C(esc_cat", "C(estciv_cat"))]
        names2 = [X3.columns[i] for i in keep2]
        X3a = np.ascontiguousarray(X3.to_numpy())
        X2a = np.ascontiguousarray(X3a[:, keep2])
        Y, n = c.Y.to_numpy(), c.n.to_numpy()
        one = np.ones(len(c))
        # partida e conferência contra statsmodels (Etapa 2): pesos 1
        f3 = E.fit_agg(c, RHS3, "poisson")
        f2 = E.fit_agg(c, f"{R} + C(idade_cat, Treatment('20-34')) + C(ano) + C(regiao, Treatment('SE'))", "poisson")
        b3 = irls(X3a, Y, n, one, f3["params"].to_numpy() * 0)
        b2 = irls(X2a, Y, n, one, f2["params"].to_numpy() * 0)
        assert np.max(np.abs(b3 - f3["params"].to_numpy())) < 1e-7 and np.max(np.abs(b2 - f2["params"].to_numpy())) < 1e-7
        j3 = [list(X3.columns).index(f"{R}[T.{g}]") for g in RACAS]
        j2 = [names2.index(f"{R}[T.{g}]") for g in RACAS]
        rp2_full, rp3_full = np.exp(b2[j2]), np.exp(b3[j3])
        cidx = np.searchsorted(clusters, c.CODMUNRES.astype(str).to_numpy())
        assert (clusters[cidx] == c.CODMUNRES.astype(str).to_numpy()).all()
        G_.update(dict(D=D, G=G, cidx=cidx, X3=X3a, X2=X2a, Y=Y, n=n, b3=b3, b2=b2, j3=j3, j2=j2))
        with get_context("fork").Pool(NPROC) as pool:
            res = sorted(pool.map(replica, range(B)))
        for bi, r2, r3 in res:
            for k, g in enumerate(RACAS):
                reps.append(dict(desfecho=desf, replica=bi + 1, raca=g, RP_M2cc=r2[k], RP_M3=r3[k]))
        log(f"{desf}: {B} réplicas em {(time.time() - t0) / 60:.1f} min (acumulado); RP M2cc/M3 Indígena = "
            f"{rp2_full[2]:.4f}/{rp3_full[2]:.4f}")
        for k, g in enumerate(RACAS):
            rows.append(dict(desfecho=desf, raca=g, RP_M2cc=rp2_full[k], RP_M3=rp3_full[k]))

    R_ = pd.DataFrame(reps)
    R_["dRP"] = R_.RP_M2cc - R_.RP_M3
    R_["atenuacao_pct"] = 100 * R_.dRP / (R_.RP_M2cc - 1)
    R_.to_csv(L.TAB / f"tab_e3_00b_bootstrap_replicas{SUF}_v1_{L.STAMP}.csv", index=False)
    P = pd.DataFrame(rows)
    P["dRP"] = P.RP_M2cc - P.RP_M3
    P["atenuacao_pct"] = np.where(P.RP_M2cc > 1, 100 * P.dRP / (P.RP_M2cc - 1), np.nan)
    q = R_.groupby(["desfecho", "raca"]).agg(
        dRP_lo=("dRP", lambda x: x.quantile(0.025)), dRP_hi=("dRP", lambda x: x.quantile(0.975)),
        aten_lo=("atenuacao_pct", lambda x: x.quantile(0.025)), aten_hi=("atenuacao_pct", lambda x: x.quantile(0.975)),
        RP_M2cc_lo=("RP_M2cc", lambda x: x.quantile(0.025)), RP_M2cc_hi=("RP_M2cc", lambda x: x.quantile(0.975)),
        pct_reps_RP_M2_le_1=("RP_M2cc", lambda x: 100 * (x <= 1).mean())).reset_index()
    P = P.merge(q, on=["desfecho", "raca"])
    P.to_csv(L.TAB / f"tab_e3_00b_atenuacao_ic{SUF}_v1_{L.STAMP}.csv", index=False)
    log("tabela de atenuação com IC gravada")


if __name__ == "__main__":
    main()
