"""
6b.1 Lacunas da Etapa 7b, com EP agrupado por REGIÃO DE SAÚDE (etapa6_lib.para_rs), estimadores validados (fit_agg,
marginal), mesmas células e fórmulas da Etapa 2 (etapa2_04_modelos.py).
 (b) M1, M2, M2cc e M3 (Brasil; 5 desfechos): PR (IC 95%) e RD marginal (por 100).
 (c) PR M2 por cenário de sensibilidade (Tabela 4): só DUM; só outro método; sem CE/DF; sem 2024; PIG com IG +0 e +6
     dias (pig_k0, pig_k6). Desfechos ptb, pig, ptb_ind (e ptb_esp). Imputação múltipla: etapa4_06_imputacao_raca.py --rs --m2.
 (d) % de PTB (e de PTB espontâneo/indicado e PIG) por raça × método da IG (contagens; amostra analítica).
Saídas: tab_e6b_01_modelos_m1m3, tab_e6b_01_m2_cenarios, tab_e6b_01_ptb_raca_metodo.
"""
import time

import pandas as pd

import etapa1_lib as E
import etapa3_lib as T
import etapa4_lib as S4
import etapa6_lib as E6
import etapa0_lib as L

log = E6.logger("6b_01_modelos_rs")
t0 = time.time()
d = S4.carrega()
x = T.load(["esc_cat", "estciv_cat"])
assert len(x) == len(d)
d = d.reset_index(drop=True)
d["esc_cat"] = x.esc_cat.to_numpy()
d["estciv_cat"] = x.estciv_cat.to_numpy()
R = T.R
I = T.I
A = T.A
G = T.G
SC = "C(esc_cat, Treatment('5_12mais')) + C(estciv_cat, Treatment('com_companheiro'))"
RHS = {"M1": R, "M2": f"{R} + {I} + {A} + {G}", "M2cc": f"{R} + {I} + {A} + {G}", "M3": f"{R} + {I} + {A} + {G} + {SC}"}


def estima(cells, rhs):
    cells = E6.para_rs(cells.assign(CODMUNRES=cells.CODMUNRES.astype(str)))
    f = E.fit_agg(cells, rhs, "poisson")
    mg = {r["nivel"]: r for r in E.marginal(f, cells, "raca", T.RACAS, "Branca")}
    out = {}
    for t in E.termos(f, R + "[T."):
        g = t["termo"].split("[T.")[1].rstrip("]")
        out[g] = dict(PR=t["est"], PR_lo=t["lo"], PR_hi=t["hi"], PR_p=t["p"], RD_pp=100 * mg[g]["dif"], RD_lo=100 * mg[g]["dif_lo"],
                      RD_hi=100 * mg[g]["dif_hi"], P_raca_pct=100 * mg[g]["p_nivel"], P_branca_pct=100 * mg[g]["p_ref"], G=f["G"])
    return out


# (b)
rows = []
for desf in ["ptb", "pig", "ptb_ind", "ptb_esp", "lbw_termo"]:
    s = d[d[desf].notna()]
    c2 = E.agrega(s, desf, ["raca", "idade_cat", "ano", "regiao"])
    s3 = s[s.estciv_cat.notna()]
    c3 = E.agrega(s3, desf, ["raca", "idade_cat", "ano", "regiao", "esc_cat", "estciv_cat"])
    assert int(c2.n.sum()) == len(s) and int(c3.n.sum()) == len(s3)
    for m, cells, nn in [("M1", c2, len(s)), ("M2", c2, len(s)), ("M2cc", c3, len(s3)), ("M3", c3, len(s3))]:
        for g, v in estima(cells, RHS[m]).items():
            rows.append(dict(modelo=m, desfecho=desf, raca=g, N=nn, casos=int(cells.Y.sum()), **v))
    log(f"(b) {desf}: M1/M2/M2cc/M3 ({(time.time() - t0) / 60:.1f} min)")
B = pd.DataFrame(rows)
B.to_csv(L.TAB / f"tab_e6b_01_modelos_m1m3_v1_{L.STAMP}.csv", index=False)
log("PR (EP região de saúde):\n" + B.pivot_table(index=["desfecho", "raca"], columns="modelo", values="PR").round(3).to_string())

# (c)
JOBS = [("so_DUM", d.ig_metodo == "DUM", ["ptb", "pig", "ptb_ind", "ptb_esp"]),
        ("so_outro_metodo", d.ig_metodo == "outro_metodo", ["ptb", "pig", "ptb_ind", "ptb_esp"]),
        ("sem_CE_DF", ~d.uf.isin(["CE", "DF"]), ["ptb", "pig", "ptb_ind", "ptb_esp"]),
        ("sem_2024", d.ano != 2024, ["ptb", "pig", "ptb_ind", "ptb_esp"]),
        ("pig_k0", None, ["pig_k0"]), ("pig_k6", None, ["pig_k6"])]
rows = []
for rot, mask, outs in JOBS:
    sub = d if mask is None else d[mask.fillna(False).to_numpy(bool)]
    for desf in outs:
        s = sub[sub[desf].notna()]
        c = E.agrega(s, desf, ["raca", "idade_cat", "ano", "regiao"])
        assert int(c.n.sum()) == len(s)
        for g, v in estima(c, RHS["M2"]).items():
            rows.append(dict(cenario=rot, desfecho=desf, raca=g, N=len(s), casos=int(c.Y.sum()), **v))
    log(f"(c) {rot}: n = {len(sub):,} ({(time.time() - t0) / 60:.1f} min)")
C = pd.DataFrame(rows)
C.to_csv(L.TAB / f"tab_e6b_01_m2_cenarios_v1_{L.STAMP}.csv", index=False)
log("PR M2 Indígena por cenário:\n" + C[C.raca == "Indigena"][["cenario", "desfecho", "N", "PR", "PR_lo", "PR_hi"]].round(3).to_string(index=False))

# (d)
rows = []
for desf in ["ptb", "ptb_esp", "ptb_ind", "pig"]:
    s = d[d[desf].notna()]
    for (g, met), x in s.groupby(["raca", "ig_metodo"], observed=True):
        rows.append(dict(desfecho=desf, raca=g, ig_metodo=met, n=len(x), casos=int(x[desf].sum()), pct=100 * x[desf].mean()))
    for g, x in s.groupby("raca", observed=True):
        rows.append(dict(desfecho=desf, raca=g, ig_metodo="todos", n=len(x), casos=int(x[desf].sum()), pct=100 * x[desf].mean()))
D = pd.DataFrame(rows)
D.to_csv(L.TAB / f"tab_e6b_01_ptb_raca_metodo_v1_{L.STAMP}.csv", index=False)
log("% PTB por raça × método:\n" + D[D.desfecho == "ptb"].pivot(index="raca", columns="ig_metodo", values="pct").round(2).to_string())
log(f"6b.1 concluído em {(time.time() - t0) / 60:.1f} min")
