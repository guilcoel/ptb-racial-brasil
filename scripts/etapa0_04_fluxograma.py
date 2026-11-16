"""
0.4 Fluxograma nacional com os critérios do artigo da RSP, por região.

Saídas:
  tab06_fluxograma_regiao      n restante e n excluído em cada passo, por região e Brasil
  tab07_fluxograma_motivos     detalhe do que foi excluído em cada passo (nulo vs código)
  tab08_ptb_incluidos_excluidos  prevalência de PTB (<37 sem) entre incluídos e excluídos, por região
  tab09_n_final_raca           n final por raça, por região e Brasil, com PTB %
PTB entre excluídos só é definível onde SEMAGESTAC não é nulo (no arquivo, 19–45 sem); o
denominador está explícito.
"""
import numpy as np
import pandas as pd

import etapa0_lib as L

log = L.Logger("04_fluxograma")
df = pd.read_parquet(L.BASE_DIR, columns=["RACACORMAE", "SEMAGESTAC", "ESCMAE", "IDADEMAE", "regiao", "uf", "ano"])
log("base lida", len(df))
ok = L.cascade_flags(df)
df["etapa"] = ok["etapa_exclusao"].values
df["incluido"] = ok["incluido"].values
df["ptb"] = np.where(df["SEMAGESTAC"].isna(), np.nan, (df["SEMAGESTAC"] < 37).astype(float))

# fluxograma
rows = []
for reg, d in [("Brasil", df)] + [(r, df[df.regiao == r]) for r in L.REGIOES]:
    n = len(d)
    rows.append(dict(regiao=reg, passo="0_fonte", descricao="nascidos vivos 2015–2024", excluidos=0, restante=n))
    for k, desc in L.CASCADE:
        e = int((d.etapa == k).sum())
        n -= e
        rows.append(dict(regiao=reg, passo=k, descricao=desc, excluidos=e, restante=n))
    assert n == int(d.incluido.sum())
fx = pd.DataFrame(rows)
fx.to_csv(L.out_name("tab06_fluxograma_regiao"), index=False)
for r in rows:
    if r["regiao"] == "Brasil":
        log(f"Brasil {r['passo']}: excluídos={r['excluidos']:,}", r["restante"])

# motivos detalhados dentro de cada passo
mot = []
def _sel(s, conds, labels):
    conds = [c.fillna(False).to_numpy(dtype=bool) for c in conds]
    return pd.Series(np.select(conds, labels, "ok"), index=s.index)


det = {
    "1_raca": ("RACACORMAE", lambda s: s.astype("string").fillna("nulo")),
    "2_ig": ("SEMAGESTAC", lambda s: _sel(s, [s.isna(), s < 22, s > 44], ["nulo", "<22", ">44"])),
    "3_esc": ("ESCMAE", lambda s: s.astype("string").fillna("nulo")),
    "4_idade": ("IDADEMAE", lambda s: _sel(s, [s.isna(), s == 99, s < 10, s > 60], ["nulo", "99", "<10", ">60 (exc. 99)"])),
}
for k, (col, fn) in det.items():
    sub = df[df.etapa == k]
    vc = pd.crosstab(fn(sub[col]), sub["regiao"])
    vc["Brasil"] = vc.sum(axis=1)
    vc = vc.reset_index().melt(id_vars=vc.index.name or "index", var_name="regiao", value_name="n")
    vc.columns = ["motivo", "regiao", "n"]
    vc.insert(0, "passo", k)
    mot.append(vc)
pd.concat(mot).to_csv(L.out_name("tab07_fluxograma_motivos"), index=False)

# PTB entre incluídos e excluídos
pr = []
for reg, d in [("Brasil", df)] + [(r, df[df.regiao == r]) for r in L.REGIOES]:
    for grp, m in [("incluidos", d.incluido), ("excluidos", ~d.incluido)] + \
                  [(f"excluidos_{k}", d.etapa == k) for k, _ in L.CASCADE]:
        s = d.loc[m, "ptb"]
        pr.append(dict(regiao=reg, grupo=grp, n=int(m.sum()), n_ig_definida=int(s.notna().sum()),
                       n_ptb=int(np.nansum(s)), ptb_pct=round(100 * np.nanmean(s), 2) if s.notna().any() else np.nan))
pd.DataFrame(pr).to_csv(L.out_name("tab08_ptb_incluidos_excluidos"), index=False)

# n final por raça
inc = df[df.incluido].copy()
inc["raca"] = inc["RACACORMAE"].map(L.RACA_LABEL)
fr = []
for reg, d in [("Brasil", inc)] + [(r, inc[inc.regiao == r]) for r in L.REGIOES]:
    for g in L.RACA_ORDER + ["Total"]:
        s = d if g == "Total" else d[d.raca == g]
        fr.append(dict(regiao=reg, raca=g, n=len(s), n_ptb=int(s.ptb.sum()), ptb_pct=round(100 * s.ptb.mean(), 2)))
pd.DataFrame(fr).to_csv(L.out_name("tab09_n_final_raca"), index=False)
log("amostra analítica nacional", len(inc))
