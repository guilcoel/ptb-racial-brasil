"""
0.2 Base nacional enxuta — SINASC 2015–2024, Parquet particionado por ano (hive: ano=AAAA).

Padronização de tipos SEM recodificar categorias:
  - códigos e contagens -> inteiro nullable (o '01' de MESPRENAT/QTDFILVIVO vira 1, como o
    2023 já trazia; 9/99/9999 continuam 9/99/9999); vazio/nulo -> nulo
  - CODMUNRES -> texto 6 dígitos (como vem do DATASUS)
  - DTNASC -> date (ddmmaaaa)
Derivadas: ano (de DTNASC; conferido = ano do arquivo), cod_uf, uf, regiao.
Também grava uma coluna _ano_arquivo para auditoria.
"""
import shutil

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

import etapa0_lib as L

log = L.Logger("02_base")
INT_COLS = [c for c in L.KEEP if c not in ("CODMUNRES", "DTNASC")]
INT_TYPE = {c: "Int32" if c == "PESO" else "Int16" for c in INT_COLS}

if L.BASE_DIR.exists():
    shutil.rmtree(L.BASE_DIR)  # só a saída deste script, nunca o bruto
L.BASE_DIR.mkdir(parents=True)

total, rows = 0, []
for y in L.YEARS:
    df = pd.read_parquet(L.RAW / f"sinasc_{y}.parquet", columns=L.KEEP)
    n_in = len(df)
    out = pd.DataFrame(index=df.index)
    out["CODMUNRES"] = df["CODMUNRES"].astype("string").str.strip()
    dt = df["DTNASC"].astype("string").str.strip().str.zfill(8)
    out["DTNASC"] = pd.to_datetime(dt, format="%d%m%Y", errors="coerce").dt.date
    n_dt_inval = int(out["DTNASC"].isna().sum())
    for c in INT_COLS:
        s = df[c]
        if not (pd.api.types.is_float_dtype(s) or pd.api.types.is_integer_dtype(s)):
            s = pd.to_numeric(s.astype("string").str.strip().replace({"": pd.NA}), errors="raise")
        out[c] = s.astype(INT_TYPE[c])
    out["ano"] = pd.to_numeric(dt.str.slice(4, 8), errors="coerce").astype("Int16")
    assert (out["ano"] == y).all(), f"{y}: DTNASC fora do ano do arquivo"
    out["_ano_arquivo"] = pd.Series(y, index=out.index, dtype="Int16")
    out["cod_uf"] = out["CODMUNRES"].str.slice(0, 2)
    out["uf"] = out["cod_uf"].map(L.UF_SIGLA).astype("string")
    out["regiao"] = out["cod_uf"].str.slice(0, 1).map(L.REGIAO).astype("string")
    assert out["uf"].notna().all() and out["regiao"].notna().all()

    pdir = L.BASE_DIR / f"ano={y}"
    pdir.mkdir()
    tbl = pa.Table.from_pandas(out.drop(columns="ano"), preserve_index=False)
    pq.write_table(tbl, pdir / "part-0.parquet", compression="zstd")
    n_out = pq.ParquetFile(pdir / "part-0.parquet").metadata.num_rows
    assert n_out == n_in
    total += n_out
    rows.append(dict(ano=y, n_bruto=n_in, n_gravado=n_out, dtnasc_invalida=n_dt_inval))
    log(f"ano={y} gravado; DTNASC inválida={n_dt_inval}", n_out)

pd.DataFrame(rows).to_csv(L.out_name("tab00_base_gravacao"), index=False)
log(f"base em {L.BASE_DIR}", total)
