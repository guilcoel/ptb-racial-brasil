"""
Auditor independente da Etapa 7c.7 — rodada 2 (verificações próprias; escritas antes de ler o código e o CSV da autoauditoria nova).
  R2.a  correções das 7 falhas da rodada 1 e das ressalvas acolhidas (descrição, grep ancorado, | escapado, LEIAME de um commit só)
  R2.b  blocos A, B, D e E refeitos no estado novo (pacote regerado às 12:24–12:26)
  R2.c  pegadas da autoauditoria nova no Forja (outputs/tables, CSVs de auditoria e logs intactos) — a revisão do código fica em
        audita_7c7_r2_revisao_v1_20261013.py, rodado depois
  R2.s  resultados do sandbox da rodada 2 (audita_7c7_r2_sandbox_v1_20261013.py → sandbox_7c7_r2_v1_20261013.json)
Não lê o CSV da autoauditoria (só o nome, o mtime e, na rodada final, o conteúdo). data/: só nomes. git: só leitura, GIT_OPTIONAL_LOCKS=0.
Grava só as linhas R2.a/R2.b/R2.c/R2.s no comparacao_7c7_v1_20261013.csv (as da rodada 1 ficam intactas; as R2 deste script são refeitas
a cada execução). Rodar: python3 audit_independente/etapa7c7/audita_7c7_r2_v1_20261013.py
"""
import ast
import difflib
import hashlib
import json
import os
import re
import subprocess
import time
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path

import docx
import openpyxl
import pandas as pd
import pymupdf
from PIL import Image

PROJ = Path("/Volumes/Forja/ptb-racial-brasil")
OUTD = PROJ / "audit_independente" / "etapa7c7"
CMP = OUTD / "comparacao_7c7_v1_20261013.csv"
MS, SUB = PROJ / "outputs" / "manuscrito", PROJ / "Submissao"
A10, A11 = MS / "_arquivo_v10", MS / "_arquivo_v11"
V10, V11, V12 = "v10_20261009", "v11_20261009", "v12_20261013"
HEAD_FULL, HEAD = "dc9328d9d652146341efdc6286462668c2a64a02", "dc9328d"
FRASE, ANTES = "Joint Wald tests were not computed for the multiple-imputation analysis.", "combined with Rubin's rules."
DESC = "in the municipality-to-health-region map used for the access index (DATASUS territorial base, December 2024)"
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
T_R2 = datetime.strptime("2026-10-13 13:32:00", "%Y-%m-%d %H:%M:%S").timestamp()       # início da rodada 2 deste auditor
R = []
MEU_PREFIXO = ("R2.a", "R2.b", "R2.c0", "R2.s")


def ok(vid, desc, cond, det=""):
    R.append(dict(verificacao=f"{vid} {desc}", ok=bool(cond), detalhe=str(det)[:1800]))
    print(f"{'OK   ' if cond else 'FALHA'} {vid} {desc[:95]} | {str(det)[:170]}", flush=True)


def git(*a):
    return subprocess.run(["git", "-C", str(PROJ), *a], capture_output=True, text=True, env=ENV, check=True).stdout


md5b = lambda b: hashlib.md5(b).hexdigest()
md5f = lambda p: md5b(Path(p).read_bytes())
hora = lambda t: datetime.fromtimestamp(t).strftime("%H:%M:%S")
st = lambda p: (PROJ / p).stat().st_mtime


def arvore_disco():
    out = []
    for raiz, dirs, fs in os.walk(PROJ):
        rel = Path(raiz).relative_to(PROJ)
        if rel == Path("."):
            dirs[:] = [d for d in dirs if d not in ("data", ".git")]
        out += [str(rel / f) if rel != Path(".") else f for f in fs]
    return sorted(out)


def hash_disco(paths):
    r = subprocess.run(["git", "-C", str(PROJ), "hash-object", "--stdin-paths"], input="\n".join(paths), capture_output=True, text=True,
                       env=ENV, check=True)
    return dict(zip(paths, r.stdout.split()))


snap = lambda: {p: md5f(PROJ / p) for p in arvore_disco() if p.startswith(("outputs/manuscrito/", "Submissao/", "scripts/", "outputs/RESUMO_ETAPA7C7"))}
SNAP0 = snap()
TCOMMIT = int(git("log", "-1", "--format=%ct", HEAD).strip())

# ======================================================================= R2.b — A (integridade) no estado novo
refs = [r for r in git("for-each-ref", "--format=%(refname) %(objectname)").split("\n") if r]
novos = [l for l in git("rev-list", "--all", "--reflog", "--format=%H %ct", "--no-commit-header").splitlines() if int(l.split()[1]) > TCOMMIT]
ok("R2.bA01", "HEAD = dc9328d; só refs/heads/main; nenhum commit novo (refs nem reflog); sem remoto, sem tag, stash vazio",
   git("rev-parse", "HEAD").strip() == HEAD_FULL and refs == [f"refs/heads/main {HEAD_FULL}"] and not novos and not git("remote").strip()
   and not git("tag", "-l").strip() and not git("stash", "list").strip(), f"refs {refs}; posteriores {novos[:2]}")
arv0 = {l.split("\t", 1)[1]: l.split()[2] for l in git("ls-tree", "-r", HEAD).splitlines()}
MOV = sorted(p for p in arv0 if p.startswith("outputs/manuscrito/") and not p.startswith("outputs/manuscrito/_arquivo_") and V11 in p)
DEST = {p: p.replace("outputs/manuscrito/", "outputs/manuscrito/_arquivo_v11/", 1) for p in MOV}
cached = [l.split("\t") for l in git("diff", "--cached", "--name-status", "-M", HEAD).splitlines()]
ok("R2.bA02", "índice: só as 38 renomeações R100 da v11 para _arquivo_v11/", len(MOV) == 38 and len(cached) == 38
   and all(x[0] == "R100" and DEST.get(x[1]) == x[2] for x in cached), dict(Counter(x[0] for x in cached)))
dif = [l.split("\t") for l in git("diff", "--no-renames", "--name-status", HEAD).splitlines()]
M_ESP = {"Submissao/ESM_1.xlsx", "Submissao/ESM_2.pdf", "Submissao/ESM_3.pdf", "Submissao/ESM_4.pdf", "outputs/manuscrito/MANIFEST.md",
         "outputs/manuscrito/data_code_availability.md", "outputs/manuscrito/legendas_figuras.md", "scripts/etapa2_03_indice_acesso.py",
         "scripts/etapa7b_lib.py", "scripts/etapa7b_01_tabelas.py", "scripts/etapa7b_02_suplementar.py", "scripts/etapa7b_04_submissao.py",
         "scripts/etapa7b_checa.py", "scripts/resumos/LEIAME.md"}
por = {s: {p for t, p in dif if t == s} for s in ("M", "D", "A")}
presentes = sorted(p for p in arv0 if (PROJ / p).exists())
hp = hash_disco(presentes)
mud = {p for p in presentes if hp[p] != arv0[p]}
ok("R2.bA03", "rastreados: M = os mesmos 14 da rodada 1 (também por git hash-object em todos os arquivos de dc9328d); D/A = 38/38",
   por["M"] == M_ESP == mud and por["D"] == set(MOV) and por["A"] == set(DEST.values()),
   f"M {len(por['M'])}; hash-object mudou {len(mud)} de {len(presentes)}; fora {sorted((por['M'] | mud) - M_ESP)}")
