#!/usr/bin/env python3
"""
Auditoria independente da Etapa 7c.4 (pacote v7_20261009 -> v8_20261009).

Código próprio, escrito do zero. Só lê arquivos do projeto; grava apenas em audit_independente/etapa7c4/.
Não lê scripts/etapa7b_checa.py, scripts/etapa7b_02_suplementar.py nem outputs/manuscrito/checa_7b_*.csv.
Não lê microdados (nada em data/).

Blocos:
  A  Tabela S2b recalculada das fontes _rs (12 células) e conferida contra CSV, aba do ESM_1 (suplementar e
     Submissao), Tabela 3 v8, tab_e6_01a_interacao, números-chave v8; gl/G do Wald; fontes por município (sem _rs).
  B  Rodapé da S2b.
  C  Números-chave v7 x v8.
  D  CSV, xlsx e docx v7 x v8.
  E  PDFs e figuras v7 x v8.
  F  MANIFEST.md e data_code_availability.md.
  G  Conferências pedidas (respostas no relatório).
Saída: comparacao_7c4_v1_20261009.csv (verificacao, ok, detalhe).
"""
import csv
import hashlib
import json
import math
import re
import warnings
from pathlib import Path

import docx
import numpy as np
import openpyxl
import pandas as pd
from PIL import Image

warnings.filterwarnings("ignore")
import pymupdf  # noqa: E402

Image.MAX_IMAGE_PIXELS = None

ROOT = Path("/Volumes/Forja/ptb-racial-brasil")
TAB = ROOT / "outputs" / "tables"
MAN = ROOT / "outputs" / "manuscrito"
V7 = MAN / "_arquivo_v7"
SUB8 = ROOT / "Submissao"
SUB7 = V7 / "Submissao"
OUT = ROOT / "audit_independente" / "etapa7c4"
SRC = "_v1_20261008.csv"
S7, S8 = "v7_20261009", "v8_20261009"

PROIBIDOS = ("etapa7b_checa.py", "etapa7b_02_suplementar.py", "checa_7b_")

linhas = []


def reg(verificacao, ok, detalhe):
    linhas.append({"verificacao": verificacao, "ok": bool(ok), "detalhe": str(detalhe)})


# ----------------------------------------------------------------------------------------------------------------
# formatação (regra do pacote)
MENOS = "−"
TRACO = "–"


def f2(x):
    return f"{float(x):.2f}".replace("-", MENOS)


def fdif(e, lo, hi):
    return f"{f2(e)} ({f2(lo)} to {f2(hi)})"


def frat(e, lo, hi):
    return f"{f2(e)} ({f2(lo)}{TRACO}{f2(hi)})"


def fp(p):
    p = float(p)
    if p < 1e-4:
        return "<0.0001"
    k = math.floor(math.log10(p))
    s = f"{p:.{max(2 - k, 0)}f}"
    if math.floor(math.log10(float(s))) > k:  # arredondamento subiu de ordem (ex.: 0.09996 -> 0.1000)
        s = f"{float(s):.{max(1 - k, 0)}f}"
    return s


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def um(df, **kw):
    m = np.ones(len(df), bool)
    for k, v in kw.items():
        m &= (df[k].astype(str) == str(v)).to_numpy()
    r = df[m]
    if len(r) != 1:
        raise ValueError(f"filtro {kw} devolveu {len(r)} linhas")
    return r.iloc[0]


def le_csv(p):
    with open(p, newline="", encoding="utf-8-sig") as fh:
        return list(csv.reader(fh))


def valores_aba(ws):
    return [list(r) for r in ws.iter_rows(values_only=True)]


# ----------------------------------------------------------------------------------------------------------------
# fontes
I = pd.read_csv(TAB / f"tab_e3_02_interacao_rs{SRC}")
W = pd.read_csv(TAB / f"tab_e3_02_wald_rs{SRC}")
C = pd.read_csv(TAB / f"tab_e3_03a_indice_continuo_rs{SRC}")
D = pd.read_csv(TAB / f"tab_e3_02_dentro_rs{SRC}")
I0 = pd.read_csv(TAB / f"tab_e3_02_interacao{SRC}")
W0 = pd.read_csv(TAB / f"tab_e3_02_wald{SRC}")
C0 = pd.read_csv(TAB / f"tab_e3_03a_indice_continuo{SRC}")
E6 = pd.read_csv(TAB / f"tab_e6_01a_interacao{SRC}")
MULT = pd.read_csv(TAB / f"tab_e6_05_multiplicidade{SRC}")

DESF = [("ptb", "Preterm birth (total)"), ("pig", "SGA"), ("ptb_ind", "Provider-initiated preterm birth")]
COLS = ["(a) IC Ind×T1, tercis por macrorregião", "(b) IC Ind×T1, tercis nacionais", "(b) Wald p",
        "(c) RP interação por 5 p.p."]


def cont(df, d):
    r = df[(df.desfecho == d) & (df.raca == "Indigena")]
    assert len(r) == 3 and r.RP_por_5pp_interacao.nunique() == 1 and r.int_lo.nunique() == 1 and r.int_hi.nunique() == 1
    return r


esperado, fonte = {}, {}
for d, lab in DESF:
    a = um(I, analise="3.2_tercil_reg", estrato="Brasil", raca="Indigena", nivel="T1", desfecho=d)
    b = um(I, analise="3.3b_tercil_nac", estrato="Brasil", raca="Indigena", nivel="T1_pior", desfecho=d)
    w = um(W, analise="3.3b_tercil_nac", estrato="Brasil", desfecho=d)
    c = cont(C, d).iloc[0]
    fonte[d] = dict(a=a, b=b, w=w, c=c)
    esperado[d] = [lab, fdif(a.ICR_pp, a.ICR_lo, a.ICR_hi), fdif(b.ICR_pp, b.ICR_lo, b.ICR_hi), fp(w.p),
                   frat(c.RP_por_5pp_interacao, c.int_lo, c.int_hi)]

# S2b publicada
P_S2B = MAN / "suplementar" / f"S2b_access_specifications_{S8}.csv"
P_ESM1_8 = MAN / "suplementar" / f"ESM_1_tables_S1_S6_{S8}.xlsx"
P_ESM1_7 = V7 / "suplementar" / f"ESM_1_tables_S1_S6_{S7}.xlsx"
s2b_csv = le_csv(P_S2B)
wb_sup = openpyxl.load_workbook(P_ESM1_8)
wb_sub = openpyxl.load_workbook(SUB8 / "ESM_1.xlsx")
ABA = "S2b_access_specifications"


