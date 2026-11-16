"""
0.6 Viabilidade: prematuridade espontânea × indicada, entre os prematuros (<37 sem) da amostra analítica.

Polaridade conferida no dicionário (Estrutura_SINASC_para_CD.pdf) e na memória do CliMaterna
(STTRABPART=1 nunca aparece em Robson 01/03): STTRABPART 1 = trabalho de parto INDUZIDO.
  indicada   = STTRABPART==1  OU  (PARTO==2 E STCESPARTO==1)
  espontânea = STTRABPART==2  E  (PARTO==1  OU  (PARTO==2 E STCESPARTO==2))
  sem classificação = o resto, com motivo.
No parto vaginal STCESPARTO não entra na regra: em 2015 ele veio nulo para quase todo vaginal
(código 3 'não se aplica' só passou a ser gravado em 2016).

Saídas:
  tab11_trabpart_cesparto_parto_regiao_ano  STTRABPART × STCESPARTO × PARTO (n e % na região-ano)
  tab12_fenotipo_regiao_ano                 indicada / espontânea / sem classificação, n e %
  tab13_fenotipo_motivos                    motivo da não classificação, por região e ano
"""
import numpy as np
import pandas as pd

import etapa0_lib as L

log = L.Logger("06_fenotipo")
df = pd.read_parquet(L.BASE_DIR, columns=["RACACORMAE", "SEMAGESTAC", "ESCMAE", "IDADEMAE", "regiao", "ano",
                                          "STTRABPART", "STCESPARTO", "PARTO"])
df["ano"] = df["ano"].astype(int)
ok = L.cascade_flags(df)
p = df[ok.incluido.values & (df.SEMAGESTAC < 37).fillna(False).to_numpy(bool)].copy()
log("prematuros na amostra analítica", len(p))

tp = p.STTRABPART.fillna(-1).astype(int).to_numpy()
ce = p.STCESPARTO.fillna(-1).astype(int).to_numpy()
pa = p.PARTO.fillna(-1).astype(int).to_numpy()
indicada = (tp == 1) | ((pa == 2) & (ce == 1))
espont = ~indicada & (tp == 2) & ((pa == 1) | ((pa == 2) & (ce == 2)))
p["fenotipo"] = np.select([indicada, espont], ["indicada", "espontanea"], "sem_classificacao")
motivo = np.select(
    [indicada | espont,
     np.isin(tp, [9, -1]),
     np.isin(pa, [9, -1]),
     (pa == 2) & np.isin(ce, [9, -1]),
     (pa == 2) & (ce == 3)],
    ["classificado", "STTRABPART ignorado/nulo", "PARTO ignorado/nulo",
     "cesárea com STCESPARTO ignorado/nulo", "cesárea com STCESPARTO=3 (inconsistente)"],
    "outro")
p["motivo"] = motivo
assert (p.motivo[p.fenotipo == "sem_classificacao"] != "classificado").all()


def lab(s):
    return s.astype("Int64").astype("string").fillna("nulo")


p["STTRABPART_c"], p["STCESPARTO_c"], p["PARTO_c"] = lab(p.STTRABPART), lab(p.STCESPARTO), lab(p.PARTO)

frames = []
for reg_name, d in [("Brasil", p)] + [(r, p[p.regiao == r]) for r in L.REGIOES]:
    for ano_name, dd in [("2015-2024", d)] + [(str(y), d[d.ano == y]) for y in L.YEARS]:
        t = dd.groupby(["STTRABPART_c", "STCESPARTO_c", "PARTO_c"]).size().rename("n").reset_index()
        t["pct"] = (100 * t.n / len(dd)).round(3)
        t.insert(0, "ano", ano_name)
        t.insert(0, "regiao", reg_name)
        frames.append(t)
pd.concat(frames).to_csv(L.out_name("tab11_trabpart_cesparto_parto_regiao_ano"), index=False)


def resumo(col, name):
    out = []
    for reg_name, d in [("Brasil", p)] + [(r, p[p.regiao == r]) for r in L.REGIOES]:
        for ano_name, dd in [("2015-2024", d)] + [(str(y), d[d.ano == y]) for y in L.YEARS]:
            vc = dd[col].value_counts()
            for k, v in vc.items():
                out.append(dict(regiao=reg_name, ano=ano_name, categoria=k, n=int(v),
                                pct=round(100 * v / len(dd), 2), n_prematuros=len(dd)))
    pd.DataFrame(out).to_csv(L.out_name(name), index=False)
    return pd.DataFrame(out)


r12 = resumo("fenotipo", "tab12_fenotipo_regiao_ano")
resumo("motivo", "tab13_fenotipo_motivos")
for _, r in r12[(r12.regiao == "Brasil") & (r12.ano == "2015-2024")].iterrows():
    log(f"Brasil 2015-2024 {r.categoria}: {r.pct}%", r.n)
# inconsistências que a regra deixa passar (contagem informativa)
log(f"vaginal com STCESPARTO=1 (tratado pela regra como vaginal): {int(((pa == 1) & (ce == 1)).sum()):,}")
log(f"induzido E cesárea antes do TP (STTRABPART=1, PARTO=2, STCESPARTO=1): {int(((tp == 1) & (pa == 2) & (ce == 1)).sum()):,}")
