"""
8.4 Sensibilidade da Etapa 8: raça × tercil de acesso com a cobertura da Atenção Básica no lugar do índice de pré-natal.
Nascimentos de 2015–2021 com região de saúde; desfechos da Tabela S2b (PTB total, PIG, PTB indicado). Duas exposições:
  tercil_aps   — tercis da cobertura da Atenção Básica (t−1) dentro da macrorregião (etapa8_03);
  tercil_ind21 — comparador: tercis do índice de pré-natal (t−1) recalculados em 2015–2021, mesma amostra e algoritmo (etapa8_03).
Modelo e estimador = os da análise principal (etapa7b3_01.ajuste_32 = etapa4_lib.roda_32 com etapa6_lib.para_rs): M2 + tercil +
raça × tercil, Poisson sobre células agregadas, Knol & VanderWeele com padronização total, referência Branca–T3, EP agrupado por
região de saúde (sem os 533 sem região, G = 433). Wald de 6 gl (todos os termos raça × tercil) e Wald indígena de 2 gl
(Indígena×T1, Indígena×T2), com a mesma covariância.
Conferência: a mesma função, com o tercil_reg na amostra 2015–2024, reproduz o IC Indígena×T1 publicado (tab_e3_02_interacao_rs)
e o Wald indígena de 2 gl (tab_e7b3_02_wald_ind) nos três desfechos.
Saídas: tab_e8_04_interacao, tab_e8_04_wald, tab_e8_04_conjunto, tab_e8_04_dentro.
Rodar da raiz: python3 scripts/etapa8_04_modelos.py
"""
import numpy as np
import pandas as pd
from scipy import stats

import etapa1_lib as E
import etapa3_lib as T
import etapa4_lib as S4
import etapa6_lib as E6
import etapa0_lib as L

log = L.Logger("8_04_modelos", etapa="etapa8")
TB, S = L.TAB, L.STAMP
OUT = ["ptb", "pig", "ptb_ind"]
NIV = ["T1", "T2", "T3"]
IND = ["ix__Indigena__T1", "ix__Indigena__T2"]
K = ["CO_REGSAUD", "ano"]


def ajuste(d, desf, mod):
    """= etapa7b3_01.ajuste_32, com o modificador como parâmetro."""
    s = d[d[desf].notna() & d.CO_REGSAUD.notna()]
    c = E.agrega(s, desf, ["raca", "idade_cat", "ano", "regiao", mod])
    assert int(c.n.sum()) == len(s) and int(c.Y.sum()) == int(s[desf].sum())
    c["CODMUNRES"] = c.CODMUNRES.astype(str)
    c["raca"] = c.raca.cat.remove_unused_categories() if c.raca.cat.categories.size > 4 else c.raca
    c = E6.para_rs(c)
    return T.knol(c, mod, NIV, "T3", mod_main=f"C({mod}, Treatment('T3'))", rotulo=mod), len(s)


def wald_ind(r):
    f, V = r["fit"], r["fit"]["cov"]["cluster"]
    idx = [f["names"].index(n) for n in IND]
    b = f["params"].to_numpy()[idx]
    w = float(b @ np.linalg.solve(V[np.ix_(idx, idx)], b))
    return w, stats.chi2.sf(w, 2)


d = S4.carrega()
# conferência com a análise principal publicada (2015–2024, tercil_reg)
pi = pd.read_csv(TB / f"tab_e3_02_interacao_rs_v1_{S}.csv").query("analise == '3.2_tercil_reg' and estrato == 'Brasil'")
pw = pd.read_csv(TB / f"tab_e7b3_02_wald_ind_v1_{S}.csv").query("cenario == 'principal'").set_index("desfecho")
for desf in OUT:
    r, _ = ajuste(d, desf, "tercil_reg")
    a = r["interacao"].set_index(["raca", "nivel"]).ICR_pp
    b = pi[pi.desfecho == desf].set_index(["raca", "nivel"]).ICR_pp
    dif = float((a - b.reindex(a.index)).abs().max())
    w2, _ = wald_ind(r)
    assert dif < 1e-9 and abs(w2 - pw.chi2_ind_2gl[desf]) < 1e-6, (desf, dif, w2)
    log(f"conferência {desf}: IC (todas as raças e níveis) = publicado (dif. máx. {dif:.1e}); Wald indígena 2 gl {w2:.4f} = publicado")

d = d[(d.ano <= 2021) & d.CO_REGSAUD.notna()].copy()
ter = pd.read_csv(L.PROC / f"tercil_aps_regsaude_ano_v1_{S}.csv", dtype={"CO_REGSAUD": str})[K + ["tercil_aps", "tercil_ind21"]]
d["CO_REGSAUD"] = d.CO_REGSAUD.astype(str)
d = d.merge(ter, on=K, how="left", validate="m:1")
for c in ("tercil_aps", "tercil_ind21"):
    assert d[c].notna().all()
    d[c] = pd.Categorical(d[c], categories=NIV)
log("amostra 2015–2021 com região de saúde", len(d))

IT, W, CJ, DT = [], [], [], []
for mod in ("tercil_aps", "tercil_ind21"):
    for desf in OUT:
        r, n = ajuste(d, desf, mod)
        w6 = r["wald"].iloc[0]
        w2, p2 = wald_ind(r)
        tag = dict(exposicao=mod, desfecho=desf, n_individual=n)
        IT.append(r["interacao"].assign(**tag))
        CJ.append(r["conjunto"].assign(**tag))
        DT.append(r["dentro"].assign(**tag))
        W.append(dict(**tag, N=int(w6.N), G=int(w6.G), chi2_6gl=w6.chi2, p_6gl=w6.p, chi2_ind_2gl=w2, p_ind_2gl=p2))
        i1 = r["interacao"].query("raca == 'Indigena' and nivel == 'T1'").iloc[0]
        log(f"{mod} {desf}: IC Indígena×T1 {i1.ICR_pp:.2f} ({i1.ICR_lo:.2f} a {i1.ICR_hi:.2f}); Wald 6 gl p = {w6.p:.3g}; "
            f"Wald indígena 2 gl χ² = {w2:.2f} (p = {p2:.3g}); N = {int(w6.N):,}; G = {int(w6.G)}")
pd.concat(IT).to_csv(L.out_name("tab_e8_04_interacao"), index=False)
pd.DataFrame(W).to_csv(L.out_name("tab_e8_04_wald"), index=False)
pd.concat(CJ).to_csv(L.out_name("tab_e8_04_conjunto"), index=False)
pd.concat(DT).to_csv(L.out_name("tab_e8_04_dentro"), index=False)
x = pd.concat(IT).query("nivel == 'T1'")[["exposicao", "desfecho", "raca", "ICR_pp", "ICR_lo", "ICR_hi"]]
log("IC ×T1, todas as raças:\n" + x.round(2).to_string(index=False))
