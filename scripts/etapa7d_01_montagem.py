"""
7d.1 Montagem dos documentos da Submissao (pacote v15). Não estima nada e não muda o texto dos autores, fora os dois pontos autorizados:
  1. ESM_3 (Supplementary Methods, Online Resource 3): o marcador "[URL from docs/referencias/aps_cobertura_ab/ACESSO.txt]" (seção S11)
     vira a URL do relatório registrada nesse ACESSO.txt; PDF pelo Microsoft Word.
  2. Manuscript: (a) os 4 marcadores "[insert from package v10]" saem e, logo depois de cada título de tabela (o do manuscrito, mantido),
     entra a tabela do pacote (CSV de outputs/manuscrito/tabelas/, v15) como tabela nativa do Word, só com linhas horizontais, e as notas
     abaixo (o rodapé do pacote, sem a linha interna "Sources:", repartido em notas gerais e notas com letra sobrescrita ligadas à célula
     a que se referem, mais uma linha de abreviações); as Tabelas 3 e 4 ficam em seção paisagem; (b) as Figs. 1–4 (PNG do pacote) entram
     no corpo, logo depois do parágrafo da 1ª citação de cada uma, na largura do texto.
  3. PDF do Manuscript pelo Word (paginação e numeração de linhas do Word) e checklist STROBE + RECORD (S8 do pacote) com página e linha de
     cada item → Online Resource 1 (ESM_1).
Saídas em outputs/manuscrito/montagem/ (sufixo da versão do pacote). O etapa7b_04_submissao.py copia para Submissao/.
Ordem: etapa7b_01, 02, 03, este script, etapa7b_04, checa. Rodar da raiz: python3 scripts/etapa7d_01_montagem.py
"""
import copy
import re
import subprocess

import docx
import pandas as pd
import pymupdf
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

import etapa7b_lib as B
import etapa0_lib as L
from etapa7d_word import docx_pdf

log = L.Logger("7d_01_montagem", etapa="etapa7d")
V = B.V
MONT = B.MS / "montagem"
MONT.mkdir(exist_ok=True)
SRC = B.PROJ / "manuscrito"
MARC_TAB = "[insert from package v10]"
MARC_URL = "[URL from docs/referencias/aps_cobertura_ab/ACESSO.txt]"


def texto(d):
    return [p.text for p in d.paragraphs]


def troca_no_paragrafo(p, velho, novo):
    """Troca um trecho que pode estar partido em vários runs: o texto novo fica no 1º run do trecho, com a formatação dele."""
    runs = p.runs
    full = "".join(r.text for r in runs)
    i = full.index(velho)
    j = i + len(velho)
    pos = 0
    primeiro = True
    for r in runs:
        a, b = pos, pos + len(r.text)
        pos = b
        if b <= i or a >= j:
            continue
        ini, fim = max(i, a) - a, min(j, b) - a
        r.text = r.text[:ini] + (novo if primeiro else "") + r.text[fim:]
        primeiro = False


# ======================= 1. ESM_3 (Online Resource 3)
acc = (B.PROJ / "docs/referencias/aps_cobertura_ab/ACESSO.txt").read_text()
url = re.search(r"https://relatorioaps\.saude\.gov\.br/[^\s),']+", acc).group(0)
e3 = docx.Document(SRC / "ESM_3_Supplementary_Methods.docx")
antes3 = texto(e3)
alvo = [p for p in e3.paragraphs if MARC_URL in p.text]
if len(alvo) != 1:
    raise RuntimeError(f"marcador da URL no ESM_3: {len(alvo)} ocorrências")
troca_no_paragrafo(alvo[0], MARC_URL, url)
depois3 = texto(e3)
dif3 = [(a, b) for a, b in zip(antes3, depois3) if a != b]
if len(antes3) != len(depois3) or len(dif3) != 1 or dif3[0][0].replace(MARC_URL, url) != dif3[0][1]:
    raise RuntimeError("ESM_3: a troca mudou outra coisa além do marcador da URL")
E3D = MONT / f"ESM_3_supplementary_methods_{V}.docx"
e3.save(E3D)
docx_pdf(E3D, MONT / f"ESM_3_supplementary_methods_{V}.pdf")
log(f"ESM_3: marcador → {url}; PDF pelo Word")

