"""
7d Autoauditoria da Etapa 7d (montagem da Submissao, pacote v15), com código próprio: não importa etapa7b_lib, o checa nem o etapa7d_02.
Nenhuma análise nova; nenhum número muda.
  A  git e árvore: HEAD, refs, remoto, tag; o que entra no commit (sem microdados, sem ._*, com manuscrito/ e a v14 arquivada);
  P  pacote v14 (arquivado) × v15: números-chave, CSVs, xlsx (S3b), TIFF em RGB (mesmos pixels), legendas, disponibilidade, MANIFEST;
  S  Submissao/: lista final, origem de cada arquivo (MD5), cabeçalho de cada Online Resource, ordem das abas do ESM_4;
  M  Manuscript montado: texto dos autores intacto, tabelas = CSV (linha a linha), notas = rodapé do pacote (sem "Sources:"), figuras =
     PNG do pacote byte a byte, seções paisagem nas Tabelas 3 e 4; ESM_3 só com a URL; Title_Page e Cover_Letter intactos;
  L  checklist (OR1): linhas recalculadas aqui por outro método (search_for do pymupdf + número de linha mais próximo) para 10 itens;
  R  renumeração: nenhum script do pacote lê Submissao/ESM_1.xlsx nem gera ESM_4.pdf; rótulos de OR nos scripts.
Grava outputs/manuscrito/audita_7d_v1_20261115.csv. Rodar da raiz: python3 scripts/etapa7d_03_audita.py
"""
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True
import docx
import openpyxl
import pandas as pd
import pymupdf
from PIL import Image

PROJ = Path(__file__).resolve().parents[1]
MS, SUB, MAN = PROJ / "outputs" / "manuscrito", PROJ / "Submissao", PROJ / "manuscrito"
A14, MONT = MS / "_arquivo_v14", MS / "montagem"
V14, V15, BASE = "v14_20261026", "v15_20261115", "a3859de"
TITULO = "Etapa 7d: montagem da Submissao (pacote v15)"
SAIDA = MS / "audita_7d_v1_20261115.csv"
R = []
md5 = lambda p: hashlib.md5(Path(p).read_bytes()).hexdigest()


def ok(vid, desc, cond, det=""):
    R.append(dict(verificacao=f"{vid} {desc}", ok=bool(cond), detalhe=str(det)[:500]))


def git(*a):
    return subprocess.run(["git", "-C", str(PROJ), *a], capture_output=True, text=True).stdout


# ======================= A. git e árvore
h = git("rev-parse", "--short", "HEAD").strip()
pre = h == BASE
pos = git("rev-parse", "--short", "HEAD^").strip() == BASE and git("log", "-1", "--format=%s").strip() == TITULO
ok("A1", "HEAD = a3859de (antes do commit) ou um commit só, com o título da etapa, sobre a3859de; só refs/heads/main; sem remoto e sem tag",
   (pre or pos) and git("for-each-ref", "--format=%(refname)").split() == ["refs/heads/main"] and not git("remote").split() and not git("tag").split(),
   f"HEAD {h}")
if pre:
    vai = [l[3:] for l in git("status", "--porcelain", "--untracked-files=all").splitlines()]
    vai = [x.split(" -> ")[-1] for x in vai if not x.startswith("docs/referencias/")]
else:
    vai = git("show", "--name-only", "--format=", "HEAD").split()
ok("A2", "no que vai para o commit: nada de data/, .parquet, .dbc, .dbf, .csv.gz, ._*, ~$, .DS_Store; nada de outputs/logs nem docs/referencias "
   "não versionados", not [x for x in vai if re.search(r"(^data/|\.parquet$|\.dbc$|\.dbf$|\.csv\.gz$|/\._|^\._|~\$|\.DS_Store$|^outputs/logs/|^docs/referencias/)", x)],
   [x for x in vai if re.search(r"(^data/|\.parquet$|\.dbc$|/\._|~\$|^outputs/logs/|^docs/referencias/)", x)][:5])
ok("A3", "manuscrito/ com os 4 .docx entra no commit; a v14 arquivada e a v15 também",
   {f"manuscrito/{f}" for f in ("Manuscript.docx", "Title_Page.docx", "Cover_Letter.docx", "ESM_3_Supplementary_Methods.docx")} <= set(vai)
   and any(x.startswith("outputs/manuscrito/_arquivo_v14/") for x in vai) and f"outputs/manuscrito/numeros_chave_{V15}.json" in vai, len(vai))
