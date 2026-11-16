"""
etapa1_lib.py — utilitários da Etapa 1: leitura da base v2, IC de Wilson, formatação e
estimação de RP / OR / diferença absoluta a partir de dados AGREGADOS.

Estimação agregada (exata, não aproximada):
  células c = padrão de covariáveis × município, com Y_c casos em n_c nascimentos.
  - RP: Poisson log-link, GLM(Y_c, X_c, offset = log n_c)  -> mesmo beta do Poisson individual
  - OR: Binomial logit, GLM([Y_c, n_c − Y_c], X_c)          -> mesmo beta da logística individual
  - DA: identidade (modelo linear de probabilidade), WLS de Y_c/n_c com peso n_c
  O score individual de uma família canônica é x_i (y_i − mu_i). Por isso:
    bread A  = Σ_c n_c w(mu_c) x_c x_c'         (w = mu p/ Poisson, mu(1−mu) p/ logit, 1 p/ identidade)
    HC0  M   = Σ_c x_c x_c' [Y_c (1−mu_c)² + (n_c − Y_c) mu_c²]     (= Σ_i x_i x_i' (y_i − mu_i)²)
    cluster  = Σ_g s_g s_g',  s_g = Σ_{c∈g} x_c (Y_c − n_c mu_c)     (= Σ_{i∈g} x_i (y_i − mu_i))
  com a mesma correção de pequena amostra do statsmodels: G/(G−1) · (N−1)/(N−K), N = Σ n_c.
  'modelo' = inversa da informação de Fisher (= EP do GLM individual).
"""
import numpy as np
import pandas as pd
import patsy
import statsmodels.api as sm
from scipy import stats

import etapa0_lib as L

V2_DIR = L.PROC / f"sinasc_brasil_2015_2024_v2_{L.STAMP}"
Z = stats.norm.ppf(0.975)


def logger(name):
    return L.Logger(name, etapa="etapa1")


def load(cols, filters=None, incl=True):
    f = [("incl", "==", True)] if incl else []
    if filters:
        f += filters
    d = pd.read_parquet(V2_DIR, columns=list(dict.fromkeys(cols + ["incl"])), filters=f or None)
    if "ano" in d:
        d["ano"] = d["ano"].astype(int)
    for c in d.columns:  # texto -> categoria (patsy não lê o dtype string do pandas)
        if pd.api.types.is_string_dtype(d[c]) and not isinstance(d[c].dtype, pd.CategoricalDtype):
            d[c] = d[c].astype(str).astype("category")
    return d


def wilson(k, n, z=Z):
    k, n = np.asarray(k, float), np.asarray(n, float)
    with np.errstate(invalid="ignore", divide="ignore"):
        p = k / n
        den = 1 + z ** 2 / n
        cen = (p + z ** 2 / (2 * n)) / den
        half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / den
    return p, cen - half, cen + half


def fmt_n(x):
    return "" if pd.isna(x) else f"{int(x):,}"


def fmt_f(x, d=2):
    return "" if pd.isna(x) else f"{x:,.{d}f}"


def agrega(d, y, covars, cluster="CODMUNRES"):
    """Contagens por padrão de covariáveis × município (só linhas com desfecho definido)."""
    s = d[d[y].notna()]
    g = s.groupby(covars + [cluster], observed=True)[y]
    a = pd.concat([g.sum().rename("Y"), g.size().rename("n")], axis=1).reset_index()
    a["Y"] = a["Y"].astype(float)
    a["n"] = a["n"].astype(float)
    return a