# ======================= 2. Manuscript
ms = docx.Document(SRC / "Manuscript.docx")
antes = texto(ms)
body_sect = ms.sections[-1]._sectPr
TXT_W = ms.sections[-1].page_width - ms.sections[-1].left_margin - ms.sections[-1].right_margin

# --- notas das tabelas: o rodapé do pacote, repartido em trechos (na ordem do rodapé) e cada trecho numa nota ('g' = geral; letra = nota
# ligada a células). A concatenação dos trechos tem de reproduzir o rodapé inteiro (fora "Sources: ..."), conferido abaixo.
NOTAS = {
    "tab01_characteristics": dict(
        trechos=[("Brown (parda)", "g"), ("Race/skin color is the mother's", "g"), ("Excluded: Asian", "g"), ("Percentages are column", "g"),
                 ("Tertiles of prenatal care access", "a"), ("The denominators of provider-initiated", "b"), ("TPMETESTIM code 8", "c"),
                 ("SGA: singletons", "d")],
        alvos={"a": [("linha", "Prenatal care access tertile (within macroregion), n (%)")],
               "b": [("linha", "Provider-initiated preterm birth"), ("linha", "Spontaneous preterm birth")],
               "c": [("linha", "Last menstrual period (TPMETESTIM code 8)")], "d": [("linha", "SGA")]},
        abrev="SD, standard deviation; SGA, small for gestational age; TPMETESTIM, field of the Live Birth Declaration that records the "
              "gestational age estimation method."),
    "tab02_models_m1m3": dict(
        trechos=[("Brown (parda)", "g"), ("PR, prevalence ratio from Poisson", "g"), ("M1: race/skin color only.", "a"), ("M2: + maternal", "b"),
                 ("M3 (extended model)", "c"), ("95% CIs from cluster-robust", "g"), ("ΔPR (primary measure", "d"),
                 ("N, M1 and M2 / M2cc and M3", "g")],
        alvos={"a": [("col", "M1 PR (95% CI)")], "b": [("col", "M2 PR (95% CI)")], "c": [("col", "M3 PR (95% CI)")],
               "d": [("col", "ΔPR M2→M3 (95% CI)"), ("col", "Attenuation, % (95% CI)")]},
        abrev="CI, confidence interval; M2cc, model M2 refitted in the complete-case sample of model M3; n.a., not applicable; "
              "PR, prevalence ratio; SGA, small for gestational age."),
    "tab03_knol_tercile": dict(
        trechos=[("Brown (parda)", "g"), ("Effect modification on the additive", "g"), ("Tertiles of prenatal care access", "g"),
                 ("Cases and non-cases", "g"), ("Joint PR/RD compare", "g"), ("PR and RD are marginally", "g"), ("IC = risk difference", "a"),
                 ("RERI = PR11", "b"), ("For provider-initiated preterm birth, where", "c"), ("95% CIs from cluster-robust", "g"),
                 ("Sample: births with a defined", "g"), ("The provider-initiated N", "g")],
        alvos={"a": [("col", "IC per 100 (95% CI)")], "b": [("col", "RERI (95% CI)"), ("col", "Multiplicative interaction (95% CI)")],
               "c": [("col", "RERI, recoded (reference = lowest-risk joint stratum), provider-initiated only (95% CI)")]},
        abrev="CI, confidence interval; IC, interaction contrast; PR, prevalence ratio; RD, risk difference; RERI, relative excess risk "
              "due to interaction; SGA, small for gestational age; T1–T3, tertiles of access to early prenatal care."),
    "tab04_sensitivity": dict(
        trechos=[("Brown (parda)", "g"), ("Indigenous vs White.", "g"), ("PR from model M2", "g"), ("95% CIs from cluster-robust", "g"),
                 ("Tertiles of prenatal care access", "g"), ("Dating-robust analysis:", "a"), ("Multiple imputation:", "b"),
                 ("Joint Wald tests were not computed", "b"), ("Live-birth bounds:", "c"), ("Wald p, Indigenous terms (2 df):", "d"),
                 ("Dating-method strata", "e"), ("Weight >P97 reclassification:", "f"), ("Unclassified preterm births:", "g2"),
                 ("N: sample of the PR M2", "g"), ("n.a., not applicable", "g"), ("Gestational age in days changes", "g"),
                 ("'Unchanged' and 'not reclassified'", "g")],
        alvos={"a": [("linha", "Dating-robust: other method, excluding preterm births with weight >P97")],
               "b": [("linha", "Multiple imputation of race/skin color (m = 10)")],
               "c": [("linha", "Live-birth bounds: Indigenous fetal death ratio 1–2× national (corrected PR M2, range)")],
               "d": [("col", "Preterm birth (total): Wald p, Indigenous terms (2 df)")],
               "e": [("linha", "LMP-dated births only (code 8)"), ("linha", "Other-method dating only (codes 1–2)"),
                     ("linha", "Other method: code 2 only (other method; includes ultrasound per the Live Birth Declaration manual)")],
               "f": [("linha", "Weight >P97 preterm reclassified as non-cases (all methods)")],
               "g2": [("linha", "Unclassified preterm births (131,809) all counted as provider-initiated"),
                      ("linha", "Unclassified preterm births (131,809) all counted as spontaneous")]},
        abrev="CE, Ceará; CI, confidence interval; DF, Federal District; GA, gestational age; IC, interaction contrast; LMP, last "
              "menstrual period; PR, prevalence ratio; SGA, small for gestational age; T1, worst-access tertile; >P97, birth weight above "
              "the 97th INTERGROWTH-21st centile."),
}
LETRA = {"a": "a", "b": "b", "c": "c", "d": "d", "e": "e", "f": "f", "g2": "g"}


