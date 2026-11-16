"""
etapa6_lib.py — agrupamento do EP por REGIÃO DE SAÚDE de residência (433), sem tocar nos estimadores validados.

etapa1_lib.fit_agg soma os escores por cells[cluster] (padrão "CODMUNRES"). Como o município está aninhado na região de
saúde (DATASUS, base territorial dez/2024; nenhum município em 2 regiões), basta substituir a coluna CODMUNRES das
células pelo identificador do cluster: mesma estimativa pontual, sanduíche agrupado por região.
Sem região de saúde (os 533 com município ignorado, código UF0000): um cluster por UF ("UF_<2 dígitos>").
"""
import pandas as pd

import etapa0_lib as L

MAPA = pd.read_csv(L.PROC / f"municipio_regsaude_dez24_v1_{L.STAMP}.csv", dtype=str).set_index("CODMUNRES").CO_REGSAUD
assert MAPA.index.is_unique


def cluster_rs(cod):
    cod = pd.Series(cod, copy=False).astype(str)
    rs = cod.map(MAPA)
    return rs.where(rs.notna(), "UF_" + cod.str[:2]).to_numpy()


def para_rs(cells):
    """Cópia das células com CODMUNRES = cluster de região de saúde (ou UF_xx)."""
    c = cells.copy()
    c["CODMUNRES"] = cluster_rs(c.CODMUNRES)
    return c


def fit_mnl(cells, rhs, ycols, cluster="CODMUNRES", tol=1e-10, maxit=50):
    """Logit multinomial de categoria-base sobre células agregadas (contagens ycols[0] = base, ycols[1:] = demais).
    Newton–Raphson na verossimilhança multinomial exata (= individual). Covariâncias: modelo (inversa da informação),
    e sanduíche agrupado por cells[cluster] com a mesma correção de etapa1_lib.fit_agg: G/(G−1)·(N−1)/(N−K).
    Devolve params (K × J), cov (KJ × KJ, ordem: categoria 1 [todos os x], categoria 2 [...]), nomes."""
    import numpy as np
    import patsy
    X = patsy.dmatrix(rhs, cells, return_type="dataframe")
    Xa = X.to_numpy()
    Yall = cells[list(ycols)].to_numpy(float)
    n = Yall.sum(1)
    Y = Yall[:, 1:]
    K, J = Xa.shape[1], Y.shape[1]
    B = np.zeros((K, J))
    p0 = Y.sum(0) / n.sum()
    B[0] = np.log(p0 / (1 - p0.sum()))  # intercepto = marginais (supõe 1ª coluna = intercepto)
    for it in range(maxit):
        eta = Xa @ B
        m = eta.max(1, keepdims=True)
        e = np.exp(eta - m)
        pi = e / (np.exp(-m) + e.sum(1, keepdims=True))
        R = Y - n[:, None] * pi
        g = (Xa.T @ R).T.reshape(-1)  # J blocos de K
        A = np.zeros((K * J, K * J))
        for a in range(J):
            for b in range(J):
                w = n * (pi[:, a] * ((a == b) - pi[:, b]))
                A[a * K:(a + 1) * K, b * K:(b + 1) * K] = (Xa * w[:, None]).T @ Xa
        step = np.linalg.solve(A, g)
        B = B + step.reshape(J, K).T
        if np.max(np.abs(step)) < tol:
            break
    else:
        raise RuntimeError("fit_mnl não convergiu")
    eta = Xa @ B
    m = eta.max(1, keepdims=True)
    e = np.exp(eta - m)
    pi = e / (np.exp(-m) + e.sum(1, keepdims=True))
    R = Y - n[:, None] * pi
    for a in range(J):
        for b in range(J):
            w = n * (pi[:, a] * ((a == b) - pi[:, b]))
            A[a * K:(a + 1) * K, b * K:(b + 1) * K] = (Xa * w[:, None]).T @ Xa
    Ainv = np.linalg.inv(A)
    Sc = np.hstack([Xa * R[:, [a]] for a in range(J)])
    S = pd.DataFrame(Sc).groupby(cells[cluster].to_numpy()).sum().to_numpy()
    G, N, KJ = S.shape[0], n.sum(), K * J
    Mc = S.T @ S * (G / (G - 1)) * ((N - 1) / (N - KJ))
    ll = float((Y * np.log(pi)).sum() + ((n - Y.sum(1)) * np.log(1 - pi.sum(1))).sum())
    return dict(params=pd.DataFrame(B, index=X.columns, columns=list(ycols[1:])), names=list(X.columns),
                cov={"modelo": Ainv, "cluster": Ainv @ Mc @ Ainv}, N=N, G=G, iter=it + 1, loglik=ll, K=K, J=J)


def logger(name):
    return L.Logger(name, etapa="etapa6")
