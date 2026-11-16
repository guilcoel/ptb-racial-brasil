"""
3.0(a) ig_metodo na base v3 (coluna derivada, sem nova versão da base).

ig_metodo = 'DUM' (TPMETESTIM 8) / 'outro_metodo' (1 ou 2) / 'ignorado' (9 ou nulo).
O código 8 não está no dicionário; ocorre em 100% dos registros com DUM válida (Etapa 2, etapa2_01_base_v3.py).
Regrava cada partição num arquivo temporário, confere n e as colunas antigas, e só então substitui.
Saída: distribuição por raça (amostra) em tab_e3_00a_ig_metodo_raca; dicionário v3 atualizado.
"""
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

import etapa0_lib as L

log = L.Logger("00a_ig_metodo", etapa="etapa3")
V3 = L.PROC / f"sinasc_brasil_2015_2024_v3_{L.STAMP}"
dist = []
for y in L.YEARS:
    f = V3 / f"ano={y}" / "part-0.parquet"
    d = pd.read_parquet(f)
    if "ig_metodo" in d:
        d = d.drop(columns="ig_metodo")
    t = d.TPMETESTIM
    d["ig_metodo"] = pd.Categorical(np.select([(t == 8).fillna(False).to_numpy(bool), t.isin([1, 2]).fillna(False).to_numpy(bool)],
                                              ["DUM", "outro_metodo"], "ignorado"), categories=["DUM", "outro_metodo", "ignorado"])
    tmp = f.with_name("part-0.tmp.parquet")
    pq.write_table(pa.Table.from_pandas(d, preserve_index=False), tmp, compression="zstd")
    chk = pd.read_parquet(tmp)
    assert len(chk) == len(d) and chk.drop(columns="ig_metodo").equals(d.drop(columns="ig_metodo"))
    tmp.replace(f)
    s = d[d.incl]
    dist.append(pd.crosstab(s.raca, s.ig_metodo).assign(ano=y))
    log(f"ano={y}: ig_metodo gravado", len(d))

D = pd.concat(dist).reset_index().groupby("raca", observed=True)[["DUM", "outro_metodo", "ignorado"]].sum()
D.loc["Total"] = D.sum()
P = D.div(D.sum(axis=1), axis=0).mul(100).round(2).add_prefix("pct_")
out = pd.concat([D, P], axis=1)
out.to_csv(L.TAB / f"tab_e3_00a_ig_metodo_raca_v1_{L.STAMP}.csv")
log("distribuição por raça: " + out[["pct_DUM", "pct_outro_metodo", "pct_ignorado"]].to_string().replace("\n", " | "))
dic = pd.read_csv(L.TAB / f"dicionario_variaveis_v3_{L.STAMP}.csv")
if "ig_metodo" not in set(dic.variavel):
    dic.loc[len(dic)] = ["ig_metodo", "derivada", "DUM (TPMETESTIM 8) / outro_metodo (1, 2) / ignorado (9 ou nulo); adicionada à v3 na Etapa 3"]
dic.to_csv(L.TAB / f"dicionario_variaveis_v3_{L.STAMP}.csv", index=False)