def rodape_pacote(nome):
    import openpyxl
    wb = openpyxl.load_workbook(B.TABD / f"tabelas_principais_{V}.xlsx", read_only=True)
    vals = [c for r in wb[nome].iter_rows(values_only=True) for c in r if c is not None]
    return str(vals[-1])


def reparte(nome):
    rod = rodape_pacote(nome)
    k = rod.index(" Sources: ")
    corpo, fontes = rod[:k], rod[k + 1:]
    espec = NOTAS[nome]["trechos"]
    pos = []
    for frase, _ in espec:
        i = corpo.find(frase, pos[-1] + 1 if pos else 0)
        if i < 0:
            raise RuntimeError(f"{nome}: trecho não achado no rodapé: {frase!r}")
        pos.append(i)
    if pos[0] != 0 or pos != sorted(pos):
        raise RuntimeError(f"{nome}: trechos fora de ordem ou não começam no início do rodapé")
    partes = [corpo[a:b].strip() for a, b in zip(pos, pos[1:] + [len(corpo)])]
    if " ".join(partes) != corpo:
        raise RuntimeError(f"{nome}: os trechos não reproduzem o rodapé")
    notas = {}
    for (_, chave), t in zip(espec, partes):
        notas.setdefault(chave, []).append(re.sub(r";$", ".", t))
    return notas, fontes


def borda(el, lado, val="single", sz=8):
    b = OxmlElement(f"w:{lado}")
    b.set(qn("w:val"), val)
    b.set(qn("w:sz"), str(sz))
    b.set(qn("w:space"), "0")
    b.set(qn("w:color"), "000000")
    el.append(b)


def borda_celula(cell, lado):
    tcPr = cell._tc.get_or_add_tcPr()
    tb = tcPr.find(qn("w:tcBorders"))
    if tb is None:
        tb = OxmlElement("w:tcBorders")
        tcPr.append(tb)
    borda(tb, lado)


def escreve(cell, txt, tam, negrito=False, sobrescrito="", recuo=False):
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    if recuo:
        p.paragraph_format.left_indent = Pt(6)
    r = p.add_run(txt)
    r.font.size, r.bold = tam, negrito
    if sobrescrito:
        s = p.add_run(sobrescrito)
        s.font.size, s.font.superscript = tam, True


