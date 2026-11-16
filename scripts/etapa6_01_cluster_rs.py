"""
6.1 EP agrupado por REGIÃO DE SAÚDE de residência (433; os 533 sem região = um cluster por UF), etapa6_lib.para_rs.
 (a) M2 Brasil (5 desfechos; RP e DR marginal; etapa1_lib.fit_agg/marginal) com EP por município E por região de saúde;
     análise 3.2 completa (etapa4_lib.roda_32 → etapa3_lib.knol) com EP por região de saúde.
 (b) ICR-chave das Etapas 4 e 4b com EP por região de saúde: PIG e PTB indicado em 4.1 (outro método, DUM), 4.2 (únicas;
     só PTB indicado), 4.3 (sem CE/DF), 4.4 (sem 2024), 4.5 (PIG +0/+6 dias); PTB espontâneo em DUM, outro método e
     plausível (4b.3, critérios b e a). A imputação múltipla (4.6) roda à parte: etapa4_06_imputacao_raca.py 10 --rs.
 (c) Indígenas: nº de regiões de saúde com ≥ 1 e ≥ 100 nascimentos indígenas por tercil; % dos nascimentos indígenas
     nas 10 maiores regiões.
Saídas: tab_e6_01a_m2, tab_e6_01a_{conjunto,dentro,interacao,wald}, tab_e6_01b_{interacao,wald}, tab_e6_01c_indigenas.
"""
import time

import numpy as np
import pandas as pd

import etapa1_lib as E
import etapa3_lib as T
import etapa4_lib as S4
import etapa6_lib as E6
import etapa0_lib as L

log = E6.logger("01_cluster_rs")
t0 = time.time()
d = S4.carrega()
fl = pd.read_parquet(L.PROC / f"implausivel_flags_v1_{L.STAMP}.parquet")
assert len(fl) == len(d)
d = d.reset_index(drop=True)
for crit in ("b", "a"):
    imp = fl[f"imp_{crit}"].fillna(0).to_numpy().astype(bool)  # NA (não elegível) = não implausível; NA→bool daria True
    for desf in ("ptb", "ptb_esp"):
        x = d[desf].astype("Float64").copy()
        x[imp & (x == 1).fillna(False).to_numpy(bool)] = 0.0
        d[f"{desf}_plaus_{crit}"] = x.astype("Int8")
    nr, ne = int((imp & (d.ptb == 1).to_numpy(bool)).sum()), int((imp & (d.ptb_esp == 1).fillna(False).to_numpy(bool)).sum())
    log(f"critério {crit}: PTB reclassificados {nr:,}; espontâneos {ne:,}")
    assert (nr, ne) == {"b": (410747, 244676), "a": (1495209, 854300)}[crit]  # = Etapa 4b.3
# coerência do cluster: CO_REGSAUD da base = mapa município → região
cl = E6.cluster_rs(d.CODMUNRES)
acc = d.CO_REGSAUD.notna().to_numpy()
assert (cl[acc] == d.CO_REGSAUD.astype(str).to_numpy()[acc]).all()
log(f"clusters: {len(np.unique(cl[acc]))} regiões de saúde + {len(np.unique(cl[~acc]))} UF (n = {int((~acc).sum())} sem região)")

# (a) M2
OUT = ["ptb", "ptb_esp", "ptb_ind", "pig", "lbw_termo"]
R = "C(raca, Treatment('Branca'))"
m2 = []
for desf in OUT:
    s = d[d[desf].notna()]
    c = E.agrega(s, desf, ["raca", "idade_cat", "ano", "regiao"])
    c["CODMUNRES"] = c.CODMUNRES.astype(str)
    assert int(c.n.sum()) == len(s)
    for nome, cc in [("municipio", c), ("regsaude", E6.para_rs(c))]:
        f = E.fit_agg(cc, T.M2, "poisson")
        mg = {r["nivel"]: r for r in E.marginal(f, cc, "raca", T.RACAS, "Branca")}
        for t in E.termos(f, R + "[T."):
            g = t["termo"].split("[T.")[1].rstrip("]")
            m2.append(dict(desfecho=desf, cluster=nome, G=f["G"], N=len(s), casos=int(s[desf].sum()), raca=g, RP=t["est"],
                           RP_lo=t["lo"], RP_hi=t["hi"], DR_pp=100 * mg[g]["dif"], DR_lo=100 * mg[g]["dif_lo"],
                           DR_hi=100 * mg[g]["dif_hi"]))
    log(f"M2 {desf}: município e região de saúde ({(time.time() - t0) / 60:.1f} min)")