untr = sorted(p for p in git("ls-files", "-o", "--exclude-standard", "-z").split("\0") if p)
U_ESP = ({p.replace(V11, V12) for p in MOV}
         | {f"outputs/manuscrito/_arquivo_v11/{x}" for x in [f"MANIFEST_{V11}.md", f"data_code_availability_{V11}.md", f"legendas_figuras_{V11}.md"]
            + [f"Submissao/{y}" for y in ["ESM_1.xlsx", "ESM_2.pdf", "ESM_3.pdf", "ESM_4.pdf", "Fig1.tif", "Fig2.tif", "Fig3.tif", "Fig4.tif"]]}
         | {"outputs/manuscrito/audita_7c7_v1_20261013.csv", "scripts/etapa7c7_01_regsaude_uf.py", "scripts/etapa7c7_02_audita.py",
            "outputs/RESUMO_ETAPA7C7_v1_20261013.md", "outputs/manuscrito/_resumo7c7_texto_v1_20261013.md", "scripts/resumos/etapa7c7_01_resumo.py"})
docs_u = [p for p in untr if p.startswith("docs/referencias/")]
meus = [p for p in untr if p.startswith("audit_independente/etapa7c7/")]
padrao = re.compile(r"^[a-z0-9_]*7c7[a-z0-9_]*_v1_20261013\.(py|json|md)$")
extra = sorted(set(untr) - U_ESP - set(docs_u) - set(meus))
ok("R2.bA04", "não rastreados = os previstos (38 da v12, 11 cópias, 2 scripts, CSV da autoauditoria, RESUMO: saída, texto e gerador), "
   "93 de docs/referencias e os deste auditor (nomes no padrão *7c7*_v1_20261013.py|json|md)",
   U_ESP <= set(untr) and not extra and len(docs_u) == 93 and all(padrao.match(Path(p).name) for p in meus),
   f"faltam {sorted(U_ESP - set(untr))}; fora {extra}; deste auditor {[Path(p).name for p in meus]}")
ign = sorted(p for p in git("ls-files", "-o", "-i", "--exclude-standard", "-z", "--", "outputs", "scripts", "docs", "audit_independente",
                              "Submissao").split("\0") if p)
ign_novos = sorted(p for p in ign if st(p) > TCOMMIT and "__pycache__" not in p and not p.startswith("audit_independente/etapa7c7/"))
ok("R2.bA05", "ignorados criados/alterados depois de dc9328d (fora de data/ e desta pasta): só a tabela nova e os logs (7b, 7c7, 7c6)",
   set(ign_novos) <= {"outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv", "outputs/logs/etapa7b_20261008.log",
                      "outputs/logs/etapa7c7_20261008.log", "outputs/logs/etapa7c6_20261008.log"},
   "; ".join(f"{p} {hora(st(p))}" for p in ign_novos))
idx = {l.split("\t", 1)[1]: l.split()[1] for l in git("ls-files", "-s").splitlines()}
hd = hash_disco([DEST[p] for p in MOV])
ok("R2.bA06", "os 38 movidos: blob em dc9328d = blob no índice = disco", all(arv0[p] == idx.get(DEST[p]) == hd[DEST[p]] for p in MOV))
COP = {f"_arquivo_v11/MANIFEST_{V11}.md": "outputs/manuscrito/MANIFEST.md", f"_arquivo_v11/data_code_availability_{V11}.md":
       "outputs/manuscrito/data_code_availability.md", f"_arquivo_v11/legendas_figuras_{V11}.md": "outputs/manuscrito/legendas_figuras.md",
       **{f"_arquivo_v11/Submissao/{y}": f"Submissao/{y}" for y in ["ESM_1.xlsx", "ESM_2.pdf", "ESM_3.pdf", "ESM_4.pdf", "Fig1.tif", "Fig2.tif", "Fig3.tif", "Fig4.tif"]}}
hc = hash_disco([f"outputs/manuscrito/{k}" for k in COP])
est = lambda d, v: sorted(str(x.relative_to(d)).replace(v, "VV") for x in d.rglob("*") if x.is_file() and not x.name.startswith("._"))
ok("R2.bA07", "_arquivo_v11/: mesma estrutura da _arquivo_v10/ (49) e as 11 cópias = dc9328d, byte a byte",
   est(A10, V10) == est(A11, V11) and all(hc[f"outputs/manuscrito/{k}"] == arv0[v] for k, v in COP.items()))
lixo = [p for p in arvore_disco() if Path(p).name.startswith("._")]
ok("R2.bA08", "._*: nenhum fora de data/ (raiz incluída); o de data/processed continua (só o nome)",
   not lixo and [n for n in os.listdir(PROJ / "data/processed") if n.startswith("._")] == ["._pig_grade_intergrowth_v1_20261008.parquet"], lixo[:3] or "0")
ok("R2.bA09", "nenhum arquivo de dc9328d sumiu além das 38 origens movidas", {p for p in arv0 if p not in set(arvore_disco()) and not p.startswith("data/")} == set(MOV))

# ======================================================================= R2.b — B (pacote v11 × v12) no estado novo
n = 0
for s in ("tabelas", "suplementar"):
    for f in sorted((A11 / s).glob(f"*_{V11}.csv")):
        n += 1
        g = MS / s / f.name.replace(V11, V12)
        ok(f"R2.bB01.{n:02d}", f"CSV {s}/{f.name.replace(V11, 'vXX')}: v11 = v12 byte a byte", g.exists() and f.read_bytes() == g.read_bytes())


def celulas(f):
    return [(ws.title, {(c.row, c.column): c.value for row in ws.iter_rows() for c in row if c.value is not None}) for ws in openpyxl.load_workbook(f).worksheets]


def zip_dif(a, b):
    za, zb = zipfile.ZipFile(a), zipfile.ZipFile(b)
    return sorted(x for x in set(za.namelist()) | set(zb.namelist()) if x not in za.namelist() or x not in zb.namelist() or za.read(x) != zb.read(x))


xa, xb = celulas(A11 / "tabelas" / f"tabelas_principais_{V11}.xlsx"), celulas(MS / "tabelas" / f"tabelas_principais_{V12}.xlsx")
difx = [(t, k) for (t, ca), (_, cb) in zip(xa, xb) for k in set(ca) | set(cb) if ca.get(k) != cb.get(k)]
t4a, t4b = dict(xa)["tab04_sensitivity"][(18, 1)], dict(xb)["tab04_sensitivity"][(18, 1)]
it4 = [t for t, _ in xb].index("tab04_sensitivity") + 1
ok("R2.bB02", "xlsx tabelas principais: só a célula (18,1) da Tabela 4 muda, por inserção exata da frase; no zip só a planilha dela e core.xml",
   [t for t, _ in xa] == [t for t, _ in xb] and difx == [("tab04_sensitivity", (18, 1))] and t4b == t4a.replace(ANTES, ANTES + " " + FRASE)
   and set(zip_dif(A11 / "tabelas" / f"tabelas_principais_{V11}.xlsx", MS / "tabelas" / f"tabelas_principais_{V12}.xlsx")) == {f"xl/worksheets/sheet{it4}.xml", "docProps/core.xml"}, difx)
ea, eb = celulas(A11 / "suplementar" / f"ESM_1_tables_S1_S6_{V11}.xlsx"), celulas(MS / "suplementar" / f"ESM_1_tables_S1_S6_{V12}.xlsx")
ok("R2.bB03", "ESM_1: v11 = v12 célula a célula; Submissao/ESM_1 = ESM_1 v12 (bytes)", ea == eb
   and (SUB / "ESM_1.xlsx").read_bytes() == (MS / "suplementar" / f"ESM_1_tables_S1_S6_{V12}.xlsx").read_bytes(), f"{sum(len(c) for _, c in eb)} células")