import os
D = Path(os.environ.get("PTB_DRIVE_SUBMISSAO", "/nonexistent"))      # 9a: pasta Submissao do Drive (local, por variável de ambiente)
if D.exists():
    ok("A4", "manuscrito/*.docx = as versões da pasta Submissao do Drive (Manuscript, Title_Page e ESM_3 de 15/11 12:47; Cover_Letter)",
       all(md5(MAN / f) == md5(D / f) for f in ("Manuscript.docx", "Title_Page.docx", "Cover_Letter.docx", "ESM_3_Supplementary_Methods.docx")))

# ======================= P. pacote v14 × v15
J14 = json.load(open(A14 / f"numeros_chave_{V14}.json"))
J15 = json.load(open(MS / f"numeros_chave_{V15}.json"))
F = ("id", "valor_formatado", "valor_bruto", "descricao", "filtro", "arquivo", "script")
ok("P1", "números-chave: mesmos 255 ids, na mesma ordem, com valores, descrições e origens idênticos",
   len(J15) == 255 and [{k: i[k] for k in F} for i in J14] == [{k: i[k] for k in F} for i in J15])
mud = {i["id"]: (i["commit_registro"], i["commit_analise"]) for i, j in zip(J15, J14)
       if (i["commit_registro"], i["commit_analise"]) != (j["commit_registro"], j["commit_analise"])}
ok("P2", "campos de commit: só os 6 Wald de 6 gl mudam (registro = 8b a3859de; análise = Etapa 8 cdddf8f)",
   set(mud) == {f"Wald6_{s}_{d}" for s in ("aps", "indice_2015_2021") for d in ("ptb", "pig", "ptb_ind")} and set(mud.values()) == {("a3859de", "cdddf8f")}, mud)
c14 = {p.name.replace(V14, "X"): p for p in list((A14 / "tabelas").glob("*.csv")) + list((A14 / "suplementar").glob("*.csv")) if not p.name.startswith("._")}
c15 = {p.name.replace(V15, "X"): p for p in list((MS / "tabelas").glob("*.csv")) + list((MS / "suplementar").glob("*.csv")) if not p.name.startswith("._")}
ren = {"tab03b_terciles_region_X.csv": "S3b_terciles_region_X.csv"}
ok("P3", "CSVs da v15 = os da v14 byte a byte; a tab03b virou S3b (mesmos bytes); nenhum a mais ou a menos",
   sorted(ren.get(k, k) for k in c14) == sorted(c15) and all(c14[k].read_bytes() == c15[ren.get(k, k)].read_bytes() for k in c14), len(c15))
wb = openpyxl.load_workbook(MS / "suplementar" / f"ESM_4_tables_S1_S6_{V15}.xlsx", read_only=True)
ok("P4", "ESM_4 (pacote): abas S1, S1b, S2, S2b, S3, S3b, S4, S4b, S5, S5c, S5d, S6, sem S5b; título 'Table S3b.'",
   [s.split("_")[0] for s in wb.sheetnames] == ["S1", "S1b", "S2", "S2b", "S3", "S3b", "S4", "S4b", "S5", "S5c", "S5d", "S6"]
   and str(next(wb["S3b_terciles_region"].iter_rows(values_only=True))[0]).startswith("Table S3b. Access tertiles by macroregion"), wb.sheetnames)
wt = openpyxl.load_workbook(MS / "tabelas" / f"tabelas_principais_{V15}.xlsx", read_only=True).sheetnames
ok("P5", "tabelas principais (xlsx): só as Tabelas 1–4", wt == ["tab01_characteristics", "tab02_models_m1m3", "tab03_knol_tercile", "tab04_sensitivity"], wt)
tifs = sorted((MS / "figuras").glob(f"*_{V15}.tif")) + sorted((MS / "suplementar").glob(f"*_{V15}.tif"))
tifs = [t for t in tifs if not t.name.startswith("._")]
def mesmo_rgb(t):
    a = Image.open((A14 / t.parent.name / t.name.replace(V15, V14)))
    b = Image.open(t)
    return b.mode == "RGB" and a.mode == "RGBA" and a.split()[3].getextrema() == (255, 255) and a.convert("RGB").tobytes() == b.tobytes() \
        and a.info["dpi"] == b.info["dpi"] and b.info.get("compression") == "tiff_lzw" and a.size == b.size
