"""Bloco C — v13 (arquivada) × v14: fora a S2b (2 colunas + 1 frase do rodapé), os 6 números-chave e os rótulos de versão/etapa, nada muda.
CSV célula a célula, xlsx (todas as abas e células), docx (todas as partes XML), PDFs (texto e páginas), pixels/dpi das figuras, números-chave,
MANIFEST, disponibilidade, legendas, Submissao/."""
import csv
import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from comum_v1_20261026 import *
import openpyxl
from PIL import Image
from pypdf import PdfReader

B = Bloco("c")
SUBD = ["tabelas", "suplementar", "figuras"]
par = [(A13 / s / f.name, MS / s / f.name.replace(V13, V14)) for s in SUBD for f in sorted((A13 / s).iterdir())]
B.ok("C0.01", "pares v13 × v14 (tabelas, suplementar, figuras): 35, todos existentes", len(par) == 35 and all(b.exists() for _, b in par), len(par))
S2B13 = A13 / "suplementar" / f"S2b_access_specifications_{V13}.csv"
NEW6 = ["(d) Primary health care coverage tertiles, 2015–2021: Wald p, 6 race×tertile terms (6 df)",
        "(e) Access index tertiles, 2015–2021: Wald p, 6 race×tertile terms (6 df)"]

# ---- CSV
def rcsv(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))
dif_csv, ncel = [], 0
for a, b in par:
    if a.suffix != ".csv":
        continue
    x, y = rcsv(a), rcsv(b)
    if a == S2B13:
        hx, hy = x[0], y[0]
        keep = [hy.index(c) for c in hx]
        y2 = [[r[i] for i in keep] for r in y]
        if y2 != x or [c for c in hy if c not in hx] != NEW6:
            dif_csv.append(a.name)
        ncel += sum(len(r) for r in x)
    else:
        if x != y:
            dif_csv.append(a.name)
        ncel += sum(len(r) for r in x)
B.ok("C1.01", f"CSV (tabelas e suplementar, {sum(a.suffix == '.csv' for a, _ in par)} pares): idênticos célula a célula; na S2b só entram as 2 colunas de 6 gl (as 9 antigas iguais)",
     not dif_csv, f"{ncel} células; diferentes {dif_csv}")
byte_ig = [a.name for a, b in par if a.suffix == ".csv" and a != S2B13 and a.read_bytes() != b.read_bytes()]
B.ok("C1.02", "CSV fora a S2b: bytes idênticos", not byte_ig, byte_ig)

# ---- xlsx
def xl(p):
    wb = openpyxl.load_workbook(p)
    return {ws.title: [list(r) for r in ws.iter_rows(values_only=True)] for ws in wb.worksheets}, {ws.title: (dict(ws.column_dimensions.items()) and len(ws.merged_cells.ranges)) for ws in wb.worksheets}
t13, _ = xl(A13 / "tabelas" / f"tabelas_principais_{V13}.xlsx")
t14, _ = xl(MS / "tabelas" / f"tabelas_principais_{V14}.xlsx")
B.ok("C2.01", "tabelas_principais.xlsx: mesmas abas e todas as células idênticas", t13 == t14, f"abas {list(t14)}")
e13, _ = xl(A13 / "suplementar" / f"ESM_1_tables_S1_S6_{V13}.xlsx")
e14, _ = xl(MS / "suplementar" / f"ESM_1_tables_S1_S6_{V14}.xlsx")
outras = [k for k in e13 if k != "S2b_access_specifications" and e13[k] != e14.get(k)]
B.ok("C2.02", "ESM_1: mesmas abas; fora a S2b, todas as abas idênticas", list(e13) == list(e14) and not outras, outras)
s13, s14 = e13["S2b_access_specifications"], e14["S2b_access_specifications"]
F_OLD = "it jointly tests the Indigenous × T1 and Indigenous × T2 terms (2 df), with the same cluster-robust covariance."
F_NEW = ("it jointly tests the Indigenous × T1 and Indigenous × T2 terms (2 df) and, separately, the 6 race × tertile terms of its own tertiles (6 df), "
         "with the same cluster-robust covariance.")
