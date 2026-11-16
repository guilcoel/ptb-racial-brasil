"""
4.6 Raça/cor ignorada — imputação múltipla (m = 10) da raça das mães com RACACORMAE nula que passam nos demais
critérios da cascata (IG 22–44, ESCMAE 1–5, IDADEMAE 10–60): 849,059 registros.

Fonte da composição municipal: IBGE, Censo Demográfico 2022, SIDRA tabela 9605 (população residente por cor ou
raça), N6, variável 93; URL, data e MD5 em docs/referencias/censo2022/ACESSO.txt.

Modelo de imputação (multinomial, 5 categorias: Branca, Preta, Amarela, Parda, Indígena), ajustado nos registros
com raça observada que passam nos demais critérios (inclui Amarela), sobre PADRÕES agregados de covariáveis:
  região, ano, idade_cat, esc_cat, estciv_cat (+ ausente), tipo de PTB (termo / espontâneo / indicado /
  sem classificação), PIG (0 / 1 / não elegível), tercil_reg (+ sem região), faixa de composição municipal
  (% Branca em 5 faixas × % Indígena em 4 faixas, Censo 2022), e interações tipo de PTB × tercil, PIG × tercil,
  região × faixa de composição.
  Desvio declarado: o município entra pela composição racial (faixas), não como efeito fixo de 5,593 níveis.
Incerteza dos parâmetros: a cada imputação, contagens observadas reamostradas por Poisson(n) (bootstrap
  individual); sorteio multinomial da raça por célula (padrão × município) com as probabilidades previstas.
Análise: 3.2 (etapa3_lib.knol) em observados + imputados (Amarela imputada fica fora), desfechos ptb, ptb_esp,
  ptb_ind, pig. Rubin: ICR (p.p.) com variância W + (1 + 1/m) B, gl de Rubin (1987): (m − 1)/λ².
Uso: python3 etapa4_06_imputacao_raca.py M [--rs]   (M = nº de imputações; 1 = medida de viabilidade;
  --rs = Etapa 6: EP agrupado por região de saúde (etapa6_lib.para_rs); mesmas imputações (mesma seed); saídas com
  sufixo _rs; --m2 = Etapa 6b: também o M2 (raça + idade + ano + região, sem modificação) em cada imputação, PR
  combinada por Rubin na escala log (amostra de acesso, como as células da 3.2): tab_e4_06_mi_m2_rubin{_rs})
Saídas: tab_e4_06_mi_icr_por_imputacao, tab_e4_06_mi_rubin, tab_e4_06_viabilidade.
"""
import json
import resource
import sys
import time

import numpy as np
import pandas as pd
from scipy import sparse, stats
from sklearn.linear_model import LogisticRegression

import etapa1_lib as E
import etapa3_lib as T
import etapa4_lib as S4
import etapa0_lib as L

M = int(sys.argv[1]) if len(sys.argv) > 1 else 10
RS = "--rs" in sys.argv
SUF = "_rs" if RS else ""
M2F = "--m2" in sys.argv
res_m2 = []
if RS:
    import etapa6_lib as E6
log = E6.logger("4.6_imputacao_rs") if RS else S4.logger("06_imputacao")
t0 = time.time()
rng = np.random.default_rng(42)
RACE5 = {1: "Branca", 2: "Preta", 3: "Amarela", 4: "Parda", 5: "Indigena"}


def mem_gb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 ** 3  # macOS: bytes


# composição municipal (Censo 2022)
js = json.load(open(L.PROJ / "docs/referencias/censo2022/sidra_9605_n6_2022.json"))[1:]
cz = pd.DataFrame(js)[["D1C", "D4C", "V"]].rename(columns={"D1C": "mun7", "D4C": "cat", "V": "v"})
cz["v"] = pd.to_numeric(cz.v, errors="coerce")
cz = cz.pivot(index="mun7", columns="cat", values="v")
comp = pd.DataFrame({"CODMUNRES": cz.index.str[:6], "pct_branca": 100 * cz["2776"] / cz["95251"],
                     "pct_indigena": 100 * cz["2780"] / cz["95251"]})