def tabela_da_aba(ws):
    v = valores_aba(ws)
    i = next(k for k, r in enumerate(v) if r and r[0] == "Outcome")
    corpo = []
    for r in v[i + 1:]:
        if r[0] is None:
            break
        corpo.append(["" if x is None else str(x) for x in r])
    notas = [r[0] for r in v[i + 1 + len(corpo):] if r and r[0]]
    return v, ["" if x is None else str(x) for x in v[i]], corpo, notas


tem_sup, tem_sub = ABA in wb_sup.sheetnames, ABA in wb_sub.sheetnames
reg("A.aba_S2b_existe", tem_sup and tem_sub, f"suplementar: {tem_sup}; Submissao/ESM_1.xlsx: {tem_sub}")
v_sup, h_sup, corpo_sup, notas_sup = tabela_da_aba(wb_sup[ABA])
v_sub, h_sub, corpo_sub, notas_sub = tabela_da_aba(wb_sub[ABA])

titulo = v_sup[0][0]
reg("A.titulo_aba", titulo == "Table S2b. Alternative specifications of access to early prenatal care"
    and v_sub[0][0] == titulo, f"A1 = {titulo!r}")
h_csv = s2b_csv[0]
palavras = ["(a)", "within macroregion", "IC Indigenous×T1 per 100 (95% CI)", "(b) National tertiles",
            "Wald p (6 df)", "(c) Continuous index", "interaction PR per 5 percentage points (95% CI)"]
falta = [p for p in palavras if p not in " | ".join(h_csv)]
reg("A.cabecalho", h_csv == h_sup == h_sub and len(h_csv) == 5 and not falta,
    f"CSV = xlsx suplementar = xlsx Submissao: {h_csv == h_sup == h_sub}; 5 colunas: {len(h_csv) == 5}; "
    f"termos ausentes: {falta or 'nenhum'}")
reg("A.linhas", [r[0] for r in s2b_csv[1:]] == [l for _, l in DESF] and len(corpo_sup) == 3 and len(corpo_sub) == 3,
    f"CSV: {[r[0] for r in s2b_csv[1:]]}; xlsx: {[r[0] for r in corpo_sup]} / {[r[0] for r in corpo_sub]}")

for k, (d, lab) in enumerate(DESF):
    for j, nome in enumerate(COLS, start=1):
        e = esperado[d][j]
        x_csv = s2b_csv[1 + k][j] if len(s2b_csv) > 1 + k else None
        x_sup = corpo_sup[k][j] if len(corpo_sup) > k else None
        x_sub = corpo_sub[k][j] if len(corpo_sub) > k else None
        reg(f"A.celula[{lab} | {nome}]", e == x_csv == x_sup == x_sub,
            f"recalculado {e!r}; CSV {x_csv!r}; xlsx suplementar {x_sup!r}; xlsx Submissao {x_sub!r}")

reg("A.aba_S2b_suplementar=Submissao", valores_aba(wb_sup[ABA]) == valores_aba(wb_sub[ABA])
    and {str(r) for r in wb_sup[ABA].merged_cells.ranges} == {str(r) for r in wb_sub[ABA].merged_cells.ranges},
    f"{wb_sup[ABA].max_row}×{wb_sup[ABA].max_column} células comparadas (inclui título e rodapé)")

# (a) = Tabela 3 v8
t3 = le_csv(MAN / "tabelas" / f"tab03_knol_tercile_{S8}.csv")
jic = t3[0].index("IC per 100 (95% CI)")


def t3_ic(lab):
    i = next(k for k, r in enumerate(t3) if r[0].startswith(lab + " (N ="))
    for r in t3[i + 1:]:
        if r[0] and not r[0].startswith("  "):
            break
        if r[0].strip() == "Indigenous – T1 (worst access)":
            return r[jic]
    return None


for k, (d, lab) in enumerate(DESF):
    x = t3_ic(lab)
    reg(f"A.(a)=Tabela3_v8[{lab}]", x == s2b_csv[1 + k][1] == esperado[d][1],
        f"Tabela 3 v8 (Indigenous – T1, IC per 100) {x!r}; S2b {s2b_csv[1 + k][1]!r}")

# (a) = tab_e6_01a_interacao
for k, (d, lab) in enumerate(DESF):
    a = fonte[d]["a"]
    e = um(E6, modificador="tercil_reg", raca="Indigena", nivel="T1", desfecho=d, sensibilidade="3.2_regsaude")
    dif = max(abs(a.ICR_pp - e.ICR_pp), abs(a.ICR_lo - e.ICR_lo), abs(a.ICR_hi - e.ICR_hi))
    fe = fdif(e.ICR_pp, e.ICR_lo, e.ICR_hi)
    reg(f"A.(a)=tab_e6_01a_interacao[{lab}]", dif < 1e-9 and fe == s2b_csv[1 + k][1],
        f"tab_e6_01a {fe!r} (bruto {e.ICR_pp:.10f}); tab_e3_02_interacao_rs {a.ICR_pp:.10f}; max|dif| = {dif:.1e}")

# números-chave v8
NK8 = {x["id"]: x for x in json.load(open(MAN / f"numeros_chave_{S8}.json", encoding="utf-8"))}
NK7 = {x["id"]: x for x in json.load(open(V7 / f"numeros_chave_{S7}.json", encoding="utf-8"))}
for k, (d, lab) in enumerate(DESF):
    f = fonte[d]
    pares = [(f"ICR_Ind_T1_{d}", 1, f["a"].ICR_pp, "(a)"),
             (f"IC_Ind_T1_tertil_nacional_{d}", 2, f["b"].ICR_pp, "(b) IC"),
             (f"Wald_p_tertil_nacional_{d}", 3, f["w"].p, "(b) Wald p"),
             (f"RP_int_5pp_indice_continuo_{d}", 4, f["c"].RP_por_5pp_interacao, "(c)")]
    for nid, j, bruto, rot in pares:
        x = NK8.get(nid)
        if x is None:
            reg(f"A.{rot}=numeros_chave_v8[{nid}]", False, "id ausente")
            continue
        okf = x["valor_formatado"] == s2b_csv[1 + k][j]
        okb = abs(float(x["valor_bruto"]) - float(bruto)) <= 1e-12 * max(1.0, abs(float(bruto)))
        reg(f"A.{rot}=numeros_chave_v8[{nid}]", okf and okb,
            f"formatado {x['valor_formatado']!r} vs S2b {s2b_csv[1 + k][j]!r}; bruto {x['valor_bruto']!r} vs fonte {bruto!r}")