def monta_tabela(nome, tam):
    df = pd.read_csv(B.TABD / f"{nome}_{V}.csv", dtype=str).fillna("")
    notas, fontes = reparte(nome)
    alvos = NOTAS[nome]["alvos"]
    marca_col, marca_lin = {}, {}
    for chave, lst in alvos.items():
        for tipo, rot in lst:
            (marca_col if tipo == "col" else marca_lin).setdefault(rot, []).append(LETRA[chave])
    cols = list(df.columns)
    dois = any(": " in c for c in cols)                  # Tabela 4: cabeçalho em dois níveis (desfecho / medida)
    nh = 2 if dois else 1
    t = ms.add_table(rows=nh + len(df), cols=len(cols))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    tblPr = t._tbl.tblPr
    for x in tblPr.findall(qn("w:tblBorders")):
        tblPr.remove(x)
    tb = OxmlElement("w:tblBorders")
    for lado in ("top", "bottom"):
        borda(tb, lado)
    for lado in ("left", "right", "insideH", "insideV"):
        borda(tb, lado, "nil", 0)
    tblPr.append(tb)
    usadas_col = set()
    if dois:
        grupos = [c.split(": ", 1)[0] if ": " in c else c for c in cols]
        subs = [c.split(": ", 1)[1] if ": " in c else "" for c in cols]
        j = 0
        while j < len(cols):
            k = j
            while k + 1 < len(cols) and grupos[k + 1] == grupos[j] and subs[j]:
                k += 1
            c0 = t.cell(0, j) if k == j else t.cell(0, j).merge(t.cell(0, k))
            escreve(c0, grupos[j], tam, negrito=True)
            if not subs[j]:
                t.cell(0, j).merge(t.cell(1, j))
            j = k + 1
        for j, c in enumerate(cols):
            if subs[j]:
                sup = ",".join(marca_col.get(c, []))
                usadas_col |= {c} if sup else set()
                escreve(t.cell(1, j), subs[j], tam, negrito=True, sobrescrito=sup)
        for j in range(len(cols)):
            if subs[j]:
                borda_celula(t.cell(0, j), "bottom")
    else:
        for j, c in enumerate(cols):
            sup = ",".join(marca_col.get(c, []))
            usadas_col |= {c} if sup else set()
            escreve(t.cell(0, j), c, tam, negrito=True, sobrescrito=sup)
    for j in range(len(cols)):
        borda_celula(t.cell(nh - 1, j), "bottom")
    for r in range(nh):
        trPr = t.rows[r]._tr.get_or_add_trPr()
        th = OxmlElement("w:tblHeader")
        th.set(qn("w:val"), "true")
        trPr.append(th)
    usadas_lin = set()
    for i, (_, row) in enumerate(df.iterrows()):
        vals = list(row)
        rot = vals[0]
        sup = ",".join(marca_lin.get(rot.strip(), []))
        usadas_lin |= {rot.strip()} if sup else set()
        so_rotulo = all(v == "" for v in vals[1:])
        if so_rotulo and not rot.startswith("  "):
            c = t.cell(nh + i, 0).merge(t.cell(nh + i, len(cols) - 1))
            escreve(c, rot, tam, negrito=True, sobrescrito=sup)
            continue
        escreve(t.cell(nh + i, 0), rot.strip(), tam, sobrescrito=sup, recuo=rot.startswith("  "))
        for j, v in enumerate(vals[1:], start=1):
            escreve(t.cell(nh + i, j), v, tam)
    # larguras: a do texto (paisagem nas Tabelas 3 e 4), 1ª coluna mais larga
    sec0 = ms.sections[0]
    larg = (sec0.page_height if nome in PAISAGEM else sec0.page_width) - sec0.left_margin - sec0.right_margin
    f1 = {"tab01_characteristics": 0.30, "tab02_models_m1m3": 0.26, "tab03_knol_tercile": 0.15, "tab04_sensitivity": 0.24}[nome]
    w1 = int(larg * f1)
    wr = int((larg - w1) / (len(cols) - 1))
    t.autofit = False
    tblW = tblPr.find(qn("w:tblW"))
    if tblW is None:
        tblW = OxmlElement("w:tblW")
        tblPr.append(tblW)
    tblW.set(qn("w:type"), "dxa")
    tblW.set(qn("w:w"), str(int(larg.twips if hasattr(larg, "twips") else larg / 635)))
    for j, gc in enumerate(t._tbl.tblGrid.findall(qn("w:gridCol"))):
        gc.set(qn("w:w"), str(int((w1 if j == 0 else wr) / 635)))
    for j, col in enumerate(t.columns):
        for c in col.cells:
            c.width = w1 if j == 0 else wr
    falta = (set(marca_col) - usadas_col) | (set(marca_lin) - usadas_lin)
    if falta:
        raise RuntimeError(f"{nome}: alvos de nota não achados na tabela: {falta}")
    # notas: gerais, abreviações e as de letra
    pars = [" ".join(notas["g"]), NOTAS[nome]["abrev"]]
    letras = [(LETRA[k], " ".join(v)) for k, v in notas.items() if k != "g"]
    return t, pars, sorted(letras), fontes