ok("P6", "5 TIFF (Figs. 1–4 e S9) em RGB, sem alfa, com os mesmos valores RGB, tamanho, dpi e LZW da v14", len(tifs) == 5 and all(mesmo_rgb(t) for t in tifs),
   [(t.name, Image.open(t).mode, Image.open(t).info.get("dpi")) for t in tifs])
l14 = (A14 / f"legendas_figuras_{V14}.md").read_text()
l15 = (MS / "legendas_figuras.md").read_text()
ok("P7", "legendas do pacote: só o rótulo de versão e 'Online Resource 4 (Fig. S9)' → 'Online Resource 5 (Fig. S9)'",
   l14.replace(V14, V15).replace("Online Resource 4 (Fig. S9)", "Online Resource 5 (Fig. S9)") == l15)
man = (MS / "MANIFEST.md").read_text()
ok("P8", "MANIFEST: v15 no histórico, correspondência OR1–OR5 com ESM_1.pdf, ESM_2.pdf, ESM_3.pdf, ESM_4.xlsx e ESM_5.pdf; S3b listada; título do commit",
   all(x in man for x in ["v15 = v14", "Online Resource 1: checklist", "| ESM_1.pdf |", "| ESM_3.pdf |", "ESM_4.xlsx (S3b_terciles_region)", "| ESM_5.pdf |",
                          f"'{TITULO}'"]) and "ESM_1.xlsx" not in man and "| ESM_4.pdf |" not in man)
dca = (MS / "data_code_availability.md").read_text()
ok("P9", "disponibilidade: referência ao commit da 7d (grep ancorado '^Etapa 7d:')", f'"{TITULO}"' in dca and '`git log --grep "^Etapa 7d:"`' in dca)
ck = pd.read_csv(MS / f"checa_7b_{V15}.csv")
ok("P10", "checa da v15: todas as verificações OK, com o bloco 9k da Etapa 7d", ck.ok.all() and ck.verificacao.str.startswith("7d ").sum() >= 15,
   f"{int(ck.ok.sum())}/{len(ck)}; 9k {int(ck.verificacao.str.startswith('7d ').sum())}")

# ======================= S. Submissao/
FINAL = ["Cover_Letter.docx", "ESM_1.pdf", "ESM_2.pdf", "ESM_3.pdf", "ESM_4.xlsx", "ESM_5.pdf", "Fig1.tif", "Fig2.tif", "Fig3.tif", "Fig4.tif",
         "Manuscript.docx", "Title_Page.docx"]
tudo = sorted(x.name for x in SUB.iterdir())
ok("S1", "Submissao/ = exatamente os 12 arquivos da lista final; nenhum ._*, ~$ ou .DS_Store", tudo == FINAL, tudo)
ORIG = {"ESM_1.pdf": MONT / f"ESM_1_strobe_record_located_{V15}.pdf", "ESM_2.pdf": MS / "suplementar" / f"S7_variables_codes_{V15}.pdf",
        "ESM_3.pdf": MONT / f"ESM_3_supplementary_methods_{V15}.pdf", "ESM_4.xlsx": MS / "suplementar" / f"ESM_4_tables_S1_S6_{V15}.xlsx",
        "Manuscript.docx": MONT / f"Manuscript_{V15}.docx", "Title_Page.docx": MAN / "Title_Page.docx", "Cover_Letter.docx": MAN / "Cover_Letter.docx",
        "Fig1.tif": MS / "figuras" / f"fig01_flowchart_{V15}.tif", "Fig2.tif": MS / "figuras" / f"fig02_pr_race_m1m3_{V15}.tif",
        "Fig3.tif": MS / "figuras" / f"fig03_rd_race_tercile_{V15}.tif", "Fig4.tif": MS / "figuras" / f"fig04_dating_{V15}.tif"}
ok("S2", "cada arquivo da Submissao/ = a sua origem byte a byte (pacote, montagem ou manuscrito/)", all(md5(SUB / k) == md5(v) for k, v in ORIG.items()),
   [k for k, v in ORIG.items() if md5(SUB / k) != md5(v)])