# Wald: gl = 6, G = 433; mesma amostra da (a)
for d, lab in DESF:
    w = fonte[d]["w"]
    wa = um(W, analise="3.2_tercil_reg", estrato="Brasil", desfecho=d)
    reg(f"A.Wald_(b)_gl6_G433[{lab}]", int(w.gl) == 6 and int(w.G) == 433 and int(w.N) == int(wa.N),
        f"chi2 = {w.chi2:.4f}, gl = {int(w.gl)}, G = {int(w.G)}, N = {int(w.N):,} (N da (a) = {int(wa.N):,}), "
        f"p = {w.p!r}, modificador = {w.modificador}")

# fonte é _rs: estimativas pontuais iguais às por município, IC 95% diferentes
for k, (d, lab) in enumerate(DESF):
    for rot, filt, j in [("(a)", dict(analise="3.2_tercil_reg", nivel="T1"), 1),
                         ("(b)", dict(analise="3.3b_tercil_nac", nivel="T1_pior"), 2)]:
        rs = um(I, estrato="Brasil", raca="Indigena", desfecho=d, **filt)
        mu = um(I0, estrato="Brasil", raca="Indigena", desfecho=d, **filt)
        igual = abs(rs.ICR_pp - mu.ICR_pp) < 1e-9
        difere = abs(rs.ICR_lo - mu.ICR_lo) > 1e-6 and abs(rs.ICR_hi - mu.ICR_hi) > 1e-6
        fmu = fdif(mu.ICR_pp, mu.ICR_lo, mu.ICR_hi)
        reg(f"A.fonte_rs_vs_municipio[{lab} | {rot}]", igual and difere and s2b_csv[1 + k][j] == esperado[d][j],
            f"_rs {esperado[d][j]!r} x município {fmu!r}; |Δ ponto| = {abs(rs.ICR_pp - mu.ICR_pp):.1e}; "
            f"Δlo = {rs.ICR_lo - mu.ICR_lo:+.4f}, Δhi = {rs.ICR_hi - mu.ICR_hi:+.4f}; S2b usa a _rs: "
            f"{s2b_csv[1 + k][j] == esperado[d][j] and s2b_csv[1 + k][j] != fmu}")
    rs, mu = cont(C, d).iloc[0], cont(C0, d).iloc[0]
    igual = abs(rs.RP_por_5pp_interacao - mu.RP_por_5pp_interacao) < 1e-9
    difere = abs(rs.int_lo - mu.int_lo) > 1e-6 and abs(rs.int_hi - mu.int_hi) > 1e-6
    fmu = frat(mu.RP_por_5pp_interacao, mu.int_lo, mu.int_hi)
    reg(f"A.fonte_rs_vs_municipio[{lab} | (c)]", igual and difere and s2b_csv[1 + k][4] == esperado[d][4],
        f"_rs {esperado[d][4]!r} (IC {rs.int_lo:.4f}–{rs.int_hi:.4f}) x município {fmu!r} (IC {mu.int_lo:.4f}–"
        f"{mu.int_hi:.4f}); |Δ ponto| = {abs(rs.RP_por_5pp_interacao - mu.RP_por_5pp_interacao):.1e}")
    wr = fonte[d]["w"]
    wm = um(W0, analise="3.3b_tercil_nac", estrato="Brasil", desfecho=d)
    reg(f"A.fonte_rs_vs_municipio[{lab} | (b) Wald]", int(wr.gl) == int(wm.gl) == 6 and abs(wr.chi2 - wm.chi2) > 1e-6
        and int(wr.G) == 433 and s2b_csv[1 + k][3] == fp(wr.p),
        f"_rs chi2 = {wr.chi2:.3f}, p = {fp(wr.p)}, G = {int(wr.G)}; município chi2 = {wm.chi2:.3f}, p = {fp(wm.p)}, "
        f"G = {int(wm.G)}; S2b {s2b_csv[1 + k][3]!r}")

# coerência interna: IC = DR(T1) − DR(T3) (tab_e3_02_dentro_rs)
for d, lab in DESF:
    for rot, an, n1, n3, ic in [("(a)", "3.2_tercil_reg", "T1", "T3", fonte[d]["a"].ICR_pp),
                                ("(b)", "3.3b_tercil_nac", "T1_pior", "T3_melhor", fonte[d]["b"].ICR_pp)]:
        r1 = um(D, analise=an, estrato="Brasil", raca="Indigena", nivel=n1, desfecho=d)
        r3 = um(D, analise=an, estrato="Brasil", raca="Indigena", nivel=n3, desfecho=d)
        calc = r1.DR_pp - r3.DR_pp
        reg(f"A.IC=DR_T1−DR_T3[{lab} | {rot}]", abs(calc - ic) < 1e-9,
            f"DR Ind×Branca {n1} = {r1.DR_pp:.6f}; {n3} = {r3.DR_pp:.6f}; diferença = {calc:.6f}; IC = {ic:.6f}")

# coerência interna: RP de interação contínua x RP em P10/P90
for d, lab in DESF:
    r = cont(C, d).set_index("ponto")
    beta = math.log(r.loc["P90", "RP"] / r.loc["P10", "RP"]) / ((r.loc["P90", "indice"] - r.loc["P10", "indice"]) / 5)
    rp = r.loc["P10", "RP_por_5pp_interacao"]
    sentido = "diminui" if rp < 1 else "aumenta"
    mono = (r.loc["P10", "RP"] > r.loc["P50", "RP"] > r.loc["P90", "RP"]) if rp < 1 else \
        (r.loc["P10", "RP"] < r.loc["P50", "RP"] < r.loc["P90", "RP"])
    reg(f"A.RP_int_coerente_P10_P90[{lab}]", abs(math.exp(beta) - rp) < 1e-6 and mono,
        f"RP Ind/Branca P10 = {r.loc['P10', 'RP']:.3f} (índice {r.loc['P10', 'indice']:.1f}), P50 = "
        f"{r.loc['P50', 'RP']:.3f}, P90 = {r.loc['P90', 'RP']:.3f} (índice {r.loc['P90', 'indice']:.1f}); "
        f"exp(inclinação/5 p.p.) = {math.exp(beta):.6f} = RP_int {rp:.6f}; a razão {sentido} com melhor acesso")