def par_depois(ancora_el, txt="", tam=Pt(8), sup=""):
    p = ms.add_paragraph()
    if sup:
        s = p.add_run(sup)
        s.font.size, s.font.superscript = tam, True
    r = p.add_run(txt)
    r.font.size = tam
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.0
    ancora_el.addnext(p._p)
    return p


def secao(par, paisagem):
    """Encerra uma seção no parágrafo par (sectPr no pPr), copiando a do corpo (margens, rodapé, numeração de linhas)."""
    s = copy.deepcopy(body_sect)
    pg = s.find(qn("w:pgSz"))
    w, h = int(pg.get(qn("w:w"))), int(pg.get(qn("w:h")))
    if paisagem:
        pg.set(qn("w:w"), str(max(w, h)))
        pg.set(qn("w:h"), str(min(w, h)))
        pg.set(qn("w:orient"), "landscape")
    par._p.get_or_add_pPr().append(s)


PAISAGEM = {"tab03_knol_tercile", "tab04_sensitivity"}
TAMS = {"tab01_characteristics": Pt(8), "tab02_models_m1m3": Pt(8), "tab03_knol_tercile": Pt(6.5), "tab04_sensitivity": Pt(7)}
titulos = [p for p in ms.paragraphs if MARC_TAB in p.text]
if [re.match(r"Table (\d)", p.text).group(1) for p in titulos] != ["1", "2", "3", "4"]:
    raise RuntimeError(f"marcadores de tabela: {[p.text[:20] for p in titulos]}")
NOMES = ["tab01_characteristics", "tab02_models_m1m3", "tab03_knol_tercile", "tab04_sensitivity"]
ultimo = {}
FONTES = {}
for p, nome in zip(titulos, NOMES):
    troca_no_paragrafo(p, " " + MARC_TAB if " " + MARC_TAB in p.text else MARC_TAB, "")
    if p.runs and p.runs[-1].text.endswith(" "):
        p.runs[-1].text = p.runs[-1].text.rstrip()
    p.paragraph_format.keep_with_next = True
    if nome in ("tab02_models_m1m3", "tab04_sensitivity"):   # a 1 segue o título "Tables"; a 3 abre a seção paisagem (página nova)
        p.paragraph_format.page_break_before = True
    t, pars, letras, FONTES[nome] = monta_tabela(nome, TAMS[nome])
    p._p.addnext(t._tbl)
    el = t._tbl
    for txt in pars:
        el = par_depois(el, txt)._p
    for le, txt in letras:
        el = par_depois(el, " " + txt, sup=le)._p
    ultimo[nome] = el
# Tabelas 3 e 4 em paisagem: seção retrato termina na última nota da Tabela 2; seção paisagem termina na última nota da Tabela 4
from docx.text.paragraph import Paragraph
secao(Paragraph(ultimo["tab02_models_m1m3"], ms._body), paisagem=False)
secao(Paragraph(ultimo["tab04_sensitivity"], ms._body), paisagem=True)
# a seção paisagem tem de começar na Tabela 3: o título da Tabela 4 só quebra página
log(f"tabelas 1–4 inseridas; fontes internas omitidas das notas: {[f[:40] for f in FONTES.values()]}")

# --- figuras: depois do parágrafo da 1ª citação (só corpo: do Abstract ao fim da Discussion; nunca nos títulos nem nas legendas)
paras = ms.paragraphs
i_ini = next(i for i, p in enumerate(paras) if p.text.strip() == "Abstract")
i_fim = next(i for i, p in enumerate(paras) if p.text.strip() == "References")
FIGS = {1: f"fig01_flowchart_{V}.png", 2: f"fig02_pr_race_m1m3_{V}.png", 3: f"fig03_rd_race_tercile_{V}.png", 4: f"fig04_dating_{V}.png"}
pos_fig = {}
for k, png in FIGS.items():
    i = next((i for i in range(i_ini, i_fim) if re.search(rf"\bFigs?\. (?:\d, )*{k}\b", paras[i].text)), None)
    if i is None:
        raise RuntimeError(f"Fig. {k} não citada no corpo")
    pos_fig[k] = i
    fp = ms.add_paragraph()
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.paragraph_format.keep_together = True
    fp.add_run().add_picture(str(B.FIGD / png), width=TXT_W)
    paras[i]._p.addnext(fp._p)