comp["faixa_comp"] = (pd.cut(comp.pct_branca, [-1, 20, 40, 60, 80, 101], labels=False).astype(str) + "_" +
                      pd.cut(comp.pct_indigena, [-1, 1, 5, 20, 101], labels=False).astype(str))
log(f"Censo 2022: {len(comp):,} municípios; faixas de composição = {comp.faixa_comp.nunique()}")

# dados: todos os registros que passam IG/esc/idade, com raça observada (1–5) ou nula
cols = ["incl", "ano", "RACACORMAE", "SEMAGESTAC", "ESCMAE", "IDADEMAE", "idade_cat", "esc_cat", "estciv_cat",
        "regiao", "CODMUNRES", "CO_REGSAUD", "ptb_tipo", "ptb", "pig"]
d = pd.read_parquet(T.V3, columns=cols)
d = d[d.SEMAGESTAC.between(22, 44).fillna(False) & d.ESCMAE.between(1, 5).fillna(False) & d.IDADEMAE.between(10, 60).fillna(False)]
d = d[d.RACACORMAE.isna() | d.RACACORMAE.isin([1, 2, 3, 4, 5])].copy()
d["ano"] = d.ano.astype(int)
d["CO_REGSAUD"] = d.CO_REGSAUD.astype(object)
d["CODMUNRES"] = d.CODMUNRES.astype(str)
ter = pd.read_csv(L.PROC / f"tercil_reg_regsaude_ano_v1_{L.STAMP}.csv", dtype={"CO_REGSAUD": str})[["CO_REGSAUD", "ano", "tercil_reg"]]
d = d.merge(ter, on=["CO_REGSAUD", "ano"], how="left").merge(comp[["CODMUNRES", "faixa_comp"]], on="CODMUNRES", how="left")
d["faixa_comp"] = d.faixa_comp.fillna("sem_censo")
d["tercil_reg"] = d.tercil_reg.fillna("sem_reg")
d["estciv_f"] = d.estciv_cat.astype(object).fillna("ausente")
d["ptb4"] = np.where(d.ptb == 0, "termo", d.ptb_tipo.astype(object))
d["pig3"] = d.pig.astype("Int8").astype("string").fillna("ne")
obs = d.RACACORMAE.notna()
log(f"registros com raça observada (inclui Amarela): {int(obs.sum()):,}; a imputar: {int((~obs).sum()):,}; "
    f"sem faixa de composição: {int((d.faixa_comp == 'sem_censo').sum())}")

FEAT = ["regiao", "ano", "idade_cat", "esc_cat", "estciv_f", "ptb4", "pig3", "tercil_reg", "faixa_comp"]
for c in FEAT:
    d[c] = d[c].astype(str)
d["pat"] = d[FEAT].agg("|".join, axis=1)
pat_codes, pat_idx = np.unique(d.pat.to_numpy(), return_inverse=True)
d["pid"] = pat_idx
P = pd.DataFrame([p.split("|") for p in pat_codes], columns=FEAT)
log(f"padrões de covariáveis: {len(P):,} ({(time.time() - t0) / 60:.1f} min; pico de memória {mem_gb():.1f} GB)")


def desenho(P):
    blocos = [pd.get_dummies(P[c], prefix=c, drop_first=True, sparse=False) for c in FEAT]
    for a, b in [("ptb4", "tercil_reg"), ("pig3", "tercil_reg"), ("regiao", "faixa_comp")]:
        blocos.append(pd.get_dummies(P[a] + "x" + P[b], prefix=f"{a}x{b}", drop_first=True))
    X = pd.concat(blocos, axis=1).astype(np.float32)
    return sparse.csr_matrix(X.to_numpy())


X = desenho(P)
log(f"matriz do modelo de imputação: {X.shape[0]:,} padrões × {X.shape[1]} colunas")
o = d[obs].groupby(["pid", "RACACORMAE"]).size().rename("n").reset_index()
miss = d[~obs].groupby(["pid", "CODMUNRES", "regiao", "idade_cat", "ano", "tercil_reg", "ptb4", "pig3"]).size().rename("n").reset_index()
log(f"linhas (padrão × raça) observadas: {len(o):,}; células a imputar (padrão × município): {len(miss):,}")