da_, db_ = docx.Document(A11 / "tabelas" / f"tabelas_principais_{V11}.docx"), docx.Document(MS / "tabelas" / f"tabelas_principais_{V12}.docx")
xa_ = zipfile.ZipFile(A11 / "tabelas" / f"tabelas_principais_{V11}.docx").read("word/document.xml").decode()
xb_ = zipfile.ZipFile(MS / "tabelas" / f"tabelas_principais_{V12}.docx").read("word/document.xml").decode()
ap = "combined with Rubin&apos;s rules." if "Rubin&apos;s" in xa_ else ANTES
ok("R2.bB04", "docx: tabelas iguais; XML = v11 com rótulo de versão e a frase; só word/document.xml muda",
   [[c.text for r in t.rows for c in r.cells] for t in da_.tables] == [[c.text for r in t.rows for c in r.cells] for t in db_.tables]
   and xa_.replace(V11, V12).replace(ap, ap + " " + FRASE) == xb_
   and zip_dif(A11 / "tabelas" / f"tabelas_principais_{V11}.docx", MS / "tabelas" / f"tabelas_principais_{V12}.docx") == ["word/document.xml"])
txt_pdf = lambda f: [pg.get_text() for pg in pymupdf.open(f)]
render = lambda f: [md5b(pg.get_pixmap(dpi=50).samples) for pg in pymupdf.open(f)]
meta = lambda f: {k: v for k, v in pymupdf.open(f).metadata.items() if k not in ("creationDate", "modDate", "title", "creator", "producer")}
PDFS = [(A11 / "suplementar" / f"S7_variables_codes_{V11}.pdf", MS / "suplementar" / f"S7_variables_codes_{V12}.pdf"),
        (A11 / "suplementar" / f"S8_strobe_record_checklist_{V11}.pdf", MS / "suplementar" / f"S8_strobe_record_checklist_{V12}.pdf")] + \
       [(A11 / "Submissao" / f"ESM_{k}.pdf", SUB / f"ESM_{k}.pdf") for k in (2, 3, 4)]
for k, (a, b) in enumerate(PDFS, 1):
    ok(f"R2.bB05.{k}", f"PDF {b.relative_to(PROJ)} (regerado): texto e renderização (50 dpi) = v11; metadados iguais fora datas, título e Chrome",
       txt_pdf(a) == txt_pdf(b) and render(a) == render(b) and meta(a) == meta(b),
       f"{len(txt_pdf(b))} pp.; criado {pymupdf.open(b).metadata.get('creationDate')}; título {pymupdf.open(b).metadata.get('title')}")
px = lambda f: (lambda im: (im.size, im.mode, im.info.get("dpi"), im.info.get("compression"), md5b(im.tobytes())))(Image.open(f))
imgs = sorted((A11 / "figuras").iterdir()) + sorted((A11 / "suplementar").glob("S9_*"))
ok("R2.bB06", "imagens (8 figuras, S9 png/tif) e Fig1–4 de Submissao/: bytes iguais à v11 e Fig1–4 = figuras v12 (bytes)",
   all(f.read_bytes() == (MS / f.parent.name / f.name.replace(V11, V12)).read_bytes() for f in imgs)
   and all((SUB / f"Fig{k}.tif").read_bytes() == (A11 / "Submissao" / f"Fig{k}.tif").read_bytes() for k in range(1, 5))
   and all((SUB / f"Fig{k}.tif").read_bytes() == (MS / "figuras" / f"{n_}_{V12}.tif").read_bytes() for k, n_ in
           {1: "fig01_flowchart", 2: "fig02_pr_race_m1m3", 3: "fig03_rd_race_tercile", 4: "fig04_dating"}.items()), f"{len(imgs)} imagens")
ok("R2.bB07", "Submissao/: só os 8 arquivos; ESM_2/ESM_3 = S7/S8 v12 (bytes); ESM_4 com a imagem do S9 e a legenda do Online Resource 4",
   sorted(os.listdir(SUB)) == ["ESM_1.xlsx", "ESM_2.pdf", "ESM_3.pdf", "ESM_4.pdf", "Fig1.tif", "Fig2.tif", "Fig3.tif", "Fig4.tif"]
   and (SUB / "ESM_2.pdf").read_bytes() == (MS / "suplementar" / f"S7_variables_codes_{V12}.pdf").read_bytes()
   and (SUB / "ESM_3.pdf").read_bytes() == (MS / "suplementar" / f"S8_strobe_record_checklist_{V12}.pdf").read_bytes()
   and Image.open(MS / "suplementar" / f"S9_maihda_caterpillar_{V12}.png").size in [(i[2], i[3]) for i in pymupdf.open(SUB / "ESM_4.pdf")[0].get_images(full=True)]
   and " ".join([l for l in (MS / "legendas_figuras.md").read_text().split("\n\n") if l.startswith("**Online Resource 4")][0].split("**", 2)[2].split())
   in " ".join(pymupdf.open(SUB / "ESM_4.pdf")[0].get_text().split()))


def manifesto(f):
    L = f.read_text().splitlines()
    rows = {}
    for l in L:
        if l.startswith(("| manuscrito/", "| Submissao/")):
            c = re.split(r"(?<!\\)\|", l.strip())[1:-1]           # separa só nos | não escapados
            rows[c[0].strip()] = [c[1].strip(), "|".join(c[2:-1]).strip(), c[-1].strip()]   # na v11 o | da origem não era escapado
    return L, rows


L11, M11 = manifesto(A11 / f"MANIFEST_{V11}.md")
L12, M12 = manifesto(MS / "MANIFEST.md")
M11n = {k.replace(V11, V12): v for k, v in M11.items()}
SENT12 = ("; v12 = v11 com o rodapé da Tabela 4 dizendo que os testes de Wald conjuntos não foram calculados na imputação múltipla, os "
          "números-chave n_regsaude_CE e n_regsaude_DF (regiões de saúde no mapa município → região de saúde da base territorial, "
          "tab_e7c7_01_regsaude_uf) e suplementar/ sem arquivos ._* (dot_clean no 02)")
FIM12 = (" As autoauditorias das etapas (audita_*.csv, na raiz de outputs/manuscrito/) ficam fora da lista de arquivos: são gravadas depois "
         "do pacote, para conferi-lo.")
l3 = (L11[2].replace(V11, V12).replace("2026-10-09", "2026-10-13").replace("8314417", HEAD)
      .replace("'Etapa 7c.6: auditoria independente 7c.5/7c.5b, RECORD e rastreabilidade'", "'Etapa 7c.7: pacote v12 com as decisões da 7c.6b'")
      .replace("nos números-chave. Scripts em scripts/.", "nos números-chave" + SENT12 + ". Scripts em scripts/." + FIM12))
fora_tab = [i for i, (a, b) in enumerate(zip(L11, L12)) if not a.startswith("| ") and a.replace(V11, V12) != b]
ok("R2.bB08", "MANIFEST × v11: fora da tabela, só o título e o parágrafo de abertura (data, commit, nome do commit, frase da v12, nota "
   "sobre os audita_*.csv)", fora_tab == [0, 2] and L12[0] == L11[0].replace("7b–7c.6", "7b–7c.7").replace(V11, V12) and L12[2] == l3
   and len(L11) == len(L12), f"linhas que mudam {fora_tab}; {len(L11)} → {len(L12)} linhas")
MD5_ESP = {f"manuscrito/tabelas/tabelas_principais_{V12}.docx", f"manuscrito/tabelas/tabelas_principais_{V12}.xlsx",
           f"manuscrito/suplementar/ESM_1_tables_S1_S6_{V12}.xlsx", f"manuscrito/suplementar/S7_variables_codes_{V12}.pdf",
           f"manuscrito/suplementar/S8_strobe_record_checklist_{V12}.pdf", f"manuscrito/checa_7b_{V12}.csv", "manuscrito/data_code_availability.md",
           "manuscrito/legendas_figuras.md", f"manuscrito/numeros_chave_{V12}.json", f"manuscrito/numeros_chave_{V12}.md", "Submissao/ESM_1.xlsx", "Submissao/ESM_2.pdf",
           "Submissao/ESM_3.pdf", "Submissao/ESM_4.pdf"}