tpdf = lambda f: " ".join(pymupdf.open(f)[0].get_text().split())
cab = {f: tpdf(SUB / f)[:80] for f in ("ESM_1.pdf", "ESM_2.pdf", "ESM_3.pdf", "ESM_5.pdf")}
ok("S3", "cabeçalho de cada PDF: ESM_1 = Online Resource 1 (STROBE + RECORD), ESM_2 = OR2, ESM_3 = OR3 (Supplementary Methods), ESM_5 = OR5 (Fig. S9)",
   "Online Resource 1. STROBE and RECORD checklist" in cab["ESM_1.pdf"] and "Online Resource 2" in cab["ESM_2.pdf"]
   and "Online Resource 3" in cab["ESM_3.pdf"] and "Supplementary Methods" in cab["ESM_3.pdf"] and "Online Resource 5 (Fig. S9)" in cab["ESM_5.pdf"], cab)
txt5 = " ".join(pymupdf.open(SUB / "ESM_5.pdf")[0].get_text().split())
txt4 = " ".join(pymupdf.open(A14 / "Submissao" / "ESM_4.pdf")[0].get_text().split())
ok("S4", "ESM_5.pdf = o ESM_4.pdf da v14 com 'Online Resource 5'; uma imagem", txt5 == txt4.replace("Online Resource 4", "Online Resource 5")
   and len(pymupdf.open(SUB / "ESM_5.pdf")[0].get_images()) == 1)
ok("S5", "Fig1 a 1,200 dpi e Figs. 2–4 a 600 dpi; 174 mm de largura; RGB",
   all(Image.open(SUB / f"Fig{k}.tif").mode == "RGB" and round(Image.open(SUB / f"Fig{k}.tif").info["dpi"][0]) == (1200 if k == 1 else 600)
       and abs(Image.open(SUB / f"Fig{k}.tif").size[0] / Image.open(SUB / f"Fig{k}.tif").info["dpi"][0] * 25.4 - 174) < 0.5 for k in range(1, 5)))

# ======================= M. manuscrito montado
orig, mont = docx.Document(MAN / "Manuscript.docx"), docx.Document(ORIG["Manuscript.docx"])
MARC = "[insert from package v10]"
to = [re.sub(r"\s*\[insert from package v10\]", "", p.text) for p in orig.paragraphs]
tm = [p.text for p in mont.paragraphs]
it = iter(tm)
ok("M1", "texto dos autores: os 134 parágrafos do original, na ordem, idênticos (só os 4 marcadores saem); os novos são notas das tabelas e "
   "parágrafos de figura", all(any(x == y for y in it) for x in to) and sum(MARC in p.text for p in orig.paragraphs) == 4, f"{len(to)} → {len(tm)}")
novos = [t for t in tm if t not in set(to)]
ok("M2", "parágrafos novos = só notas de tabela (gerais, abreviações, letras) e parágrafos vazios das figuras",
   all(t == "" or t.startswith(("Brown (parda)", "SD,", "CI,", "CE,")) or re.match(r"^[a-g] ", t) for t in novos), [t[:40] for t in novos if t][:20])
def celtxt(c):
    return "".join(r.text for p in c.paragraphs for r in p.runs if not r.font.superscript).strip()
def linhas_tab(t):
    out = []
    for r in t.rows:
        vis, lin = set(), []
        for c in r.cells:
            if id(c._tc) in vis:
                continue
            vis.add(id(c._tc))
            lin.append(celtxt(c))
        out.append(lin)
    return out
okt = []
for t, n in zip(mont.tables, ["tab01_characteristics", "tab02_models_m1m3", "tab03_knol_tercile", "tab04_sensitivity"]):
    df = pd.read_csv(MS / "tabelas" / f"{n}_{V15}.csv", dtype=str).fillna("")
    nh = 2 if n == "tab04_sensitivity" else 1
    lt = linhas_tab(t)[nh:]
    esp = []
    for _, r in df.iterrows():
        v = [x.strip() for x in r]
        esp.append([v[0]] if all(x == "" for x in v[1:]) and not r.iloc[0].startswith("  ") else v)
    okt.append(lt == esp)