# células observadas da análise 3.2 (amostra analítica de acesso), por desfecho
OUT = ["ptb", "ptb_esp", "ptb_ind", "pig"]
an = T.anexa_acesso(T.load(["raca", "idade_cat", "regiao", "CODMUNRES", "CO_REGSAUD", "ptb", "ptb_esp", "ptb_ind", "pig"]))
an = an[an.CO_REGSAUD.notna()]
an["CODMUNRES"] = an.CODMUNRES.astype(str)
KEYS = ["raca", "idade_cat", "ano", "regiao", "tercil_reg", "CODMUNRES"]
cel_obs = {}
for desf in OUT:
    s = an[an[desf].notna()]
    g = s.groupby([k for k in KEYS], observed=True)[desf].agg(["sum", "size"]).reset_index()
    cel_obs[desf] = g.rename(columns={"sum": "Y", "size": "n"})
del an
log(f"células observadas prontas ({(time.time() - t0) / 60:.1f} min; pico {mem_gb():.1f} GB)")


def y_de(ptb4, pig3, desf):
    if desf == "ptb":
        return (ptb4 != "termo").astype(float), np.ones(len(ptb4), bool)
    if desf == "ptb_esp":
        return (ptb4 == "espontaneo").astype(float), (ptb4 != "sem_classif")
    if desf == "ptb_ind":
        return (ptb4 == "indicado").astype(float), (ptb4 != "sem_classif")
    return (pig3 == "1").astype(float), (pig3 != "ne")


ACH = [("A", "pig", "Indigena"), ("B", "ptb_ind", "Indigena"), ("B", "ptb_ind", "Parda"),
       ("C", "ptb_esp", "Indigena"), ("D", "ptb", "Indigena")]
res, tempos = [], []
racas_ord = [1, 2, 3, 4, 5]
for m in range(1, M + 1):
    tm = time.time()
    w = rng.poisson(o.n.to_numpy()).astype(float)
    k = w > 0
    clf = LogisticRegression(penalty=None, solver="lbfgs", max_iter=1000, tol=1e-8)
    clf.fit(X[o.pid.to_numpy()[k]], o.RACACORMAE.to_numpy()[k], sample_weight=w[k])
    assert list(clf.classes_) == racas_ord
    pr = clf.predict_proba(X[miss.pid.to_numpy()])
    draws = np.vstack([rng.multinomial(n, p / p.sum()) for n, p in zip(miss.n.to_numpy(), pr)])
    imp = pd.concat([miss.drop(columns="n").assign(raca=RACE5[r], n=draws[:, j]) for j, r in enumerate(racas_ord)])
    imp = imp[(imp.n > 0) & (imp.raca != "Amarela") & (imp.tercil_reg != "sem_reg")]
    t_fit = time.time() - tm
    for desf in OUT:
        y, ok = y_de(imp.ptb4.to_numpy(), imp.pig3.to_numpy(), desf)
        ii = imp[ok].assign(Y=y[ok] * imp.n.to_numpy()[ok])
        ci = ii.groupby(KEYS)[["Y", "n"]].sum().reset_index()
        c = pd.concat([cel_obs[desf].assign(**{k: cel_obs[desf][k].astype(str) for k in KEYS if k != "ano"}),
                       ci.assign(**{k: ci[k].astype(str) for k in KEYS if k != "ano"})])
        c["ano"] = c.ano.astype(int)
        c = c.groupby(KEYS, observed=True)[["Y", "n"]].sum().reset_index()
        assert int(c.n.sum()) == int(cel_obs[desf].n.sum()) + int(ci.n.sum())
        c["raca"] = pd.Categorical(c.raca, categories=T.RACAS)
        c["idade_cat"] = pd.Categorical(c.idade_cat, categories=["20-34", "<20", ">=35"])
        c["regiao"] = c.regiao.astype("category")
        c["tercil_reg"] = pd.Categorical(c.tercil_reg, categories=["T1", "T2", "T3"])
        if RS:
            c = E6.para_rs(c)
        r = T.knol(c, "tercil_reg", ["T1", "T2", "T3"], "T3", mod_main="C(tercil_reg, Treatment('T3'))", rotulo="tercil_reg")
        if M2F:
            f2 = E.fit_agg(c, T.M2, "poisson")
            V2 = f2["cov"]["cluster"]
            for g in T.RACAS[1:]:
                j = f2["names"].index(f"{T.R}[T.{g}]")
                res_m2.append(dict(imputacao=m, desfecho=desf, raca=g, logPR=float(f2["params"].iloc[j]), se=float(np.sqrt(V2[j, j])),
                                   N=int(c.n.sum()), G=f2["G"]))
        it = r["interacao"].assign(imputacao=m, desfecho=desf, N=int(c.n.sum()))
        it["ICR_se"] = (it.ICR_hi - it.ICR_lo) / (2 * E.Z)
        res.append(it)
    tempos.append(dict(imputacao=m, seg_modelo_e_sorteio=t_fit, seg_total=time.time() - tm, pico_mem_gb=mem_gb()))
    log(f"imputação {m}/{M}: {time.time() - tm:.0f} s (modelo+sorteio {t_fit:.0f} s); pico {mem_gb():.1f} GB")