pd.DataFrame(m2).to_csv(L.TAB / f"tab_e6_01a_m2_v1_{L.STAMP}.csv", index=False)

res = {k: [] for k in ("conjunto", "dentro", "interacao", "wald")}
for desf in OUT:
    r = S4.roda_32(d, desf, "3.2_regsaude", remap=E6.para_rs)
    for k in res:
        res[k].append(r[k])
    w = r["wald"].iloc[0]
    log(f"3.2 {desf} (região de saúde): G = {w.G}; Wald χ² = {w.chi2:.1f}, p = {w.p:.2e} ({(time.time() - t0) / 60:.1f} min)")
for k, v in res.items():
    pd.concat(v).to_csv(L.TAB / f"tab_e6_01a_{k}_v1_{L.STAMP}.csv", index=False)

# (b)
JOBS = [("4.1_outro_metodo", d.ig_metodo == "outro_metodo", ["pig", "ptb_ind", "ptb_esp"]),
        ("4.1_DUM", d.ig_metodo == "DUM", ["pig", "ptb_ind", "ptb_esp"]),
        ("4.2_unicas", d.unica == 1, ["ptb_ind"]),
        ("4.3_sem_CE_DF", ~d.uf.isin(["CE", "DF"]), ["pig", "ptb_ind"]),
        ("4.4_sem_2024", d.ano != 2024, ["pig", "ptb_ind"]),
        ("4.5_pig_k0", None, ["pig_k0"]),
        ("4.5_pig_k6", None, ["pig_k6"]),
        ("4b.3_plausivel", None, ["ptb_esp_plaus_b", "ptb_esp_plaus_a", "ptb_plaus_b", "ptb_plaus_a"])]
rb = {k: [] for k in ("interacao", "wald")}
for rot, mask, outs in JOBS:
    sub = d if mask is None else d[mask.fillna(False).to_numpy(bool)]
    for desf in outs:
        r = S4.roda_32(sub, desf, rot, remap=E6.para_rs)
        for k in rb:
            rb[k].append(r[k])
    log(f"(b) {rot}: n = {len(sub):,}; {outs} ({(time.time() - t0) / 60:.1f} min)")
for k, v in rb.items():
    pd.concat(v).to_csv(L.TAB / f"tab_e6_01b_{k}_v1_{L.STAMP}.csv", index=False)

# (c)
ind = d[(d.raca == "Indigena") & d.CO_REGSAUD.notna()]
por = ind.groupby(["tercil_reg", "CO_REGSAUD"], observed=True).size().rename("n").reset_index()
rows = []
for t, x in por.groupby("tercil_reg", observed=True):
    rows.append(dict(tercil=str(t), n_indigenas=int(x.n.sum()), regioes_ge1=int(x.CO_REGSAUD.nunique()),
                     regioes_ge100=int(x.groupby("CO_REGSAUD").n.sum().ge(100).sum())))
tot = ind.groupby("CO_REGSAUD").size().sort_values(ascending=False)
mp = pd.read_csv(L.PROC / f"municipio_regsaude_dez24_v1_{L.STAMP}.csv", dtype=str).drop_duplicates("CO_REGSAUD").set_index("CO_REGSAUD").nome_regsaud
rows.append(dict(tercil="todos", n_indigenas=int(tot.sum()), regioes_ge1=int((tot >= 1).sum()), regioes_ge100=int((tot >= 100).sum()),
                 pct_top10=100 * tot.head(10).sum() / tot.sum(),
                 top10="; ".join(f"{mp.get(k, k)} ({v:,})" for k, v in tot.head(10).items())))
C = pd.DataFrame(rows)
C.to_csv(L.TAB / f"tab_e6_01c_indigenas_v1_{L.STAMP}.csv", index=False)
log("(c) indígenas por região de saúde:\n" + C.to_string(index=False))
log(f"6.1 concluído em {(time.time() - t0) / 60:.1f} min")
