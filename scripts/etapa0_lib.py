"""
etapa0_lib.py — constantes e utilitários comuns da Etapa 0 (ptb-racial-brasil).

Brutos SOMENTE LEITURA. Seed 42. Nenhuma linha individual vai para log ou saída:
só contagens agregadas.
"""
import os
import random
from datetime import datetime
from pathlib import Path

import numpy as np

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

RAW = Path(os.environ.get("SINASC_RAW", "/Volumes/Forja/CliMaterna/01_data/raw/SINASC"))
PROJ = Path(__file__).resolve().parents[1]
PROC = PROJ / "data" / "processed"
TAB = PROJ / "outputs" / "tables"
LOGD = PROJ / "outputs" / "logs"
STAMP = "20261008"
YEARS = list(range(2015, 2025))

BASE_DIR = PROC / f"sinasc_brasil_2015_2024_v1_{STAMP}"  # Parquet particionado por ano

KEEP = ["CODMUNRES", "DTNASC", "RACACORMAE", "SEMAGESTAC", "GESTACAO", "IDADEMAE",
        "ESCMAE", "ESCMAE2010", "GRAVIDEZ", "PARTO", "CONSULTAS", "MESPRENAT",
        "QTDFILVIVO", "ESTCIVMAE", "STTRABPART", "STCESPARTO", "TPROBSON", "PESO"]

UF_SIGLA = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL",
    "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
    "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}
REGIAO = {"1": "N", "2": "NE", "3": "SE", "4": "S", "5": "CO"}  # 1º dígito do código IBGE da UF
REGIOES = ["N", "NE", "SE", "S", "CO"]

for d in (PROC, TAB, LOGD):
    d.mkdir(parents=True, exist_ok=True)


RACA_LABEL = {1: "Branca", 2: "Preta", 4: "Parda", 5: "Indigena"}
RACA_ORDER = ["Branca", "Parda", "Preta", "Indigena"]

# Cascata do artigo da RSP (lib_baseB.build_cascade, Racial-PTB-SINASC), em sequência:
#   1 raça/cor: exclui nulo, amarela (3) e qualquer código fora de {1,2,4,5}
#   2 IG: exclui SEMAGESTAC nulo ou fora de 22–44
#   3 escolaridade: exclui ESCMAE nulo ou 9 (o artigo exige ESCMAE em 1–5)
#   4 idade materna: exclui IDADEMAE nulo, < 10 ou > 60 (99 = ignorado cai aqui)
CASCADE = [
    ("1_raca", "raça/cor ausente, ignorada ou amarela"),
    ("2_ig", "IG ausente ou fora de 22–44 sem"),
    ("3_esc", "escolaridade (ESCMAE) ausente ou ignorada"),
    ("4_idade", "idade materna ausente, <10 ou >60"),
]


def cascade_flags(df):
    """Devolve DataFrame booleano com o critério de cada passo (True = passa) e a etapa de exclusão."""
    import pandas as pd
    ok = pd.DataFrame(index=df.index)
    ok["1_raca"] = df["RACACORMAE"].isin([1, 2, 4, 5]).fillna(False).astype(bool)
    ok["2_ig"] = df["SEMAGESTAC"].between(22, 44).fillna(False).astype(bool)
    ok["3_esc"] = df["ESCMAE"].between(1, 5).fillna(False).astype(bool)
    ok["4_idade"] = df["IDADEMAE"].between(10, 60).fillna(False).astype(bool)
    etapa = pd.Series("incluido", index=df.index, dtype="object")
    alive = pd.Series(True, index=df.index)
    for k, _ in CASCADE:
        hit = alive & ~ok[k]
        etapa[hit] = k
        alive &= ok[k]
    ok["etapa_exclusao"] = etapa
    ok["incluido"] = alive
    return ok


class Logger:
    def __init__(self, name, etapa="etapa0"):
        self.path = LOGD / f"{etapa}_{STAMP}.log"
        self.name = name

    def __call__(self, msg, n=None):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [{self.name}] {msg}" + (f" | n={n:,}" if n is not None else "")
        print(line, flush=True)
        with open(self.path, "a") as fh:
            fh.write(line + "\n")


def out_name(prefix, version="v1", ext="csv"):
    return TAB / f"{prefix}_{version}_{STAMP}.{ext}"