R = pd.concat(res)
R.to_csv(L.TAB / f"tab_e4_06_mi_icr_por_imputacao{SUF}_v1_{L.STAMP}.csv", index=False)
pd.DataFrame(tempos).to_csv(L.TAB / f"tab_e4_06_viabilidade{SUF}_v1_{L.STAMP}.csv", index=False)
if M > 1:
    rows = []
    for (desf, g, niv), x in R.groupby(["desfecho", "raca", "nivel"]):
        q, u = x.ICR_pp.to_numpy(), (x.ICR_se.to_numpy()) ** 2
        qb, W, B = q.mean(), u.mean(), q.var(ddof=1)
        Tt = W + (1 + 1 / M) * B
        lam = (1 + 1 / M) * B / Tt
        df = (M - 1) / lam ** 2 if lam > 0 else np.inf
        tq = stats.t.ppf(0.975, df)
        rows.append(dict(desfecho=desf, raca=g, nivel=niv, ICR_pp=qb, ICR_lo=qb - tq * np.sqrt(Tt), ICR_hi=qb + tq * np.sqrt(Tt),
                         W=W, B=B, fmi=lam, gl=df, m=M))
    pd.DataFrame(rows).to_csv(L.TAB / f"tab_e4_06_mi_rubin{SUF}_v1_{L.STAMP}.csv", index=False)
    if M2F:
        Q = pd.DataFrame(res_m2)
        Q.to_csv(L.TAB / f"tab_e4_06_mi_m2_por_imputacao{SUF}_v1_{L.STAMP}.csv", index=False)
        rr = []
        for (desf, g), x in Q.groupby(["desfecho", "raca"]):
            q, u = x.logPR.to_numpy(), x.se.to_numpy() ** 2
            qb, W, B = q.mean(), u.mean(), q.var(ddof=1)
            Tt = W + (1 + 1 / M) * B
            lam = (1 + 1 / M) * B / Tt
            df = (M - 1) / lam ** 2 if lam > 0 else np.inf
            tq = stats.t.ppf(0.975, df)
            rr.append(dict(desfecho=desf, raca=g, PR=np.exp(qb), PR_lo=np.exp(qb - tq * np.sqrt(Tt)), PR_hi=np.exp(qb + tq * np.sqrt(Tt)),
                           W=W, B=B, fmi=lam, gl=df, m=M, N_medio=x.N.mean(), G=x.G.iloc[0]))
        pd.DataFrame(rr).to_csv(L.TAB / f"tab_e4_06_mi_m2_rubin{SUF}_v1_{L.STAMP}.csv", index=False)
        log("M2 (Rubin, PR):\n" + pd.DataFrame(rr)[["desfecho", "raca", "PR", "PR_lo", "PR_hi", "fmi"]].round(3).to_string(index=False))
log(f"4.6 concluído: M = {M}, {(time.time() - t0) / 60:.1f} min; pico de memória {mem_gb():.1f} GB")