md5m = {k for k in M11n if k in M12 and M11n[k][-1] != M12[k][-1]}
orig_dif = {k for k in M11n if k in M12 and M11n[k][:-1] != M12[k][:-1]}
ok("R2.bB09", "MANIFEST: mesmas linhas da v11 (nenhuma audita_*); MD5 muda só nos 14 regenerados (os mesmos da rodada 1); "
   "origem/script iguais, fora o | escapado da Tabela 2",
   set(M12) == set(M11n) and not any("audita_" in k for k in M12) and md5m == MD5_ESP
   and orig_dif == {f"manuscrito/tabelas/tab02_models_m1m3_{V12}.csv"}
   and M12[f"manuscrito/tabelas/tab02_models_m1m3_{V12}.csv"][1] == M11n[f"manuscrito/tabelas/tab02_models_m1m3_{V12}.csv"][1].replace("|", "\\|"),
   f"linhas {len(M11n)} → {len(M12)}; MD5 mudou {len(md5m)}; fora do previsto {sorted(md5m ^ MD5_ESP)}; origem diferente {sorted(orig_dif)}")
abs_ = lambda k: (MS / k.split("/", 1)[1]) if k.startswith("manuscrito/") else PROJ / k
ok("R2.bB10", "MANIFEST: MD5 de cada arquivo listado = disco", all(abs_(k).exists() and md5f(abs_(k))[:12] == v[-1] for k, v in M12.items()),
   f"{len(M12)} linhas")
lista = sorted([f"manuscrito/{d}/{f.name}" for d in ("tabelas", "figuras", "suplementar") for f in (MS / d).iterdir() if f.is_file()
                and not f.name.startswith(("._", "_", "audita_"))] + [f"manuscrito/{f.name}" for f in MS.iterdir() if f.is_file()
               and not f.name.startswith(("._", "_", "audita_")) and f.name != "MANIFEST.md"] + [f"Submissao/{f.name}" for f in SUB.iterdir() if not f.name.startswith("._")])
ok("R2.bB11", "MANIFEST completo: lista tudo o que o 04 listaria hoje (com a regra nova, que tira só os audita_*.csv)",
   set(lista) == set(M12), f"não listados {sorted(set(lista) - set(M12))}; sobrando {sorted(set(M12) - set(lista))}")
d11 = (A11 / f"data_code_availability_{V11}.md").read_text()
d12 = (MS / "data_code_availability.md").read_text()
volta = (d12.replace(V12, V11).replace("Etapa 7c.7: pacote v12 com as decisões da 7c.6b", "Etapa 7c.6: auditoria independente 7c.5/7c.5b, RECORD e rastreabilidade")
         .replace('git log --grep "^Etapa 7c.7:"', 'git log --grep "Etapa 7c.6"').replace("Etapa 7c.7)", "Etapa 7c.6)"))
dl = [l for l in difflib.unified_diff(d11.splitlines(), d12.splitlines(), lineterm="", n=0) if l[:1] in "+-" and not l.startswith(("+++", "---"))]
ok("R2.bB12", "disponibilidade: v12 = v11 fora versão, etapa e commit de referência com o grep ancorado (\"^Etapa 7c.7:\"); 2 linhas mudam",
   volta == d11 and len(dl) == 4 and 'git log --grep "^Etapa 7c.7:"' in d12, " | ".join(l[:100] for l in dl))
ok("R2.bB13", "legendas: v12 = v11 fora o rótulo de versão", (MS / "legendas_figuras.md").read_text().replace(V12, V11) == (A11 / f"legendas_figuras_{V11}.md").read_text())
J11 = json.load(open(A11 / f"numeros_chave_{V11}.json"))
J12 = json.load(open(MS / f"numeros_chave_{V12}.json"))
dj = [(a["id"], c) for a, b in zip(J11, J12) for c in set(a) | set(b) if c != "commit_pacote" and a.get(c) != b.get(c)]
ok("R2.bB14", "números-chave: os 226 da v11, na mesma ordem, com todos os campos e tipos iguais fora commit_pacote (8314417 → dc9328d)",
   [i["id"] for i in J12[:226]] == [i["id"] for i in J11] and not dj and all(type(a["valor_bruto"]) is type(b["valor_bruto"]) for a, b in zip(J11, J12))
   and {i["commit_pacote"] for i in J11} == {"8314417"} and {i["commit_pacote"] for i in J12} == {HEAD}, f"v12 {len(J12)}; divergentes {dj[:3]}")
nv = {i["id"]: i for i in J12[226:]}
ok("R2.bB15", "os 2 novos: CE = 5, DF = 1 (int), descrição nova 'Health regions in {UF} in the municipality-to-health-region map used for the "
   "access index (DATASUS territorial base, December 2024)', origem, filtro e commits vazios",
   list(nv) == ["n_regsaude_CE", "n_regsaude_DF"] and [nv[k]["valor_bruto"] for k in nv] == [5, 1] and [nv[k]["valor_formatado"] for k in nv] == ["5", "1"]
   and nv["n_regsaude_CE"]["descricao"] == f"Health regions in Ceará {DESC}" and nv["n_regsaude_DF"]["descricao"] == f"Health regions in Federal District {DESC}"
   and all(nv[k]["arquivo"] == "outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv" and nv[k]["script"] == "scripts/etapa7c7_01_regsaude_uf.py"
           and nv[k]["filtro"] == f"uf={k[-2:]}" and not nv[k]["commit_registro"] and not nv[k]["commit_analise"] for k in nv),
   " | ".join(v["descricao"] for v in nv.values()))
m11, m12 = (A11 / f"numeros_chave_{V11}.md").read_text().splitlines(), (MS / f"numeros_chave_{V12}.md").read_text().splitlines()
r11 = [l for l in m11 if l.startswith("| ") and not l.startswith(("| id ", "|---"))]
r12 = [l for l in m12 if l.startswith("| ") and not l.startswith(("| id ", "|---"))]
ok("R2.bB16", "numeros_chave .md: cabeçalho = v11 fora etapa, versão e commit_pacote; 226 linhas idênticas; 2 novas com as descrições novas",
   m12[0] == m11[0].replace("7b–7c.6", "7b–7c.7") and m12[2] == m11[2].replace(V11, V12).replace("commit_pacote 8314417", f"commit_pacote {HEAD}")
   and m12[1] == m11[1] and m12[3:6] == m11[3:6] and r12[:226] == r11 and len(r12) == 228
   and all(r.startswith(f"| {k} | {nv[k]['valor_formatado']} | {nv[k]['descricao']} |") for r, k in zip(r12[226:], nv)))
TX = {}
for s in ("tabelas", "suplementar"):
    for f in (MS / s).glob(f"*_{V12}.csv"):
        TX[f.name] = f.read_text()
for f in [MS / "tabelas" / f"tabelas_principais_{V12}.xlsx", MS / "suplementar" / f"ESM_1_tables_S1_S6_{V12}.xlsx", SUB / "ESM_1.xlsx"]:
    TX[str(f.relative_to(PROJ))] = "\n".join(str(v) for _, c in celulas(f) for v in c.values())
TX["docx"] = "\n".join([p.text for p in db_.paragraphs] + [c.text for t in db_.tables for r in t.rows for c in r.cells])
for f in list((MS / "suplementar").glob(f"*_{V12}.pdf")) + sorted(SUB.glob("ESM_*.pdf")):
    TX[str(f.relative_to(PROJ))] = " ".join(" ".join(txt_pdf(f)).split())
for f in [MS / "MANIFEST.md", MS / "data_code_availability.md", MS / "legendas_figuras.md", MS / f"numeros_chave_{V12}.md", MS / f"numeros_chave_{V12}.json"]:
    TX[f.name] = f.read_text()