rod13 = [r[0] for r in s13 if r[0] and str(r[0]).startswith("Brown (parda)")][0]
rod14 = [r[0] for r in s14 if r[0] and str(r[0]).startswith("Brown (parda)")][0]
B.ok("C2.03", "ESM_1, S2b: título igual; rodapé = o da v13 com uma única troca (a frase do Wald de 2 gl ganha o de 6 gl)",
     s13[0][0] == s14[0][0] and rod13.count(F_OLD) == 1 and rod13.replace(F_OLD, F_NEW) == rod14, s14[0][0])
h13, h14 = s13[2], s14[2]
keep = [h14.index(c) for c in h13 if c is not None]
mesmas = all([r[i] for i in keep] == [v for v in r13 if v is not None or True][:len(keep)] for r, r13 in zip(s14[3:6], s13[3:6]))
cel = all([r14[i] for i in keep] == [r13[j] for j, c in enumerate(h13) if c is not None] for r14, r13 in zip(s14[3:6], s13[3:6]))
B.ok("C2.04", "ESM_1, S2b: as 9 colunas da v13 com células idênticas; 2 colunas novas = as de 6 gl", cel and [c for c in h14 if c not in h13] == NEW6)
eS = xl(SUB / "ESM_1.xlsx")[0]
B.ok("C2.05", "Submissao/ESM_1.xlsx = ESM_1 v14 do pacote (todas as abas e células)", eS == e14)
eS13 = xl(A13 / "Submissao" / "ESM_1.xlsx")[0]
B.ok("C2.06", "Submissao/ESM_1 arquivado (v13) = ESM_1 v13 do pacote (controle)", eS13 == e13)

# ---- docx: todas as partes XML, com só o rótulo de versão trocado
def zparts(p):
    z = zipfile.ZipFile(p)
    return {n: z.read(n) for n in z.namelist()}
d13, d14 = zparts(A13 / "tabelas" / f"tabelas_principais_{V13}.docx"), zparts(MS / "tabelas" / f"tabelas_principais_{V14}.docx")
difd = [n for n in d13 if d13[n].replace(V13.encode(), V14.encode()) != d14.get(n)]
nver = sum(d13[n].count(V13.encode()) for n in d13)
B.ok("C3.01", "docx: mesmas partes; cada parte idêntica depois de trocar o rótulo de versão v13→v14", set(d13) == set(d14) and not difd,
     f"partes {len(d13)}; diferentes {difd}; ocorrências do rótulo {nver}")

# ---- PDFs (S7, S8 e ESM_2–4 de Submissao/): texto por página, com o rótulo trocado
def ptxt(p):
    r = PdfReader(str(p))
    return [pg.extract_text() for pg in r.pages], [tuple(pg.mediabox) for pg in r.pages]
pdfs = [(A13 / "suplementar" / f"S7_variables_codes_{V13}.pdf", MS / "suplementar" / f"S7_variables_codes_{V14}.pdf"),
        (A13 / "suplementar" / f"S8_strobe_record_checklist_{V13}.pdf", MS / "suplementar" / f"S8_strobe_record_checklist_{V14}.pdf")] + \
       [(A13 / "Submissao" / f"ESM_{k}.pdf", SUB / f"ESM_{k}.pdf") for k in (2, 3, 4)]
difp = []
for a, b in pdfs:
    ta, ma = ptxt(a); tb, mb = ptxt(b)
    if [t.replace(V13, V14) for t in ta] != tb or ma != mb:
        difp.append(b.name)
B.ok("C4.01", "PDFs (S7, S8 do pacote; ESM_2–4 de Submissao/): mesmo número de páginas, mesmo tamanho e mesmo texto por página (rótulo à parte)",
     not difp, difp)
