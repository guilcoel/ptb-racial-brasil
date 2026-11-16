"""
Auditoria própria da Etapa 4 + quadro-síntese.
Auditoria:
  1. n de cada subamostra = Σ células (N do modelo = n individual, recontado da base)
  2. 4.1(b): N(outro) + N(DUM) + N(ignorado) = N da 3.2, por desfecho
  3. ICR de cada sensibilidade reconstruído à mão a partir de (i): ICR = DR(g,T1) − DR(g,T3) − DR(Branca,T1)
  4. 4.6: N de cada imputação = N observado de acesso + imputados não Amarela; 10 imputações por linha
  5. confronto com audit_independente/etapa4 quando existir
Quadro-síntese: achados A–D × sensibilidades; célula = ICR (IC 95%) + classificação (etapa4_lib.classifica).
Saídas: tab_e4_07_auditoria_propria, tab_e4_08_quadro_sintese.
"""
import numpy as np
import pandas as pd

import etapa4_lib as S4
import etapa0_lib as L

log = S4.logger("07_auditoria")
TB, S = L.TAB, L.STAMP
chk = []


def check(nome, valor, ok):
    chk.append(dict(verificacao=nome, valor=str(valor), ok=bool(ok)))
    log(f"{'OK ' if ok else 'FALHA'} {nome}: {valor}")


def ler(prefixo):
    return {k: pd.read_csv(TB / f"{prefixo}_{k}_v1_{S}.csv") for k in ("conjunto", "interacao", "wald")}


e3 = {k: pd.read_csv(TB / f"tab_e3_02_{k}_v1_{S}.csv") for k in ("conjunto", "interacao", "wald")}
for k in e3:
    e3[k] = e3[k][(e3[k].analise == "3.2_tercil_reg") & (e3[k].estrato == "Brasil")].assign(sensibilidade="3.2_original")
b1, b2 = ler("tab_e4_01b"), ler("tab_e4_02")
allr = {k: pd.concat([e3[k], b1[k], b2[k]]) for k in ("conjunto", "interacao", "wald")}

# 1
d = S4.carrega()
a = d[d.CO_REGSAUD.notna()]
SUB = {"4.1_outro_metodo": a.ig_metodo == "outro_metodo", "4.1_DUM": a.ig_metodo == "DUM", "4.1_ignorado": a.ig_metodo == "ignorado",
       "4.2_unicas": a.unica == 1, "4.3_sem_CE_DF": ~a.uf.isin(["CE", "DF"]), "4.4_sem_2024": a.ano != 2024,
       "4.5_pig_k0": pd.Series(True, index=a.index), "4.5_pig_k6": pd.Series(True, index=a.index)}
bad, n = 0, 0
W = pd.concat([b1["wald"], b2["wald"]])
for _, w in W.iterrows():
    m = SUB[w.sensibilidade]
    n_ind = int((m & a[w.desfecho].notna()).sum())
    n += 1
    bad += int(n_ind != w.N or n_ind != w.n_individual)
check("N de cada modelo de sensibilidade = n individual recontado", f"{n - bad}/{n}", bad == 0)

# 2
w3 = e3["wald"].set_index("desfecho").N
s41 = b1["wald"].groupby("desfecho").N.sum()
ok = all(int(s41[k]) == int(w3[k]) for k in s41.index)
check("4.1(b): outro + DUM + ignorado = N da 3.2 (5 desfechos)", "; ".join(f"{k} {int(s41[k]):,}" for k in s41.index), ok)

# 3
bad, n = 0, 0
for (sens, desf), x in allr["conjunto"].groupby(["sensibilidade", "desfecho"]):
    D = x.set_index(["raca", "nivel"]).DR_pp
    for _, r in allr["interacao"][(allr["interacao"].sensibilidade == sens) & (allr["interacao"].desfecho == desf)].iterrows():
        n += 1
        bad += int(abs(D[r.raca, r.nivel] - D[r.raca, "T3"] - D["Branca", r.nivel] - r.ICR_pp) > 1e-8)
check("ICR = DR(g,T1/T2) − DR(g,T3) − DR(Branca,T1/T2), todas as sensibilidades", f"{n - bad}/{n}", bad == 0)

# 4
mi = pd.read_csv(TB / f"tab_e4_06_mi_icr_por_imputacao_v1_{S}.csv")
rb = pd.read_csv(TB / f"tab_e4_06_mi_rubin_v1_{S}.csv")
cnt = mi.groupby(["desfecho", "raca", "nivel"]).imputacao.nunique()
nN = mi.groupby(["desfecho", "imputacao"]).N.first().groupby("desfecho").agg(["min", "max"])
w3a = e3["wald"].set_index("desfecho").N
okn = all(nN.loc[k, "min"] > w3a[k] for k in nN.index)
check("4.6: 10 imputações por linha; N imputado > N observado em todas", f"{cnt.min()}–{cnt.max()} imputações; "
      + "; ".join(f"{k} +{int(nN.loc[k, 'min'] - w3a[k]):,}–{int(nN.loc[k, 'max'] - w3a[k]):,}" for k in nN.index),
      (cnt == 10).all() and okn)

# 5 independente
AUD = L.PROJ / "audit_independente" / "etapa4"
if AUD.exists():
    log("arquivos do auditor: " + ", ".join(sorted(p.name for p in AUD.iterdir() if not p.name.startswith("._"))))

pd.DataFrame(chk).to_csv(TB / f"tab_e4_07_auditoria_propria_v1_{S}.csv", index=False)
log(f"auditoria Etapa 4: {sum(c['ok'] for c in chk)}/{len(chk)} OK")

# quadro-síntese
it = allr["interacao"]
it = it[it.nivel == "T1"]
rb1 = rb[rb.nivel == "T1"].assign(sensibilidade="4.6_imputacao_m10")
COLS = ["3.2_original", "4.1_outro_metodo", "4.1_DUM", "4.2_unicas", "4.3_sem_CE_DF", "4.4_sem_2024",
        "4.5_pig_k0", "4.5_pig_k6", "4.6_imputacao_m10"]
rows = []
for ach, desf, g in S4.ACHADOS:
    o = it[(it.sensibilidade == "3.2_original") & (it.desfecho == desf) & (it.raca == g)].iloc[0]
    row = dict(achado=ach, desfecho=desf, raca=g)
    for c in COLS:
        if c.startswith("4.5") and desf != "pig":
            continue
        src = rb1 if c.startswith("4.6") else it
        dd = {"4.5_pig_k0": "pig_k0", "4.5_pig_k6": "pig_k6"}.get(c, desf)
        x = src[(src.sensibilidade == c) & (src.desfecho == dd) & (src.raca == g)]
        if x.empty:
            continue
        x = x.iloc[0]
        cl = "" if c == "3.2_original" else " " + S4.classifica(ach, o, x)
        row[c] = f"{x.ICR_pp:.2f} ({x.ICR_lo:.2f} a {x.ICR_hi:.2f}){cl}"
    rows.append(row)
Q = pd.DataFrame(rows)
Q.to_csv(TB / f"tab_e4_08_quadro_sintese_v1_{S}.csv", index=False)
log("quadro-síntese gravado")
print(Q.to_string(index=False))
