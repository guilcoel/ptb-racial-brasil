"""
3.2–3.6 Modificação de efeito (Knol & VanderWeele) sobre o M2, para PTB, PTB espontâneo, PTB indicado, PIG
(e lbw_termo, só suplementar).

  3.2  principal: raça × tercil de acesso DENTRO da macrorregião (ref Branca–T3); amostra de acesso (sem os 533)
  3.3a índice contínuo (por 5 p.p.): M2 + índice + raça×índice; RP de cada raça em P10/P50/P90 nacionais
  3.3b tercis nacionais (Etapa 2; ref Branca–T3_melhor)
  3.3c 3.2 estratificado por macrorregião (exploratório; base sem região)
  3.4  raça × macrorregião (ref Branca–SE); 3.5 raça × idade (ref 20-34), × escolaridade em 3 níveis (≤7, 8–11, ≥12;
       ref ≥12; M2 + esc + raça×esc), × período (ref 2015–2019; período ⊂ ano: sem efeito principal, padronização
       dentro do período)
  3.6  limites: 3.2 refeito com os 131,809 PTB sem classificação (a) como espontâneos, (b) como indicados
Saídas: tab_e3_02_{conjunto,dentro,interacao,wald}, tab_e3_03a_indice_continuo.
Etapa 6: com --rs, EP agrupado por região de saúde (etapa6_lib.para_rs); saídas com sufixo _rs; log da etapa 6.
"""
import sys
import time

import numpy as np
import pandas as pd

import etapa1_lib as E
import etapa3_lib as T
import etapa0_lib as L

RS = "--rs" in sys.argv
SUF = "_rs" if RS else ""
if RS:
    import etapa6_lib as E6
log = E6.logger("3.2-3.6_knol_rs") if RS else T.logger("02_knol")
OUT = ["ptb", "ptb_esp", "ptb_ind", "pig", "lbw_termo"]
d = T.load(["raca", "idade_cat", "esc_cat", "regiao", "CODMUNRES", "CO_REGSAUD", "periodo", "ptb", "ptb_tipo",
            "ptb_esp", "ptb_ind", "pig", "lbw_termo"])
d = T.anexa_acesso(d)
d["esc3"] = pd.Categorical(d.esc_cat.map({"1_nenhuma": "le7", "2_1a3anos": "le7", "3_4a7anos": "le7",
                                          "4_8a11anos": "8a11", "5_12mais": "ge12"}), categories=["le7", "8a11", "ge12"])
d["periodo"] = pd.Categorical(d.periodo.astype(str), categories=["2015-2019", "2020-2021", "2022-2024"])
# 3.6 limites
sc = (d.ptb_tipo == "sem_classif").to_numpy()
for lado, alvo in [("a", "ptb_esp"), ("b", "ptb_ind")]:
    for desf in ("ptb_esp", "ptb_ind"):
        x = d[desf].astype("Float64").copy()
        x[sc] = 1.0 if desf == alvo else 0.0
        d[f"{desf}_{lado}"] = x.astype("Int8")
log("amostra", len(d))
acc = d.CO_REGSAUD.notna()
assert int((~acc).sum()) == 533 and d.loc[acc, "tercil_reg"].notna().all() and d.loc[acc, "tercil_nac"].notna().all()

res = {k: [] for k in ("conjunto", "dentro", "interacao", "wald")}
cont = []
t0 = time.time()


def guarda(r, analise, desf, estrato="Brasil"):
    for k in res:
        res[k].append(r[k].assign(analise=analise, desfecho=desf, estrato=estrato))


