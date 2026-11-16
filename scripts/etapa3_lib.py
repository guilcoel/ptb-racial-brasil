"""
etapa3_lib.py — modificação de efeito no formato de Knol & VanderWeele (2012), sobre a estimação
agregada validada (etapa1_lib.fit_agg: Poisson log, offset log n, EP clusterizado por CODMUNRES).

Modelo: base (M2) + [efeito principal do modificador, se não estiver na base e não for colinear]
        + colunas indicadoras ix__<raça>__<nível> (raça ≠ Branca, nível ≠ referência).
Probabilidades padronizadas P(g, m) = Σ_c n_c mu_c(raça = g, mod = m) / Σ_c n_c sobre TODAS as células
  do modelo ("total"); para modificador determinado por covariável do modelo (período ⊂ ano) usa-se
  padronização dentro do estrato ("within": células do nível m, só a raça é trocada).
Com padronização total e modelo log-linear, P(g,m)/P(Branca,ref) = exp(β_g + β_m + β_gm) exatamente.
Quantidades (IC 95% delta com a covariância clusterizada):
  (i)   RP e DR de (g, m) vs (Branca, ref)
  (ii)  RP e DR de g vs Branca dentro de m
  (iii) interação multiplicativa = RP(g|m)/RP(g|ref); contraste aditivo (DR) = DR(g|m) − DR(g|ref);
        RERI = RP11 − RP10 − RP01 + 1 (RP vs Branca–ref), sinalizado quando RP10 > 1 e RP01 > 1
  (iv)  Wald robusto conjunto dos termos ix
"""
import numpy as np
import pandas as pd
import patsy
from scipy import stats

import etapa1_lib as E
import etapa0_lib as L

V3 = L.PROC / f"sinasc_brasil_2015_2024_v3_{L.STAMP}"
Z = E.Z
RACAS = ["Branca", "Parda", "Preta", "Indigena"]
R = "C(raca, Treatment('Branca'))"
I = "C(idade_cat, Treatment('20-34'))"
A = "C(ano)"
G = "C(regiao, Treatment('SE'))"
M2 = f"{R} + {I} + {A} + {G}"


def logger(name):
    return L.Logger(name, etapa="etapa3")


def load(cols):
    d = pd.read_parquet(V3, columns=list(dict.fromkeys(["incl", "ano"] + cols)), filters=[("incl", "==", True)])
    d["ano"] = d.ano.astype(int)
    for c in ["regiao", "CODMUNRES", "CO_REGSAUD"]:
        if c in d:
            d[c] = d[c].astype(str).astype("category") if c != "CO_REGSAUD" else d[c].astype(object)
    if "raca" in d:
        d["raca"] = d.raca.cat.remove_unused_categories()
    return d


def anexa_acesso(d):
    """Índice t−1, tercil nacional (Etapa 2) e tercil dentro da macrorregião (Etapa 3)."""
    ind = pd.read_csv(L.PROC / f"indice_acesso_regsaude_ano_v1_{L.STAMP}.csv", dtype={"CO_REGSAUD": str})
    ind = ind[["CO_REGSAUD", "ano", "indice"]].assign(ano=lambda x: x.ano + 1).rename(columns={"indice": "indice_t1"})
    ter = pd.read_csv(L.PROC / f"tercil_regsaude_ano_v1_{L.STAMP}.csv", dtype={"CO_REGSAUD": str})[["CO_REGSAUD", "ano", "tercil"]]
    ter = ter.rename(columns={"tercil": "tercil_nac"})
    tr = pd.read_csv(L.PROC / f"tercil_reg_regsaude_ano_v1_{L.STAMP}.csv", dtype={"CO_REGSAUD": str})[["CO_REGSAUD", "ano", "tercil_reg"]]
    k = ["CO_REGSAUD", "ano"]
    d = d.merge(ind, on=k, how="left").merge(ter, on=k, how="left").merge(tr, on=k, how="left")
    for c, lv in [("tercil_nac", ["T1_pior", "T2", "T3_melhor"]), ("tercil_reg", ["T1", "T2", "T3"])]:
        d[c] = pd.Categorical(d[c], categories=lv)
    return d


def _ix(cells, mod, niveis, ref):
    cols = []
    for g in RACAS[1:]:
        for m in niveis:
            if m == ref:
                continue
            nm = f"ix__{g}__{m}".replace("-", "_").replace(">=", "ge").replace("<", "lt").replace(" ", "")
            cells[nm] = ((cells.raca == g) & (cells[mod] == m)).astype(float)
            cols.append((g, m, nm))
    return cols


def _pred(fit, cells, assign, ixcols, mod, mask=None):
    cg = cells if mask is None else cells[mask]
    cg = cg.copy()
    for var, val in assign.items():
        cg[var] = pd.Categorical([val] * len(cg), categories=cells[var].cat.categories)
    for g, m, nm in ixcols:
        cg[nm] = ((cg.raca == g) & (cg[mod] == m)).astype(float)
    X = np.asarray(patsy.build_design_matrices([fit["design_info"]], cg)[0])
    mu = np.exp(X @ fit["params"].to_numpy())
    n = cg.n.to_numpy()
    return (n * mu).sum() / n.sum(), (X * (n * mu)[:, None]).sum(axis=0) / n.sum()