def fit_agg(cells, rhs, family, cluster="CODMUNRES"):
    """family in {'poisson','logit','identity'}. Devolve params e matrizes de covariância."""
    X = patsy.dmatrix(rhs, cells, return_type="dataframe")
    Y, n = cells["Y"].to_numpy(), cells["n"].to_numpy()
    if family == "poisson":
        res = sm.GLM(Y, X, family=sm.families.Poisson(), offset=np.log(n)).fit()
        mu = np.exp(X.to_numpy() @ res.params.to_numpy())
        w = mu
    elif family == "logit":
        res = sm.GLM(np.column_stack([Y, n - Y]), X, family=sm.families.Binomial()).fit()
        mu = 1 / (1 + np.exp(-(X.to_numpy() @ res.params.to_numpy())))
        w = mu * (1 - mu)
    elif family == "identity":
        res = sm.WLS(Y / n, X, weights=n).fit()
        mu = X.to_numpy() @ res.params.to_numpy()
        w = np.ones_like(mu)
    else:
        raise ValueError(family)
    Xa = X.to_numpy()
    N, K = n.sum(), Xa.shape[1]
    A = (Xa * (n * w)[:, None]).T @ Xa
    Ainv = np.linalg.inv(A)
    M0 = (Xa * (Y * (1 - mu) ** 2 + (n - Y) * mu ** 2)[:, None]).T @ Xa
    S = pd.DataFrame(Xa * (Y - n * mu)[:, None]).groupby(cells[cluster].to_numpy()).sum().to_numpy()
    G = S.shape[0]
    Mc = S.T @ S * (G / (G - 1)) * ((N - 1) / (N - K))
    if family == "identity":
        V_mod = Ainv * (Y * (1 - mu) ** 2 + (n - Y) * mu ** 2).sum() / (N - K)  # OLS individual
    else:
        V_mod = Ainv
    cov = {"modelo": V_mod, "hc0": Ainv @ M0 @ Ainv, "cluster": Ainv @ Mc @ Ainv}
    return dict(params=res.params, cov=cov, names=list(X.columns), n_cells=len(cells), N=N, G=G, res=res,
                design_info=X.design_info, family=family)


def marginal(fit, cells, var, niveis, ref, cov="cluster"):
    """Padronização marginal sobre a distribuição de covariáveis das células (pesos n_c):
    P_g = Σ n_c mu_c(var = g) / Σ n_c. Diferença P_g − P_ref com IC pelo método delta (cov dada).
    Só para família poisson (log) ou logit."""
    beta = fit["params"].to_numpy()
    n = cells["n"].to_numpy()
    N = n.sum()
    P, G = {}, {}
    for g in niveis:
        cg = cells.copy()
        cg[var] = pd.Categorical([g] * len(cg), categories=cells[var].cat.categories)
        Xg = np.asarray(patsy.build_design_matrices([fit["design_info"]], cg)[0])
        eta = Xg @ beta
        if fit["family"] == "poisson":
            mu = np.exp(eta)
            dmu = mu
        else:
            mu = 1 / (1 + np.exp(-eta))
            dmu = mu * (1 - mu)
        P[g] = (n * mu).sum() / N
        G[g] = (Xg * (n * dmu)[:, None]).sum(axis=0) / N
    V = fit["cov"][cov]
    out = []
    for g in niveis:
        if g == ref:
            continue
        diff = P[g] - P[ref]
        gr = G[g] - G[ref]
        se = float(np.sqrt(gr @ V @ gr))
        out.append(dict(nivel=g, p_nivel=P[g], p_ref=P[ref], dif=diff, dif_lo=diff - Z * se, dif_hi=diff + Z * se))
    return out


def termos(fit, prefix, cov="cluster", expo=True):
    """Linhas (termo, estimativa, IC) para os coeficientes cujo nome começa com prefix."""
    out = []
    for j, nm in enumerate(fit["names"]):
        if not nm.startswith(prefix):
            continue
        b = fit["params"].iloc[j]
        se = np.sqrt(fit["cov"][cov][j, j])
        lo, hi = b - Z * se, b + Z * se
        p = 2 * stats.norm.sf(abs(b / se))
        if expo:
            b, lo, hi = np.exp(b), np.exp(lo), np.exp(hi)
        out.append(dict(termo=nm, est=b, lo=lo, hi=hi, p=p, se=se, cov=cov))
    return out