oc = {k: v.count(FRASE) for k, v in TX.items() if FRASE in v}
t4 = pd.read_csv(MS / "tabelas" / f"tab04_sensitivity_{V12}.csv", dtype=str).fillna("")
mi = t4[t4.Scenario.str.contains("imputation", case=False)]
ok("R2.bB17", "frase nova: 1 vez no xlsx e 1 no docx das tabelas principais, em nenhum outro lugar; linha da imputação múltipla com Wald 'n.a.'",
   oc == {f"outputs/manuscrito/tabelas/tabelas_principais_{V12}.xlsx": 1, "docx": 1} and len(mi) == 1
   and all(mi.iloc[0][c] == "n.a." for c in t4.columns if "Wald" in c), oc)
TER = PROJ / "docs/referencias/territorio_dez24"
rl = pd.read_csv(TER / "rl_municip_regsaud.csv", dtype=str)
uf_ = rl.CO_MUNICIP.str[:2]
tn = pd.read_csv(PROJ / "outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv", dtype={"cod_uf": str})
SIG = {"11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN",
       "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR", "42": "SC",
       "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF"}
eh = ~rl.CO_MUNICIP.str.endswith("0000")
meu = [(c, s, rl[uf_ == c].CO_REGSAUD.nunique(), int((eh & (uf_ == c)).sum()), round((eh & (uf_ == c)).sum() / rl[uf_ == c].CO_REGSAUD.nunique(), 1)) for c, s in SIG.items()]
meu.append(("", "Brasil", rl.CO_REGSAUD.nunique(), int(eh.sum()), round(eh.sum() / rl.CO_REGSAUD.nunique(), 1)))
deles = [("" if pd.isna(r.cod_uf) else str(r.cod_uf), r.uf, int(r.n_regioes_saude), int(r.n_municipios), float(r.municipios_por_regiao)) for r in tn.itertuples()]
tr = pd.read_csv(TER / "tb_regsaud.csv", dtype=str)
nao_us = sorted(set(tr.REGSAUD) - set(rl.CO_REGSAUD))
ok("R2.bB18", "CE/DF: recontagem própria (5 e 1), tabela nova = recálculo próprio nas 28 linhas (regerada às 12:24, mesmo conteúdo), "
   "433 − 6 = 427 na ficha; tb_regsaud: CE 25 e DF 8, 20 e 7 sem município no mapa",
   (meu[9][2], meu[26][2]) == (5, 1) and deles == meu and "3.2 sem CE/DF: 427" in (MS / "ficha_metodos_7c0_v1_20261009.md").read_text()
   and (sum(tr.REGSAUD.str[:2] == "23"), sum(tr.REGSAUD.str[:2] == "53")) == (25, 8)
   and (sum(r[:2] == "23" for r in nao_us), sum(r[:2] == "53" for r in nao_us)) == (20, 7) and len(nao_us) == 27,
   f"tabela mtime {hora(st('outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv'))}; md5 {md5f(PROJ / 'outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv')[:12]}")

# ======================================================================= R2.a — correções da rodada 1 e ressalvas acolhidas
s04 = (PROJ / "scripts/etapa7b_04_submissao.py").read_text()
ok("R2.a01", "B7.05 corrigida: o 04 tira da lista só os audita_* (e os _*, ._*, MANIFEST); o MANIFEST não tem linha audita_*, lista todo o "
   "resto e diz no parágrafo de abertura que as autoauditorias ficam fora", 'f.name.startswith(("._", "_", "audita_"))' in s04
   and set(lista) == set(M12) and not any("audita_" in k for k in M12) and FIM12.strip() in L12[2], "R2.bB09–bB11")
ok("R2.a01b", "B7.05: suficiente? a correção resolve a completude; ressalva: o 04 também tira qualquer arquivo 'audita_*' das pastas do pacote "
   "(tabelas/, figuras/, suplementar/), não só da raiz — hoje não há nenhum", not [f for d in ("tabelas", "figuras", "suplementar") for f in (MS / d).iterdir()
                                                                                 if f.name.startswith("audita_")], "regra mais larga que o texto do MANIFEST ('na raiz')")
s01 = (PROJ / "scripts/etapa7b_01_tabelas.py").read_text()
ok("R2.a02", "ressalva acolhida (descrição): JSON, .md e o 01 com 'municipality-to-health-region map used for the access index'; o checa exige o termo",
   all(DESC in nv[k]["descricao"] for k in nv) and "municipality-to-health-region map used for the access index" in s01
   and '"municipality-to-health-region map" in Jcur[f"n_regsaude_{u}"]["descricao"]' in (PROJ / "scripts/etapa7b_checa.py").read_text())
s02 = (PROJ / "scripts/etapa7b_02_suplementar.py").read_text()
ok("R2.a03", "ressalva acolhida (grep ancorado): 02 e disponibilidade com git log --grep \"^Etapa 7c.7:\" (o teste no git simulado está em R2.s)",
   '`git log --grep "^Etapa 7c.7:"`' in s02 and 'git log --grep "^Etapa 7c.7:"' in d12)
linhas_tab = [l for l in L12[L12.index("## Arquivos"):] if l.startswith("| ")]
ok("R2.a04", "ressalva acolhida (| escapado): toda linha da tabela do MANIFEST tem 4 células separando só nos | não escapados; a da Tabela 2 com \\|",
   all(len(re.split(r"(?<!\\)\|", l.strip())) == 6 for l in linhas_tab) and "\\|PR_M2cc − 1\\|" in "\n".join(L12)
   and "o.replace('|', chr(92) + '|')" in s04, f"{len(linhas_tab)} linhas de tabela")
lei = (PROJ / "scripts/resumos/LEIAME.md").read_text()
ok("R2.a05", "ressalva acolhida (LEIAME): 'cada versão do pacote entra num commit só, o da etapa, e não é regenerada depois dele com o mesmo rótulo'",
   "cada versão do pacote entra num commit só, o da etapa, e não é regenerada depois dele com o mesmo rótulo" in lei
   and "com um commit no meio, ou com o pacote regerado depois do commit" in lei)
s71 = (PROJ / "scripts/etapa7c7_01_regsaude_uf.py").read_text()
ok("R2.a06", "etapa7c7_01: docstring nova bate com a base (CE 25 e DF 8 na tb_regsaud; 20 e 7 sem município no mapa); código: uma leitura "
   "(rl_municip_regsaud) e uma gravação (a tabela); a tabela continua = recálculo próprio",
   "(CE 25, DF 8)" in s71 and "20 do CE e 7 do DF não têm município no mapa" in s71 and deles == meu
   and len([n for n in ast.walk(ast.parse(s71)) if isinstance(n, ast.Call) and ast.unparse(n.func) == "pd.read_csv"]) == 1
   and s71.count(".to_csv(") == 1, "sem cópia da versão da rodada 1: 'só a docstring' conferido pelo comportamento (mesma tabela), não por diff")


def diff_linhas(rel):
    a = git("show", f"{HEAD}:{rel}").splitlines()
    b = (PROJ / rel).read_text().splitlines()
    rem, add = [], []
    for l in difflib.unified_diff(a, b, lineterm="", n=0):
        if not l.startswith(("---", "+++", "@@")):
            (rem if l[0] == "-" else add).append(l[1:])
    return rem, add


def confere(rel, er, ea):
    rem, add = diff_linhas(rel)
    ruim = [m for m in er if sum(m in l for l in rem) != 1] + [m for m in ea if sum(m in l for l in add) != 1]
    sobra = [l for l in rem if not any(m in l for m in er)] + [l for l in add if not any(m in l for m in ea)]
    return not ruim and not sobra and len(rem) == len(er) and len(add) == len(ea), f"-{len(rem)} +{len(add)}; sem par {ruim}; fora {sobra[:3]}"


