"""
2.4 Modelos M1–M3 (Poisson log, estimação agregada validada na Etapa 1, EP clusterizado por CODMUNRES).

  M1   raça
  M2   raça + idade_cat + ano + região (PRINCIPAL)
  M2s  M2 sem idade (sensibilidade)
  M3   M2 + esc_cat + estciv_cat (casos completos em estciv_cat)
  M2cc M2 no mesmo subconjunto do M3 (base da atenuação M2 -> M3)
Referências: Branca; 20-34; 5_12mais; com_companheiro; SE; 2015.
Desfechos: ptb (todas), ptb_esp, ptb_ind, lbw_termo (únicas), pig (únicas, +3 dias).
Medidas: RP (IC 95%); diferença absoluta (p.p.) por padronização marginal sobre a amostra do modelo, IC delta;
  atenuação = (RP_M2cc − RP_M3)/(RP_M2cc − 1) × 100 quando RP_M2cc > 1; OR (logit, mesmo desenho) suplementar.
M2 estratificado por macrorregião (sem região no modelo, sem interação).
Saídas: tab_e2_04_modelos_long, tab_e2_04_modelos_brasil_fmt, tab_e2_04_m2_regioes_fmt, tab_e2_04_or_suplementar.
"""
import time

import numpy as np
import pandas as pd

import etapa1_lib as E
import etapa0_lib as L

log = L.Logger("04_modelos", etapa="etapa2")
V3 = L.PROC / f"sinasc_brasil_2015_2024_v3_{L.STAMP}"
OUT = ["ptb", "ptb_esp", "ptb_ind", "lbw_termo", "pig"]
d = pd.read_parquet(V3, columns=["incl", "ano", "raca", "idade_cat", "esc_cat", "estciv_cat", "regiao", "CODMUNRES"] + OUT,
                    filters=[("incl", "==", True)])
d["ano"] = d.ano.astype(int)
for c in ["regiao", "CODMUNRES"]:
    d[c] = d[c].astype(str).astype("category")
d["raca"] = d.raca.cat.remove_unused_categories()
log("amostra", len(d))

R = "C(raca, Treatment('Branca'))"
I = "C(idade_cat, Treatment('20-34'))"
A = "C(ano)"
G = "C(regiao, Treatment('SE'))"
S = "C(esc_cat, Treatment('5_12mais')) + C(estciv_cat, Treatment('com_companheiro'))"
RHS = {"M1": R, "M2": f"{R} + {I} + {A} + {G}", "M2s": f"{R} + {A} + {G}", "M3": f"{R} + {I} + {A} + {G} + {S}"}
RHS["M2cc"] = RHS["M2"]
PREF = R + "[T."
RACAS = E.L.RACA_ORDER


def estima(cells, rhs, modelo, desf, reg, com_or):
    out = []
    f = E.fit_agg(cells, rhs, "poisson")
    rp = {t["termo"].split("[T.")[1].rstrip("]"): t for t in E.termos(f, PREF)}
    mg = {m["nivel"]: m for m in E.marginal(f, cells, "raca", RACAS, "Branca")}
    orr = {}
    if com_or:
        fo = E.fit_agg(cells, rhs, "logit")
        orr = {t["termo"].split("[T.")[1].rstrip("]"): t for t in E.termos(fo, PREF)}
    for g in RACAS[1:]:
        r = dict(modelo=modelo, desfecho=desf, regiao=reg, raca=g, N=int(f["N"]), n_celulas=f["n_cells"], n_clusters=f["G"],
                 RP=rp[g]["est"], RP_lo=rp[g]["lo"], RP_hi=rp[g]["hi"], RP_p=rp[g]["p"],
                 P_raca=100 * mg[g]["p_nivel"], P_branca=100 * mg[g]["p_ref"],
                 DA_pp=100 * mg[g]["dif"], DA_lo=100 * mg[g]["dif_lo"], DA_hi=100 * mg[g]["dif_hi"])
        if g in orr:
            r.update(OR=orr[g]["est"], OR_lo=orr[g]["lo"], OR_hi=orr[g]["hi"])
        out.append(r)
    return out