def roda(desf, analises):
    s = d[d[desf].notna()]
    sa = s[s.CO_REGSAUD.notna()]
    ca = E.agrega(sa, desf, ["raca", "idade_cat", "ano", "regiao", "tercil_reg", "tercil_nac", "indice_t1"])
    cf = E.agrega(s, desf, ["raca", "idade_cat", "ano", "regiao", "esc3", "periodo"])
    assert int(ca.n.sum()) == len(sa) and int(cf.n.sum()) == len(s)
    for c in (ca, cf):
        c["CODMUNRES"] = c.CODMUNRES.astype(str)
    if RS:
        ca, cf = E6.para_rs(ca), E6.para_rs(cf)
    if "principal" in analises:
        guarda(T.knol(ca, "tercil_reg", ["T1", "T2", "T3"], "T3", mod_main="C(tercil_reg, Treatment('T3'))",
                      rotulo="tercil_reg"), "3.2_tercil_reg", desf)
    if "nacional" in analises:
        guarda(T.knol(ca, "tercil_nac", ["T1_pior", "T2", "T3_melhor"], "T3_melhor",
                      mod_main="C(tercil_nac, Treatment('T3_melhor'))", rotulo="tercil_nac"), "3.3b_tercil_nac", desf)
    if "estrat" in analises:
        for reg in L.REGIOES:
            cr = ca[ca.regiao == reg].copy()
            cr["regiao"] = cr.regiao.cat.remove_unused_categories()
            guarda(T.knol(cr, "tercil_reg", ["T1", "T2", "T3"], "T3", base=f"{T.R} + {T.I} + {T.A}",
                          mod_main="C(tercil_reg, Treatment('T3'))", rotulo="tercil_reg"), "3.3c_estratificado", desf, reg)
    if "continuo" in analises:
        c = ca.copy()
        c["ind5"] = c.indice_t1 / 5
        for g in T.RACAS[1:]:
            c[f"ixc__{g}"] = (c.raca == g) * c.ind5
        f = E.fit_agg(c, T.M2 + " + ind5 + " + " + ".join(f"ixc__{g}" for g in T.RACAS[1:]), "poisson")
        V = f["cov"]["cluster"]
        pct = np.percentile(sa.indice_t1.to_numpy(), [10, 50, 90])
        for g in T.RACAS[1:]:
            j1, j2 = f["names"].index(f"{T.R}[T.{g}]"), f["names"].index(f"ixc__{g}")
            for nome, x in zip(["P10", "P50", "P90"], pct):
                gr = np.zeros(len(f["names"]))
                gr[j1], gr[j2] = 1, x / 5
                v = float(gr @ f["params"].to_numpy())
                se = float(np.sqrt(gr @ V @ gr))
                cont.append(dict(desfecho=desf, raca=g, ponto=nome, indice=x, RP=np.exp(v), RP_lo=np.exp(v - E.Z * se),
                                 RP_hi=np.exp(v + E.Z * se), RP_por_5pp_interacao=np.exp(f["params"].iloc[j2]),
                                 int_lo=np.exp(f["params"].iloc[j2] - E.Z * np.sqrt(V[j2, j2])),
                                 int_hi=np.exp(f["params"].iloc[j2] + E.Z * np.sqrt(V[j2, j2]))))
    if "outros" in analises:
        guarda(T.knol(cf, "regiao", ["N", "NE", "SE", "S", "CO"], "SE", rotulo="regiao"), "3.4_regiao", desf)
        guarda(T.knol(cf, "idade_cat", ["<20", "20-34", ">=35"], "20-34", rotulo="idade_cat"), "3.5_idade", desf)
        guarda(T.knol(cf, "esc3", ["le7", "8a11", "ge12"], "ge12", mod_main="C(esc3, Treatment('ge12'))", rotulo="esc3"),
               "3.5_escolaridade", desf)
        guarda(T.knol(cf, "periodo", ["2015-2019", "2020-2021", "2022-2024"], "2015-2019", within=True, rotulo="periodo"),
               "3.5_periodo", desf)
    log(f"{desf}: {', '.join(analises)} ({(time.time() - t0) / 60:.1f} min)")


if "--teste" in sys.argv:
    roda("ptb", ["principal"])
    print(pd.concat(res["conjunto"]).round(3).to_string())
    print(pd.concat(res["interacao"]).round(3).to_string())
    sys.exit()
for desf in OUT:
    roda(desf, ["principal", "nacional", "estrat", "continuo", "outros"])
for desf in ["ptb_esp_a", "ptb_ind_a", "ptb_esp_b", "ptb_ind_b"]:
    roda(desf, ["principal"])

for k, v in res.items():
    pd.concat(v).to_csv(L.TAB / f"tab_e3_02_{k}{SUF}_v1_{L.STAMP}.csv", index=False)
pd.DataFrame(cont).to_csv(L.TAB / f"tab_e3_03a_indice_continuo{SUF}_v1_{L.STAMP}.csv", index=False)
log(f"concluído em {(time.time() - t0) / 60:.1f} min")
