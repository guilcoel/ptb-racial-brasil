"""
0.1 Descoberta — inventário dos Parquets anuais do SINASC (2015–2024) no Forja.

Lê só as colunas de interesse. Saídas (agregadas):
  tab00_inventario_ano          n, colunas, UFs, CODMUNRES inválido, DTNASC fora do ano
  tab00_inventario_uf_ano       n por UF × ano (detecta UF faltante)
  tab00_esquema_ano             presença e tipo físico de cada coluna-alvo por ano
  tab00_distribuicao_codigos    contagem de cada valor bruto por variável × ano (exceto PESO)
  tab00_peso_resumo             PESO: nulos, vazios, min, max, n fora de 100–7000
"""
import pandas as pd
import pyarrow.parquet as pq

import etapa0_lib as L

log = L.Logger("01_descoberta")
log("início; fonte=" + str(L.RAW))


def as_text(s):
    """Texto bruto padronizado: strip; float inteiro (2023) vira '9', não '9.0'; nulo continua nulo."""
    if pd.api.types.is_float_dtype(s) or pd.api.types.is_integer_dtype(s):
        return s.astype("Int64").astype("string")
    return s.astype("string").str.strip()


inv, inv_uf, schema, dist, peso = [], [], [], [], []
for y in L.YEARS:
    f = L.RAW / f"sinasc_{y}.parquet"
    pf = pq.ParquetFile(f)
    sch = pf.schema_arrow
    for c in L.KEEP:
        schema.append(dict(ano=y, variavel=c, presente=c in sch.names,
                           tipo=str(sch.field(c).type) if c in sch.names else ""))
    cols = [c for c in L.KEEP if c in sch.names]
    df = pd.read_parquet(f, columns=cols)
    n = len(df)
    log(f"lido {f.name}", n)

    cod = as_text(df["CODMUNRES"])
    uf2 = cod.str.slice(0, 2)
    valid_uf = uf2.isin(list(L.UF_SIGLA))
    dt = as_text(df["DTNASC"]).str.zfill(8)
    ano_dt = pd.to_numeric(dt.str.slice(4, 8), errors="coerce")
    inv.append(dict(
        ano=y, arquivo=f.name, bytes=f.stat().st_size, n_registros=n,
        n_colunas_arquivo=len(sch.names), n_uf=int(uf2[valid_uf].nunique()),
        codmunres_nulo=int(cod.isna().sum()),
        codmunres_uf_invalida=int((~valid_uf & cod.notna()).sum()),
        codmunres_len6=int((cod.str.len() == 6).sum()), codmunres_len7=int((cod.str.len() == 7).sum()),
        dtnasc_nulo=int(dt.isna().sum()), dtnasc_ano_diferente=int((ano_dt != y).sum()),
    ))
    vc = uf2.where(valid_uf, "XX").value_counts()
    for k, v in vc.items():
        inv_uf.append(dict(ano=y, cod_uf=k, uf=L.UF_SIGLA.get(k, "invalida"), n=int(v)))

    for c in cols:
        if c in ("CODMUNRES", "DTNASC"):
            continue
        s = as_text(df[c])
        if c == "PESO":
            p = pd.to_numeric(s, errors="coerce")
            peso.append(dict(ano=y, nulo=int(s.isna().sum()), vazio=int((s == "").sum()),
                             nao_numerico=int((p.isna() & s.notna() & (s != "")).sum()),
                             min=p.min(), max=p.max(), fora_100_7000=int(((p < 100) | (p > 7000)).sum()),
                             igual_9999=int((p == 9999).sum())))
            continue
        vc = s.fillna("<NULO>").replace({"": "<VAZIO>"}).value_counts(dropna=False)
        for k, v in vc.items():
            dist.append(dict(variavel=c, ano=y, valor=k, n=int(v), pct=round(100 * v / n, 4)))

pd.DataFrame(inv).to_csv(L.out_name("tab00_inventario_ano"), index=False)
pd.DataFrame(inv_uf).to_csv(L.out_name("tab00_inventario_uf_ano"), index=False)
pd.DataFrame(schema).to_csv(L.out_name("tab00_esquema_ano"), index=False)
pd.DataFrame(dist).to_csv(L.out_name("tab00_distribuicao_codigos"), index=False)
pd.DataFrame(peso).to_csv(L.out_name("tab00_peso_resumo"), index=False)
log("fim", sum(r["n_registros"] for r in inv))