# ----------------------------------------------------------------------------------------------------------------
# B. rodapé
rod = notas_sup[-1] if notas_sup else ""
reg("B.rodape_presente_e_igual", bool(rod) and notas_sup == notas_sub and len(notas_sup) == 1,
    f"{len(notas_sup)} nota(s) na aba suplementar, {len(notas_sub)} na Submissao; iguais: {notas_sup == notas_sub}; "
    f"{len(rod)} caracteres")
NOTA = ("Brown (parda) and Black (preta) follow the Brazilian Institute of Geography and Statistics categories; "
        "race/skin color is analyzed as a marker of exposure to structural racism.")
reg("B.abre_com_nota_raca", rod.startswith(NOTA), f"início: {rod[:150]!r}")
reg("B.cita_G433", "G = 433" in rod, "trecho: " + (re.search(r"[^.]*G = 433[^.]*\.", rod) or [""])[0][:200])
DEF_IC = ("IC (interaction contrast) = risk difference (Indigenous vs White) within T1 minus the same difference "
          "within T3")
reg("B.define_IC", DEF_IC in rod and "per 100 live births" in rod,
    f"definição presente: {DEF_IC in rod}; conferida nos dados (A.IC=DR_T1−DR_T3)")
okw = "jointly tests the 6 race × tertile interaction terms" in rod and "6 df" in rod and \
    "Brown, Black, and Indigenous × T1 and T2" in rod
reg("B.Wald_6gl", okw, "trecho: " + (re.search(r"The Wald test[^)]*\)\.", rod) or [""])[0])
fontes = ["tab_e3_02_interacao_rs", "tab_e3_02_wald_rs", "tab_e3_03a_indice_continuo_rs"]
reg("B.cita_tres_fontes", all(f in rod for f in fontes),
    "trecho: " + (re.search(r"Sources:.*$", rod) or [""])[0])
INT = "interaction PR = multiplicative change in the Indigenous vs White PR per 5-point increase in the index " \
      "(PR < 1: the ratio decreases with better access)"
idx_def = "percentage of births with prenatal care initiated in the first trimester" in rod
reg("B.interpretacao_RP_int", INT in rod and idx_def,
    "texto: 'PR < 1: the ratio decreases with better access'; índice = % com pré-natal iniciado no 1º trimestre "
    "(maior = melhor acesso); RP_int = exp(coef. raça×índice/5) (scripts/etapa3_02_knol.py, l. 83–99); "
    "SGA 0.90 com RP Ind/Branca 1.59→1.26→1.11 de P10 a P90 e provider-initiated 1.25 com 0.44→0.73→0.93: "
    "interpretação correta")

# afirmações do rodapé x fontes
tab1 = le_csv(MAN / "tabelas" / f"tab01_characteristics_{S8}.csv")
sem_rs = next((r for r in tab1 if r[0].strip().startswith("Missing (no health region)")), None)
w32 = um(W, analise="3.2_tercil_reg", estrato="Brasil", desfecho="ptb")
w35 = um(W, analise="3.5_idade", estrato="Brasil", desfecho="ptb")
reg("B.afirma_533_excluidos", "the 533 without one are excluded" in rod and sem_rs is not None and
    sem_rs[-1] == "533" and int(w35.N) - int(w32.N) == 533,
    f"Tabela 1 v8 'Missing (no health region)' total = {sem_rs[-1] if sem_rs else None}; N (3.5, todos) − N (3.2/3.3b) "
    f"= {int(w35.N):,} − {int(w32.N):,} = {int(w35.N) - int(w32.N)}")
s23 = (ROOT / "scripts" / "etapa2_03_indice_acesso.py").read_text(encoding="utf-8")
s32 = (ROOT / "scripts" / "etapa3_02_knol.py").read_text(encoding="utf-8")
ok_nac = ("national distribution of health region × year (2015–2024), weighted by births; T1 = worst access" in rod
          and 'groupby(["CO_REGSAUD", "ano"]).agg(n=("ptb", "size")' in s23 and "w.n.cumsum() / w.n.sum()" in s23
          and '"T1_pior", "T2", "T3_melhor"' in s23 and "sinasc_brasil_2015_2024" in s23)
reg("B.afirma_tercis_nacionais", ok_nac,
    "rodapé: tercis da distribuição nacional região de saúde × ano 2015–2024, ponderados por nascimentos, T1 = pior; "
    "scripts/etapa2_03_indice_acesso.py l. 80–86 (peso = nascidos vivos da amostra analítica por região-ano, "
    "cortes em 1/3 e 2/3 do peso acumulado, rótulos T1_pior/T2/T3_melhor)")
ok_idx = ("in the mother's health region of residence in the previous year" in rod and
          'A["indice"] = 100 * A.tri1 / A.mes_valido' in s23 and "ano=lambda x: x.ano + 1" in s23 and
          'c["ind5"] = c.indice_t1 / 5' in s32)
t3_rod = valores_aba(openpyxl.load_workbook(MAN / "tabelas" / f"tabelas_principais_{S8}.xlsx")["tab03_knol_tercile"])
t3_rod = [r[0] for r in t3_rod if r[0] and str(r[0]).startswith("Brown (parda)")][0]
mesma_def = ("percentage of births with prenatal care initiated in the first trimester in the mother's health region "
             "of residence in the previous year") in t3_rod
reg("B.afirma_definicao_indice", ok_idx and mesma_def,
    "índice = 100 × início do pré-natal no mês 1–3 / MESPRENAT válido (1–9), atribuído com defasagem de 1 ano; "
    "por 5 p.p. (ind5 = índice/5). Mesma redação do rodapé da Tabela 3. Nuance: o denominador é o nº de nascimentos "
    f"com mês de início do pré-natal válido, não todos os nascimentos (redação igual à da Tabela 3: {mesma_def})")
