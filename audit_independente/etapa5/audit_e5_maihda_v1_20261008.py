#!/usr/bin/env python3
"""Auditoria independente da Etapa 5 (MAIHDA, desfecho PIG) — ptb-racial-brasil.

Reproducao independente: agregacao em DuckDB + logistica binomial com intercepto
aleatorio de estrato ajustada por maxima verossimilhanca marginal com quadratura
de Gauss-Hermite ADAPTATIVA (implementacao propria em numpy/scipy).
Nao usa lme4. Somente agregados saem do DuckDB. seed 42.
"""
import sys, time, json
import numpy as np
import pandas as pd
import duckdb
from scipy import optimize
from scipy.special import expit, gammaln, logsumexp

np.random.seed(42)
BASE = "/Volumes/Forja/ptb-racial-brasil"
OUT = f"{BASE}/audit_independente/etapa5"
TAG = "v1_20261008"
LOG = open(f"{OUT}/audit_e5_log_{TAG}.txt", "w")


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s); LOG.write(s + "\n"); LOG.flush()


t0 = time.time()
# ---------------------------------------------------------------- 1. estratos
con = duckdb.connect()
src = (f"read_parquet('{BASE}/data/processed/sinasc_brasil_2015_2024_v3_20261008/"
       f"ano=*/part-0.parquet', hive_partitioning=true)")
ter = (f"read_csv('{BASE}/data/processed/tercil_reg_regsaude_ano_v1_20261008.csv', "
       f"header=true, types={{'CO_REGSAUD':'VARCHAR','ano':'BIGINT','tercil_reg':'VARCHAR'}})")

con.sql(f"""
create temp table base as
select b.ano, b.raca,
  case when b.esc_cat in ('1_nenhuma','2_1a3anos','3_4a7anos') then 'Ate7'
       when b.esc_cat = '4_8a11anos' then '8a11'
       when b.esc_cat = '5_12mais' then '12mais' end as esc3,
  b.idade_cat, b.regiao, t.tercil_reg, t.regiao as regiao_csv, b.pig, b.CO_REGSAUD
from {src} b
left join {ter} t on t.CO_REGSAUD = b.CO_REGSAUD and t.ano = b.ano  -- coluna ano do CSV ja e o ano do nascimento (indice defasado t-1); correcao do coordenador
where b.incl and b.pig is not null
""")
# fluxo de exclusao (agregados)
flux = con.sql("""select ano, count(*) n_elig,
   sum((CO_REGSAUD is null)::int) sem_regsaud,
   sum((tercil_reg is null)::int) sem_tercil,
   sum((regiao_csv is not null and regiao_csv<>regiao)::int) regiao_discordante,
   sum((esc3 is null or idade_cat is null or raca is null or regiao is null)::int) cat_nula
   from base group by 1 order by 1""").df()
log("Fluxo (incl & pig nao nulo):\n" + flux.to_string(index=False))

agg = con.sql("""
select raca, esc3, idade_cat, regiao, tercil_reg, count(*)::BIGINT n, sum(pig)::BIGINT casos
from base where tercil_reg is not null and esc3 is not null and idade_cat is not null
  and raca is not null and regiao is not null
group by all order by all""").df()
agg["estrato"] = (agg.raca + "|" + agg.esc3 + "|" + agg.idade_cat + "|" + agg.regiao
                  + "|" + agg.tercil_reg)
agg["pct_obs"] = 100 * agg.casos / agg.n
agg = agg[["estrato", "raca", "esc3", "idade_cat", "regiao", "tercil_reg", "n", "casos",
           "pct_obs"]]
agg.to_csv(f"{OUT}/audit_e5_estratos_{TAG}.csv", index=False)
N, Y, J = int(agg.n.sum()), int(agg.casos.sum()), len(agg)
qs = np.percentile(agg.n, [0, 10, 25, 50])
log(f"\nN={N}  casos={Y} ({100*Y/N:.3f}%)  estratos={J}")
log(f"n min={agg.n.min()} P10={qs[1]:.1f} P25={qs[2]:.1f} mediana={qs[3]:.1f} max={agg.n.max()}")
log(f"estratos com n<10: {(agg.n<10).sum()}, n<50: {(agg.n<50).sum()}, casos=0: {(agg.casos==0).sum()}")
log(f"[agregacao {time.time()-t0:.0f}s]")

# ---------------------------------------------------------------- 2. modelos
y = agg.casos.to_numpy(float); n = agg.n.to_numpy(float)
lbin = gammaln(n + 1) - gammaln(y + 1) - gammaln(n - y + 1)  # constante binomial


def design(full):
    cols = ["(Intercept)"]; X = [np.ones(J)]
    if full:
        spec = [("raca", "Branca", ["Preta", "Parda", "Indigena"]),
                ("esc3", "12mais", ["Ate7", "8a11"]),
                ("idade_cat", "20-34", ["<20", ">=35"]),
                ("regiao", "SE", ["N", "NE", "S", "CO"]),
                ("tercil_reg", "T3", ["T1", "T2"])]
        for v, ref, levs in spec:
            for l in levs:
                X.append((agg[v] == l).to_numpy(float)); cols.append(f"{v}{l}")
    return np.column_stack(X), cols