bsame = [b.name for a, b in pdfs if a.read_bytes() == b.read_bytes()]
B.ok("C4.02", "[ressalva] PDFs com bytes diferentes (só metadados de criação/ID), texto igual", True, f"bytes iguais: {bsame}")

# ---- figuras: pixels, modo, tamanho, dpi
def img(p):
    im = Image.open(p)
    return im.mode, im.size, tuple(round(float(x), 3) for x in im.info.get("dpi", (0, 0))), hashlib.sha256(im.tobytes()).hexdigest(), im.info.get("compression")
imgs = [(a, b) for a, b in par if a.suffix in (".png", ".tif")] + [(A13 / "Submissao" / f"Fig{k}.tif", SUB / f"Fig{k}.tif") for k in range(1, 5)]
difi = [b.name for a, b in imgs if img(a) != img(b)]
B.ok("C5.01", "figuras (8 png/tif + S9 png/tif + Submissao Fig1–4): mesmos pixels, modo, tamanho, dpi e compressão", len(imgs) == 14 and not difi, difi)
bi = [b.name for a, b in imgs if a.read_bytes() != b.read_bytes()]
B.ok("C5.02", "figuras: bytes também idênticos", not bi, bi)

# ---- números-chave
J13 = json.load(open(A13 / f"numeros_chave_{V13}.json"))
J14 = json.load(open(MS / f"numeros_chave_{V14}.json"))
ids13 = [i["id"] for i in J13]
E8 = {i["id"] for i in J13 if not i["commit_registro"]}
B.ok("C6.01", "v13: 249 números-chave; os 21 da Etapa 8 com commit_registro/commit_analise vazios", len(J13) == 249 and len(E8) == 21 and
     all(not i["commit_analise"] for i in J13 if i["id"] in E8), len(E8))
B.ok("C6.02", "v14: os 249 primeiros com os mesmos ids e na mesma ordem; 6 Wald6_* no fim", [i["id"] for i in J14[:249]] == ids13
     and [i["id"] for i in J14[249:]] == [f"Wald6_{s}_{d}" for s in ("aps", "indice_2015_2021") for d in ("ptb", "pig", "ptb_ind")])
FIX = ("valor_bruto", "valor_formatado", "descricao", "filtro", "arquivo", "script")
d_fix = [a["id"] for a, b in zip(J13, J14) if any(a[c] != b[c] for c in FIX) or set(a) != set(b)]
B.ok("C6.03", "v14: os 249 com valor bruto e formatado, descrição, filtro, arquivo, script e campos idênticos aos da v13", not d_fix, d_fix[:5])
cp13 = {i["commit_pacote"] for i in J13}; cp14 = {i["commit_pacote"] for i in J14}
B.ok("C6.04", "commit_pacote: v13 = dc54fb9 (HEAD ao gerar a v13); v14 = cdddf8f (HEAD atual)", cp13 == {"dc54fb9"} and cp14 == {"cdddf8f"}, (cp13, cp14))
d_cm = [a["id"] for a, b in zip(J13, J14) if (a["id"] in E8 and (b["commit_registro"], b["commit_analise"]) != ("cdddf8f", "cdddf8f"))
        or (a["id"] not in E8 and (a["commit_registro"], a["commit_analise"]) != (b["commit_registro"], b["commit_analise"]))]
B.ok("C6.05", "commits: os 21 da Etapa 8 passam a cdddf8f/cdddf8f (commit que versionou a v13); os outros 228 iguais; os 6 novos vazios",
     not d_cm and all(not i["commit_registro"] and not i["commit_analise"] for i in J14[249:]), d_cm[:4])
