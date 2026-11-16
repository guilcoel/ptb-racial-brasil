"""
etapa4_lib.py — sensibilidades da análise de referência 3.2 (raça × tercil de acesso dentro da região, M2,
Knol & VanderWeele, ref. Branca–T3), reaproveitando etapa3_lib.knol (estimador não reescrito).

roda_32(d, desf, rotulo): agrega a subamostra (sem os 533 sem região de saúde) e devolve as tabelas de knol
com colunas sensibilidade/desfecho. classifica(): regra do quadro-síntese:
  mantém = mesmo sinal do original e IC exclui 0; enfraquece = mesmo sinal e IC inclui 0;
  inverte = sinal oposto e IC exclui 0; (sinal oposto com IC incluindo 0 = enfraquece)
  achado D (PTB total sem modificação): mantém se o IC do ICR Indígena×T1 inclui 0, senão muda.
"""
import pandas as pd

import etapa1_lib as E
import etapa3_lib as T
import etapa0_lib as L

COLS = ["raca", "idade_cat", "regiao", "uf", "CODMUNRES", "CO_REGSAUD", "ig_metodo", "unica", "ptb", "ptb_tipo",
        "ptb_esp", "ptb_ind", "pig", "pig_k0", "pig_k6", "lbw_termo"]


def logger(name):
    return L.Logger(name, etapa="etapa4")


def carrega():
    d = T.anexa_acesso(T.load(COLS))
    d["ig_metodo"] = pd.Categorical(d.ig_metodo.astype(str), categories=["DUM", "outro_metodo", "ignorado"])
    return d


def roda_32(d, desf, rotulo, remap=None):
    """remap: função sobre as células que troca o identificador de cluster (Etapa 6: etapa6_lib.para_rs)."""
    s = d[d[desf].notna() & d.CO_REGSAUD.notna()]
    c = E.agrega(s, desf, ["raca", "idade_cat", "ano", "regiao", "tercil_reg"])
    assert int(c.n.sum()) == len(s) and int(c.Y.sum()) == int(s[desf].sum())
    c["CODMUNRES"] = c.CODMUNRES.astype(str)
    if remap is not None:
        c = remap(c)
    c["raca"] = c.raca.cat.remove_unused_categories() if c.raca.cat.categories.size > 4 else c.raca
    r = T.knol(c, "tercil_reg", ["T1", "T2", "T3"], "T3", mod_main="C(tercil_reg, Treatment('T3'))", rotulo="tercil_reg")
    out = {k: r[k].assign(sensibilidade=rotulo, desfecho=desf, n_individual=len(s)) for k in ("conjunto", "dentro", "interacao", "wald")}
    return out


def classifica(achado, orig, novo):
    """orig/novo: dict com ICR_pp, ICR_lo, ICR_hi."""
    if achado == "D":
        return "mantém" if (novo["ICR_lo"] <= 0 <= novo["ICR_hi"]) else "muda"
    s0 = 1 if orig["ICR_pp"] > 0 else -1
    s1 = 1 if novo["ICR_pp"] > 0 else -1
    exclui = novo["ICR_lo"] > 0 or novo["ICR_hi"] < 0
    if s1 == s0:
        return "mantém" if exclui else "enfraquece"
    return "inverte" if exclui else "enfraquece"


ACHADOS = [("A", "pig", "Indigena"), ("B", "ptb_ind", "Indigena"), ("B", "ptb_ind", "Parda"),
           ("C", "ptb_esp", "Indigena"), ("D", "ptb", "Indigena")]