def cond_mode(eta, sig2, u0=None, it=100):
    """Modo de h(u)=y(eta+u)-n log(1+e^{eta+u}) - u^2/(2 sig2), Newton vetorizado."""
    u = np.zeros_like(eta) if u0 is None else u0.copy()
    for _ in range(it):
        p = expit(eta + u)
        g = y - n * p - u / sig2
        H = -n * p * (1 - p) - 1 / sig2
        step = np.clip(g / H, -2, 2)
        u -= step
        if np.max(np.abs(step)) < 1e-12:
            break
    p = expit(eta + u)
    H = -n * p * (1 - p) - 1 / sig2
    return u, H


def loglik_cond(eta_u):
    # y*log p + (n-y) log(1-p), estavel
    yy, nn = (y, n) if eta_u.ndim == 1 else (y[:, None], n[:, None])
    return yy * eta_u - nn * np.logaddexp(0, eta_u)


class AGHQ:
    def __init__(self, X, K):
        self.X, self.K = X, K
        z, w = np.polynomial.hermite.hermgauss(K)
        self.z, self.lw = z, np.log(w) + z ** 2   # peso com e^{z^2}
        self.ucache = None

    def nll(self, th, ret=False):
        b, ls = th[:-1], th[-1]
        sig2 = np.exp(2 * ls)
        eta = self.X @ b
        u, H = cond_mode(eta, sig2, self.ucache)
        self.ucache = u
        s = 1 / np.sqrt(-H)
        if self.K == 1:   # Laplace
            ll = (loglik_cond(eta + u) - u ** 2 / (2 * sig2) - 0.5 * np.log(sig2)
                  + np.log(s))
            lj = ll + lbin
            if ret:
                return -lj.sum(), u, u, s
            return -lj.sum()
        U = u[:, None] + np.sqrt(2) * s[:, None] * self.z[None, :]
        lf = (loglik_cond(eta[:, None] + U) - U ** 2 / (2 * sig2)
              - 0.5 * np.log(2 * np.pi * sig2))
        a = self.lw[None, :] + lf
        lj = np.log(np.sqrt(2) * s) + logsumexp(a, axis=1) + lbin
        if ret:
            wpost = np.exp(a - logsumexp(a, axis=1, keepdims=True))
            umean = (wpost * U).sum(1)
            usd = np.sqrt((wpost * (U - umean[:, None]) ** 2).sum(1))
            return -lj.sum(), u, umean, usd
        return -lj.sum()


def num_grad(f, x, h=1e-6):
    g = np.zeros_like(x)
    for i in range(len(x)):
        e = np.zeros_like(x); e[i] = h
        g[i] = (f(x + e) - f(x - e)) / (2 * h)
    return g


def num_hess(f, x, h=1e-4):
    k = len(x); Hm = np.zeros((k, k))
    for i in range(k):
        for j in range(i, k):
            ei = np.zeros(k); ej = np.zeros(k); ei[i] = h; ej[j] = h
            Hm[i, j] = Hm[j, i] = (f(x + ei + ej) - f(x + ei - ej) - f(x - ei + ej)
                                   + f(x - ei - ej)) / (4 * h * h)
    return Hm


def fit(full, K):
    X, cols = design(full)
    m = AGHQ(X, K)
    # partida: GLM agregado sem efeito aleatorio
    def glm_nll(b):
        return -loglik_cond(X @ b).sum()
    b0 = optimize.minimize(glm_nll, np.r_[np.log(Y / (N - Y)), np.zeros(X.shape[1] - 1)],
                           method="BFGS").x
    th0 = np.r_[b0, np.log(0.3)]
    f = lambda th: m.nll(th)
    best = None
    for meth in ("L-BFGS-B", "BFGS", "Nelder-Mead"):
        start = th0 if best is None else best.x
        opts = {"maxiter": 20000, "gtol": 1e-9} if meth != "Nelder-Mead" else \
               {"maxiter": 40000, "xatol": 1e-9, "fatol": 1e-10}
        if meth == "L-BFGS-B":
            opts = {"maxiter": 20000, "gtol": 1e-10, "ftol": 1e-15}
        r = optimize.minimize(f, start, method=meth, options=opts,
                              jac=(lambda th: num_grad(f, th)) if meth != "Nelder-Mead" else None)
        if best is None or r.fun < best.fun - 1e-10:
            best = r
    th = best.x
    # polimento por Newton com hessiana numerica
    for _ in range(5):
        g = num_grad(f, th); Hm = num_hess(f, th)
        step = np.linalg.solve(Hm, g)
        if f(th - step) < f(th):
            th = th - step
        if np.max(np.abs(step)) < 1e-9:
            break
    g = num_grad(f, th); Hm = num_hess(f, th)
    cov = np.linalg.inv(Hm)
    nll, umode, umean, usd = m.nll(th, ret=True)
    return dict(th=th, cols=cols, X=X, nll=nll, grad=g, cov=cov, umode=umode,
                umean=umean, usd=usd, sig2=np.exp(2 * th[-1]))


