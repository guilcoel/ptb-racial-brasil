#!/usr/bin/env python3
"""
Auditoria independente das Etapas 7c.5, 7c.5b e 7c.6 (pacote v8 -> v10 -> v11) — ptb-racial-brasil.

Regras seguidas por este script:
- Somente leitura no projeto; grava apenas em audit_independente/etapa7c6/ (um .csv por verificação e um .csv por id do G1).
- Não lê scripts/etapa7b_checa.py nem nenhum checa_7b_*.csv (atuais ou arquivados); não lê nada em data/.
- Dos arquivos de audit_independente/ só lê os 41 .txt de etapa1..etapa7b3 (item F) e nunca grava o conteúdo deles: só contagens.
- git só em modo leitura (log, show, ls-files, diff, cat-file, hash-object sem -w).
- Rede (item G3): baixa para um diretório temporário do sistema, fora do projeto.

Uso: python3 audita_7c6_v1_20261009.py
Saídas: comparacao_7c6_v1_20261009.csv (verificacao,ok,detalhe) e commit_analise_por_id_7c6_v1_20261009.csv
"""
import ast
import collections
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
import warnings
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
from PIL import Image

warnings.filterwarnings("ignore")
import pymupdf  # noqa: E402
import docx  # noqa: E402

Image.MAX_IMAGE_PIXELS = None

PROJ = Path("/Volumes/Forja/ptb-racial-brasil")
OUT = PROJ / "audit_independente" / "etapa7c6"
MS = PROJ / "outputs" / "manuscrito"
SUB = PROJ / "Submissao"
TB = PROJ / "outputs" / "tables"
SCR = PROJ / "scripts"
STAMP = "20261009"
HEAD_ESPERADO = "8314417"

PROIBIDO = re.compile(r"(checa_7b|etapa7b_checa|(^|/)data/|\.parquet$|\.dbc$|\.dbf$)")

R = []  # (verificacao, ok, detalhe)


def reg(nome, ok, det):
    R.append((nome, bool(ok), str(det).replace("\n", " ")))
    print(f"[{'OK ' if ok else 'FALHA'}] {nome}: {str(det)[:300]}")


def guarda(p):
    s = str(p)
    assert not PROIBIDO.search(s), f"leitura proibida: {s}"
    return p


def rb(p):
    return guarda(Path(p)).read_bytes()


def rt(p):
    return guarda(Path(p)).read_text(encoding="utf-8")


def git(*a, binary=False, ok_fail=False):
    r = subprocess.run(["git", "-C", str(PROJ), *a], capture_output=True)
    if r.returncode and not ok_fail:
        raise RuntimeError(f"git {' '.join(a)}: {r.stderr.decode()[:300]}")
    return r.stdout if binary else r.stdout.decode()


def git_show(rev, path):
    guarda(path)
    return git("show", f"{rev}:{path}", binary=True)


def md5b(b):
    return hashlib.md5(b).hexdigest()


def norm_ws(t):
    return re.sub(r"\s+", " ", t.replace("’", "'").replace("­", "")).strip()


def norm_ver(t):
    return re.sub(r"v(8|9|10|11)_20261009", "vX_20261009", t)


# ---------------------------------------------------------------- constantes de texto
OLD_FRAG = "initiated in the first trimester in the mother's health region"
OLD_RE = re.compile(r"first\s+trimester\s+in\s+the\s+mother", re.I)
NEW_FULL = ("percentage of births with prenatal care initiated in the first trimester, among births with known month of prenatal "
            "care initiation, in the mother's health region of residence in the previous year")
NEW_INS = ", among births with known month of prenatal care initiation,"
APROVADO = ("excluded because this small group (0.43% of registered births) would not yield stable estimates in analyses "
            "stratified by access tertile within macroregion, and to keep the eligibility criteria of our regional study")
FRASE_S1 = "Births to mothers of Asian (amarela) race/skin color were " + APROVADO + ". "
IDX11 = ["tab01_characteristics", "tab03_knol_tercile", "tab03b_terciles_region", "tab04_sensitivity", "S2_knol_spontaneous",
         "S2b_access_specifications", "S3_multinomial", "S4_exploratory_strata", "S5c_other_method_by_code",
         "S5d_spontaneous_by_code_wald", "S6_maihda"]


# ---------------------------------------------------------------- caminhos por versão
def base(v):
    return {8: MS / "_arquivo_v8", 10: MS / "_arquivo_v10", 11: MS}[v]


def sub(v):
    return SUB if v == 11 else base(v) / "Submissao"


def vlab(v):
    return f"v{v}_{STAMP}"


def workbooks(v):
    b = base(v)
    return {"tabelas_principais": b / "tabelas" / f"tabelas_principais_{vlab(v)}.xlsx",
            "ESM_1(suplementar)": b / "suplementar" / f"ESM_1_tables_S1_S6_{vlab(v)}.xlsx",
            "Submissao/ESM_1": sub(v) / "ESM_1.xlsx"}


def csvs(v):
    out = {}
    for pasta in ("tabelas", "suplementar"):
        for p in sorted((base(v) / pasta).glob(f"*_{vlab(v)}.csv")):
            if p.name.startswith("._") or PROIBIDO.search(str(p)):
                continue
            out[f"{pasta}/{p.name.replace('_' + vlab(v), '')}"] = p
    return out


def tiffs(v):
    b = base(v)
    d = {f"figuras/{n}": b / "figuras" / f"{n}_{vlab(v)}.tif" for n in
         ("fig01_flowchart", "fig02_pr_race_m1m3", "fig03_rd_race_tercile", "fig04_dating")}
    d["suplementar/S9_maihda_caterpillar"] = b / "suplementar" / f"S9_maihda_caterpillar_{vlab(v)}.tif"
    for k in range(1, 5):
        d[f"Submissao/Fig{k}"] = sub(v) / f"Fig{k}.tif"
    return d


def pngs(v):
    b = base(v)
    d = {f"figuras/{n}": b / "figuras" / f"{n}_{vlab(v)}.png" for n in
         ("fig01_flowchart", "fig02_pr_race_m1m3", "fig03_rd_race_tercile", "fig04_dating")}
    d["suplementar/S9_maihda_caterpillar"] = b / "suplementar" / f"S9_maihda_caterpillar_{vlab(v)}.png"
    return d


def pdfs(v):
    b = base(v)
    return {"Submissao/ESM_2": sub(v) / "ESM_2.pdf", "Submissao/ESM_3": sub(v) / "ESM_3.pdf", "Submissao/ESM_4": sub(v) / "ESM_4.pdf",
            "suplementar/S7_variables_codes": b / "suplementar" / f"S7_variables_codes_{vlab(v)}.pdf",
            "suplementar/S8_strobe_record_checklist": b / "suplementar" / f"S8_strobe_record_checklist_{vlab(v)}.pdf"}


def keyjson(v):
    return base(v) / f"numeros_chave_{vlab(v)}.json"


# ---------------------------------------------------------------- leitores
def xlsx_cells(p):
    wb = openpyxl.load_workbook(guarda(p), data_only=True)
    out = {}
    for ws in wb.worksheets:
        out[ws.title] = [(c.coordinate, c.value) for row in ws.iter_rows() for c in row if c.value is not None and str(c.value) != ""]
    return out


def partes(cells):
    return cells[0][1], cells[-1][1], cells[1:-1]


def csv_rows(p):
    return list(csv.reader(io.StringIO(rb(p).decode("utf-8"))))


def pdf_text(p):
    d = pymupdf.open(guarda(p))
    return [pg.get_text() for pg in d]


def docx_text(p):
    d = docx.Document(guarda(p))
    t = [("p", x.text) for x in d.paragraphs]
    for k, tab in enumerate(d.tables):
        for i, row in enumerate(tab.rows):
            for j, c in enumerate(row.cells):
                t.append((f"t{k}.{i}.{j}", c.text))
    return t


def pix_sig(p):
    im = Image.open(guarda(p))
    sig = []
    for i in range(getattr(im, "n_frames", 1)):
        im.seek(i)
        a = np.asarray(im)
        sig.append((im.mode, im.size, hashlib.sha256(a.tobytes()).hexdigest()))
    return sig


NUM_RE = re.compile(r"(?<![A-Za-z_\d.,])[−-]?\d+(?:[.,]\d+)*")


def nums(t):
    return collections.Counter(m.group(0).rstrip(".,") for m in NUM_RE.finditer(str(t)))