rows = []
t0 = time.time()
for desf in OUT:
    s = d[d[desf].notna()]
    c2 = E.agrega(s, desf, ["raca", "idade_cat", "ano", "regiao"])
    s3 = s[s.estciv_cat.notna()]
    c3 = E.agrega(s3, desf, ["raca", "idade_cat", "ano", "regiao", "esc_cat", "estciv_cat"])
    assert int(c2.n.sum()) == len(s) and int(c3.n.sum()) == len(s3)
    for m, cells in [("M1", c2), ("M2", c2), ("M2s", c2), ("M2cc", c3), ("M3", c3)]:
        rows += estima(cells, RHS[m], m, desf, "Brasil", com_or=m in ("M1", "M2", "M3"))
        log(f"{desf} {m} Brasil: N={int(cells.n.sum()):,}, células={len(cells):,} ({(time.time() - t0) / 60:.1f} min)")
    for reg in L.REGIOES:
        cr = c2[c2.regiao == reg].copy()
        cr["regiao"] = cr.regiao.cat.remove_unused_categories()
        rows += estima(cr, f"{R} + {I} + {A}", "M2", desf, reg, com_or=False)
    log(f"{desf}: M2 por macrorregião feito")

t = pd.DataFrame(rows)
# atenuação M2cc -> M3
k = ["desfecho", "regiao", "raca"]
at = t[t.modelo == "M2cc"][k + ["RP"]].merge(t[t.modelo == "M3"][k + ["RP"]], on=k, suffixes=("_M2cc", "_M3"))
at["atenuacao_pct"] = np.where(at.RP_M2cc > 1, 100 * (at.RP_M2cc - at.RP_M3) / (at.RP_M2cc - 1), np.nan)
t = t.merge(at[k + ["atenuacao_pct"]].assign(modelo="M3"), on=k + ["modelo"], how="left")
t.to_csv(L.TAB / f"tab_e2_04_modelos_long_v1_{L.STAMP}.csv", index=False)


def f2(v):
    return E.fmt_f(v, 2)


t["RP_fmt"] = t.RP.map(f2) + " (" + t.RP_lo.map(f2) + "–" + t.RP_hi.map(f2) + ")"
t["DA_fmt"] = t.DA_pp.map(f2) + " (" + t.DA_lo.map(f2) + "–" + t.DA_hi.map(f2) + ")"
b = t[t.regiao == "Brasil"]
w = b.pivot_table(index=["desfecho", "raca"], columns="modelo", values=["RP_fmt", "DA_fmt"], aggfunc="first")
w[("atenuacao_M2cc_M3_pct", "")] = b[b.modelo == "M3"].set_index(["desfecho", "raca"]).atenuacao_pct.round(1)
w.to_csv(L.TAB / f"tab_e2_04_modelos_brasil_fmt_v1_{L.STAMP}.csv")
r = t[(t.modelo == "M2")]
r.pivot_table(index=["desfecho", "raca"], columns="regiao", values="RP_fmt", aggfunc="first")[["Brasil"] + L.REGIOES].to_csv(
    L.TAB / f"tab_e2_04_m2_regioes_fmt_v1_{L.STAMP}.csv")
o = b[b.OR.notna()].copy()
o["OR_fmt"] = o.OR.map(f2) + " (" + o.OR_lo.map(f2) + "–" + o.OR_hi.map(f2) + ")"
o.pivot_table(index=["desfecho", "raca"], columns="modelo", values="OR_fmt", aggfunc="first").to_csv(
    L.TAB / f"tab_e2_04_or_suplementar_v1_{L.STAMP}.csv")
log(f"modelos concluídos em {(time.time() - t0) / 60:.1f} min")