log(f"figuras inseridas depois dos parágrafos {pos_fig} (índices do docx original)")

# --- o texto dos autores não pode ter mudado, fora os marcadores das tabelas
depois = [p.text for p in ms.paragraphs]
orig_sem = [t.replace(" " + MARC_TAB, "").replace(MARC_TAB, "") for t in antes]
if [t for t in orig_sem if t not in depois]:
    raise RuntimeError("parágrafo dos autores sumiu ou mudou")
MSD = MONT / f"Manuscript_{V}.docx"
ms.save(MSD)
MSP = docx_pdf(MSD, MONT / f"Manuscript_{V}.pdf")
log(f"Manuscript montado e PDF pelo Word: {len(depois)} parágrafos ({len(antes)} no original)")

# ======================= 3. página e linha (PDF do Word) → checklist STROBE + RECORD (Online Resource 1)
pdf = pymupdf.open(MSP)
NUMLIN = []                                           # (página, y-centro, nº da linha) dos números de linha da margem esquerda
for pg in pdf:
    marg = ms.sections[0].left_margin.pt - 2                  # números de linha: na margem esquerda (antes do texto)
    for b in pg.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            for sp in ln["spans"]:
                if re.fullmatch(r"\d+", sp["text"].strip()) and sp["bbox"][2] < marg:
                    NUMLIN.append((pg.number, (sp["bbox"][1] + sp["bbox"][3]) / 2, int(sp["text"])))
if len(NUMLIN) < 300:
    raise RuntimeError(f"números de linha não achados no PDF do Word: {len(NUMLIN)}")


def linha_em(pnum, y):
    c = [(abs(yy - y), n) for p_, yy, n in NUMLIN if p_ == pnum]
    d, n = min(c)
    if d > 8:
        raise RuntimeError(f"sem número de linha perto de y={y:.0f} na p. {pnum + 1}")
    return n


def acha(frase, desde=(0, -1.0)):
    """1ª ocorrência de frase no PDF a partir de (página, y)."""
    for pnum in range(desde[0], len(pdf)):
        for r in pdf[pnum].search_for(frase):
            yc = (r.y0 + r.y1) / 2
            if pnum > desde[0] or yc > desde[1]:
                return pnum, yc
    return None


def palavras(t, n, fim=False):
    w = t.split()
    return " ".join(w[-n:] if fim else w[:n])


PTXT = [p.text for p in ms.paragraphs]


def paragrafo(prefixo):
    m = [t for t in PTXT if t.startswith(prefixo)]
    if len(m) != 1:
        raise RuntimeError(f"prefixo de parágrafo ambíguo ou ausente: {prefixo!r} ({len(m)})")
    return m[0]


import unicodedata
nz = lambda t: unicodedata.normalize("NFKC", t)
# sequência de palavras do PDF na ordem de leitura, sem os números de linha (margem esquerda) e sem o rodapé (número de página)
FLUXO = []
for pg in pdf:
    marg = ms.sections[0].left_margin.pt - 2
    baixo = pg.rect.height - ms.sections[0].bottom_margin.pt + 2
    for w in pg.get_text("words"):
        if w[2] < marg or w[1] > baixo:
            continue
        FLUXO.append((pg.number, (w[1] + w[3]) / 2, nz(w[4])))
FW = [w for _, _, w in FLUXO]


def _igual(pdfw, w):
    """Palavra do PDF = palavra do docx; tolera até 2 caracteres espúrios antes dela (o Word às vezes emite um glifo invisível
    no início de um parágrafo, que a extração cola na 1ª palavra: 'cRacial', 'S aOnline')."""
    return pdfw == w or (pdfw.endswith(w) and len(pdfw) - len(w) <= 2)


def _acha_seq(seq, desde=0, ate=None):
    ate = len(FW) if ate is None else min(ate, len(FW))
    for i in range(desde, ate - len(seq) + 1):
        if all(_igual(FW[i + k], w) for k, w in enumerate(seq)):
            return i
    return None