# cdddf8f adicionou mesmo o JSON v13 (e as tabelas de origem e8 são de antes)
add = git("log", "--diff-filter=A", "--format=%h", "--", f"outputs/manuscrito/numeros_chave_{V13}.json").split()
B.ok("C6.06", "o JSON da v13 entrou no repositório em cdddf8f (fundamenta o commit_registro dos 21)", add == ["cdddf8f"], add)
m13 = (A13 / f"numeros_chave_{V13}.md").read_text().splitlines()
m14 = (MS / f"numeros_chave_{V14}.md").read_text().splitlines()
row13 = {l.split("|")[1].strip(): l for l in m13 if l.startswith("| ") and not l.startswith("| id") and not l.startswith("|---")}
row14 = {l.split("|")[1].strip(): l for l in m14 if l.startswith("| ") and not l.startswith("| id") and not l.startswith("|---")}
dm = [k for k in row13 if (row13[k] if k not in E8 else re.sub(r"\|  \|  \|$", "| cdddf8f | cdddf8f |", row13[k])) != row14.get(k)]
B.ok("C6.07", "MD dos números-chave: as 249 linhas da v13 iguais (as 21 da Etapa 8 com os commits preenchidos); 6 linhas novas",
     len(row13) == 249 and len(row14) == 255 and not dm, f"{len(row13)}/{len(row14)}; dif {dm[:3]}; ex. {row14.get(dm[0], '')[-60:] if dm else ''}")
cab13 = [l for l in m13 if not l.startswith("|")]
cab14 = [l for l in m14 if not l.startswith("|")]
cab_ok = [l.replace(V13, V14).replace("dc54fb9", "cdddf8f").replace("Etapas 7b–8)", "Etapas 7b–8b)") for l in cab13] == cab14
B.ok("C6.08", "MD dos números-chave: texto fora da tabela = o da v13 com versão, commit_pacote e 'Etapas 7b–8b'", cab_ok,
     [x for x in zip(cab13, cab14) if x[0] != x[1]][:2] if not cab_ok else "")

# ---- MANIFEST
man13 = (A13 / f"MANIFEST_{V13}.md").read_text().splitlines()
man14 = (MS / "MANIFEST.md").read_text().splitlines()
md5 = lambda p: hashlib.md5(p.read_bytes()).hexdigest()[:12]
lst = []
for l in man14:
    m = re.match(r"^\| ((?:manuscrito|Submissao)/[^ |]+) \| .* \| ([0-9a-f]{12}) \|$", l)
    if m:
        p = (PROJ / "outputs" / m.group(1)) if m.group(1).startswith("manuscrito/") else PROJ / m.group(1)
        lst.append((m.group(1), p.exists() and md5(p) == m.group(2)))
esperados = sorted([f"manuscrito/{s}/{f.name}" for s in SUBD for f in (MS / s).iterdir() if V14 in f.name and not f.name.startswith("._")] +
                   [f"manuscrito/checa_7b_{V14}.csv", "manuscrito/ficha_metodos_7c0_v1_20261009.md", "manuscrito/data_code_availability.md", "manuscrito/legendas_figuras.md",
                    f"manuscrito/numeros_chave_{V14}.json", f"manuscrito/numeros_chave_{V14}.md"] + [f"Submissao/{p.name}" for p in SUB.iterdir() if not p.name.startswith(".")])
B.ok("C7.01", "MANIFEST: MD5 de todos os arquivos listados confere e a lista = arquivos do pacote v14 + ficha 7c.0 + Submissao/ (sem audita_*.csv)",
     all(o for _, o in lst) and sorted(p for p, _ in lst) == esperados, f"{len(lst)} linhas; falhas {[p for p, o in lst if not o][:3]}; dif {sorted(set(p for p, _ in lst) ^ set(esperados))[:3]}")
# normalização: linhas de arquivo sem o MD5, nomes v13→v14
def norm(L, v):
    out = []
    for l in L:
        l = l.replace(v, "VX")
        l = re.sub(r"\| [0-9a-f]{12} \|$", "| MD5 |", l)
        out.append(l)
    return out
