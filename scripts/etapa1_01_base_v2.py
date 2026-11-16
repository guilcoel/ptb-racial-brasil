"""
1.1 Base v2 — base enxuta da Etapa 0 + SEXO, com desfechos e categorias derivados.

Lê os brutos (somente leitura), padroniza como na v1 (etapa0_02_base.py) e acrescenta SEXO.
A v1 não é tocada. Grava data/processed/sinasc_brasil_2015_2024_v2_<STAMP>/ano=AAAA/part-0.parquet
e outputs/tables/dicionario_variaveis_v2_<STAMP>.csv.

PIG: grade INTERGROWTH-21st de etapa1_02b_pig_grade.R (gigs, ig_nbs/wfga), IG em dias = 7*semanas + k.
"""
import shutil

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

import etapa0_lib as L

log = L.Logger("01_base_v2", etapa="etapa1")

V2_DIR = L.PROC / f"sinasc_brasil_2015_2024_v2_{L.STAMP}"
KEEP2 = L.KEEP + ["SEXO"]
INT_COLS = [c for c in KEEP2 if c not in ("CODMUNRES", "DTNASC")]
GRADE = pd.read_parquet(L.PROC / f"pig_grade_intergrowth_v1_{L.STAMP}.parquet")

ESC = {1: "1_nenhuma", 2: "2_1a3anos", 3: "3_4a7anos", 4: "4_8a11anos", 5: "5_12mais"}
ESTCIV = {1: "sem_companheiro", 2: "com_companheiro", 3: "sem_companheiro", 4: "sem_companheiro",
          5: "com_companheiro"}


def b(s):
    """Booleano nullable -> ndarray bool (nulo = False)."""
    return s.fillna(False).to_numpy(dtype=bool)


def cat(s, cats):
    return pd.Categorical(s, categories=cats)


def deriva(df):
    d = pd.DataFrame(index=df.index)
    ok = L.cascade_flags(df)
    d["incl"] = ok["incluido"].to_numpy()
    d["raca"] = cat(df.RACACORMAE.map(L.RACA_LABEL), L.RACA_ORDER)
    ig = df.SEMAGESTAC
    d["ptb"] = (ig < 37).astype("Int8")  # nulo onde SEMAGESTAC é nulo
    sub = np.select([b(ig < 28), b(ig.between(28, 31)), b(ig.between(32, 36)),
                     b(ig >= 37)], ["1_extremo_lt28", "2_muito_28a31", "3_moderado_tardio_32a36",
                                                 "0_termo_ou_pos"], None)
    d["ptb_sub"] = cat(sub, ["0_termo_ou_pos", "1_extremo_lt28", "2_muito_28a31", "3_moderado_tardio_32a36"])
    tp = df.STTRABPART.fillna(-1).to_numpy()
    ce = df.STCESPARTO.fillna(-1).to_numpy()
    pa_ = df.PARTO.fillna(-1).to_numpy()
    ind = (tp == 1) | ((pa_ == 2) & (ce == 1))
    esp = ~ind & (tp == 2) & ((pa_ == 1) | ((pa_ == 2) & (ce == 2)))
    tipo = np.where(ind, "indicado", np.where(esp, "espontaneo", "sem_classif"))
    d["ptb_tipo"] = cat(np.where(b(d.ptb == 1), tipo, None),
                        ["espontaneo", "indicado", "sem_classif"])
    peso_ok = df.PESO.between(100, 7000).fillna(False)
    termo = ig.between(37, 41).fillna(False)
    d["lbw_termo"] = pd.array(np.where(b(termo & peso_ok), b(df.PESO < 2500).astype(int), -1), dtype="Int8")
    d.loc[d.lbw_termo == -1, "lbw_termo"] = pd.NA
    d["unica"] = pd.array(np.select([b(df.GRAVIDEZ == 1), b(df.GRAVIDEZ.isin([2, 3]))], [1, 0], -1), dtype="Int8")
    d.loc[d.unica == -1, "unica"] = pd.NA
    # PIG: elegível = única, IG 24–42, SEXO 1/2, PESO 100–7000
    eleg = (df.GRAVIDEZ == 1).fillna(False) & ig.between(24, 42).fillna(False) & df.SEXO.isin([1, 2]) & peso_ok
    d["pig_elegivel"] = eleg.to_numpy()
    key = pd.DataFrame({"SEMAGESTAC": ig.where(eleg), "SEXO": df.SEXO.where(eleg), "PESO": df.PESO.where(eleg)})
    m = key[eleg].astype("int32").merge(
        GRADE.astype({"SEMAGESTAC": "int32", "SEXO": "int32", "PESO": "int32"}),
        on=["SEMAGESTAC", "SEXO", "PESO"], how="left", validate="many_to_one")
    assert m.centil_k3.notna().all()
    idx = key.index[eleg]
    for k in (0, 3, 6):
        s = pd.Series(pd.NA, index=d.index, dtype="Int8")
        s.loc[idx] = (m[f"centil_k{k}"].to_numpy() < 0.1).astype(int)
        d[f"pig_k{k}" if k != 3 else "pig"] = s
    s = pd.Series(pd.NA, index=d.index, dtype="Int8")
    s.loc[idx] = (m.PESO.to_numpy() / 1000 < m.p10_oficial_kg_k3.to_numpy()).astype(int)
    d["pig_tabela_oficial"] = s
    d["idade_cat"] = cat(np.select([b(df.IDADEMAE < 20), b(df.IDADEMAE.between(20, 34)),
                                    b(df.IDADEMAE.between(35, 60))], ["<20", "20-34", ">=35"], None),
                         ["20-34", "<20", ">=35"])
    d["esc_cat"] = cat(df.ESCMAE.map(ESC), list(ESC.values()))
    d["estciv_cat"] = cat(df.ESTCIVMAE.map(ESTCIV), ["com_companheiro", "sem_companheiro"])
    return d