fam = MULT[MULT.desfecho.isin([d for d, _ in DESF])]
fb = fam[(fam.analise == "3.3b_tercil_nac")]
fc = fam[(fam.analise == "3.3a_indice_continuo") & (fam.termo == "Indigena×índice")]
ok_fam = (len(fb) > 0 and (fb.familia == "secundaria").all() and fb.q_BH.isna().all() and len(fc) == 3
          and (fc.familia == "secundaria").all() and fc.q_BH.isna().all())
reg("B.afirma_familia_secundaria", ok_fam and "secondary family of the analysis hierarchy (no multiplicity adjustment)"
    in rod, f"tab_e6_05_multiplicidade: 3.3b ({len(fb)} linhas) e 3.3a Indígena ({len(fc)} linhas) na família "
            f"{sorted(set(fb.familia) | set(fc.familia))}, q_BH vazio (sem ajuste)")
ok_mod = ("model M2 plus the access variable and race × access terms" in rod and
          'mod_main="C(tercil_nac, Treatment(\'T3_melhor\'))"' in s32 and 'T.M2 + " + ind5 + "' in s32)
reg("B.afirma_modelo_e_variancia", ok_mod and "clustering by health region of residence" in rod and
    all(int(fonte[d]["w"].G) == 433 for d, _ in DESF),
    "M2 + acesso + raça×acesso (etapa3_02_knol.py l. 70–99); EP agrupado por região de saúde (--rs), G = 433 na fonte")
# frases do rodapé sem correspondência conferida
frases = [s.strip() for s in re.split(r"(?<=\.)\s+(?=[A-Z(])", rod) if s.strip()]
okB = all(r["ok"] for r in linhas if r["verificacao"].startswith("B."))
reg("B.sem_afirmacao_nao_sustentada", okB,
    f"{len(frases)} frases no rodapé; cada uma conferida acima (nota de raça, 'Indigenous vs White', modelo, 533, (a)=Tabela 3, "
    "tercis nacionais, índice contínuo e RP de interação, definição do IC, Wald 6 gl, variância/G, família secundária, "
    "fontes). Observação: o 'Wald p (6 df)' testa os 6 termos (Parda, Preta e Indígena), não só os indígenas — o rodapé "
    "diz isso corretamente")

# ----------------------------------------------------------------------------------------------------------------
# C. números-chave v7 x v8
L7 = json.load(open(V7 / f"numeros_chave_{S7}.json", encoding="utf-8"))
L8 = json.load(open(MAN / f"numeros_chave_{S8}.json", encoding="utf-8"))
ids7, ids8 = [x["id"] for x in L7], [x["id"] for x in L8]
reg("C.mesmos_ids", ids7 == ids8 and len(set(ids8)) == len(ids8),
    f"v7 {len(ids7)} ids, v8 {len(ids8)} ids, mesma ordem: {ids7 == ids8}; só v7: {sorted(set(ids7) - set(ids8))}; "
    f"só v8: {sorted(set(ids8) - set(ids7))}")


def igual_bruto(a, b):
    if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
        return True
    return a == b and type(a) is type(b)


difb = [i for i in ids7 if i in NK8 and not igual_bruto(NK7[i]["valor_bruto"], NK8[i]["valor_bruto"])]
diff_ = [i for i in ids7 if i in NK8 and NK7[i]["valor_formatado"] != NK8[i]["valor_formatado"]]
reg("C.valor_bruto_identico", not difb, f"{len(ids7) - len(difb)}/{len(ids7)} idênticos; diferentes: {difb[:10]}")
reg("C.valor_formatado_identico", not diff_, f"{len(ids7) - len(diff_)}/{len(ids7)} idênticos; diferentes: {diff_[:10]}")
outros = {}
for campo in ("descricao", "filtro", "arquivo", "script"):
    outros[campo] = [i for i in ids7 if i in NK8 and NK7[i].get(campo) != NK8[i].get(campo)]
reg("C.descricao_filtro_arquivo_script", not any(outros.values()),
    "; ".join(f"{k}: {len(v)} diferenças" for k, v in outros.items()))
cm = sorted({(NK7[i].get("commit"), NK8[i].get("commit")) for i in ids7 if i in NK8})
ncm = sum(NK7[i].get("commit") != NK8[i].get("commit") for i in ids7 if i in NK8)
chaves = sorted({k for x in L7 + L8 for k in x})
_mf8 = (MAN / "MANIFEST.md").read_text(encoding="utf-8")
ok_cm = cm == [("2cde6a0", "3092186")] and "Commit do repositório ao gerar o pacote: 3092186" in _mf8
reg("C.metadado_commit", ok_cm,
    f"campo 'commit' mudou em {ncm}/{len(ids7)} itens: {cm} (commit do repositório ao gerar o pacote, igual ao do "
    f"MANIFEST v8; metadado, não número). Campos: {chaves}")
md7 = (V7 / f"numeros_chave_{S7}.md").read_text(encoding="utf-8").splitlines()
md8 = (MAN / f"numeros_chave_{S8}.md").read_text(encoding="utf-8").splitlines()
dif_md = [(k + 1, a, b) for k, (a, b) in enumerate(zip(md7, md8)) if a != b]
ok_md = len(md7) == len(md8) and [k for k, _, _ in dif_md] == [1, 3] and md8[0] == "# Key numbers (Etapas 7b–7c.4)"
reg("C.md_titulo_e_corpo", ok_md,
    f"{len(md7)} x {len(md8)} linhas; linhas diferentes: {[k for k, _, _ in dif_md]} — título {md7[0]!r} → {md8[0]!r}; "
    f"l.3 = versão/commit do pacote; tabela de valores idêntica")
nove = [f"{p}_{d}" for d, _ in DESF for p in ("IC_Ind_T1_tertil_nacional", "Wald_p_tertil_nacional",
                                               "RP_int_5pp_indice_continuo")]
ja_v7 = all(i in NK7 for i in nove) and all(NK7[i]["valor_formatado"] == NK8[i]["valor_formatado"] for i in nove)
reg("C.numeros_S2b_ja_existiam_v7", ja_v7,
    "os 9 números de (b) e (c) já estavam nos números-chave v7 com o mesmo valor: a S2b não cria número novo")