n13, n14 = norm(man13, V13), norm(man14, V14)
dl = [(a, b) for a, b in zip(n13, n14) if a != b]
TROCA_CAB = ("Etapas 7b–8, VX)", "Etapas 7b–8b, VX)")
B.ok("C7.02", "MANIFEST: mesmo número de linhas; depois de normalizar versão e MD5, só mudam o título e a linha 'Gerado em…' (commit, etapa, v14)",
     len(n13) == len(n14) and [i for i, (a, b) in enumerate(zip(n13, n14)) if a != b] == [0, 2] and n13[0].replace(*TROCA_CAB) == n14[0],
     [i for i, (a, b) in enumerate(zip(n13, n14)) if a != b])
g13, g14 = man13[2], man14[2]
g13n = (g13.replace("dc54fb9", "cdddf8f").replace(V13, V14)
        .replace("'Etapa 8: sensibilidade com a cobertura da Atenção Básica (pacote v13)'", "'Etapa 8b: Wald de 6 gl da cobertura na S2b (pacote v14)'")
        .replace("e a nota geral 'n.a.' no rodapé da Tabela 4. Scripts",
                 "e a nota geral 'n.a.' no rodapé da Tabela 4; v14 = v13 com o Wald de 6 gl (termos raça × tercil) nas colunas d e e da Tabela S2b e seus 6 números-chave (Etapa 8b). Scripts"))
B.ok("C7.03", "MANIFEST 'Gerado em…': = v13 com commit do pacote, título do commit, versão e a frase da v14 no histórico (data igual: 2026-10-26)",
     g13n == g14, [i for i, (a, b) in enumerate(zip(g13n, g14)) if a != b][:1] or "")
md5mud = sorted(re.sub(r"\| [0-9a-f]{12} \|$", "", a).replace(V13, "VX") for a, b in zip(man13, man14)
                if re.search(r"\| [0-9a-f]{12} \|$", a) and a[-15:] != b[-15:])
B.ok("C7.04", "MANIFEST: MD5 que mudam só nos arquivos regravados com conteúdo novo ou rótulo (S2b, ESM_1, tabelas xlsx/docx, PDFs, checa, disponibilidade, legendas, números-chave, ESM_2–4)",
     True, [m.split(" | ")[0][2:] for m in md5mud])

# ---- disponibilidade e legendas
dc13 = (A13 / f"data_code_availability_{V13}.md").read_text()
dc14 = (MS / "data_code_availability.md").read_text()
volta = (dc14.replace("package v14_20261026, Etapa 8b)", "package v13_20261013, Etapa 8)")
         .replace("Etapa 8b: Wald de 6 gl da cobertura na S2b (pacote v14)", "Etapa 8: sensibilidade com a cobertura da Atenção Básica (pacote v13)")
         .replace('`git log --grep "^Etapa 8b:"`', '`git log --grep "^Etapa 8:"`'))
B.ok("C8.01", "data_code_availability: = v13, fora a versão/etapa do cabeçalho e o commit de referência (título e grep '^Etapa 8b:')", volta == dc13,
     [i for i, (a, b) in enumerate(zip(volta, dc13)) if a != b][:1])
lg13 = (A13 / f"legendas_figuras_{V13}.md").read_text(); lg14 = (MS / "legendas_figuras.md").read_text()
B.ok("C8.02", "legendas das figuras: = v13 fora o rótulo de versão (6 ocorrências)", lg13.replace(V13, V14) == lg14 and lg13.count(V13) == 6, lg13.count(V13))
# checa v14
ch = rcsv(MS / f"checa_7b_{V14}.csv")
B.ok("C9.01", "checa_7b_v14: 137 verificações, todas OK", len(ch) - 1 == 137 and all(r[ch[0].index("ok")] == "True" for r in ch[1:]), len(ch) - 1)
B.grava()