ok("R2.a07", "01: diff × dc9328d = frase da Tabela 4 e o bloco dos números novos (agora com a descrição em 3 linhas); nada mais",
   *confere("scripts/etapa7b_01_tabelas.py", ["access sample, combined with Rubin's rules. Live-birth bounds"],
            ["combined with Rubin's rules. Joint Wald tests were not computed for the multiple-imputation analysis. Live-birth bounds",
             "# 7c.7: regiões de saúde de CE e DF", 'rsu = B.rd("tab_e7c7_01_regsaude_uf").set_index("uf")',
             'for uf_, nome_ in (("CE", "Ceará"), ("DF", "Federal District")):', 'R.add(f"n_regsaude_{uf_}", int(rsu.n_regioes_saude[uf_])',
             'f"Health regions in {nome_} in the municipality-to-health-region map used for the access index (DATASUS territorial base, "',
             '"December 2024)", f"uf={uf_}")']))
ok("R2.a08", "02: diff × dc9328d = etapa, título e grep ancorado da disponibilidade + dot_clean no fim; nada mais",
   *confere("scripts/etapa7b_02_suplementar.py", ['ETAPA = "Etapa 7c.6: auditoria', "package {B.V}, Etapa 7c.6)", '`git log --grep "Etapa 7c.6"`'],
            ['ETAPA = "Etapa 7c.7: pacote v12 com as decisões da 7c.6b"', "package {B.V}, Etapa 7c.7)", '`git log --grep "^Etapa 7c.7:"`',
             "# 7c.7: os PDFs do Chrome", 'subprocess.run(["dot_clean", "-m", str(B.SUPD)], check=True)', 'if list(B.SUPD.glob("._*")):',
             'raise RuntimeError(f"._* em {B.SUPD}")']))
ok("R2.a09", "04: diff × dc9328d = docstring (1 linha), título, nome do commit, parágrafo da v12 + nota dos audita_*, exclusão audita_ e "
   "escape do |; nada mais",
   *confere("scripts/etapa7b_04_submissao.py",
            ['(Etapas 7b–7c.6, {V})', "'Etapa 7c.6: auditoria independente", "commit_analise nos números-chave. \"", '"Scripts em scripts/.", "",',
             'f.name.startswith(("._", "_"))', 'linhas.append(f"| {rot}/{f.name} | {s} | {o} | {md5(f)[:12]} |")'],
            ["7c.7: o MANIFEST deixa fora as autoauditorias", '(Etapas 7b–7c.7, {V})', "'Etapa 7c.7: pacote v12 com as decisões da 7c.6b'",
             "commit_analise nos números-chave; v12 = v11 com o rodapé da Tabela 4", '"dizendo que os testes de Wald conjuntos',
             '"n_regsaude_DF (regiões de saúde no mapa município', '"suplementar/ sem arquivos ._* (dot_clean no 02). Scripts em scripts/. As autoauditorias',
             '"outputs/manuscrito/) ficam fora da lista de arquivos', 'f.name.startswith(("._", "_", "audita_"))', "o.replace('|', chr(92) + '|')"]))
ok("R2.a10", "lib e etapa2_03: iguais ao que a rodada 1 conferiu (mtime 10:37:33; diffs com os mesmos marcadores)",
   confere("scripts/etapa7b_lib.py", ['V = "v11_20261009"', 'md = ["# Key numbers (Etapas 7b–7c.6)"'],
           ['V = "v12_20261013"', "# 7c.7: regiões de saúde e municípios por UF", '"tab_e7c7_01_regsaude_uf": "scripts/etapa7c7_01_regsaude_uf.py",',
            'md = ["# Key numbers (Etapas 7b–7c.7)"'])[0] and len(diff_linhas("scripts/etapa2_03_indice_acesso.py")[1]) == 1
   and hora(st("scripts/etapa7b_lib.py")) == hora(st("scripts/etapa2_03_indice_acesso.py")) == "10:37:33")
ck = (PROJ / "scripts/etapa7b_checa.py").read_text()
nomes_r1 = [v for v, o in json.load(open(OUTD / "sandbox_7c7_v1_20261013.json"))["linha_de_base"]["linhas"]]
SB2 = json.load(open(OUTD / "sandbox_7c7_r2_v1_20261013.json"))
nomes_r2 = [x[0] for x in SB2.get("linha_de_base", {}).get("linhas", [])]
dn = [(a, b) for a, b in zip(nomes_r1, nomes_r2) if a != b]
ok("R2.a11", "checa × rodada 1: mesmas 113 verificações, na mesma ordem; só o rótulo do volta8 muda (grep ancorado); a de n_regsaude exige "
   "o termo novo na descrição", len(nomes_r1) == len(nomes_r2) == 113 and len(dn) == 1 and "ancorado" in dn[0][1]
   and ck.count('"municipality-to-health-region map" in Jcur') == 1 and ck.count(""".replace('"^Etapa 7c.7:"', '"Etapa 7c.6"')""") == 1,
   [(a[:45] + "…", "…" + b[45:]) for a, b in dn])

# ======================================================================= R2.b — D (logs) no estado novo
RX = re.compile(r"^\[(2026-10-13 \d\d:\d\d:\d\d)\] \[([^\]]+)\] ?(.*)$")
ev = []
for f in sorted((PROJ / "outputs/logs").glob("*.log")):
    for l in f.read_text(errors="replace").splitlines():
        m = RX.match(l)
        if m and m.group(1) > "2026-10-13 10:21":
            ev.append((m.group(1), m.group(2), "INICIO" if m.group(2) == "7b_checa" and "números-chave = arquivo de origem" in m.group(3)
                       else ("" if m.group(2) == "7b_checa" else m.group(3))))
ev.sort(key=lambda e: e[0])
runs = []
for t, n_, msg in ev:
    novo = not runs or runs[-1][1] != n_ or (n_ == "7b_checa" and msg == "INICIO") or (n_ == "7c7_01_regsaude_uf" and msg.startswith("códigos UF0000")) \
        or (n_ == "7c7_01_regsaude_uf" and t != runs[-1][2] and not msg.startswith("regiões"))
    if novo:
        runs.append([t, n_, t, 1, msg])
    else:
        runs[-1][2] = t
        runs[-1][3] += 1
fin = [r for r in runs if r[0] >= "2026-10-13 12:2"]
seq = [r[1] for r in fin]
T = lambda s: datetime.strptime(s, "%Y-%m-%d %H:%M:%S").timestamp()
ok("R2.bD01", "regeneração final (12:24–12:26): 7c7_01, 01, 02, 03, 04, checa (uma execução), 04 — e depois só o gerador do RESUMO (13:30)",
   seq == ["7c7_01_regsaude_uf", "7b_01_tabelas", "7b_02_suplementar", "7b_03_figuras", "7b_04_submissao", "7b_checa", "7b_04_submissao", "7c7_01_resumo"],
   "; ".join(f"{a[11:]}–{c[11:]} {b} ({d})" for a, b, c, d, _ in fin))
f = {r[1]: r for r in fin}
c_run = [r for r in fin if r[1] == "7b_checa"][0]
mt = {"tabela 7c7_01": st("outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv"),
      "tabelas+JSON (01)": max([x.stat().st_mtime for x in (MS / "tabelas").iterdir()] + [st(f"outputs/manuscrito/numeros_chave_{V12}.json"), st(f"outputs/manuscrito/numeros_chave_{V12}.md")]),
      "suplementar+disp (02)": max([x.stat().st_mtime for x in (MS / "suplementar").iterdir() if not x.name.startswith("S9")] + [st("outputs/manuscrito/data_code_availability.md")]),
      "figuras+S9+legendas (03)": max([x.stat().st_mtime for x in (MS / "figuras").iterdir()] + [x.stat().st_mtime for x in (MS / "suplementar").glob("S9*")] + [st("outputs/manuscrito/legendas_figuras.md")]),
      "checa CSV": st(f"outputs/manuscrito/checa_7b_{V12}.csv"), "ESM_4+MANIFEST (2º 04)": max(st("Submissao/ESM_4.pdf"), st("outputs/manuscrito/MANIFEST.md"))}