def _ci(val, grad, V, log=False):
    se = float(np.sqrt(grad @ V @ grad))
    if log:
        return np.exp(val), np.exp(val - Z * se), np.exp(val + Z * se), 2 * stats.norm.sf(abs(val / se))
    return val, val - Z * se, val + Z * se, 2 * stats.norm.sf(abs(val / se))


def knol(cells, mod, niveis, ref, base=M2, mod_main=None, within=False, rotulo=""):
    """cells: agregado com raca, mod, covariáveis, Y, n, CODMUNRES. Devolve dict de DataFrames."""
    cells = cells.copy()
    ixcols = _ix(cells, mod, niveis, ref)
    rhs = base + (f" + {mod_main}" if mod_main else "") + " + " + " + ".join(nm for _, _, nm in ixcols)
    fit = E.fit_agg(cells, rhs, "poisson")
    V = fit["cov"]["cluster"]
    P, Gd = {}, {}
    for g in RACAS:
        for m in niveis:
            if within:
                P[g, m], Gd[g, m] = _pred(fit, cells, {"raca": g}, ixcols, mod, mask=(cells[mod] == m).to_numpy())
            else:
                P[g, m], Gd[g, m] = _pred(fit, cells, {"raca": g, mod: m}, ixcols, mod)
    B0 = ("Branca", ref)

    def lr(a, b):  # log razão P[a]/P[b]
        return np.log(P[a] / P[b]), Gd[a] / P[a] - Gd[b] / P[b]

    def df(a, b):
        return P[a] - P[b], Gd[a] - Gd[b]

    conj, dentro, inter = [], [], []
    for g in RACAS:
        for m in niveis:
            v, gr = lr((g, m), B0)
            rp = _ci(v, gr, V, log=True)
            v, gr = df((g, m), B0)
            dr = _ci(v, gr, V)
            conj.append(dict(modificador=rotulo, raca=g, nivel=m, P_pct=100 * P[g, m], RP=rp[0], RP_lo=rp[1], RP_hi=rp[2],
                             DR_pp=100 * dr[0], DR_lo=100 * dr[1], DR_hi=100 * dr[2]))
    for g in RACAS[1:]:
        for m in niveis:
            v, gr = lr((g, m), ("Branca", m))
            rp = _ci(v, gr, V, log=True)
            v, gr = df((g, m), ("Branca", m))
            dr = _ci(v, gr, V)
            dentro.append(dict(modificador=rotulo, raca=g, nivel=m, RP=rp[0], RP_lo=rp[1], RP_hi=rp[2], RP_p=rp[3],
                               DR_pp=100 * dr[0], DR_lo=100 * dr[1], DR_hi=100 * dr[2]))
            if m == ref:
                continue
            # multiplicativa: [P(g,m)/P(B,m)] / [P(g,ref)/P(B,ref)]
            v1, g1 = lr((g, m), ("Branca", m))
            v0, g0 = lr((g, ref), B0)
            mi = _ci(v1 - v0, g1 - g0, V, log=True)
            d1, h1 = df((g, m), ("Branca", m))
            d0, h0 = df((g, ref), B0)
            ic = _ci(d1 - d0, h1 - h0, V)
            r11, r10, r01 = P[g, m] / P[B0], P[g, ref] / P[B0], P["Branca", m] / P[B0]
            gr11 = r11 * (Gd[g, m] / P[g, m] - Gd[B0] / P[B0])
            gr10 = r10 * (Gd[g, ref] / P[g, ref] - Gd[B0] / P[B0])
            gr01 = r01 * (Gd["Branca", m] / P["Branca", m] - Gd[B0] / P[B0])
            reri = _ci(r11 - r10 - r01 + 1, gr11 - gr10 - gr01, V)
            inter.append(dict(modificador=rotulo, raca=g, nivel=m, int_mult=mi[0], int_mult_lo=mi[1], int_mult_hi=mi[2],
                              ICR_pp=100 * ic[0], ICR_lo=100 * ic[1], ICR_hi=100 * ic[2], ICR_p=ic[3],
                              RERI=reri[0], RERI_lo=reri[1], RERI_hi=reri[2], RERI_aplicavel=bool(r10 > 1 and r01 > 1),
                              RP10=r10, RP01=r01))
    idx = [j for j, nm in enumerate(fit["names"]) if nm.startswith("ix__")]
    b = fit["params"].to_numpy()[idx]
    Vi = V[np.ix_(idx, idx)]
    w = float(b @ np.linalg.solve(Vi, b))
    wald = dict(modificador=rotulo, chi2=w, gl=len(idx), p=stats.chi2.sf(w, len(idx)), N=int(fit["N"]), G=fit["G"],
                n_celulas=fit["n_cells"])
    return dict(conjunto=pd.DataFrame(conj), dentro=pd.DataFrame(dentro), interacao=pd.DataFrame(inter),
                wald=pd.DataFrame([wald]), fit=fit, P=P)