def local(prefixo_ini, prefixo_fim=None):
    """Página e linhas do parágrafo (ou do trecho de parágrafos) no PDF do Word: casa as primeiras 8 palavras do 1º parágrafo e as
    últimas 4 do último na sequência de palavras do PDF (independe de onde caem as quebras de linha)."""
    a, b = nz(paragrafo(prefixo_ini)).split(), nz(paragrafo(prefixo_fim or prefixo_ini)).split()
    i = _acha_seq(a[:8])
    if i is None:
        raise RuntimeError(f"início não achado no PDF: {prefixo_ini!r}")
    j = i if prefixo_fim is None else _acha_seq(b[:8], i)
    if j is None:
        raise RuntimeError(f"início do último parágrafo não achado no PDF: {prefixo_fim!r}")
    k = _acha_seq(b[-4:], j + len(b) - 4 - 5, j + len(b) + 40)
    if k is None:
        raise RuntimeError(f"fim não achado no PDF: {(prefixo_fim or prefixo_ini)!r}")
    e = k + 3
    p1, l1 = FLUXO[i][0] + 1, linha_em(*FLUXO[i][:2])
    p2, l2 = FLUXO[e][0] + 1, linha_em(*FLUXO[e][:2])
    return f"p. {p1}, lines {l1}–{l2}" if p1 == p2 else f"pp. {p1}–{p2}, lines {l1}–{l2}"


def pagina_tabela(k):
    r = acha(f"Table {k} ")
    titulo = [i for i, t in enumerate(PTXT) if t.startswith(f"Table {k} ")]
    # o título da tabela é a última ocorrência de "Table k " no PDF (as anteriores são citações no texto)
    ult = None
    pos = (0, -1.0)
    while True:
        x = acha(f"Table {k} {PTXT[titulo[-1]].split(' ', 2)[2][:30]}", pos)
        if not x:
            break
        ult, pos = x, (x[0], x[1] + 1)
    return f"Table {k} (p. {ult[0] + 1})"


IMGP = [pg.number + 1 for pg in pdf for _ in pg.get_images()]
if len(IMGP) != 4:
    raise RuntimeError(f"imagens no PDF: {len(IMGP)}")
FIGP = {k: f"Fig. {k} (p. {IMGP[k - 1]})" for k in range(1, 5)}
TABP = {k: pagina_tabela(k) for k in range(1, 5)}

S = {"tit": "Racial disparities in fetal growth and preterm birth across levels", "abs": "Racial disparities in preterm birth and fetal growth are",
     "i1": "Racial and ethnic inequities in birth outcomes", "i5": "A further question is how much", "obj": "To our knowledge, no national study",
     "des": "We conducted a population-based cross-sectional", "fon": "We also used fetal death records", "pop": "Of 27,489,150 live births, we sequentially",
     "rac": "The Live Birth Declaration records maternal", "out": "The pre-specified primary outcome was", "sga": "SGA was defined as birth weight",
     "ace": "We measured access to early prenatal care", "dat": "According to the official instructions, gestational age",
     "cov": "We selected covariates using a causal", "est": "We estimated prevalence ratios (PRs)", "mul": "Total preterm birth was the pre-specified",
     "sen": "Sensitivity analyses repeated the main", "r1": "Of 27,489,150 live births registered", "r2": "The prevalence of preterm birth was 11.47%",
     "r3": "In the primary model, Indigenous mothers", "r6": "For total preterm birth, the six-term Wald", "r7": "The SGA and provider-initiated findings kept",
     "r9": "Estimates were similar after multiple imputation", "d1": "In 25.8 million births in Brazil", "d2": "The SGA findings agree in direction",
     "d4": "The finding with the broadest methodological", "d5": "For Black and Brown mothers, the main disparity", "lim": "This study has several strengths",
     "imp": "Our findings have implications for care", "con": "In conclusion, the disparities affecting", "fun": "Funding This research did not",
     "dav": "Data Availability SINASC and SIM"}