ok("M3", "tabelas 1–4 no docx: cada linha = a linha do CSV do pacote (rótulo + valores; linhas só de rótulo mescladas)", okt == [True] * 4 and len(mont.tables) == 4, okt)
# notas = rodapé do pacote sem "Sources:"
xl = openpyxl.load_workbook(MS / "tabelas" / f"tabelas_principais_{V15}.xlsx", read_only=True)
okn = []
for k, n in enumerate(["tab01_characteristics", "tab02_models_m1m3", "tab03_knol_tercile", "tab04_sensitivity"]):
    rod = [c for r in xl[n].iter_rows(values_only=True) for c in r if c is not None][-1]
    corpo = rod[:rod.index(" Sources: ")]
    tel = mont.tables[k]._tbl
    notas, el = [], tel.getnext()
    while el is not None and el.tag.endswith("}p"):
        t_ = "".join(x.text or "" for x in el.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"))
        if not t_ or re.match(r"^(Table \d|Figure Legends)", t_):
            break
        notas.append(t_)
        el = el.getnext()
    junto = " ".join(notas)
    frases = [f.strip() for f in re.split(r"(?<=[.;])\s+(?=[A-Z0-9'(Δ])", corpo) if f.strip()]
    falta = [f for f in frases if f.rstrip(";") not in junto]
    okn.append((not falta and "Sources:" not in junto, falta[:2]))
ok("M4", "notas de cada tabela: toda frase do rodapé do pacote está nas notas abaixo da tabela; a linha interna 'Sources:' não vai",
   all(x for x, _ in okn), okn)
z = zipfile.ZipFile(ORIG["Manuscript.docx"])
media = sorted(n for n in z.namelist() if n.startswith("word/media/"))
pngs = [MS / "figuras" / f"fig0{k}_{n}_{V15}.png" for k, n in enumerate(["flowchart", "pr_race_m1m3", "rd_race_tercile", "dating"], start=1)]
ok("M5", "as 4 imagens do docx = os 4 PNG do pacote byte a byte", sorted(hashlib.md5(z.read(n)).hexdigest() for n in media) == sorted(md5(p) for p in pngs),
   media)
pdf = pymupdf.open(MONT / f"Manuscript_{V15}.pdf")
paisagem = [pg.number + 1 for pg in pdf if pg.rect.width > pg.rect.height]
t3p = [pg.number + 1 for pg in pdf if "Table 3 Effect modification" in pg.get_text()]
t4p = [pg.number + 1 for pg in pdf if "Table 4 Gestational age dating" in pg.get_text()]
ok("M6", "PDF do Word: as páginas em paisagem são exatamente as das Tabelas 3 e 4 (da 1ª página da Tabela 3 até a última antes de 'Figure Legends')",
   paisagem and paisagem[0] == t3p[-1] and t4p[-1] in paisagem and all(b - a == 1 for a, b in zip(paisagem, paisagem[1:]))
   and "Figure Legends" in pdf[paisagem[-1]].get_text(), f"paisagem {paisagem}; T3 {t3p}; T4 {t4p}")
e3o = [p.text for p in docx.Document(MAN / "ESM_3_Supplementary_Methods.docx").paragraphs]
e3m = [p.text for p in docx.Document(MONT / f"ESM_3_supplementary_methods_{V15}.docx").paragraphs]
dif = [(a, b) for a, b in zip(e3o, e3m) if a != b]
acc = (PROJ / "docs/referencias/aps_cobertura_ab/ACESSO.txt").read_text().splitlines()
ok("M7", "ESM_3: um único parágrafo difere, só pela troca do marcador pela URL do relatório que está na 2ª linha do ACESSO.txt",
   len(e3o) == len(e3m) and len(dif) == 1 and dif[0][0].replace("[URL from docs/referencias/aps_cobertura_ab/ACESSO.txt]",
                                                                 "https://relatorioaps.saude.gov.br/cobertura/ab") == dif[0][1]
   and "https://relatorioaps.saude.gov.br/cobertura/ab" in acc[1])
ok("M8", "Title_Page e Cover_Letter de Submissao/ = manuscrito/ byte a byte (texto dos autores intocado)",
   md5(SUB / "Title_Page.docx") == md5(MAN / "Title_Page.docx") and md5(SUB / "Cover_Letter.docx") == md5(MAN / "Cover_Letter.docx"))

# ======================= L. checklist: 10 itens por outro método (search_for + número de linha mais próximo)
NUM = [(pg.number + 1, (s["bbox"][1] + s["bbox"][3]) / 2, int(s["text"])) for pg in pdf for b in pg.get_text("dict")["blocks"] for l in b.get("lines", [])
       for s in l["spans"] if s["text"].strip().isdigit() and s["bbox"][2] < 68]
def linha(frase):
    for pg in pdf:
        r = pg.search_for(frase)
        if r:
            y = (r[0].y0 + r[0].y1) / 2
            return pg.number + 1, min(((abs(yy - y), n) for p, yy, n in NUM if p == pg.number + 1))[1]
    return None
chk = pd.read_csv(MONT / f"ESM_1_strobe_record_located_{V15}.csv", dtype=str).fillna("")
loc = dict(zip(chk.Topic.where(chk.Topic != "", chk.Section), chk["Page/location in manuscript"]))
AMOSTRA = {"Objectives": "To our knowledge, no national study", "Study Design": "We conducted a population-based cross-sectional",
           "Study size": "we sequentially excluded those", "Statistical methods": "We estimated prevalence ratios (PRs) with",
           "Linkage": "We also used fetal death records", "Key results": "In 25.8 million births in Brazil",
           "Funding": "This research did not receive", "Accessibility of protocol, raw data, and programming code": "SINASC and SIM microdata are publicly",
           "Outcome data": "The prevalence of preterm birth was 11.47%", "Main results": "In the primary model, Indigenous mothers"}
res = {}
for top, frase in AMOSTRA.items():
    pl = linha(frase)
    m = re.search(r"pp?\. (\d+)(?:–\d+)?, lines (\d+)–", loc.get(top, ""))
    res[top] = (pl, m.groups() if m else None)
ok("L1", "checklist: página e 1ª linha de 10 itens recalculadas aqui por outro método = as da coluna de localização",
   all(pl is not None and g is not None and (str(pl[0]), str(pl[1])) == g for pl, g in res.values()), res)
ok("L2", "checklist: as 25 linhas com localização; o ESM_1.pdf traz cada localização", (chk["Page/location in manuscript"] != "").all()
   and all(x.split(";")[0][:20] in " ".join(" ".join(pg.get_text().split()) for pg in pymupdf.open(SUB / "ESM_1.pdf")) for x in chk["Page/location in manuscript"]))

# ======================= R. renumeração nos scripts
src = {f: (PROJ / "scripts" / f).read_text() for f in ["etapa7b_02_suplementar.py", "etapa7b_03_figuras.py", "etapa7b_04_submissao.py", "etapa7b_checa.py"]}
ok("R1", "scripts: nenhum lê 'Submissao/ESM_1.xlsx' nem grava ESM_4.pdf; o 04 grava ESM_5.pdf e procura a legenda 'Online Resource 5' com raise",
   'B.SUB / "ESM_1.xlsx"' not in "".join(src.values()) and '"ESM_4.pdf")' not in src["etapa7b_04_submissao.py"]
   and 'B.SUB / "ESM_5.pdf")' in src["etapa7b_04_submissao.py"] and 'startswith("**Online Resource 5")' in src["etapa7b_04_submissao.py"]
   and "raise RuntimeError(f\"legenda da Online Resource 5" in src["etapa7b_04_submissao.py"])
ok("R2", "rótulos: S8 'Online Resource 1 (S8)' no 02; S9 'Online Resource 5 (Fig. S9)' no 03; xlsx 'ESM_4_tables_S1_S6' no 02",
   "Online Resource 1 (S8)" in src["etapa7b_02_suplementar.py"] and "Online Resource 3 (S8)" not in src["etapa7b_02_suplementar.py"]
   and 'LEG.append(("Online Resource 5 (Fig. S9)"' in src["etapa7b_03_figuras.py"] and 'f"ESM_4_tables_S1_S6_{B.V}.xlsx"' in src["etapa7b_02_suplementar.py"])
ms_or = [p.text for p in mont.paragraphs if p.text.startswith("Online Resource ")]
ok("R3", "lista de ESM no fim do Manuscript: OR1 checklists, OR2 variáveis, OR3 métodos, OR4 tabelas, OR5 MAIHDA = conteúdo dos ESM_1–5",
   [x[:17] for x in ms_or] == [f"Online Resource {k}" for k in range(1, 6)] and "STROBE and RECORD" in ms_or[0] and "Variables and codes" in ms_or[1]
   and "Supplementary methods" in ms_or[2] and "Supplementary tables" in ms_or[3] and "MAIHDA" in ms_or[4])

pd.DataFrame(R).to_csv(SAIDA, index=False)
print(f"autoauditoria 7d: {sum(r['ok'] for r in R)}/{len(R)} OK")
for r in R:
    if not r["ok"]:
        print("FALHA", r["verificacao"], "|", r["detalhe"])