def auc_strata(p):
    # P(p_caso > p_naocaso) + 0.5 P(empate), pesos casos/nao casos por estrato
    nc = n - y
    gt = (p[:, None] > p[None, :]).astype(float)
    eq = (p[:, None] == p[None, :]).astype(float)
    return float((y[:, None] * nc[None, :] * (gt + 0.5 * eq)).sum() / (Y * (N - Y)))


PI2_3 = np.pi ** 2 / 3
res = {}
for full, nome in [(False, "M1"), (True, "M2")]:
    for K in (1, 25, 50):
        t1 = time.time()
        r = fit(full, K)
        r["vpc"] = 100 * r["sig2"] / (r["sig2"] + PI2_3)
        p_mode = expit(r["X"] @ r["th"][:-1] + r["umode"])
        r["p_mode"] = p_mode
        r["auc"] = auc_strata(p_mode)
        r["p_mean"] = expit(r["X"] @ r["th"][:-1] + r["umean"])
        r["auc_mean"] = auc_strata(r["p_mean"])
        res[(nome, K)] = r
        log(f"\n{nome} K={K}: -logL={r['nll']:.4f} sigma2={r['sig2']:.6f} "
            f"VPC={r['vpc']:.4f}% AUC(modo)={r['auc']:.5f} AUC(media)={r['auc_mean']:.5f} "
            f"|grad|max={np.max(np.abs(r['grad'])):.2e} [{time.time()-t1:.0f}s]")

rows = []
for (nome, K), r in res.items():
    rows.append(dict(modelo=nome, nos=K, metodo="Laplace" if K == 1 else "AGHQ",
                     neg_loglik=r["nll"], deviance=2 * r["nll"], s2=r["sig2"],
                     sigma=np.sqrt(r["sig2"]), VPC_pct=r["vpc"], AUC=r["auc"],
                     AUC_media_post=r["auc_mean"], grad_max=np.max(np.abs(r["grad"]))))
par = pd.DataFrame(rows)
for K in (1, 25, 50):
    s1 = par.query("modelo=='M1' and nos==@K").s2.iloc[0]
    s2 = par.query("modelo=='M2' and nos==@K").s2.iloc[0]
    par.loc[par.nos == K, "PCV_pct"] = 100 * (s1 - s2) / s1
par.to_csv(f"{OUT}/audit_e5_parametros_{TAG}.csv", index=False)
log("\nParametros:\n" + par.to_string(index=False))

KP = 25  # principal
fx = []
for nome in ("M1", "M2"):
    for K in (1, KP):
        r = res[(nome, K)]
        se = np.sqrt(np.diag(r["cov"]))
        for i, c in enumerate(r["cols"]):
            b = r["th"][i]
            fx.append(dict(modelo=nome, nos=K, termo=c, beta=b, se=se[i], OR=np.exp(b),
                           OR_lo=np.exp(b - 1.959964 * se[i]), OR_hi=np.exp(b + 1.959964 * se[i])))
        fx.append(dict(modelo=nome, nos=K, termo="log_sigma", beta=r["th"][-1], se=se[-1]))
fx = pd.DataFrame(fx)
fx.to_csv(f"{OUT}/audit_e5_efeitos_fixos_{TAG}.csv", index=False)
log("\nEfeitos fixos M2 (AGHQ K=25):\n" +
    fx.query("modelo=='M2' and nos==@KP").to_string(index=False))

r2, r1 = res[("M2", KP)], res[("M1", KP)]
r2L = res[("M2", 1)]
pred = agg.copy()
pred["xb_M2"] = r2["X"] @ r2["th"][:-1]
pred["u_modo_M2"] = r2["umode"]; pred["u_media_M2"] = r2["umean"]; pred["u_sd_M2"] = r2["usd"]
pred["p_pct_M2"] = 100 * r2["p_mode"]; pred["p_pct_M2_mediaU"] = 100 * r2["p_mean"]
pred["u_modo_M2_laplace"] = r2L["umode"]; pred["p_pct_M2_laplace"] = 100 * r2L["p_mode"]
pred["u_modo_M1"] = r1["umode"]; pred["p_pct_M1"] = 100 * r1["p_mode"]
pred = pred.sort_values("p_pct_M2", ascending=False)
pred.to_csv(f"{OUT}/audit_e5_predicoes_{TAG}.csv", index=False)

top15 = pred.head(15)[["estrato", "n", "casos", "pct_obs", "p_pct_M2", "u_modo_M2"]]
log("\nTop 15 p_j (M2, AGHQ K=25, modo):\n" + top15.to_string(index=False))
topu = pred.sort_values("u_modo_M2", ascending=False).head(5)[
    ["estrato", "n", "casos", "pct_obs", "p_pct_M2", "u_modo_M2", "u_media_M2", "u_sd_M2"]]
log("\nTop 5 u_j (M2):\n" + topu.to_string(index=False))
log(f"\nmax |u_modo - u_media| M2 = {np.max(np.abs(r2['umode']-r2['umean'])):.3e}")
log(f"[total {time.time()-t0:.0f}s]")
LOG.close()