def mesmo(a, b, tol=1e-12):
    if isinstance(a, list) or isinstance(b, list):
        return isinstance(a, list) and isinstance(b, list) and len(a) == len(b) and all(mesmo(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        if a == b:
            return True
        if tol == 0:
            return False
        return abs(a - b) <= tol * max(abs(a), abs(b))
    return a == b


# ================================================================ A. v8 × v10
def bloco_A():
    J8 = json.loads(rb(keyjson(8)))
    J10 = json.loads(rb(keyjson(10)))
    d8, d10 = {i["id"]: i for i in J8}, {i["id"]: i for i in J10}
    reg("A.01 números-chave: v8 tem 225 ids, todos presentes na v10", len(J8) == 225 and len(d8) == 225 and set(d8) <= set(d10),
        f"v8: {len(J8)} itens/{len(d8)} ids únicos; v10: {len(J10)} itens; ids da v8 ausentes na v10: {sorted(set(d8) - set(d10))}")
    db = [k for k in d8 if not mesmo(d8[k]["valor_bruto"], d10[k]["valor_bruto"], tol=0)]
    reg("A.02 números-chave: valor_bruto idêntico (igualdade exata) nos 225 ids", not db, f"diferenças: {db}")
    dfm = [k for k in d8 if d8[k]["valor_formatado"] != d10[k]["valor_formatado"]]
    reg("A.03 números-chave: valor_formatado idêntico nos 225 ids", not dfm, f"diferenças: {dfm}")
    novos = sorted(set(d10) - set(d8))
    reg("A.04 números-chave: único id novo na v10 é pct_amarela_fonte", novos == ["pct_amarela_fonte"] and len(d10) == 226,
        f"novos: {novos}; v10 com {len(d10)} ids")
    outros = [k for k in d8 if any(d8[k][c] != d10[k][c] for c in ("descricao", "filtro", "arquivo", "script"))]
    reg("A.05 números-chave: descricao/filtro/arquivo/script iguais nos 225 ids (extra)", not outros, f"diferenças: {outros}")

    # CSV
    c8, c10 = csvs(8), csvs(10)
    reg("A.06 CSV: mesmo conjunto de arquivos em tabelas/ e suplementar/", set(c8) == set(c10),
        f"{len(c8)} arquivos na v8, {len(c10)} na v10; só v8: {sorted(set(c8) - set(c10))}; só v10: {sorted(set(c10) - set(c8))}")
    dif, ncel = [], 0
    for k in sorted(set(c8) & set(c10)):
        a, b = csv_rows(c8[k]), csv_rows(c10[k])
        ncel += sum(len(r) for r in a)
        if a != b:
            dif.append(k)
    reg("A.07 CSV: idênticos célula a célula (v8 × v10)", not dif, f"{len(set(c8) & set(c10))} arquivos, {ncel:,} células comparadas; diferentes: {dif}")

    # xlsx
    esperado_rod = {"tabelas_principais": {s for s in IDX11 if s.startswith("tab")},
                    "ESM_1(suplementar)": {"S1_flow_excluded"} | {s for s in IDX11 if s.startswith("S")},
                    "Submissao/ESM_1": {"S1_flow_excluded"} | {s for s in IDX11 if s.startswith("S")}}
    w8, w10 = workbooks(8), workbooks(10)
    abas_ok, tit_dif, corpo_dif, rod_mud, idx_ruim, s1_ruim, num_ruim = [], [], [], {}, [], [], []
    nabas = 0
    for wbn in w8:
        X8, X10 = xlsx_cells(w8[wbn]), xlsx_cells(w10[wbn])
        abas_ok.append((wbn, list(X8) == list(X10)))
        rod_mud[wbn] = set()
        for s in X8:
            if s not in X10:
                continue
            nabas += 1
            t8, f8, b8 = partes(X8[s])
            t10, f10, b10 = partes(X10[s])
            if t8 != t10:
                tit_dif.append(f"{wbn}:{s}")
            if b8 != b10:
                corpo_dif.append(f"{wbn}:{s}")
            if f8 != f10:
                rod_mud[wbn].add(s)
                if s in IDX11:
                    if not (f10.replace(NEW_INS, "") == f8 and f10.count(NEW_INS) == 1):
                        idx_ruim.append(f"{wbn}:{s}")
                elif s == "S1_flow_excluded":
                    if not (f10.count(FRASE_S1) == 1 and f10.replace(FRASE_S1, "") == f8):
                        s1_ruim.append(f"{wbn}:{s}")
            dn = nums(f10) - nums(f8)
            up = nums(f8) - nums(f10)
            esperado_n = collections.Counter({"0.43": 1}) if s == "S1_flow_excluded" else collections.Counter()
            if dn != esperado_n or up:
                num_ruim.append(f"{wbn}:{s} (+{dict(dn)} −{dict(up)})")
    reg("A.08 xlsx: mesmas abas, na mesma ordem (3 planilhas: tabelas_principais, ESM_1 suplementar, Submissao/ESM_1)",
        all(o for _, o in abas_ok), f"{abas_ok}; {nabas} abas comparadas")
    reg("A.09 xlsx: títulos (1ª célula não vazia) iguais em todas as abas", not tit_dif, f"diferentes: {tit_dif}")
    reg("A.10 xlsx: corpo das tabelas (todas as células entre título e rodapé) igual em todas as abas (extra)", not corpo_dif,
        f"diferentes: {corpo_dif}")
    ok11 = all(rod_mud[w] == esperado_rod[w] for w in rod_mud)
    reg("A.11 xlsx: rodapés mudaram exatamente na S1 e nas 11 abas da definição do índice; os demais rodapés estão iguais", ok11,
        "; ".join(f"{w}: mudaram {sorted(rod_mud[w])}" + ("" if rod_mud[w] == esperado_rod[w] else
                                                          f" (esperado {sorted(esperado_rod[w])})") for w in rod_mud))
    reg("A.12 xlsx: nas 11 abas, a única mudança do rodapé é a inserção de ', among births with known month of prenatal care initiation,'",
        not idx_ruim, f"abas com outra mudança: {idx_ruim}")
    reg("A.13 xlsx: na S1, a única mudança do rodapé é a frase da justificativa Asian (texto aprovado)", not s1_ruim,
        f"abas com outra mudança: {s1_ruim}")
    reg("A.14 xlsx: nenhum número entra ou sai dos rodapés, exceto '0.43' na S1", not num_ruim, f"divergências: {num_ruim}")

    # docx (extra)
    d8t, d10t = docx_text(base(8) / "tabelas" / f"tabelas_principais_{vlab(8)}.docx"), docx_text(base(10) / "tabelas" / f"tabelas_principais_{vlab(10)}.docx")
    rep = [(k, norm_ver(t.replace(NEW_INS, ""))) for k, t in d10t]
    nins = sum(t.count(NEW_INS) for _, t in d10t)
    reg("A.15 docx das tabelas principais: v10 = v8 + inserção do denominador nos 4 rodapés, fora o rótulo de versão do cabeçalho (extra)",
        rep == [(k, norm_ver(t)) for k, t in d8t] and nins == 4,
        f"{len(d8t)} blocos de texto; inserções na v10: {nins}; blocos que diferem só pelo rótulo de versão: "
        f"{sum(1 for (k, a), (_, b) in zip(d8t, d10t) if a != b and norm_ver(a) == norm_ver(b))}")

    # TIFF / PNG
    t8, t10 = tiffs(8), tiffs(10)
    tdif = [k for k in t8 if pix_sig(t8[k]) != pix_sig(t10[k])]
    reg("A.16 TIFF: mesmos pixels (figuras 1–4, S9 e Submissao/Fig1–4)", not tdif, f"{len(t8)} TIFF comparados; diferentes: {tdif}")
    p8, p10 = pngs(8), pngs(10)
    pdif = [k for k in p8 if pix_sig(p8[k]) != pix_sig(p10[k])]
    reg("A.17 PNG: mesmos pixels (extra)", not pdif, f"{len(p8)} PNG comparados; diferentes: {pdif}")
    # PDF
    f8, f10 = pdfs(8), pdfs(10)
    fdif = [k for k in f8 if [norm_ver(x) for x in pdf_text(f8[k])] != [norm_ver(x) for x in pdf_text(f10[k])]]
    reg("A.18 PDF: mesmo texto, página a página (ESM_2–4 da Submissao; S7 e S8 da suplementar)", not fdif,
        f"{len(f8)} PDFs comparados; diferentes: {fdif}")


# ================================================================ B. nota do índice
def todos_textos_v11():
    """(rótulo, texto) de todo o pacote v11: xlsx, docx, CSV, md, json, PDFs."""
    out = []
    for wbn, p in workbooks(11).items():
        for s, cells in xlsx_cells(p).items():
            for co, v in cells:
                out.append((f"xlsx {wbn}:{s}!{co}", str(v)))
    for k, t in docx_text(base(11) / "tabelas" / f"tabelas_principais_{vlab(11)}.docx"):
        out.append((f"docx tabelas_principais:{k}", t))
    for k, p in csvs(11).items():
        out.append((f"csv {k}", rb(p).decode("utf-8")))
    for p in [MS / f"numeros_chave_{vlab(11)}.md", MS / "data_code_availability.md", MS / "legendas_figuras.md", MS / "MANIFEST.md"]:
        out.append((f"md {p.name}", rt(p)))
    out.append((f"json numeros_chave_{vlab(11)}", rt(keyjson(11))))
    for k, p in pdfs(11).items():
        out.append((f"pdf {k}", "\n".join(pdf_text(p))))
    return out


def bloco_B():
    for wbn, p in workbooks(11).items():
        X = xlsx_cells(p)
        alvo = [s for s in IDX11 if s in X]
        falta = [s for s in alvo if NEW_FULL not in norm_ws(str(partes(X[s])[1]))]
        com = [s for s in X if any(NEW_FULL in norm_ws(str(v)) for _, v in X[s])]
        nome = "B.01" if wbn == "tabelas_principais" else ("B.02" if wbn.startswith("ESM") else "B.03")
        reg(f"{nome} texto novo do índice no rodapé de todas as abas-alvo — {wbn} (v11)", not falta and len(alvo) == (4 if wbn == "tabelas_principais" else 7),
            f"abas-alvo: {len(alvo)}; sem o texto: {falta}; abas onde o texto aparece: {com}")
        extra = sorted(set(com) - set(IDX11))
        if extra:
            reg(f"{nome}b texto novo fora das 11 abas — {wbn}", False, f"{extra}")
    textos = todos_textos_v11()
    docx_new = sum(norm_ws(t).count(NEW_FULL) for k, t in textos if k.startswith("docx"))
    reg("B.04 docx v11: texto novo nos 4 rodapés das tabelas principais (extra)", docx_new == 4, f"ocorrências: {docx_new}")
    por_tipo = collections.Counter()
    achados = []
    for k, t in textos:
        tipo = k.split()[0]
        por_tipo[tipo] += 1
        n = norm_ws(t)
        if OLD_FRAG in n or OLD_RE.search(n):
            achados.append(k)
    for tipo, cod in [("xlsx", "B.05"), ("docx", "B.06"), ("csv", "B.07"), ("md", "B.08"), ("json", "B.09"), ("pdf", "B.10")]:
        a = [k for k in achados if k.startswith(tipo)]
        reg(f"{cod} texto antigo ('{OLD_FRAG}') ausente — {tipo} do pacote v11", not a,
            f"{por_tipo[tipo]} blocos/arquivos varridos (normalização de espaços e apóstrofo); ocorrências: {a}")
    # Submissao em separado (xlsx + PDFs), como pedido
    subs = [k for k in achados if "Submissao" in k]
    nsub = sum(1 for k, _ in textos if "Submissao" in k)
    reg("B.11 texto antigo ausente em Submissao/ (ESM_1.xlsx e ESM_2–4.pdf)", not subs, f"{nsub} blocos varridos; ocorrências: {subs}")
    fora = sorted(p for p in MS.glob("*.md") if not p.name.startswith("._") and p.name not in
                  {f"numeros_chave_{vlab(11)}.md", "data_code_availability.md", "legendas_figuras.md", "MANIFEST.md"})
    com = [p.name for p in fora if OLD_RE.search(norm_ws(rt(p)))]
    reg("B.12 (registro) .md de outputs/manuscrito fora do pacote (resumos, ficha dos Métodos) com o texto antigo", True,
        f"{len(fora)} arquivos varridos; com o texto antigo: {com}")


# ================================================================ C. código do índice
def bloco_C():
    p = SCR / "etapa2_03_indice_acesso.py"
    L = rt(p).splitlines()

    def acha(rx):
        return [(i + 1, l.rstrip()) for i, l in enumerate(L) if re.search(rx, l)]

    num = acha(r'"tri1":\s*mes\.between\(1,\s*3\)\.fillna\(False\)')
    den = acha(r'"mes_valido":\s*mes\.between\(1,\s*9\)\.fillna\(False\)')
    ind = acha(r'A\["indice"\]\s*=\s*100\s*\*\s*A\.tri1\s*/\s*A\.mes_valido')
    soma = acha(r'g\[\["mes_valido",\s*"tri1"')
    fora = acha(r'"mes_nulo":\s*mes\.isna\(\).*"mes_99":\s*\(mes\s*==\s*99\)')
    conv = acha(r'astype\("Int16"\)')
    doc = acha(r"MESPRENAT 1–3|MESPRENAT válido \(1–9; 99")
    lag = acha(r"assign\(ano=lambda x: x\.ano \+ 1\)")
    res = acha(r"cod = r\.CODMUNRES")
    fmt = lambda xs: " | ".join(f"L{i}: {t.strip()}" for i, t in xs)
    reg("C.01 numerador = MESPRENAT 1–3", len(num) == 1, fmt(num))
    reg("C.02 denominador = MESPRENAT 1–9 (99 e nulo fora: between(1, 9) é falso para 99 e NA→False)", len(den) == 1, fmt(den))
    reg("C.03 índice = 100 × soma(numerador) / soma(denominador) por região de saúde × ano", len(ind) == 1 and len(soma) == 1,
        fmt(soma + ind))
    reg("C.04 99 e nulo contados à parte (completude), fora do índice; docstring coerente", len(fora) == 1 and len(doc) >= 2, fmt(fora + doc))
    reg("C.05 região de residência da mãe e ano anterior (t−1) (extra)", len(lag) == 1 and len(res) == 1, fmt(res + lag))
    # teste sintético do mesmo idioma pandas (Int16 + between + fillna), nos dois caminhos da função num()
    s = pd.Series([1, 2, 3, 4, 9, 99, None, 0, 10], dtype="Int16")
    v1, t1 = s.between(1, 9).fillna(False).tolist(), s.between(1, 3).fillna(False).tolist()
    s2 = pd.to_numeric(pd.Series(["1", "03", " 9", "99", "", None]).astype("string").str.strip().replace({"": pd.NA}),
                       errors="raise").astype("Int16")
    v2, t2 = s2.between(1, 9).fillna(False).tolist(), s2.between(1, 3).fillna(False).tolist()
    ok = (v1 == [True] * 5 + [False] * 4 and t1 == [True] * 3 + [False] * 6 and v2 == [True, True, True, False, False, False]
          and t2 == [True, True, False, False, False, False])
    reg("C.06 teste sintético da expressão: 1–9 válidos, 1–3 no numerador; 99, nulo, 0, 10 e '' fora", ok,
        f"valores [1,2,3,4,9,99,NA,0,10] → válido {v1}, 1º tri {t1}; strings ['1','03',' 9','99','',None] → válido {v2}, 1º tri {t2}")
    # tabela agregada de completude (outputs/tables, sem microdado)
    C = pd.read_csv(guarda(TB / "tab_e2_03_mesprenat_completude_v1_20261008.csv"))
    C["outros"] = C.n - C.n_valido - C.n_nulo - C.n_99
    br = C[C.macro == "Brasil"]
    reg("C.07 (registro) completude agregada (tab_e2_03_mesprenat_completude): válidos 1–9 + nulos + 99 + outros códigos = n; "
        "os 'outros' (fora de 1–9 e de 99) também ficam fora do índice", (C.outros >= 0).all(),
        f"{len(C)} linhas ano × macrorregião; Brasil 2014–2024: n = {int(br.n.sum()):,}, válidos {int(br.n_valido.sum()):,} "
        f"({100 * br.n_valido.sum() / br.n.sum():.2f}%), nulos {int(br.n_nulo.sum()):,}, 99 {int(br.n_99.sum()):,}, "
        f"outros códigos {int(br.outros.sum()):,} ({100 * br.outros.sum() / br.n.sum():.4f}%), em {int((br.outros > 0).sum())} dos "
        f"{len(br)} anos")
    return dict(num=num, den=den, ind=ind, soma=soma, fora=fora, doc=doc, lag=lag, res=res)


# ================================================================ D. justificativa Asian
def bloco_D():
    for wbn in ("ESM_1(suplementar)", "Submissao/ESM_1"):
        X = xlsx_cells(workbooks(11)[wbn])
        f = str(partes(X["S1_flow_excluded"])[1])
        reg(f"D.0{1 if wbn.startswith('ESM') else 2} texto aprovado idêntico no rodapé da S1_flow_excluded — {wbn}", APROVADO in f,
            f"ocorrências exatas: {f.count(APROVADO)}")
    dca = rt(MS / "data_code_availability.md")
    reg("D.03 texto aprovado idêntico em data_code_availability.md", APROVADO in dca, f"ocorrências exatas: {dca.count(APROVADO)}")
    t7 = pd.read_csv(guarda(TB / "tab07_fluxograma_motivos_v1_20261008.csv"), dtype=str)
    t6 = pd.read_csv(guarda(TB / "tab06_fluxograma_regiao_v1_20261008.csv"), dtype=str)
    am = t7[(t7.regiao == "Brasil") & (t7.passo == "1_raca") & (t7.motivo == "3")]
    fo = t6[(t6.regiao == "Brasil") & (t6.passo == "0_fonte")]
    n_am, n_fo = int(am.n.iloc[0]), int(fo.restante.iloc[0])
    reg("D.04 fontes: Asian (Brasil, 1_raca, motivo 3) = 117,549 e nascidos vivos (Brasil, 0_fonte, restante) = 27,489,150",
        len(am) == 1 and len(fo) == 1 and n_am == 117549 and n_fo == 27489150, f"{n_am:,} / {n_fo:,} (linhas casadas: {len(am)}, {len(fo)})")
    pct = 100 * n_am / n_fo
    reg("D.05 recálculo: 117,549 / 27,489,150 = 0.43%", f"{pct:.2f}" == "0.43", f"{pct:.6f}% → {pct:.2f}%")
    J = {i["id"]: i for i in json.loads(rb(keyjson(11)))}
    J10 = {i["id"]: i for i in json.loads(rb(keyjson(10)))}
    k = J.get("pct_amarela_fonte")
    ok = k is not None and k["valor_formatado"] == "0.43%" and mesmo(k["valor_bruto"], pct)
    reg("D.06 número-chave pct_amarela_fonte (v11) coincide com o recálculo", ok,
        f"bruto {k['valor_bruto']!r} × recalculado {pct!r}; formatado {k['valor_formatado']!r}; v10 igual: "
        f"{J10['pct_amarela_fonte']['valor_bruto'] == k['valor_bruto']}")
    ok = (J["excl_amarela"]["valor_bruto"] == n_am and J["N_fonte"]["valor_bruto"] == n_fo and
          f"0.43% = {n_am:,} / {n_fo:,}" in dca)
    reg("D.07 excl_amarela, N_fonte e a fração escrita na disponibilidade batem com as fontes (extra)", ok,
        f"excl_amarela={J['excl_amarela']['valor_bruto']}, N_fonte={J['N_fonte']['valor_bruto']}")


# ================================================================ E. arquivos ._*
def bloco_E():
    sobra, ds = [], []
    for raiz, dirs, fs in os.walk(SUB):
        for f in fs + dirs:
            if f.startswith("._"):
                sobra.append(os.path.relpath(os.path.join(raiz, f), SUB))
            if f == ".DS_Store":
                ds.append(os.path.relpath(os.path.join(raiz, f), SUB))
    reg("E.01 nenhum ._* em Submissao/ (recursivo)", not sobra, f"encontrados: {sobra}")
    reg("E.02 nenhum .DS_Store em Submissao/ (extra)", not ds, f"encontrados: {ds}")
    gi = [l.strip() for l in rt(PROJ / ".gitignore").splitlines()]
    reg("E.03 .gitignore tem a linha '._*'", "._*" in gi, f"linhas: {len(gi)}")
    reg("E.04 .gitignore tem a linha '.DS_Store'", ".DS_Store" in gi, f"linhas: {len(gi)}")
    p = SCR / "etapa7b_04_submissao.py"
    src = rt(p)
    tree = ast.parse(src)
    fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "limpa_macos"]
    ok_fn, det = False, "função limpa_macos não encontrada"
    if fn:
        f = fn[0]
        runs = [n for n in ast.walk(f) if isinstance(n, ast.Call) and ast.unparse(n.func) == "subprocess.run"]
        dc = [n for n in runs if n.args and isinstance(n.args[0], ast.List) and [ast.unparse(x) for x in n.args[0].elts][:2] == ["'dot_clean'", "'-m'"]
              and any(k.arg == "check" and ast.unparse(k.value) == "True" for k in n.keywords)]
        globs = [n for n in ast.walk(f) if isinstance(n, ast.Call) and ast.unparse(n.func).endswith(".rglob") and n.args
                 and ast.unparse(n.args[0]) == "'._*'"]
        asserts = [n for n in ast.walk(f) if isinstance(n, ast.Assert)]
        ok_fn = bool(dc and globs and asserts)
        det = (f"L{f.lineno}–L{f.end_lineno}: dot_clean -m com check=True em L{[n.lineno for n in dc]}; rglob('._*') em "
               f"L{[n.lineno for n in globs]}; assert em L{[n.lineno for n in asserts]} ({[ast.unparse(a.test) for a in asserts]})")
    reg("E.05 etapa7b_04_submissao.py: limpa_macos roda 'dot_clean -m' (check=True) e falha (assert) se sobrar ._*", ok_fn, det)
    chamadas = [n.lineno for n in tree.body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                and ast.unparse(n.value.func) == "limpa_macos" and ast.unparse(n.value.args[0]) == "B.SUB"]
    escritas = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            fu = ast.unparse(n.func)
            if fu in ("shutil.copy2", "B.html_pdf") and any("B.SUB" in ast.unparse(a) for a in n.args):
                escritas.append(n.lineno)
    ok = bool(chamadas and escritas) and min(chamadas) < min(escritas) and max(chamadas) > max(escritas)
    reg("E.06 limpa_macos(B.SUB) é chamada antes da 1ª e depois da última escrita em Submissao/", ok,
        f"chamadas em L{chamadas}; escritas em Submissao/ (copy2/html_pdf) em L{sorted(set(escritas))}")
    cont = {}
    for top in ("outputs", "scripts", "audit_independente", "docs"):
        porpasta = collections.Counter()
        for raiz, dirs, fs in os.walk(PROJ / top):
            for f in fs:
                if f.startswith("._"):
                    porpasta[os.path.relpath(raiz, PROJ)] += 1
        cont[top] = porpasta
    det = "; ".join(f"{t}/: {sum(c.values())} em {len(c)} pastas" for t, c in cont.items())
    reg("E.07 (registro) ._* fora de Submissao/", True, det)
    return cont


# ================================================================ F. os 41 .txt
DIRS_F = ["etapa1", "etapa2", "etapa3", "etapa4", "etapa4b", "etapa5", "etapa6", "etapa6b", "etapa7b", "etapa7b1", "etapa7b2", "etapa7b3"]
ROTULO_AGREG = re.compile(r"(?i)(N\s*=|\bn\s+CO\b|casos|total|brutos|cascata|registros|c[eé]lulas|clusters|macro|distrib|base por|amostra|"
                          r"tercil|linhas|esperado|estratos|padr[õo]es|treino|iter=|seed|vers[aã]o|\bv\d|faixa|\bx\s+ra[cç]a|"
                          r"\[\(|_v\d+_20\d{6}\b)")
GRUPO = re.compile(r"\b(Branca|Parda|Preta|Indigena|Indígena|ptb|ptb_esp|ptb_ind|pig|lbw|DUM|outro_metodo|ignorado|Total|TOTAL|TODOS|"
                   r"T[123]|20(1[4-9]|2[0-4]))\b|^\s*\d+:?\s")
PROCESSO = re.compile(r"(?i)(carimbo|arquivo|script|in[ií]cio|mtime|regravad|gravad|regerad|depois|antes|auditor|autor|rascunho|bug|SHA|"
                      r"vers[õo]es|verificador|\bàs\s+\d\d:\d\d|^\s*-\s*\d\d:\d\d:\d\d)")
IDVARS = re.compile(r"\b(NUMERODN|NUMERODO|DTNASC|DTOBITO|HORANASC|HORAOBITO|CODESTAB|CNES|DTNASCMAE|NOMEMAE|CPF|CNS|DTCADASTRO|"
                    r"DTRECEBIM|NUMREGCART|CODCART|CODMUNNASC|DTULTMENS)\b")


def colunas(l):
    s = l.strip()
    if not s:
        return 0
    if "│" in s or (s.startswith("|") and s.endswith("|")):         # tabela desenhada (DuckDB) ou markdown
        return len([c for c in re.split(r"[│|]", s) if c.strip()])
    if "[(" in s:                                                   # lista de tuplas impressa pelo Python: campos por tupla
        tup = re.findall(r"\(([^()]*)\)", s)
        return max((len([x for x in t.split(",") if x.strip()]) for t in tup), default=1)
    toks = s.split()
    numerico = sum(bool(re.fullmatch(r"[−-]?[\d.,]+(e[−+-]?\d+)?%?|NA|NaN|NULL|TRUE|FALSE|True|False|None", t)) for t in toks)
    return len(toks) if (len(toks) >= 3 and numerico >= len(toks) / 2) else 1


def bloco_F():
    fs = sorted(p for d in DIRS_F for p in (PROJ / "audit_independente" / d).rglob("*.txt") if not p.name.startswith("._"))
    rel = [str(p.relative_to(PROJ)) for p in fs]
    reg("F.01 41 arquivos .txt em audit_independente/etapa1 … etapa7b3", len(fs) == 41,
        f"{len(fs)} arquivos; por pasta: {dict(collections.Counter(p.parent.name for p in fs))}")
    lsf = set(git("ls-files", "--", *[f"audit_independente/{d}" for d in DIRS_F]).split("\n")) - {""}
    lsf = {x for x in lsf if x.endswith(".txt")}
    mod = git("diff", "--name-only", "--", *rel).split()
    mod_idx = git("diff", "--cached", "--name-only", "HEAD", "--", *rel).split()
    quando = collections.Counter(git("log", "--diff-filter=A", "--format=%h", "-1", "--", r).strip() for r in rel)
    reg("F.02 os 41 .txt estão no git (git ls-files) e sem alteração no working tree nem no índice", set(rel) == lsf and not mod and not mod_idx,
        f"rastreados: {len(lsf)}; só no disco: {sorted(set(rel) - lsf)}; só no git: {sorted(lsf - set(rel))}; modificados: {mod + mod_idx}; "
        f"commit que os adicionou: {dict(quando)}")
    cat = collections.Counter()
    porarq = {}
    maxlin, maxcol, maxtok = (0, ""), (0, ""), (0, "")
    for p, r in zip(fs, rel):
        t = rb(p).decode("utf-8", errors="replace")
        L = t.splitlines()
        if len(L) > maxlin[0]:
            maxlin = (len(L), r)
        c = collections.Counter()
        for l in L:
            nc = colunas(l)
            if nc > maxcol[0]:
                maxcol = (nc, r)
            nt = len(l.split())
            if nt > maxtok[0]:
                maxtok = (nt, r)
            # datas (qualquer formato) com ano 1900–2024 = possível data de nascimento/óbito/DUM
            for m in re.finditer(r"\b(19\d\d|20[01]\d|202[0-4])-(0[1-9]|1[0-2])-([0-2]\d|3[01])\b", l):
                c["data_ate_2024"] += 1
            for m in re.finditer(r"\b([0-2]?\d|3[01])[/.](0?[1-9]|1[0-2])[/.](19\d\d|20[01]\d|202[0-4])\b", l):
                c["data_ate_2024"] += 1
            for m in re.finditer(r"(?<![\d.,])([0-2]\d|3[01])(0[1-9]|1[0-2])(19\d\d|20[01]\d|202[0-4])(?![\d.,])", l):
                c["data_ate_2024"] += 1
            for m in re.finditer(r"(?<![\d.,])(19\d\d|20[01]\d|202[0-4])(0[1-9]|1[0-2])([0-2]\d|3[01])(?![\d.,])", l):
                c["data_ate_2024"] += 1
            for m in re.finditer(r"\b(20(25|26))-\d\d-\d\d\b|\b\d\d/\d\d/2026\b", l):
                c["data_2025_2026(carimbo/versao)"] += 1
            # horas: aceitáveis só em carimbo de log ([aaaa-mm-dd hh:mm) ou junto de data de 2026
            for m in re.finditer(r"\b([01]\d|2[0-3]):[0-5]\d\b", l):
                if re.search(r"20(25|26)-\d\d-\d\d", l):
                    c["hora_em_carimbo_de_log"] += 1
                elif PROCESSO.search(l):
                    c["hora_de_processo_em_prosa"] += 1
                else:
                    c["hora_solta"] += 1
            if re.search(r"(?i)\bHORA\w*\b\D{0,10}\d{3,4}\b", l):
                c["hora_rotulada"] += 1
            # CPF formatado ou CNS (15 dígitos), sem contar casas decimais (precedidas de '.' ou ',')
            if re.search(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|(?<![\d.,])[1-9]\d{14}(?![\d.,])", l):
                c["cpf_cns"] += 1
            c["decimal_15_digitos(nao_e_cns)"] += len(re.findall(r"(?<=[.,])\d{15,}", l))
            if IDVARS.search(l):
                c["var_identificadora_" + ("tabular" if colunas(l) > 1 else "prosa/contagem")] += 1
            longos = re.findall(r"(?<![\d.,A-Za-z])\d{7,12}(?![\d.,A-Za-z])", l)
            hexs = re.findall(r"\b[0-9a-f]{32,}\b", l)
            if longos or hexs:
                if hexs and not longos:
                    c["num_longo:hash_hex"] += 1
                elif ROTULO_AGREG.search(l):
                    c["num_longo:contagem_rotulada"] += 1
                elif re.search(r"\d\.\d|TRUE|FALSE|True|False|NaN|NULL|\bNA\b", l):
                    c["num_longo:linha_de_estimativas"] += 1
                elif GRUPO.search(l):
                    c["num_longo:tabela_agregada_por_grupo_ou_ano"] += 1
                else:
                    c["num_longo:sem_classificacao"] += 1
        porarq[r] = c
        cat.update(c)
    reg("F.03 nenhuma data com ano 1900–2024 (dd/mm/aaaa, aaaa-mm-dd, ddmmaaaa, aaaammdd)", cat["data_ate_2024"] == 0,
        f"ocorrências: {cat['data_ate_2024']}; datas de 2025–2026 (carimbos de log, data de relatório, data de versão do R): "
        f"{cat['data_2025_2026(carimbo/versao)']}")
    reg("F.04 nenhuma hora de evento individual: horas só em carimbo de log ou em prosa sobre o processo de auditoria; nenhum campo HORA*",
        cat["hora_solta"] == 0 and cat["hora_rotulada"] == 0,
        f"horas em carimbo de log (linha com data 2025/2026): {cat['hora_em_carimbo_de_log']}; em prosa sobre geração/comparação de "
        f"arquivos: {cat['hora_de_processo_em_prosa']}; sem contexto: {cat['hora_solta']}; campos HORA* com valor: {cat['hora_rotulada']}")
    reg("F.05 nenhum padrão de CPF/CNS", cat["cpf_cns"] == 0,
        f"ocorrências: {cat['cpf_cns']}; sequências de ≥15 dígitos que são casas decimais (descartadas): {cat['decimal_15_digitos(nao_e_cns)']}")
    reg("F.06 nenhuma variável identificadora (NUMERODN, DTNASC, HORANASC, CODESTAB, CNES, DTOBITO...) como coluna de tabela",
        cat["var_identificadora_tabular"] == 0,
        f"como coluna: {cat['var_identificadora_tabular']}; citada em prosa/contagem agregada: {cat['var_identificadora_prosa/contagem']} "
        f"(arquivos: {[k for k, v in porarq.items() if v['var_identificadora_prosa/contagem']]})")
    nl = {k.split(':')[1]: v for k, v in cat.items() if k.startswith("num_longo")}
    reg("F.07 números de 7–12 dígitos: todos em contexto agregado (contagem, linha de estimativa, tabela por grupo/ano) ou hash",
        nl.get("sem_classificacao", 0) == 0, f"linhas com número longo: {nl}")
    reg("F.08 (registro) maior número de linhas", True, f"{maxlin[0]} linhas ({maxlin[1]})")
    reg("F.09 (registro) maior número de colunas", True,
        f"{maxcol[0]} colunas ({maxcol[1]}); coluna = célula entre '│' (DuckDB) ou entre '|' (linha markdown que abre e fecha com '|'); "
        f"campo de tupla em lista impressa pelo Python ('[(...)]'); ou token separado por espaço em linha tabular (≥3 tokens, ≥ metade "
        f"numéricos/NA/TRUE/FALSE, como as impressões de data.frame do R); prosa conta 1. Máximo de tokens por espaço em qualquer "
        f"linha, inclusive prosa: {maxtok[0]} ({maxtok[1]})")
    return porarq, maxlin, maxcol, maxtok


# ================================================================ G1. números-chave v10 × v11 e commit_analise
def bloco_G1():
    J10 = json.loads(rb(keyjson(10)))
    J11 = json.loads(rb(keyjson(11)))
    ids10, ids11 = [i["id"] for i in J10], [i["id"] for i in J11]
    reg("G1.01 mesmos ids, na mesma ordem (v10 × v11)", ids10 == ids11 and len(set(ids11)) == len(ids11),
        f"v10: {len(ids10)}; v11: {len(ids11)}; só v10: {sorted(set(ids10) - set(ids11))}; só v11: {sorted(set(ids11) - set(ids10))}")
    d10, d11 = {i["id"]: i for i in J10}, {i["id"]: i for i in J11}
    dv = [k for k in d10 if k in d11 and not (mesmo(d10[k]["valor_bruto"], d11[k]["valor_bruto"], tol=0)
                                               and d10[k]["valor_formatado"] == d11[k]["valor_formatado"])]
    reg("G1.02 valor_bruto e valor_formatado idênticos (igualdade exata)", not dv, f"diferenças: {dv}")
    do = [k for k in d10 if k in d11 and any(d10[k][c] != d11[k][c] for c in ("descricao", "filtro", "arquivo", "script"))]
    reg("G1.03 descricao/filtro/arquivo/script idênticos (extra)", not do, f"diferenças: {do}")
    k10 = {tuple(i.keys()) for i in J10}
    k11 = {tuple(i.keys()) for i in J11}
    ok = (all("commit" in i for i in J10) and not any("commit" in i for i in J11) and all("commit_pacote" in i and "commit_analise" in i for i in J11)
          and all(set(i.keys()) == (set(d10[i["id"]].keys()) - {"commit"}) | {"commit_pacote", "commit_analise"} for i in J11))
    reg("G1.04 campo 'commit' virou 'commit_pacote' e entrou 'commit_analise' (nenhum outro campo mudou)", ok,
        f"chaves v10: {sorted(k10)}; chaves v11: {sorted(k11)}")
    cp = collections.Counter(i["commit_pacote"] for i in J11)
    c10 = collections.Counter(i["commit"] for i in J10)
    head = git("rev-parse", "--short", "HEAD").strip()
    reg("G1.05 commit_pacote = HEAD no momento da geração (8314417) em todos os itens", set(cp) == {head} == {HEAD_ESPERADO},
        f"commit_pacote: {dict(cp)}; HEAD atual: {head}; campo 'commit' da v10: {dict(c10)}")

    # versões arquivadas: commit que adicionou o JSON no caminho original, e conteúdo lido do próprio git
    vers = []
    integ = []
    for n in range(1, 11):
        orig = f"outputs/manuscrito/numeros_chave_v{n}_{STAMP}.json"
        adds = git("log", "--diff-filter=A", "--format=%h", "--", orig).split()
        arq = MS / f"_arquivo_v{n}" / f"numeros_chave_v{n}_{STAMP}.json"
        if len(adds) != 1:
            integ.append(f"v{n}: {len(adds)} commits de adição {adds}")
        c = adds[-1] if adds else ""
        bg = git_show(c, orig) if c else b""
        ba = rb(arq) if arq.exists() else b""
        if bg != ba:
            integ.append(f"v{n}: arquivo arquivado difere do git {c}")
        vers.append((n, c, {i["id"]: i for i in json.loads(bg or ba)}))
    reg("G1.06 JSON arquivados v1–v10 = versão adicionada ao git; um único commit de adição por versão (extra)", not integ,
        f"commits de adição: {[(n, c) for n, c, _ in vers]}; problemas: {integ}")

    def recalc(tol):
        out = {}
        for it in J11:
            ca, vmin = "", None
            for n, c, J in sorted(vers, key=lambda x: -x[0]):
                x = J.get(it["id"])
                if x is None or x["valor_formatado"] != it["valor_formatado"] or not mesmo(x["valor_bruto"], it["valor_bruto"], tol):
                    break
                ca, vmin = c, n
            out[it["id"]] = (ca, vmin)
        return out

    meu = recalc(1e-12)
    exato = recalc(0)
    dif = [k for k in d11 if d11[k]["commit_analise"] != meu[k][0]]
    reg("G1.07 commit_analise recalculado de forma independente = commit_analise do pacote, id a id", not dif,
        f"{len(d11)} ids comparados; divergentes: {len(dif)} {dif[:20]}")
    dist = collections.Counter(meu[k][0] for k in ids11)
    pacote_dist = collections.Counter(d11[k]["commit_analise"] for k in ids11)
    vaz = sum(1 for k in ids11 if not d11[k]["commit_analise"])
    ordem = {c: n for n, c, _ in vers}
    reg("G1.08 (registro) distribuição de commit_analise e vazios", True,
        "; ".join(f"{c or '(vazio)'} [v{ordem.get(c, '?')}]: {n}" for c, n in sorted(pacote_dist.items(), key=lambda x: ordem.get(x[0], 99)))
        + f"; vazios: {vaz}")
    tol_imp = [k for k in ids11 if meu[k] != exato[k]]
    reg("G1.09 (registro) a tolerância 1e-12 não muda nenhum commit_analise em relação à igualdade exata", not tol_imp,
        f"ids afetados pela tolerância: {tol_imp}")
    # coerência com o .md
    md = rt(MS / f"numeros_chave_{vlab(11)}.md").splitlines()
    linhas = [l for l in md if l.startswith("| ") and not l.startswith("| id ") and not l.startswith("|---")]
    # a coluna id do .md não é escapada; a comparação é por posição (o .md segue a ordem do JSON) e pela última célula
    ult = [re.split(r"(?<!\\)\|", l)[-2].strip() for l in linhas]
    mdd = [J11[i]["id"] for i in range(min(len(ult), len(J11))) if ult[i] != J11[i]["commit_analise"]
           or not linhas[i].startswith(f"| {J11[i]['id']} |")]
    reg("G1.10 numeros_chave_v11.md traz o mesmo commit_analise do JSON, na mesma ordem (extra)", len(ult) == len(ids11) and not mdd,
        f"linhas no md: {len(ult)}; divergentes: {mdd[:10]}; ids com '|': {[k for k in ids11 if '|' in k]}")

    # por que a sequência para: id ausente na versão anterior ou valor diferente (número recalculado/reformatado)?
    motivo = collections.Counter()
    mudou = []
    for k in ids11:
        vmin = meu[k][1]
        ant = [J for n, c, J in vers if n == vmin - 1]
        if vmin == 1 or not ant:
            motivo["começa na v1"] += 1
        elif k not in ant[0]:
            motivo["id ausente na versão anterior"] += 1
        else:
            motivo["valor diferente na versão anterior"] += 1
            mudou.append(f"{k} (v{vmin - 1}→v{vmin})")
    novos_por_v = collections.Counter()
    for n, c, J in vers:
        prev = [J2 for n2, c2, J2 in vers if n2 == n - 1]
        novos_por_v[f"v{n}"] = len(set(J) - set(prev[0])) if prev else len(J)
    reg("G1.13 (registro) onde começa a sequência de mesmo valor", True,
        f"{dict(motivo)}; ids com valor alterado em alguma versão: {mudou}; ids novos por versão: {dict(novos_por_v)}")
    # dentro da sequência de versões com o mesmo valor, a origem declarada (arquivo/script/filtro) mudou?
    mud = collections.Counter()
    ex = {}
    for k in ids11:
        vmin = meu[k][1]
        if not vmin:
            continue
        for n, c, J in vers:
            if n >= vmin:
                for campo in ("arquivo", "script", "filtro"):
                    if J[k].get(campo) != d11[k][campo]:
                        mud[campo] += 1
                        ex.setdefault(campo, set()).add(k)
    reg("G1.12 (registro) ids cuja origem declarada (arquivo/script/filtro) mudou dentro da sequência de mesmo valor", True,
        f"ocorrências (id × versão): {dict(mud)}; ids: { {c: sorted(v)[:8] for c, v in ex.items()} }")
    # alternativa para discutir a definição: último commit do script de origem até o commit_analise
    alt = {}
    for k in ids11:
        it = d11[k]
        sc = it["script"].split()[0] if it["script"] else ""
        ca = meu[k][0]
        if sc and ca:
            alt[k] = git("log", "-1", "--format=%h", ca, "--", sc).strip()
        else:
            alt[k] = ""
    # gravar comparação id a id
    with open(OUT / f"commit_analise_por_id_7c6_v1_{STAMP}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "commit_analise_pacote", "commit_analise_auditor", "versao_mais_antiga_com_mesmo_valor", "igual",
                    "script_origem", "ultimo_commit_do_script_ate_commit_analise"])
        for k in ids11:
            w.writerow([k, d11[k]["commit_analise"], meu[k][0], f"v{meu[k][1]}" if meu[k][1] else "", d11[k]["commit_analise"] == meu[k][0],
                        d11[k]["script"], alt[k]])
    altd = collections.Counter(alt.values())
    mesmo_commit = sum(1 for k in ids11 if alt[k] == meu[k][0])
    reg("G1.11 (registro) commit do script de origem × commit_analise", True,
        f"o último commit que tocou o script de origem até o commit_analise coincide com o commit_analise em {mesmo_commit}/{len(ids11)} "
        f"ids; distribuição: {dict(altd)}")
    return dict(dist=dist, vaz=vaz, ordem=ordem, alt=altd, mesmo_commit=mesmo_commit, meu=meu)


# ================================================================ G2. demais arquivos v10 × v11
def bloco_G2():
    c10, c11 = csvs(10), csvs(11)
    dif = [k for k in c10 if k in c11 and norm_ver(rb(c10[k]).decode("utf-8")) != norm_ver(rb(c11[k]).decode("utf-8"))]
    byte = [k for k in c10 if k in c11 and rb(c10[k]) != rb(c11[k])]
    reg("G2.01 CSV idênticos (v10 × v11; tabelas/ e suplementar/)", set(c10) == set(c11) and not dif,
        f"{len(c10)} × {len(c11)} arquivos; diferentes após normalizar rótulo de versão: {dif}; diferentes byte a byte: {byte}")
    w10, w11 = workbooks(10), workbooks(11)
    xd = []
    nab = 0
    for wbn in w10:
        X10, X11 = xlsx_cells(w10[wbn]), xlsx_cells(w11[wbn])
        if list(X10) != list(X11):
            xd.append(f"{wbn}: abas diferentes")
        for s in X10:
            nab += 1
            a = [(co, norm_ver(str(v))) for co, v in X10[s]]
            b = [(co, norm_ver(str(v))) for co, v in X11.get(s, [])]
            if a != b:
                t0, f0, b0 = partes(X10[s])
                t1, f1, b1 = partes(X11.get(s, [("", "")]))
                xd.append(f"{wbn}:{s} (título {'=' if t0 == t1 else '≠'}, rodapé {'=' if f0 == f1 else '≠'}, corpo {'=' if b0 == b1 else '≠'})")
    reg("G2.02 xlsx idênticos célula a célula, inclusive títulos e rodapés (tabelas_principais, ESM_1, Submissao/ESM_1)", not xd,
        f"{nab} abas; diferenças: {xd}")
    d10 = docx_text(base(10) / "tabelas" / f"tabelas_principais_{vlab(10)}.docx")
    d11 = docx_text(base(11) / "tabelas" / f"tabelas_principais_{vlab(11)}.docx")
    reg("G2.03 docx das tabelas principais: mesmo texto (extra)", [(k, norm_ver(t)) for k, t in d10] == [(k, norm_ver(t)) for k, t in d11],
        f"{len(d10)} blocos de texto")
    f10, f11 = pdfs(10), pdfs(11)
    pd_ = [k for k in f10 if [norm_ver(x) for x in pdf_text(f10[k])] != [norm_ver(x) for x in pdf_text(f11[k])]]
    reg("G2.04 PDFs com o mesmo texto página a página (ESM_2–4; S7 e S8)", not pd_, f"{len(f10)} PDFs; diferentes: {pd_}")
    t10, t11 = tiffs(10), tiffs(11)
    td = [k for k in t10 if pix_sig(t10[k]) != pix_sig(t11[k])]
    reg("G2.05 TIFF com os mesmos pixels (figuras 1–4, S9, Submissao/Fig1–4)", not td, f"{len(t10)} TIFF; diferentes: {td}")
    p10, p11 = pngs(10), pngs(11)
    pdd = [k for k in p10 if pix_sig(p10[k]) != pix_sig(p11[k])]
    reg("G2.06 PNG com os mesmos pixels (extra)", not pdd, f"{len(p10)} PNG; diferentes: {pdd}")
    a = rt(base(10) / f"data_code_availability_{vlab(10)}.md")
    b = rt(MS / "data_code_availability.md")
    E5b = "Etapa 7c.5b: pontas soltas (referências, auditorias, denominador do índice)"
    E6 = "Etapa 7c.6: auditoria independente 7c.5/7c.5b, RECORD e rastreabilidade"

    def nz(t):
        return norm_ver(t).replace(E5b, "ETAPA").replace(E6, "ETAPA").replace('"Etapa 7c.5b"', '"ETAPA_ID"').replace(
            '"Etapa 7c.6"', '"ETAPA_ID"').replace("Etapa 7c.5b)", "ETAPA_ID)").replace("Etapa 7c.6)", "ETAPA_ID)")

    la, lb = a.splitlines(), b.splitlines()
    linhas_dif = [i + 1 for i, (x, y) in enumerate(zip(la, lb)) if x != y]
    reg("G2.07 data_code_availability.md igual ao da v10, exceto rótulo de versão e nome do commit de referência", nz(a) == nz(b) and len(la) == len(lb),
        f"linhas diferentes antes da normalização: {linhas_dif}")
    a = rt(base(10) / f"legendas_figuras_{vlab(10)}.md")
    b = rt(MS / "legendas_figuras.md")
    reg("G2.08 legendas_figuras.md igual ao da v10, exceto rótulos de versão (extra)", norm_ver(a) == norm_ver(b), "")
    # integridade do arquivo v10: _arquivo_v10 = o que está no commit 8314417
    ruins, n = [], 0
    mapa = {f"data_code_availability_{vlab(10)}.md": "outputs/manuscrito/data_code_availability.md",
            f"legendas_figuras_{vlab(10)}.md": "outputs/manuscrito/legendas_figuras.md",
            f"MANIFEST_{vlab(10)}.md": "outputs/manuscrito/MANIFEST.md"}
    for p in sorted(base(10).rglob("*")):
        if p.is_dir() or p.name.startswith("._") or PROIBIDO.search(str(p)):
            continue
        relp = p.relative_to(base(10))
        if str(relp) in mapa:
            g = mapa[str(relp)]
        elif relp.parts[0] == "Submissao":
            g = "Submissao/" + "/".join(relp.parts[1:])
        else:
            g = "outputs/manuscrito/" + str(relp)
        n += 1
        if git_show(HEAD_ESPERADO, g) != rb(p):
            ruins.append(str(relp))
    reg("G2.09 _arquivo_v10 é cópia byte a byte do pacote v10 versionado em 8314417 (extra)", not ruins, f"{n} arquivos; diferentes: {ruins}")
    # MANIFEST v11: o MD5 (12 primeiros) de cada arquivo listado confere com o arquivo atual (checa_7b_* não é lido)
    man = rt(MS / "MANIFEST.md").splitlines()
    pref = {"manuscrito/tabelas": MS / "tabelas", "manuscrito/figuras": MS / "figuras", "manuscrito/suplementar": MS / "suplementar",
            "manuscrito": MS, "Submissao": SUB}
    ruins, n, pulados = [], 0, 0
    for l in man:
        m = re.match(r"\| (manuscrito(?:/tabelas|/figuras|/suplementar)?|Submissao)/([^ |]+) \| [^|]* \| [^|]* \| ([0-9a-f]{12}) \|$", l)
        if not m:
            continue
        p = pref[m.group(1)] / m.group(2)
        if PROIBIDO.search(str(p)):
            pulados += 1
            continue
        n += 1
        if not p.exists() or md5b(rb(p))[:12] != m.group(3):
            ruins.append(f"{m.group(1)}/{m.group(2)}")
    reg("G2.10 MANIFEST.md (v11): MD5 de cada arquivo listado confere com o arquivo no disco (extra)", n > 0 and not ruins,
        f"{n} arquivos conferidos ({pulados} checa_7b_* não lidos por regra de independência); divergentes: {ruins}")


# ================================================================ G3. RECORD e atribuição
def bloco_G3():
    alvo = ["docs/referencias/RECORD_checklist_acesso20261009.docx", "docs/referencias/ATRIBUICAO.txt"]
    for k, a in enumerate(alvo):
        st = git("ls-files", "-s", "--", a).split()
        wt = git("hash-object", "--", a).strip()
        head = git("ls-tree", "HEAD", "--", a).split()
        reg(f"G3.0{k + 1} {Path(a).name} está no índice do git e igual ao working tree", bool(st) and st[1] == wt,
            f"índice: {st[1] if st else '—'}; working tree: {wt}; no HEAD: {'sim' if head else 'não (entra no commit da 7c.6)'}")
    b = rb(PROJ / alvo[0])
    m = md5b(b)
    reg("G3.03 MD5 do RECORD docx = d50bd10feb3c20398ccce6f3c27b7777", m == "d50bd10feb3c20398ccce6f3c27b7777", f"MD5 {m}; {len(b):,} bytes")
    t = rt(PROJ / alvo[1])
    tn = norm_ws(t)
    obra = ["Benchimol EI", "PLoS Med. 2015;12(10):e1001885", "doi:10.1371/journal.pmed.1001885"]
    reg("G3.04 ATRIBUICAO.txt cita a obra (Benchimol et al., PLoS Med 2015;12(10):e1001885, doi)", all(o in tn for o in obra),
        f"faltando: {[o for o in obra if o not in tn]}")
    lic = ["CC BY", "creativecommons.org/licenses/by/4.0"]
    reg("G3.05 ATRIBUICAO.txt traz a licença CC BY 4.0", all(o in tn for o in lic),
        f"faltando: {[o for o in lic if o not in tn]}; a string literal 'CC BY 4.0' {'aparece' if 'CC BY 4.0' in tn else 'não aparece'} "
        f"(a versão 4.0 vem da URL)")
    urls = ["https://www.record-statement.org/checklist.php", "https://www.record-statement.org/Files/checklist/RECORD%20Checklist.docx"]
    reg("G3.06 ATRIBUICAO.txt traz as URLs da página e do arquivo", all(u in tn for u in urls), f"faltando: {[u for u in urls if u not in tn]}")
    d = docx.Document(io.BytesIO(b))
    tx = [p.text for p in d.paragraphs] + [c.text for tb_ in d.tables for r in tb_.rows for c in r.cells]
    frase = [x for x in tx if "Creative Commons Attribution (CC BY)" in x]
    reg("G3.07 o próprio docx traz a frase de licença CC BY", bool(frase), f"{len(set(frase))} parágrafo(s): {sorted(set(frase))}")
    # rede
    try:
        with tempfile.TemporaryDirectory() as tmp:
            H = {"User-Agent": "curl/8.7.1", "Accept": "*/*"}       # o servidor devolve 406 para o User-Agent padrão do urllib
            req = urllib.request.Request(urls[0], headers=H)
            html = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", errors="replace")
            texto = norm_ws(re.sub(r"<[^>]+>", " ", html))
            links = re.findall(r'href="([^"]*creativecommons[^"]*)"', html)
            okp = "Creative Common Attribution (CC BY) license" in texto or "Creative Commons Attribution (CC BY)" in texto
            reg("G3.08 site do RECORD (checklist.php): checklist sob CC BY, com link para a licença 4.0", okp and any("by/4.0" in x for x in links),
                f"frase {'encontrada' if okp else 'não encontrada'}; links: {links}")
            req = urllib.request.Request(urls[1], headers=H)
            bb = urllib.request.urlopen(req, timeout=60).read()
            Path(tmp, "RECORD Checklist.docx").write_bytes(bb)
            mm = md5b(Path(tmp, "RECORD Checklist.docx").read_bytes())
            reg("G3.09 MD5 do docx baixado do site = MD5 do arquivo local", mm == m, f"baixado: {mm} ({len(bb):,} bytes) em diretório temporário fora do projeto")
    except Exception as e:  # sem rede
        reg("G3.08 site do RECORD (checklist.php)", False, f"não verificável: {type(e).__name__}: {e}")
        reg("G3.09 MD5 do docx baixado do site", False, f"não verificável: {type(e).__name__}: {e}")


# ================================================================ G4. geradores de RESUMO
RESUMOS = ["etapa7b_05_resumo.py", "etapa7b1_03_resumo.py", "etapa7b2_02_resumo.py", "etapa7b3_02_resumo.py", "etapa7c1_02_resumo.py",
           "etapa7c2_02_resumo.py", "etapa7c3_01_resumo.py", "etapa7c4_01_resumo.py", "etapa7c5_01_resumo.py", "etapa7c5b_01_resumo.py"]


def bloco_G4():
    for k, nm in enumerate(RESUMOS, 1):
        novo = SCR / "resumos" / nm
        antigo = git_show(HEAD_ESPERADO, f"scripts/{nm}")
        ok = novo.exists() and rb(novo) == antigo
        reg(f"G4.{k:02d} {nm}: scripts/resumos/ = git show 8314417:scripts/ (byte a byte)", ok,
            f"{len(antigo):,} bytes no commit; {'existe' if novo.exists() else 'NÃO existe'} em scripts/resumos; MD5 {md5b(antigo)}")
    sobra_fs = [nm for nm in RESUMOS if (SCR / nm).exists()]
    sobra_idx = [nm for nm in RESUMOS if git("ls-files", "--", f"scripts/{nm}").strip()]
    reg("G4.11 nenhum dos 10 ficou em scripts/ (disco e índice)", not sobra_fs and not sobra_idx, f"no disco: {sobra_fs}; no índice: {sobra_idx}")
    idx_ok = []
    for nm in RESUMOS:
        st = git("ls-files", "-s", "--", f"scripts/resumos/{nm}").split()
        hd = git("ls-tree", HEAD_ESPERADO, "--", f"scripts/{nm}").split()
        idx_ok.append(bool(st) and bool(hd) and st[1] == hd[2])
    st = git("diff", "--cached", "-M", "--name-status", "HEAD", "--", "scripts/").splitlines()
    ren = [l for l in st if l.startswith("R") and "resumo" in l]
    reg("G4.12 no índice, os 10 aparecem como renomeação sem mudança de conteúdo (R100) (extra)",
        all(idx_ok) and len(ren) == 10 and all(l.startswith("R100") for l in ren), f"blobs iguais ao HEAD: {sum(idx_ok)}/10; renomeações: {len(ren)}")
    soltos = sorted(p.name for p in SCR.glob("*resumo*.py") if not p.name.startswith("._"))
    reg("G4.13 nenhum *resumo*.py solto em scripts/ (extra)", not soltos, f"{soltos}")
    novos = sorted(p.name for p in (SCR / "resumos").iterdir() if not p.name.startswith("._") and p.name not in RESUMOS)
    rastreados = [x for x in novos if git("ls-files", "--", f"scripts/resumos/{x}").strip()]
    reg("G4.14 (registro) outros arquivos em scripts/resumos/", True, f"{novos}; no índice: {rastreados}")


# ================================================================ integridade do arquivo v8 (apoio ao bloco A)
def integ_v8():
    c8 = git("log", "--diff-filter=A", "--format=%h", "--", f"outputs/manuscrito/numeros_chave_v8_{STAMP}.json").split()[-1]
    mapa = {f"data_code_availability_{vlab(8)}.md": "outputs/manuscrito/data_code_availability.md",
            f"legendas_figuras_{vlab(8)}.md": "outputs/manuscrito/legendas_figuras.md",
            f"MANIFEST_{vlab(8)}.md": "outputs/manuscrito/MANIFEST.md"}
    ruins, n = [], 0
    for p in sorted(base(8).rglob("*")):
        if p.is_dir() or p.name.startswith("._") or PROIBIDO.search(str(p)):
            continue
        relp = p.relative_to(base(8))
        g = mapa.get(str(relp)) or ("Submissao/" + "/".join(relp.parts[1:]) if relp.parts[0] == "Submissao" else "outputs/manuscrito/" + str(relp))
        n += 1
        if git_show(c8, g) != rb(p):
            ruins.append(str(relp))
    c10 = HEAD_ESPERADO
    reg("A.19 _arquivo_v8 é cópia byte a byte do pacote v8 versionado no commit da 7c.4 (extra)", not ruins,
        f"commit {c8}; {n} arquivos; diferentes: {ruins}")


def main():
    OUT.mkdir(exist_ok=True)
    print("HEAD:", git("rev-parse", "--short", "HEAD").strip())
    bloco_A()
    integ_v8()
    bloco_B()
    cinfo = bloco_C()
    bloco_D()
    econt = bloco_E()
    finfo = bloco_F()
    g1 = bloco_G1()
    bloco_G2()
    bloco_G3()
    bloco_G4()
    R.sort(key=lambda x: (x[0].split()[0][0], [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", x[0].split()[0])]))
    with open(OUT / f"comparacao_7c6_v1_{STAMP}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["verificacao", "ok", "detalhe"])
        for nome, ok, det in R:
            w.writerow([nome, "True" if ok else "False", det])
    n_ok = sum(1 for _, ok, _ in R if ok)
    print(f"\n{len(R)} verificações, {n_ok} OK, {len(R) - n_ok} falhas")
    for nome, ok, det in R:
        if not ok:
            print("FALHA:", nome, "—", det)
    print("\nC (linhas):")
    for k, v in cinfo.items():
        for i, t in v:
            print(f"  {k}: L{i}: {t.strip()}")
    print("\nE (._* por pasta):")
    for top, c in econt.items():
        for pasta, n in sorted(c.items()):
            print(f"  {pasta}: {n}")
    print("\nG1 distribuição (auditor):", {f"{c or '(vazio)'}[v{g1['ordem'].get(c, '?')}]": n for c, n in g1["dist"].items()}, "vazios:", g1["vaz"])
    print("G1 script de origem:", dict(g1["alt"]), "coincide:", g1["mesmo_commit"])


if __name__ == "__main__":
    main()