L_ = lambda a, b=None: local(S[a], S[b] if b else None)
LOC = [
    [f"Title ({L_('tit')})", f"Abstract ({L_('abs')})"],
    [f"Introduction ({L_('i1', 'i5')})"],
    [f"Introduction ({L_('obj')})"],
    [f"Methods, Study Design and Data Sources ({L_('des')})"],
    [f"Methods, Study Design and Data Sources ({L_('des', 'fon')})"],
    [f"Methods, Study Population ({L_('pop')})", f"Gestational Age Dating Method ({L_('dat')}; validation of code 8)",
     f"linkage ({L_('fon')})", "Online Resource 2"],
    [f"Methods, Maternal Race/Skin Color to Covariates and Missing Data ({L_('rac', 'cov')})", "Online Resource 2 (codes and algorithms)"],
    [f"Methods ({L_('des', 'fon')}; {L_('rac')}; {L_('out', 'sga')}; {L_('ace')}; {L_('dat')})", "Online Resource 2"],
    [f"Methods ({L_('cov')}; {L_('sen')})", f"Discussion ({L_('lim')})"],
    [f"Methods, Study Population ({L_('pop')})", FIGP[1]],
    [f"Methods ({L_('sga')}; {L_('ace')}; {L_('cov')})"],
    [f"Methods, Statistical Analysis ({L_('est', 'mul')})", "Online Resource 3"],
    [f"Methods ({L_('des', 'fon')}; {L_('pop')})", "Online Resources 2 and 3"],
    [f"Methods ({L_('fon')})"],
    [f"Results, Study Population ({L_('r1')})", FIGP[1], "Online Resource 4 (Table S1)"],
    [f"Results ({L_('r1', 'r2')})", TABP[1], "Online Resource 4 (Table S1b)"],
    [f"Results ({L_('r2')})", TABP[1]],
    [f"Results ({L_('r3', 'r6')})", TABP[2], TABP[3], FIGP[2], FIGP[3]],
    [f"Results ({L_('r7', 'r9')})", TABP[4], FIGP[4], "Online Resources 4 and 5"],
    [f"Discussion ({L_('d1')})"],
    [f"Discussion ({L_('d4')}; {L_('lim')})"],
    [f"Discussion ({L_('d2', 'd5')}; {L_('con')})"],
    [f"Discussion ({L_('d4')}; {L_('imp')})"],
    [f"Statements and Declarations, Funding ({L_('fun')})"],
    [f"Statements and Declarations, Data Availability ({L_('dav')})"],
]
s8 = pd.read_csv(B.SUPD / f"S8_strobe_record_checklist_{V}.csv", dtype=str).fillna("")
if len(s8) != len(LOC):
    raise RuntimeError(f"S8 com {len(s8)} linhas; mapa com {len(LOC)}")
s8["Page/location in manuscript"] = ["; ".join(x) for x in LOC]
s8.to_csv(MONT / f"ESM_1_strobe_record_located_{V}.csv", index=False)
TIT = PTXT[0]
h = [B.HTML_CSS, "<h1>Online Resource 1. STROBE and RECORD checklist</h1>",
     f"<p class='note'><i>{TIT}</i>. Journal of Racial and Ethnic Health Disparities.</p>",
     "<p class='note'>Items reproduced from the RECORD checklist (Benchimol et al., PLoS Med 2015; CC BY), which includes the STROBE "
     "items. Page and line numbers refer to the submitted manuscript file (Manuscript.docx, with continuous line numbering).</p>"
     "<table><tr><th>Section</th><th>Topic</th><th>Item</th><th>STROBE recommendation</th><th>RECORD item</th><th>Page/location in manuscript</th></tr>"]
for _, r in s8.iterrows():
    h.append(f"<tr><td>{r.Section}</td><td>{r.Topic}</td><td>{r['STROBE item']}</td><td>{r['STROBE recommendation']}</td>"
             f"<td>{r['RECORD item']}</td><td>{r['Page/location in manuscript']}</td></tr>")
h.append("</table>")
B.html_pdf("\n".join(h), MONT / f"ESM_1_strobe_record_located_{V}.pdf")
subprocess.run(["dot_clean", "-m", str(MONT)], check=True)
for x in MONT.glob("~$*"):                            # arquivo de trava do Word, se sobrar
    subprocess.run(["trash", str(x)], check=True)
if list(MONT.glob("._*")):
    raise RuntimeError(f"._* em {MONT}")
log(f"checklist: {len(s8)} itens com página e linha; PDF do Manuscript com {len(pdf)} páginas e {len(NUMLIN)} números de linha; "
    f"tabelas {TABP}; figuras {FIGP}")
