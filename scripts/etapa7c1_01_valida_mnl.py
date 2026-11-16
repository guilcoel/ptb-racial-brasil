"""
7c.1 Validação de etapa6_lib.fit_mnl contra statsmodels MNLogit. Na Etapa 6 (2026-10-08) ela rodou em linha de comando, sem
script versionado; o código foi recuperado da transcrição da sessão e reescrito aqui como script com log.
Subamostra de 1% (pandas.sample, random_state = 42) dos nascimentos da amostra analítica com PTB classificado (termo / espontâneo /
indicado; os sem classificação ficam fora, como na 6.3), modelo M2 (raça + idade + ano + macrorregião), categoria-base = termo.
 (1) β e EP do modelo: MNLogit individual (Newton) × fit_mnl nas células raça × idade × ano × região × município.
 (2) EP agrupado por região de saúde: MNLogit individual com cov_type = "cluster" (grupos = etapa6_lib.cluster_rs) × fit_mnl nas
     mesmas células com para_rs.
Diferença da Etapa 6: lá o passo (2) foi rodado sem o termo de ano; aqui os dois passos usam o M2 completo, que é o modelo do pacote.
Saída: outputs/tables/tab_e7c1_01_valida_mnl_v1_20261008.csv (parâmetro a parâmetro; só agregados) e log etapa7c1.
"""
import time

import numpy as np
import pandas as pd
import patsy
import statsmodels.api as sm

import etapa3_lib as T
import etapa6_lib as E6
import etapa0_lib as L

log = L.Logger("7c1_01_valida_mnl", etapa="etapa7c1")
t0 = time.time()
d = T.load(["raca", "idade_cat", "regiao", "ptb_tipo", "CODMUNRES"])
d = d[d.ptb_tipo.astype(str) != "sem_classif"].sample(frac=0.01, random_state=42)
d["y"] = d.ptb_tipo.astype(str).map({"nan": 0, "espontaneo": 1, "indicado": 2}).fillna(0).astype(int)
d["cl"] = E6.cluster_rs(d.CODMUNRES)
rhs = T.M2
X = patsy.dmatrix(rhs, d, return_type="dataframe")
g = pd.factorize(d.cl)[0]
r = sm.MNLogit(d.y.to_numpy(), X).fit(disp=0, method="newton", maxiter=100)
rc = sm.MNLogit(d.y.to_numpy(), X).fit(disp=0, method="newton", maxiter=100, cov_type="cluster", cov_kwds={"groups": g})
assert r.mle_retvals["converged"] and rc.mle_retvals["converged"]
c = d.assign(y0=(d.y == 0).astype(float), y1=(d.y == 1).astype(float), y2=(d.y == 2).astype(float)).groupby(
    ["raca", "idade_cat", "ano", "regiao", "CODMUNRES"], observed=True)[["y0", "y1", "y2"]].sum().reset_index()
c["CODMUNRES"] = c.CODMUNRES.astype(str)
assert int(c[["y0", "y1", "y2"]].to_numpy().sum()) == len(d)
f = E6.fit_mnl(E6.para_rs(c), rhs, ["y0", "y1", "y2"])
assert f["names"] == list(X.columns)
b_f = f["params"].to_numpy().T.reshape(-1)                 # ordem: categoria 1 (todos os x), categoria 2
b_s = r.params.to_numpy().T.reshape(-1)
se_mod_f, se_mod_s = np.sqrt(np.diag(f["cov"]["modelo"])), r.bse.to_numpy().T.reshape(-1)
se_cl_f, se_cl_s = np.sqrt(np.diag(f["cov"]["cluster"])), rc.bse.to_numpy().T.reshape(-1)
assert np.allclose(rc.params.to_numpy(), r.params.to_numpy(), rtol=0, atol=1e-10)
cat = np.repeat(["espontaneo", "indicado"], len(X.columns))
P = pd.DataFrame(dict(categoria=cat, termo=list(X.columns) * 2, beta_fit_mnl=b_f, beta_statsmodels=b_s,
                      ep_modelo_fit_mnl=se_mod_f, ep_modelo_statsmodels=se_mod_s, ep_cluster_fit_mnl=se_cl_f, ep_cluster_statsmodels=se_cl_s))
P["dif_beta"] = P.beta_fit_mnl - P.beta_statsmodels
P["dif_rel_ep_modelo"] = P.ep_modelo_fit_mnl / P.ep_modelo_statsmodels - 1
P["dif_rel_ep_cluster"] = P.ep_cluster_fit_mnl / P.ep_cluster_statsmodels - 1
P.to_csv(L.TAB / f"tab_e7c1_01_valida_mnl_v1_{L.STAMP}.csv", index=False)
res = dict(n=len(d), celulas=len(c), parametros=len(P), G=int(f["G"]), G_statsmodels=int(len(np.unique(g))), iter_fit_mnl=int(f["iter"]),
           max_abs_dif_beta=float(P.dif_beta.abs().max()), max_abs_dif_ep_modelo=float((P.ep_modelo_fit_mnl - P.ep_modelo_statsmodels).abs().max()),
           max_rel_dif_ep_modelo=float(P.dif_rel_ep_modelo.abs().max()), max_rel_dif_ep_cluster=float(P.dif_rel_ep_cluster.abs().max()),
           loglik_fit_mnl=float(f["loglik"]), loglik_statsmodels=float(r.llf))
log("validação fit_mnl × statsmodels MNLogit (1%, seed 42, M2): " + "; ".join(f"{k} = {v:.3g}" if isinstance(v, float) else f"{k} = {v}"
                                                                            for k, v in res.items()))
log(f"statsmodels {sm.__version__}; {(time.time() - t0) / 60:.1f} min")
ok = res["max_abs_dif_beta"] < 1e-8 and res["max_rel_dif_ep_modelo"] < 1e-6 and res["max_rel_dif_ep_cluster"] < 1e-6 and res["G"] == res["G_statsmodels"]
log(("OK" if ok else "FALHA") + ": β, EP do modelo e EP por cluster idênticos (|Δβ| < 1e-8; EP com diferença relativa < 1e-6)")
pd.DataFrame([res]).to_csv(L.TAB / f"tab_e7c1_01_valida_mnl_resumo_v1_{L.STAMP}.csv", index=False)
assert ok, res