# ----------------------------------------------------------------------------------------------------------------
# D. CSV, xlsx, docx
for pasta in ("tabelas", "suplementar"):
    f7 = sorted(x for x in (V7 / pasta).glob(f"*_{S7}.csv") if not x.name.startswith("._"))
    f8 = sorted(x for x in (MAN / pasta).glob(f"*_{S8}.csv") if not x.name.startswith("._"))
    n7 = {p.name.replace(S7, "X") for p in f7}
    n8 = {p.name.replace(S8, "X") for p in f8}
    reg(f"D.conjunto_csv[{pasta}]", n8 - n7 == ({"S2b_access_specifications_X.csv"} if pasta == "suplementar" else set())
        and not (n7 - n8), f"v7 {len(n7)}, v8 {len(n8)}; novos na v8: {sorted(n8 - n7)}; ausentes na v8: {sorted(n7 - n8)}")
    for p7 in f7:
        p8 = MAN / pasta / p7.name.replace(S7, S8)
        if not p8.exists():
            reg(f"D.csv[{pasta}/{p7.name}]", False, "sem correspondente v8")
            continue
        a, b = le_csv(p7), le_csv(p8)
        ncel = sum(len(r) for r in a)
        dif = [(i, j) for i, (ra, rb) in enumerate(zip(a, b)) for j, (x, y) in enumerate(zip(ra, rb)) if x != y]
        forma = len(a) == len(b) and all(len(ra) == len(rb) for ra, rb in zip(a, b))
        reg(f"D.csv[{pasta}/{p7.name.replace(S7, 'v7→v8')}]", forma and not dif,
            f"{len(a)} linhas, {ncel} células; células diferentes: {len(dif)} {dif[:5]}; bytes idênticos: "
            f"{md5(p7) == md5(p8)}")


def compara_wb(p7, p8, rotulo, nova=None):
    w7, w8 = openpyxl.load_workbook(p7), openpyxl.load_workbook(p8)
    esperado_ordem = list(w7.sheetnames)
    if nova:
        esperado_ordem.insert(esperado_ordem.index(nova[1]) + 1, nova[0])
    reg(f"D.xlsx_abas[{rotulo}]", w8.sheetnames == esperado_ordem,
        f"v7 {w7.sheetnames}; v8 {w8.sheetnames}" + (f"; {nova[0]} logo após {nova[1]}" if nova else ""))
    for s in w7.sheetnames:
        if s not in w8.sheetnames:
            reg(f"D.xlsx[{rotulo} | {s}]", False, "aba ausente na v8")
            continue
        a, b = valores_aba(w7[s]), valores_aba(w8[s])
        a2 = [[(x.replace(S7, S8) if isinstance(x, str) else x) for x in r] for r in a]
        dif = [(i + 1, j + 1) for i, (ra, rb) in enumerate(zip(a2, b)) for j, (x, y) in enumerate(zip(ra, rb)) if x != y]
        dif_bruto = sum(x != y for ra, rb in zip(a, b) for x, y in zip(ra, rb))
        mg = {str(r) for r in w7[s].merged_cells.ranges} == {str(r) for r in w8[s].merged_cells.ranges}
        forma = (len(a), max(map(len, a))) == (len(b), max(map(len, b)))
        txt = [x for r in a for x in r if isinstance(x, str)]
        reg(f"D.xlsx[{rotulo} | {s}]", forma and not dif and mg,
            f"{len(a)}×{max(map(len, a))} células (título: {str(a[0][0])[:60]!r}; última nota: "
            f"{str(next((x for x in reversed(txt)), ''))[:50]!r}…); diferentes: {len(dif)} {dif[:5]}"
            + (f" (antes de normalizar v7→v8: {dif_bruto})" if dif_bruto != len(dif) else "")
            + f"; mesclas iguais: {mg}")


compara_wb(V7 / "tabelas" / f"tabelas_principais_{S7}.xlsx", MAN / "tabelas" / f"tabelas_principais_{S8}.xlsx",
           "tabelas_principais")
compara_wb(P_ESM1_7, P_ESM1_8, "ESM_1 suplementar", nova=(ABA, "S2_knol_spontaneous"))
compara_wb(SUB7 / "ESM_1.xlsx", SUB8 / "ESM_1.xlsx", "Submissao/ESM_1", nova=(ABA, "S2_knol_spontaneous"))
reg("D.Submissao_ESM_1=suplementar_v8", md5(SUB8 / "ESM_1.xlsx") == md5(P_ESM1_8),
    f"md5 {md5(SUB8 / 'ESM_1.xlsx')[:12]} / {md5(P_ESM1_8)[:12]}")


def texto_docx(p):
    d = docx.Document(p)
    t = [x.text for x in d.paragraphs]
    for tb in d.tables:
        for r in tb.rows:
            t.append(" | ".join(c.text for c in r.cells))
    for s in d.sections:
        t += [x.text for x in s.header.paragraphs] + [x.text for x in s.footer.paragraphs]
    return t


NUM = re.compile(r"[−-]?\d[\d,]*(?:\.\d+)?")
ta = texto_docx(V7 / "tabelas" / f"tabelas_principais_{S7}.docx")
tb = texto_docx(MAN / "tabelas" / f"tabelas_principais_{S8}.docx")
ta_n = [x.replace(S7, S8) for x in ta]
dif = [(k, a, b) for k, (a, b) in enumerate(zip(ta, tb)) if a != b]
na = [m for x in ta_n for m in NUM.findall(x)]
nb = [m for x in tb for m in NUM.findall(x)]
reg("D.docx_tabelas_principais", len(ta) == len(tb) and ta_n == tb and na == nb,
    f"{len(ta)} blocos de texto, {len(nb)} números; idênticos após trocar '{S7}'→'{S8}': {ta_n == tb}; "
    f"diferenças brutas: {[(k, a[:45], b[:45]) for k, a, b in dif][:3]}")

# ----------------------------------------------------------------------------------------------------------------
# E. PDFs e figuras