ini = lambda n_: T([r for r in fin if r[1] == n_][0][0])
fimr = lambda n_, k=0: T([r for r in fin if r[1] == n_][k][2])
coer = {"7c7_01": abs(mt["tabela 7c7_01"] - fimr("7c7_01_regsaude_uf")) <= 1, "01": fimr("7c7_01_regsaude_uf") - 1 <= mt["tabelas+JSON (01)"] <= fimr("7b_01_tabelas") + 1,
        "02": fimr("7b_01_tabelas") <= mt["suplementar+disp (02)"] <= fimr("7b_02_suplementar") + 1,
        "03": fimr("7b_02_suplementar") <= mt["figuras+S9+legendas (03)"] <= fimr("7b_03_figuras") + 1,
        "checa": abs(mt["checa CSV"] - T(c_run[2])) <= 1, "2º 04": abs(mt["ESM_4+MANIFEST (2º 04)"] - fimr("7b_04_submissao", 1)) <= 2}
pac = [p for p in arvore_disco() if p.startswith(("outputs/manuscrito/tabelas/", "outputs/manuscrito/figuras/", "outputs/manuscrito/suplementar/", "Submissao/"))
       or p in ("outputs/manuscrito/MANIFEST.md", "outputs/manuscrito/data_code_availability.md", "outputs/manuscrito/legendas_figuras.md",
                f"outputs/manuscrito/numeros_chave_{V12}.json", f"outputs/manuscrito/numeros_chave_{V12}.md", f"outputs/manuscrito/checa_7b_{V12}.csv")]
ok("R2.bD02", "mtimes × logs da regeneração final coerentes; nenhum arquivo do pacote gravado depois do 2º 04 (12:26:33)",
   all(coer.values()) and max(st(p) for p in pac) <= fimr("7b_04_submissao", 1) + 1,
   "; ".join(f"{k} {v}" for k, v in coer.items()) + " | " + "; ".join(f"{k} {hora(v)}" for k, v in mt.items()))
SCR = {s: st(f"scripts/{s}") for s in ["etapa7b_lib.py", "etapa7b_01_tabelas.py", "etapa7b_02_suplementar.py", "etapa7b_03_figuras.py",
                                        "etapa7b_04_submissao.py", "etapa7b_checa.py", "etapa7c7_01_regsaude_uf.py", "etapa2_03_indice_acesso.py"]}
ok("R2.bD03", "scripts do pacote, checa e 7c7_01 editados antes da regeneração final (nenhum depois das 12:24:02)",
   max(SCR.values()) < ini("7c7_01_regsaude_uf"), "; ".join(f"{k} {hora(v)}" for k, v in SCR.items()))
nchk = [r for r in runs if r[1] == "7b_checa"]
ok("R2.bD04", "checa: 3 execuções no dia depois de dc9328d (10:43:50 interrompida; 10:44:57; 12:25:23), cada uma com o 1º item; o CSV vem da "
   "última, com o script final", len(nchk) == 3 and SCR["etapa7b_checa.py"] < T(nchk[-1][0]) and abs(mt["checa CSV"] - T(nchk[-1][2])) <= 1,
   [(r[0][11:], r[2][11:], r[3]) for r in nchk])
ok("R2.bD05", "autoauditoria e RESUMO: CSV da autoauditoria depois do script dela; RESUMO depois do texto, do gerador, da autoauditoria e do "
   "comparacao deste auditor", st("scripts/etapa7c7_02_audita.py") < st("outputs/manuscrito/audita_7c7_v1_20261013.csv")
   < st("outputs/RESUMO_ETAPA7C7_v1_20261013.md") and max(st("outputs/manuscrito/_resumo7c7_texto_v1_20261013.md"), st("scripts/resumos/etapa7c7_01_resumo.py"))
   < st("outputs/RESUMO_ETAPA7C7_v1_20261013.md") and SB2["gerador"]["reproduz"]["comparacao_lida_mtime"] < hora(st("outputs/RESUMO_ETAPA7C7_v1_20261013.md")),
   f"audita {hora(st('scripts/etapa7c7_02_audita.py'))} → CSV {hora(st('outputs/manuscrito/audita_7c7_v1_20261013.csv'))}; RESUMO {hora(st('outputs/RESUMO_ETAPA7C7_v1_20261013.md'))}")
RUNS_DIA = [(r[0][11:], r[1], r[2][11:], r[3]) for r in runs]
json.dump(RUNS_DIA, open(OUTD / "logs_execucoes_7c7_r2_v1_20261013.json", "w"), ensure_ascii=False, indent=1)

# ======================================================================= R2.b — E (microdados e git)
para_commit = sorted(set(DEST.values()) | M_ESP | set(untr))
ruim = [p for p in para_commit if p.startswith("data/") or re.search(r"\.(parquet|dbc|dbf|csv\.gz|rds|sav|dta)$", p)
        or Path(p).name.startswith("._") or Path(p).name == ".DS_Store"]
ok("R2.bE01", "o que iria para o commit: nada em data/, nenhum parquet/dbc/dbf/rds, ._* ou .DS_Store", not ruim, f"{len(para_commit)} arquivos; {ruim[:3]}")
ID_RX = re.compile(r"^(DTNASC|HORANASC|NUMERODN|NUMERODO|CODESTAB|DTOBITO|DTNASCMAE|DTULTMENST|CNS|CPF|CODMUNRES|CODMUNNASC)$", re.I)
susp = []
for p in para_commit:
    if p.endswith(".csv") and not p.startswith("docs/referencias/") and p != "outputs/manuscrito/audita_7c7_v1_20261013.csv":
        h = pd.read_csv(PROJ / p, nrows=0).columns
        nl = sum(1 for _ in open(PROJ / p, errors="ignore")) - 1
        if any(ID_RX.match(str(c).strip()) for c in h) or nl > 5000:
            susp.append((p, nl))
ok("R2.bE02", "CSVs da etapa que iriam para o commit (o da autoauditoria fica para a rodada final): sem coluna identificadora, ≤ 5,000 linhas", not susp, susp)
pad = re.compile(r"\b\d{6}\b.{0,3}\b(19|20)\d{2}-?\d{2}-?\d{2}\b")
txts = [p for p in para_commit if p.endswith((".md", ".py", ".json")) and not p.startswith("docs/referencias/")]
ok("R2.bE03", "texto que iria para o commit (.md, .py, .json, inclusive o RESUMO e os arquivos deste auditor): sem código de município + data completa",
   not [p for p in txts if pad.search((PROJ / p).read_text(errors="ignore"))], f"{len(txts)} arquivos")
ok("R2.bE04", "tabela nova fora do git e .gitignore igual ao de dc9328d", bool(subprocess.run(["git", "-C", str(PROJ), "check-ignore", "-q",
   "outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv"], env=ENV).returncode == 0) and hash_disco([".gitignore"])[".gitignore"] == arv0[".gitignore"])

# ======================================================================= R2.c — pegadas da autoauditoria nova no Forja (antes de ler o código dela)
ta = st("outputs/manuscrito/audita_7c7_v1_20261013.csv")
tabs = {f.name: f.stat().st_mtime for f in (PROJ / "outputs/tables").iterdir() if f.is_file()}
ok("R2.c01", "outputs/tables intacta depois da autoauditoria: nada com mtime depois de dc9328d, fora a tabela nova (12:24:02, da execução do 7c7_01)",
   all(v < TCOMMIT for k, v in tabs.items() if not k.startswith("tab_e7c7_01")) and abs(tabs["tab_e7c7_01_regsaude_uf_v1_20261008.csv"] - ini("7c7_01_regsaude_uf")) <= 1,
   f"{len(tabs)} arquivos; mais recente fora a nova: {hora(max(v for k, v in tabs.items() if not k.startswith('tab_e7c7_01')))} de {datetime.fromtimestamp(max(v for k, v in tabs.items() if not k.startswith('tab_e7c7_01'))).date()}")
