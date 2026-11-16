"""
2.1 Base v3 = v2 + TPMETESTIM + região de saúde + desfechos da Etapa 2. A v2 não é tocada.

TPMETESTIM (bruto): 1 exame físico; 2 outro método; 9 ignorado (dicionários 2019 e 2024).
  O código 8 NÃO está em nenhum dicionário; no dado ocorre em 100% dos registros com DUM válida e
  em ~0% dos demais (conferido em 2015, 2019, 2024): 8 = IG calculada pela DUM (método não se aplica).
Mudanças de definição em relação à v2:
  lbw_termo: só em gestação única (GRAVIDEZ = 1), 37–41 sem, peso 100–7,000 g
  pig / pig_k0 / pig_k6: já restritos a únicas na v2 (sem mudança)
Novos desfechos (denominador = amostra exceto PTB sem classificação):
  ptb_esp = 1 PTB espontâneo; 0 termo ou PTB indicado; nulo se PTB sem classificação
  ptb_ind = 1 PTB indicado;  0 termo ou PTB espontâneo; nulo se PTB sem classificação
Região de saúde: CO_REGSAUD pela tabela DATASUS dez/2024 (etapa2_02_regiao_saude.py); nulo em UF+0000.
"""
import shutil

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

import etapa0_lib as L

log = L.Logger("01_base_v3", etapa="etapa2")
V2 = L.PROC / f"sinasc_brasil_2015_2024_v2_{L.STAMP}"
V3 = L.PROC / f"sinasc_brasil_2015_2024_v3_{L.STAMP}"
mapa = pd.read_csv(L.PROC / f"municipio_regsaude_dez24_v1_{L.STAMP}.csv", dtype=str)
mp = dict(zip(mapa.CODMUNRES, mapa.CO_REGSAUD))

if V3.exists():
    shutil.rmtree(V3)  # só a saída deste script
V3.mkdir(parents=True)
tot, inc = 0, 0
for y in L.YEARS:
    v2 = pd.read_parquet(V2 / f"ano={y}" / "part-0.parquet")
    raw = pd.read_parquet(L.RAW / f"sinasc_{y}.parquet", columns=["TPMETESTIM", "CODMUNRES", "PESO"])
    assert len(raw) == len(v2)
    # a v2 foi gravada na ordem do bruto: confere alinhamento linha a linha
    assert (raw.CODMUNRES.astype("string").str.strip().to_numpy() == v2.CODMUNRES.to_numpy()).all()
    pr = pd.to_numeric(raw.PESO.astype("string").str.strip().replace({"": pd.NA}), errors="raise").astype("Int32")
    assert pr.equals(v2.PESO.astype("Int32")) or ((pr == v2.PESO) | (pr.isna() & v2.PESO.isna())).all()
    s = raw.TPMETESTIM
    if not (pd.api.types.is_float_dtype(s) or pd.api.types.is_integer_dtype(s)):
        s = pd.to_numeric(s.astype("string").str.strip().replace({"": pd.NA}), errors="raise")
    v2["TPMETESTIM"] = s.astype("Int16").to_numpy()
    v2["CO_REGSAUD"] = v2.CODMUNRES.map(mp).astype("string")
    sing = (v2.unica == 1).fillna(False).to_numpy(bool)
    v2.loc[~sing, "lbw_termo"] = pd.NA
    tipo = v2.ptb_tipo.astype(object)
    termo = (v2.ptb == 0).fillna(False).to_numpy(bool)
    for col, alvo, outro in [("ptb_esp", "espontaneo", "indicado"), ("ptb_ind", "indicado", "espontaneo")]:
        x = pd.Series(pd.NA, index=v2.index, dtype="Int8")
        x[termo | (tipo == outro).to_numpy(bool)] = 0
        x[(tipo == alvo).to_numpy(bool)] = 1
        v2[col] = x
    pdir = V3 / f"ano={y}"
    pdir.mkdir()
    pq.write_table(pa.Table.from_pandas(v2, preserve_index=False), pdir / "part-0.parquet", compression="zstd")
    tot += len(v2)
    inc += int(v2.incl.sum())
    log(f"ano={y}: incl={int(v2.incl.sum()):,}; sem região de saúde={int(v2.CO_REGSAUD.isna().sum())}", len(v2))
assert inc == 25808740, inc
log(f"base v3 em {V3}; incl = {inc:,}", tot)

dic = pd.read_csv(L.TAB / f"dicionario_variaveis_v2_{L.STAMP}.csv")
dic.loc[dic.variavel == "lbw_termo", "definicao"] = "PESO < 2500; só gestação única (GRAVIDEZ 1), SEMAGESTAC 37–41, PESO 100–7000 (v3)"
novas = pd.DataFrame([
    ("TPMETESTIM", "bruto", "1 exame físico; 2 outro método; 9 ignorado (dicionário); 8 = não documentado, ocorre em 100% dos registros com DUM válida -> IG pela DUM"),
    ("CO_REGSAUD", "derivada", "região de saúde (CIR), tabela DATASUS base territorial dez/2024 fixa para 2015–2024; nulo nos códigos UF+0000"),
    ("ptb_esp", "desfecho", "1 PTB espontâneo; 0 termo ou PTB indicado; nulo se PTB sem classificação"),
    ("ptb_ind", "desfecho", "1 PTB indicado; 0 termo ou PTB espontâneo; nulo se PTB sem classificação"),
], columns=dic.columns)
pd.concat([dic, novas]).to_csv(L.TAB / f"dicionario_variaveis_v3_{L.STAMP}.csv", index=False)
log("dicionário v3 gravado")