def compara_pdf(p7, p8, rotulo):
    A, B = pymupdf.open(p7), pymupdf.open(p8)
    ta = [p.get_text() for p in A]
    tb = [p.get_text() for p in B]
    na = [m for x in ta for m in NUM.findall(x)]
    nb = [m for x in tb for m in NUM.findall(x)]
    tam = [tuple(round(v, 2) for v in p.rect) for p in A] == [tuple(round(v, 2) for v in p.rect) for p in B]
    pix_ok, img_ok, nimg = True, True, 0
    for pa, pb in zip(A, B):
        xa = pa.get_pixmap(dpi=100)
        xb = pb.get_pixmap(dpi=100)
        if (xa.width, xa.height, xa.n) != (xb.width, xb.height, xb.n) or xa.samples != xb.samples:
            pix_ok = False
        ia, ib = pa.get_images(full=True), pb.get_images(full=True)
        nimg += len(ia)
        if len(ia) != len(ib):
            img_ok = False
            continue
        for ga, gb in zip(ia, ib):
            ea, eb = A.extract_image(ga[0]), B.extract_image(gb[0])
            if (ea["width"], ea["height"]) != (eb["width"], eb["height"]) or \
                    pymupdf.Pixmap(A, ga[0]).samples != pymupdf.Pixmap(B, gb[0]).samples:
                img_ok = False
    reg(f"E.pdf[{rotulo}]", len(A) == len(B) and ta == tb and na == nb and tam and pix_ok and img_ok,
        f"páginas {len(A)}/{len(B)}; texto idêntico: {ta == tb}; {len(nb)} números idênticos: {na == nb}; "
        f"tamanho das páginas igual: {tam}; páginas renderizadas (100 dpi) idênticas pixel a pixel: {pix_ok}; "
        f"{nimg} imagem(ns) embutida(s) idêntica(s): {img_ok}; md5 igual: {md5(p7) == md5(p8)} "
        f"(datas de criação {A.metadata.get('creationDate')} / {B.metadata.get('creationDate')})")


for i in (2, 3, 4):
    compara_pdf(SUB7 / f"ESM_{i}.pdf", SUB8 / f"ESM_{i}.pdf", f"Submissao/ESM_{i}.pdf")
for nome in ("S7_variables_codes", "S8_strobe_record_checklist"):
    compara_pdf(V7 / "suplementar" / f"{nome}_{S7}.pdf", MAN / "suplementar" / f"{nome}_{S8}.pdf",
                f"suplementar/{nome}.pdf")


def compara_img(p7, p8, rotulo):
    a, b = Image.open(p7), Image.open(p8)
    fa, fb = getattr(a, "n_frames", 1), getattr(b, "n_frames", 1)
    da, db = a.info.get("dpi"), b.info.get("dpi")
    da = tuple(round(float(v), 2) for v in da) if da else None
    db = tuple(round(float(v), 2) for v in db) if db else None
    pix = a.size == b.size and a.mode == b.mode and fa == fb and np.array_equal(np.asarray(a), np.asarray(b))
    comp_a, comp_b = a.info.get("compression"), b.info.get("compression")
    reg(f"E.imagem[{rotulo}]", pix and da == db,
        f"dpi {da}/{db}; tamanho {a.size}/{b.size}; modo {a.mode}/{b.mode}; quadros {fa}/{fb}; "
        f"compressão {comp_a}/{comp_b}; pixels idênticos: {pix}; md5 igual: {md5(p7) == md5(p8)}")


for p7 in sorted(x for x in (V7 / "figuras").glob(f"*_{S7}.*") if not x.name.startswith("._")):
    compara_img(p7, MAN / "figuras" / p7.name.replace(S7, S8), f"figuras/{p7.name.replace(S7, 'v7→v8')}")
for ext in ("tif", "png"):
    p7 = V7 / "suplementar" / f"S9_maihda_caterpillar_{S7}.{ext}"
    compara_img(p7, MAN / "suplementar" / p7.name.replace(S7, S8), f"suplementar/{p7.name.replace(S7, 'v7→v8')}")
for i in range(1, 5):
    compara_img(SUB7 / f"Fig{i}.tif", SUB8 / f"Fig{i}.tif", f"Submissao/Fig{i}.tif")
mapa_fig = {1: "fig01_flowchart", 2: "fig02_pr_race_m1m3", 3: "fig03_rd_race_tercile", 4: "fig04_dating"}
ok_cp = {i: md5(SUB8 / f"Fig{i}.tif") == md5(MAN / "figuras" / f"{n}_{S8}.tif") for i, n in mapa_fig.items()}
reg("E.Submissao_Fig=figuras_v8", all(ok_cp.values()), f"cópia byte a byte: {ok_cp}")
lg7 = (V7 / f"legendas_figuras_{S7}.md").read_text(encoding="utf-8").replace(S7, S8)
lg8 = (MAN / "legendas_figuras.md").read_text(encoding="utf-8")
reg("E.legendas_figuras", lg7 == lg8, f"idênticas após trocar '{S7}'→'{S8}': {lg7 == lg8}")

# ----------------------------------------------------------------------------------------------------------------
# F. MANIFEST e declaração de disponibilidade
mf8 = (MAN / "MANIFEST.md").read_text(encoding="utf-8")
mf7 = (V7 / f"MANIFEST_{S7}.md").read_text(encoding="utf-8")
lin_s2b = [l for l in mf8.splitlines() if l.startswith("| S2b |")]
reg("F.MANIFEST_mapa_S2b", len(lin_s2b) == 1 and "ESM_1.xlsx (S2b_access_specifications)" in lin_s2b[0],
    lin_s2b[0] if lin_s2b else "linha S2b ausente no mapa S → ESM")
mapa = [l.split("|")[1].strip() for l in mf8.split("## Arquivos")[0].splitlines() if l.startswith("| S")]
reg("F.MANIFEST_ordem_mapa", mapa.index("S2b") == mapa.index("S2") + 1, f"ordem: {mapa}")
lin_arq = [l for l in mf8.splitlines() if f"S2b_access_specifications_{S8}.csv" in l]
reg("F.MANIFEST_arquivo_S2b", len(lin_arq) == 1 and all(f in lin_arq[0] for f in fontes),
    lin_arq[0] if lin_arq else "linha do CSV da S2b ausente")