csvs_aud = {str(p.relative_to(PROJ)): p.stat().st_mtime for p in (PROJ / "audit_independente").rglob("*.csv") if "etapa7c7/" not in str(p)}
ok("R2.c02", "CSVs de audit_independente intactos: nenhum gravado depois de dc9328d (o comparacao_7c7 deste auditor estava com mtime 11:55 "
   "ao começar a rodada 2, antes da autoauditoria; depois só este auditor grava nele)",
   max(csvs_aud.values()) < TCOMMIT, f"{len(csvs_aud)} CSVs; mais recente {max(csvs_aud, key=csvs_aud.get)} {datetime.fromtimestamp(max(csvs_aud.values()))}")
ult = {}
for f_ in ("etapa7b_20261008.log", "etapa7c7_20261008.log"):
    ls_ = [RX.match(l) for l in (PROJ / "outputs/logs" / f_).read_text(errors="replace").splitlines()]
    ult[f_] = [(m.group(1)[11:], m.group(2)) for m in ls_ if m and m.group(1) > "2026-10-13 12:27"]
ok("R2.c03", "logs reais: nenhuma linha do checa nem de outro script depois das 12:26:33, fora a do gerador do RESUMO (13:30:19) — o sandbox da "
   "autoauditoria não escreveu nos logs do Forja", ult["etapa7b_20261008.log"] == [] and [n_ for _, n_ in ult["etapa7c7_20261008.log"]] == ["7c7_01_resumo"], ult)
SNAP1 = snap()
mud_aud = sorted(k for k in set(SNAP0) | set(SNAP1) if SNAP0.get(k) != SNAP1.get(k))
depois = sorted(p for p in arvore_disco() if st(p) >= T_R2 and not p.startswith("audit_independente/etapa7c7/"))
ok("R2.bA10", "estado estável durante a rodada 2 (nada mudou no projeto fora desta pasta desde 13:32; MD5 iguais no início e no fim deste script)",
   not mud_aud and not depois, f"mudaram {mud_aud[:3]}; mtime ≥ 13:32 {depois[:3]}")

# ======================================================================= R2.s — sandbox da rodada 2
B_ = SB2.get("base", {})
ok("R2.s01", "sandbox: só rastreados e não ignorados copiados; ignorados (outputs/tables, comparacao_*.csv) como links para o Forja; "
   "nada de data/; índice = real; HEAD dc9328d", B_.get("indice_igual") and B_.get("head") == HEAD and not B_.get("ignorados_copiados")
   and B_.get("links_para_forja") and not B_.get("data_no_sandbox"), B_)
G_ = SB2.get("guarda", {})
ok("R2.s02", "guarda carregada em toda execução: escrita via link bloqueada e cópia de ignorado para fora do Forja bloqueada",
   G_.get("saida") == ["BLOQUEOU", "BLOQUEOU"] and G_.get("link") and G_.get("sem_copia"), G_)
ok("R2.s03", "Forja intacto depois do sandbox: MD5 e mtime de outputs/tables/* e de todo CSV de audit_independente iguais antes e depois; sandbox apagado",
   SB2.get("ignorados_intactos") and SB2.get("sandbox_apagado"), f"{SB2.get('n_ignorados_conferidos')} arquivos; mudaram {SB2.get('ignorados_mudaram')}")
lb = SB2.get("linha_de_base", {})
ok("R2.s04", "checa (cópia, assert desligado) no estado novo: 113/113, nenhuma tentativa de escrita barrada pela guarda",
   lb.get("rc") == 0 and len(lb.get("linhas", [])) == 113 and all(x[1] for x in lb["linhas"]) and not lb.get("guarda"),
   f"{sum(x[1] for x in lb.get('linhas', []))}/{len(lb.get('linhas', []))}; {lb.get('seg')} s")
for k_, alvo_ in (("mut_desc", "7c.7 n_regsaude_CE e n_regsaude_DF"), ("mut_grep", "7c.7 data_code_availability")):
    r_ = SB2.get(k_, {})
    fal = [x[0] for x in r_.get("linhas", []) if not x[1]]
    ok(f"R2.s05.{k_[4:]}", f"mutação nova ({'descrição sem o termo' if k_ == 'mut_desc' else 'grep sem âncora na disponibilidade'}) → só '{alvo_}' falha",
       r_.get("rc") == 0 and len(fal) == 1 and fal[0].startswith(alvo_), fal)
C_ = SB2.get("commits", {})
cl = C_.get("checa", {}).get("linhas", [])
ok("R2.s06", "commit único simulado: checa 113/113; nenhum ignorado entrou no commit; git log --grep '^Etapa 7c.7:' = só o commit da etapa",
   len(cl) == 113 and all(x[1] for x in cl) and not C_.get("ignorados_no_commit") and C_.get("grep_ancorado") == [C_.get("head")],
   f"HEAD {C_.get('head')}; grep {C_.get('grep_ancorado')}")
ok("R2.s07", "grep ancorado resiste a um 'Etapa 7c.7b:' depois (continua 1 commit; sem âncora daria 2); '^Etapa 7c.6:' = só b9d6272 "
   "(sem âncora, 7c.6 e 7c.6b)", C_.get("grep_ancorado_apos_7c7b") == [C_.get("head")] and len(C_.get("grep_solto_apos_7c7b", [])) == 2
   and C_.get("grep_76_ancorado") == ["b9d6272"] and sorted(C_.get("grep_76_solto", [])) == ["b9d6272", "dc9328d"],
   {k: C_.get(k) for k in ("grep_ancorado_apos_7c7b", "grep_solto_apos_7c7b", "grep_76_ancorado", "grep_76_solto")})
GR = SB2.get("gerador", {})
ok("R2.s08", "gerador do RESUMO (cópia, saída desviada, comparacao deste auditor no estado da rodada 1): reproduz outputs/RESUMO_ETAPA7C7 byte a byte",
   GR.get("reproduz", {}).get("rc") == 0 and GR.get("reproduz", {}).get("igual") is True, GR.get("reproduz"))
ok("R2.s09", "LEIAME ('o etapa7c7_01 fixa a v12 do mesmo jeito'): com a v12 arquivada, o gerador para (FileNotFoundError) e não grava nada",
   GR.get("apos_arquivar_v12", {}).get("rc") not in (0, None) and "FileNotFoundError" in GR.get("apos_arquivar_v12", {}).get("ultima", "")
   and not GR.get("apos_arquivar_v12", {}).get("gravou"), GR.get("apos_arquivar_v12"))
RP = SB2.get("reproducao", {})
ok("R2.s10", "reprodução (cópias do 01 e do 03 no sandbox): JSON, .md, CSVs, xlsx/docx, legendas e figuras da v12 = os do Forja",
   all(v.get("rc") == 0 for v in RP.get("execucoes", {}).values()) and RP.get("comparacoes") and all(RP["comparacoes"].values()),
   f"{sum(RP.get('comparacoes', {}).values())}/{len(RP.get('comparacoes', {}))}; diferentes {[k for k, v in RP.get('comparacoes', {}).items() if not v]}")

# ======================================================================= grava
velho = pd.read_csv(CMP)
velho = velho[~velho.verificacao.str.startswith(MEU_PREFIXO)]
out = pd.concat([velho, pd.DataFrame(R)], ignore_index=True)
out.to_csv(CMP, index=False)
print(f"\nR2 (este script): {sum(r['ok'] for r in R)}/{len(R)} OK; CSV total {len(out)} linhas")
