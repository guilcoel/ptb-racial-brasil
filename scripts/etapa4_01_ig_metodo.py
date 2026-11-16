"""
4.1 Método de estimação da IG (ig_metodo: DUM / outro_metodo / ignorado).
 (a) distribuição de ig_metodo por raça × tercil_reg × macrorregião (amostra de acesso)
 (b) 3.2 (i–iii) para ptb, ptb_esp, ptb_ind, pig, lbw_termo restrito a outro_metodo e, separadamente, a DUM
     (e a ignorado, só para a auditoria de soma)
 (c) M2 + ig_metodo + raça×ig_metodo (ref DUM), amostra analítica completa, Wald robusto conjunto
Saídas: tab_e4_01a_ig_metodo_distribuicao, tab_e4_01b_{conjunto,dentro,interacao,wald}, tab_e4_01c_raca_x_igmetodo_*.
"""
import time

import pandas as pd

import etapa1_lib as E
import etapa3_lib as T
import etapa4_lib as S4
import etapa0_lib as L

log = S4.logger("01_ig_metodo")
d = S4.carrega()
log("amostra", len(d))
t0 = time.time()

# (a)
a = d[d.CO_REGSAUD.notna()]
ct = a.groupby(["regiao", "raca", "tercil_reg", "ig_metodo"], observed=True).size().rename("n").reset_index()
tot = ct.groupby(["regiao", "raca", "tercil_reg"], observed=True).n.transform("sum")
ct["pct"] = 100 * ct.n / tot
br = a.groupby(["raca", "tercil_reg", "ig_metodo"], observed=True).size().rename("n").reset_index().assign(regiao="Brasil")
br["pct"] = 100 * br.n / br.groupby(["raca", "tercil_reg"], observed=True).n.transform("sum")
pd.concat([br, ct]).to_csv(L.TAB / f"tab_e4_01a_ig_metodo_distribuicao_v1_{L.STAMP}.csv", index=False)
x = br[br.ig_metodo == "DUM"].pivot(index="raca", columns="tercil_reg", values="pct").round(1)
log("% DUM por raça × tercil (Brasil): " + x.to_string().replace("\n", " | "))

# (b)
OUT = ["ptb", "ptb_esp", "ptb_ind", "pig", "lbw_termo"]
res = {k: [] for k in ("conjunto", "dentro", "interacao", "wald")}
for metodo in ["outro_metodo", "DUM", "ignorado"]:
    sub = d[d.ig_metodo == metodo]
    for desf in OUT:
        r = S4.roda_32(sub, desf, f"4.1_{metodo}")
        for k in res:
            res[k].append(r[k])
    log(f"3.2 em ig_metodo = {metodo}: n = {len(sub):,} ({(time.time() - t0) / 60:.1f} min)")
for k, v in res.items():
    pd.concat(v).to_csv(L.TAB / f"tab_e4_01b_{k}_v1_{L.STAMP}.csv", index=False)

# (c) raça × ig_metodo na amostra completa (inclui os 533; acesso não entra)
rc = {k: [] for k in ("conjunto", "dentro", "interacao", "wald")}
for desf in OUT:
    s = d[d[desf].notna()]
    c = E.agrega(s, desf, ["raca", "idade_cat", "ano", "regiao", "ig_metodo"])
    c["CODMUNRES"] = c.CODMUNRES.astype(str)
    assert int(c.n.sum()) == len(s)
    r = T.knol(c, "ig_metodo", ["DUM", "outro_metodo", "ignorado"], "DUM", mod_main="C(ig_metodo, Treatment('DUM'))",
               rotulo="ig_metodo")
    for k in rc:
        rc[k].append(r[k].assign(desfecho=desf))
    w = r["wald"].iloc[0]
    log(f"raça × ig_metodo, {desf}: Wald χ² = {w.chi2:.1f} ({w.gl} gl), p = {w.p:.2e}")
for k, v in rc.items():
    pd.concat(v).to_csv(L.TAB / f"tab_e4_01c_raca_x_igmetodo_{k}_v1_{L.STAMP}.csv", index=False)
log(f"4.1 concluído em {(time.time() - t0) / 60:.1f} min")