# MD5 listados x arquivos
ruins, conf, pulados = [], 0, []
for l in mf8.splitlines():
    m = re.match(r"\| (\S+) \|.*\| ([0-9a-f]{12}) \|$", l)
    if not m:
        continue
    rel, h = m.groups()
    if any(x in rel for x in PROIBIDOS):
        pulados.append(rel)
        continue
    p = (ROOT / "outputs" / rel) if rel.startswith("manuscrito/") else (ROOT / rel)
    conf += 1
    if not p.exists() or md5(p)[:12] != h:
        ruins.append(rel)
reg("F.MANIFEST_md5", not ruins and conf > 40,
    f"{conf} MD5 conferidos, divergentes: {ruins or 'nenhum'}; não lidos (regra de independência): {pulados}")


def normaliza_mf(t):
    return [re.sub(r"\| [0-9a-f]{12} \|$", "| MD5 |", l.replace(S7, S8)) for l in t.splitlines()]


n7, n8 = normaliza_mf(mf7), normaliza_mf(mf8)
so8 = [l for l in n8 if l not in n7]
so7 = [l for l in n7 if l not in n8]
esper = [l for l in so8 if l.startswith("# MANIFEST") or l.startswith("Gerado em") or "S2b" in l]
reg("F.MANIFEST_so_mudancas_previstas", len(esper) == len(so8) == 4 and len(so7) == 2,
    f"linhas novas/alteradas na v8 (após normalizar versão e MD5): {len(so8)} — título, introdução (commit e 'v8 = v7 com "
    f"a Tabela S2b'), linha S2b do mapa, linha do CSV S2b; removidas da v7: {len(so7)} (título e introdução antigos)")
reg("F.MANIFEST_cita_commit", "'Etapa 7c.4: Tabela S2b e conferências'" in mf8,
    re.search(r"Commit do repositório[^)]*\)", mf8)[0])
dca8 = (MAN / "data_code_availability.md").read_text(encoding="utf-8")
dca7 = (V7 / f"data_code_availability_{S7}.md").read_text(encoding="utf-8")
reg("F.data_code_availability_commit", '"Etapa 7c.4: Tabela S2b e conferências"' in dca8 and
    'git log --grep "Etapa 7c.4"' in dca8, re.search(r'Reference version[^\n]*\n[^\n]*', dca8)[0].strip()[:260])
d7, d8 = dca7.splitlines(), dca8.splitlines()
dl = [k + 1 for k, (a, b) in enumerate(zip(d7, d8)) if a != b]
reg("F.data_code_availability_resto_igual", len(d7) == len(d8) and len(dl) == 2,
    f"linhas diferentes v7×v8: {dl} (título com pacote/etapa e frase do commit de referência); restante idêntico")

# ----------------------------------------------------------------------------------------------------------------
# G. conferências pedidas
wp = {d: fonte[d]["w"] for d, _ in DESF}
reg("G1.gl_do_Wald_p0436", int(wp["ptb"].gl) == 6 and fp(wp["ptb"].p) == "0.436",
    f"PTB total, tercis nacionais: chi2 = {wp['ptb'].chi2!r}, gl = {int(wp['ptb'].gl)}, p = {wp['ptb'].p!r}; "
    f"SGA (gl {int(wp['pig'].gl)}): p = {wp['pig'].p!r}; provider-initiated (gl {int(wp['ptb_ind'].gl)}): "
    f"p = {wp['ptb_ind'].p!r}")
achados = []
for f in sorted(TAB.glob("*.csv")):
    if f.name.startswith("._") or any(x in f.name for x in PROIBIDOS):  # ._ = AppleDouble do exFAT
        continue
    df = pd.read_csv(f, low_memory=False)
    col2 = [c for c in df.columns if re.search(r"2gl|2_gl|gl2|2df", str(c))]
    gl2 = "gl" in df.columns and (pd.to_numeric(df["gl"], errors="coerce") == 2).any()
    if col2 or gl2:
        txt = df.astype(str)
        nac = bool(txt.apply(lambda s: s.str.contains(r"tercil_nac|3\.3b|T1_pior|nacional", regex=True)).any().any())
        achados.append((f.name, col2, bool(gl2), nac))
nac2 = [a for a in achados if a[3]]
wi = pd.read_csv(TAB / f"tab_e7b3_02_wald_ind{SRC}")
pri = wi[wi.cenario == "principal"]
liga_reg = all(abs(float(pri[pri.desfecho == d].chi2_6gl.iloc[0]) -
                   float(um(W, analise="3.2_tercil_reg", estrato="Brasil", desfecho=d).chi2)) < 1e-6 for d, _ in DESF)
reg("G1.Wald_2gl_indigena_tercis_nacionais", not nac2,
    f"tabelas com Wald de 2 gl: {[(a[0], a[1]) for a in achados]}; alguma com tercis nacionais: {bool(nac2)}. "
    f"tab_e7b3_02_wald_ind é dos tercis por macrorregião (chi2_6gl do 'principal' = tab_e3_02_wald_rs 3.2: {liga_reg}); "
    f"cenários: {sorted(wi.cenario.unique())}. Não existe Wald de 2 gl só indígena para os tercis nacionais "
    f"(e não dá para calculá-lo das tabelas: falta a covariância Ind×T1_pior/Ind×T2)")
cp = fonte["pig"]["c"]
reg("G2.RP_int_PIG_4casas", frat(cp.RP_por_5pp_interacao, cp.int_lo, cp.int_hi) == s2b_csv[2][4],
    f"SGA, Indígena: RP de interação por 5 p.p. = {cp.RP_por_5pp_interacao:.4f} ({cp.int_lo:.4f}–{cp.int_hi:.4f}); "
    f"bruto {cp.RP_por_5pp_interacao!r} ({cp.int_lo!r}–{cp.int_hi!r})")

# ----------------------------------------------------------------------------------------------------------------
OUT.mkdir(parents=True, exist_ok=True)
saida = OUT / "comparacao_7c4_v1_20261009.csv"
pd.DataFrame(linhas, columns=["verificacao", "ok", "detalhe"]).to_csv(saida, index=False, encoding="utf-8")
n, nok = len(linhas), sum(r["ok"] for r in linhas)
print(f"{n} verificações; {nok} OK; {n - nok} falharam")
for r in linhas:
    if not r["ok"]:
        print("FALHA:", r["verificacao"], "|", r["detalhe"])