if V2_DIR.exists():
    shutil.rmtree(V2_DIR)  # só a saída deste script
V2_DIR.mkdir(parents=True)
total = 0
for y in L.YEARS:
    raw = pd.read_parquet(L.RAW / f"sinasc_{y}.parquet", columns=KEEP2)
    df = pd.DataFrame(index=raw.index)
    df["CODMUNRES"] = raw.CODMUNRES.astype("string").str.strip()
    dt = raw.DTNASC.astype("string").str.strip().str.zfill(8)
    df["DTNASC"] = pd.to_datetime(dt, format="%d%m%Y", errors="raise").dt.date
    for c in INT_COLS:
        s = raw[c]
        if not (pd.api.types.is_float_dtype(s) or pd.api.types.is_integer_dtype(s)):
            s = pd.to_numeric(s.astype("string").str.strip().replace({"": pd.NA}), errors="raise")
        df[c] = s.astype("Int32" if c == "PESO" else "Int16")
    df["cod_uf"] = df.CODMUNRES.str.slice(0, 2)
    df["uf"] = df.cod_uf.map(L.UF_SIGLA).astype("string")
    df["regiao"] = df.cod_uf.str.slice(0, 1).map(L.REGIAO).astype("string")
    df["periodo"] = "2015-2019" if y <= 2019 else ("2020-2021" if y <= 2021 else "2022-2024")
    out = pd.concat([df, deriva(df)], axis=1)
    pdir = V2_DIR / f"ano={y}"
    pdir.mkdir()
    pq.write_table(pa.Table.from_pandas(out, preserve_index=False), pdir / "part-0.parquet", compression="zstd")
    n_out = pq.ParquetFile(pdir / "part-0.parquet").metadata.num_rows
    assert n_out == len(raw)
    total += n_out
    log(f"ano={y} gravado; incl={int(out.incl.sum()):,}", n_out)
log(f"base v2 em {V2_DIR}", total)

DIC = [
    ("CODMUNRES..PESO, SEXO", "bruto", "18 variáveis da v1 + SEXO (1 M, 2 F, 0 ignorado); inteiros, códigos originais preservados"),
    ("cod_uf, uf, regiao", "derivada", "2 primeiros dígitos de CODMUNRES; região pelo 1º dígito (N, NE, SE, S, CO)"),
    ("ano", "partição", "ano de DTNASC (= ano do arquivo)"),
    ("periodo", "derivada", "2015-2019 / 2020-2021 / 2022-2024"),
    ("incl", "derivada", "amostra analítica da Etapa 0 (cascata RSP: raça 1/2/4/5; SEMAGESTAC 22–44; ESCMAE 1–5; IDADEMAE 10–60)"),
    ("raca", "derivada", "Branca (1), Parda (4), Preta (2), Indigena (5); nulo nos demais"),
    ("ptb", "desfecho", "SEMAGESTAC < 37; nulo se SEMAGESTAC nulo"),
    ("ptb_sub", "desfecho", "<28 extremo; 28–31 muito; 32–36 moderado/tardio; >=37 termo_ou_pos"),
    ("ptb_tipo", "desfecho", "só em ptb=1. indicado = STTRABPART 1 ou (PARTO 2 e STCESPARTO 1); espontaneo = STTRABPART 2 e (PARTO 1 ou (PARTO 2 e STCESPARTO 2)); sem_classif = resto"),
    ("lbw_termo", "desfecho", "PESO < 2500; definido só em SEMAGESTAC 37–41 com PESO 100–7000 (todas as gestações)"),
    ("unica", "derivada", "GRAVIDEZ 1 = 1; 2/3 = 0; 9/nulo = nulo"),
    ("pig_elegivel", "derivada", "única, SEMAGESTAC 24–42, SEXO 1/2, PESO 100–7000"),
    ("pig", "desfecho", "INTERGROWTH-21st peso/IG (gigs ig_nbs wfga) centil < 0,10; IG = 7*semanas+3 dias; só elegíveis"),
    ("pig_k0, pig_k6", "sensibilidade", "idem com IG = 7*semanas+0 e +6 dias"),
    ("pig_tabela_oficial", "sensibilidade", "PESO < P10 da tabela oficial em PDF (semanas+3 dias)"),
    ("idade_cat", "derivada", "<20; 20-34 (ref); >=35 (10–60 anos)"),
    ("esc_cat", "derivada", "ESCMAE 1 nenhuma; 2 1–3 anos; 3 4–7; 4 8–11; 5 12+; 9/nulo = nulo"),
    ("estciv_cat", "derivada", "com companheiro = casada (2) ou união estável (5); sem = solteira (1), viúva (3), separada (4); 9/nulo = nulo"),
]
pd.DataFrame(DIC, columns=["variavel", "tipo", "definicao"]).to_csv(
    L.TAB / f"dicionario_variaveis_v2_{L.STAMP}.csv", index=False)
log("dicionário gravado")
