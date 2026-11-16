"""
8b Autoauditoria da Etapa 8b (Wald de 6 gl da cobertura da Atenção Básica na Tabela S2b; pacote v14), com código próprio: não importa
etapa7b_lib nem o checa (o checa e o gerador só rodam, como subprocesso, em cópias descartáveis). Nenhuma análise nova: os Wald de 6 gl já
estavam em tab_e8_04_wald (Etapa 8, conferidos então por refit em statsmodels e em R).
  A  git e árvore: HEAD, refs, remoto, tag e stash; o que mudou desde cdddf8f, arquivo por arquivo; v13 arquivada byte a byte; ._*;
  P  pacote v13 × v14: números-chave (os 6 novos recalculados de tab_e8_04_wald); CSVs; S2b; xlsx; docx; PDFs; imagens; MANIFEST;
     disponibilidade; legendas;
  C  scripts: lib, 01, 02 e 04 contra cdddf8f pela lista exata de trocas; checa por região e checa da v14; sandbox: checa com mutações
     dirigidas ao bloco 9j (com controle negativo), checa depois de um commit simulado (único e com um commit no meio);
  D  logs desde cdddf8f × mtimes;
  E  microdados e git no que vai para o commit.
Sandbox e guarda como na autoauditoria da Etapa 8 (scripts/etapa8_05_audita.py). Grava outputs/manuscrito/audita_8b_v1_20261026.csv.
Rodar da raiz: python3 scripts/etapa8b_01_audita.py
"""
import concurrent.futures as cf
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True
import docx
import openpyxl
import pandas as pd
import pymupdf
from PIL import Image

PROJ = Path(__file__).resolve().parents[1]
MS, SUB, TB = PROJ / "outputs" / "manuscrito", PROJ / "Submissao", PROJ / "outputs" / "tables"
A12, A13 = MS / "_arquivo_v12", MS / "_arquivo_v13"
V12, V13, V14, BASE, S = "v12_20261013", "v13_20261013", "v14_20261026", "cdddf8f", "20261008"
TITULO = "Etapa 8b: Wald de 6 gl da cobertura na S2b (pacote v14)"
T8 = "Etapa 8: sensibilidade com a cobertura da Atenção Básica (pacote v13)"
SAIDA = MS / "audita_8b_v1_20261026.csv"
RAW = PROJ / "data" / "raw" / "aps_cobertura_ab"
ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
OUTC = {"ptb": "Preterm birth (total)", "pig": "SGA", "ptb_ind": "Provider-initiated preterm birth"}
EXP = {"tercil_aps": "aps", "tercil_ind21": "indice_2015_2021"}
COLN = {"tercil_aps": "(d) Primary health care coverage tertiles, 2015\u20132021", "tercil_ind21": "(e) Access index tertiles, 2015\u20132021"}
TXT = {"tercil_aps": "primary health care coverage tertiles", "tercil_ind21": "access index tertiles recomputed in 2015\u20132021"}


def git(*a, cwd=PROJ, b=False):
    return subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=not b, check=True, env=ENV).stdout


md5 = lambda b: hashlib.md5(b).hexdigest()
R = []


def ok(vid, desc, cond, det=""):
    R.append(dict(verificacao=f"{vid} {desc}", ok=bool(cond), detalhe=str(det)))


pv = lambda p: "<0.0001" if p < 0.0001 else f"{p:.3g}"
T_BASE = int(git("log", "-1", "--format=%ct", BASE))

# ======================= A. git e árvore =======================
h = git("rev-parse", "--short", "HEAD").strip()
head_ok = h == BASE or (git("rev-parse", "--short", "HEAD^").strip() == BASE and git("log", "-1", "--format=%s").strip() == TITULO
                        and len(git("rev-list", f"{BASE}..HEAD").split()) == 1)
refs = git("for-each-ref", "--format=%(refname)").split()
remotos, stash = git("remote").split(), git("stash", "list").strip()
ok("A0.01", "HEAD = cdddf8f (antes do commit) ou um commit só, com o título da etapa, sobre cdddf8f; só refs/heads/main; sem remoto, "
   "sem tag, stash vazio", head_ok and refs == ["refs/heads/main"] and not remotos and not stash, f"HEAD {h}; refs {refs}; remotos {remotos}")
_z = git("diff", "--name-status", "-z", "--no-renames", BASE).split("\0")
ns = [(_z[i], _z[i + 1]) for i in range(0, len(_z) - 1, 2)]


def st(*a):
    return [(e[:2], e[3:]) for e in git("status", "--porcelain", "-z", "--no-renames", "--untracked-files=all", *a).split("\0") if e]


naor = [p for c, p in st() if c == "??"]
VELHOS = sorted(p for p in git("ls-tree", "-r", "--name-only", BASE, "outputs/manuscrito").splitlines() if V13 in p and "/_arquivo_" not in p)
PAC14 = {p.replace(V13, V14) for p in VELHOS}
ARQ13 = {f"outputs/manuscrito/_arquivo_v13/{str(x.relative_to(A12)).replace(V12, V13)}" for x in A12.rglob("*")
         if x.is_file() and not x.name.startswith("._")}
FIXOS = {"scripts/etapa8b_01_audita.py", "scripts/resumos/etapa8b_01_resumo.py", "outputs/manuscrito/_resumo8b_texto_v1_20261026.md"}
OPC = {"outputs/RESUMO_ETAPA8b_v1_20261026.md", "outputs/manuscrito/audita_8b_v1_20261026.csv"}
MOD_OK = {"Submissao/ESM_1.xlsx", "Submissao/ESM_2.pdf", "Submissao/ESM_3.pdf", "Submissao/ESM_4.pdf", "outputs/manuscrito/MANIFEST.md",
          "outputs/manuscrito/data_code_availability.md", "outputs/manuscrito/legendas_figuras.md", "scripts/etapa7b_lib.py",
          "scripts/etapa7b_01_tabelas.py", "scripts/etapa7b_02_suplementar.py", "scripts/etapa7b_04_submissao.py", "scripts/etapa7b_checa.py"}
AUDRX = re.compile(r"^audit_independente/etapa8b/[A-Za-z0-9_]+_v1_20261026\.(md|py|R|json)$")
apagados = sorted(p for s_, p in ns if s_ == "D")
mods = sorted(p for s_, p in ns if s_ == "M")
adic = sorted([p for s_, p in ns if s_ == "A"] + naor)
docs_nr = [p for p in adic if p.startswith("docs/referencias/")]
aud_n = [p for p in adic if p.startswith("audit_independente/")]
resto = [p for p in adic if p not in PAC14 | ARQ13 | FIXOS | OPC and p not in docs_nr and p not in aud_n]
falta = sorted((PAC14 | ARQ13 | FIXOS) - set(adic))
ok("A1.01", "desde cdddf8f: apagados só os 38 da v13; modificados exatamente os 12 previstos; novos exatamente os 38 da v14, os 49 do "
   "_arquivo_v13, os 3 da Etapa 8b (+ RESUMO e CSV desta autoauditoria) e os do auditor na pasta etapa8b; em docs/referencias, só os 93 "
   "não rastreados de antes", len(VELHOS) == 38 and apagados == VELHOS and set(mods) == MOD_OK and len(ARQ13) == 49 and not resto and not falta
   and all(AUDRX.match(p) for p in aud_n) and len(docs_nr) == 93 and all((PROJ / p).stat().st_mtime < T_BASE for p in docs_nr),
   f"apagados {len(apagados)}; modificados {len(mods)}; novos {len(adic)}; fora do previsto {resto[:3]}; faltando {falta[:3]}; "
   f"auditor fora do padrão {[p for p in aud_n if not AUDRX.match(p)][:3]}")
mov = [p for p in VELHOS if (A13 / p[len("outputs/manuscrito/"):]).read_bytes() == git("show", f"{BASE}:{p}", b=True)]
cop = {"MANIFEST_v13_20261013.md": "outputs/manuscrito/MANIFEST.md", "data_code_availability_v13_20261013.md": "outputs/manuscrito/data_code_availability.md",
       "legendas_figuras_v13_20261013.md": "outputs/manuscrito/legendas_figuras.md"}
cop.update({f"Submissao/{n}": f"Submissao/{n}" for n in ("ESM_1.xlsx", "ESM_2.pdf", "ESM_3.pdf", "ESM_4.pdf", "Fig1.tif", "Fig2.tif", "Fig3.tif", "Fig4.tif")})
cop_ok = [k for k, v in cop.items() if (A13 / k).read_bytes() == git("show", f"{BASE}:{v}", b=True)]
arq = lambda d, v: sorted(str(x.relative_to(d)).replace(v, "VX") for x in d.rglob("*") if x.is_file() and not x.name.startswith("._"))
ok("A1.02", "_arquivo_v13: os 38 da v13 e as cópias (MANIFEST, disponibilidade, legendas, Submissao/) com os bytes de cdddf8f; mesma estrutura "
   "do _arquivo_v12", len(mov) == 38 and len(cop_ok) == len(cop) and arq(A13, V13) == arq(A12, V12), f"{len(mov)}/38; cópias {len(cop_ok)}/{len(cop)}")
ign = [p for c, p in st("--ignored") if c == "!!"]
ign_nov = sorted(p for p in ign if not p.endswith("/") and not p.startswith("data/") and (PROJ / p).stat().st_mtime > T_BASE)
IGN_OK = re.compile(r"^(outputs/logs/etapa(7b|8b?)_20261008\.log|(scripts/(resumos/)?|audit_independente/etapa8b?/)__pycache__/[^/]+\.pyc|"
                    r"audit_independente/etapa8b/[A-Za-z0-9_]+_v1_20261026\.csv)$")
dnov = sorted(str(Path(r).relative_to(PROJ) / f) for r, _, fs in os.walk(PROJ / "data") for f in fs if os.stat(Path(r) / f).st_mtime > T_BASE)
ok("A1.03", "ignorados depois de cdddf8f: só logs, __pycache__ e CSVs do auditor da 8b; nada em outputs/tables nem em data/ (só nome e mtime)",
   not [p for p in ign_nov if not IGN_OK.match(p)] and not dnov, f"fora do previsto {[p for p in ign_nov if not IGN_OK.match(p)][:5]}; data/ {dnov[:3]}")
lixo = [str(Path(r).relative_to(PROJ) / f) for r, d_, fs in os.walk(PROJ) if ".git" not in Path(r).relative_to(PROJ).parts[:1]
        and Path(r).relative_to(PROJ).parts[:1] != ("data",) for f in fs if f.startswith("._")]
ok("A2.01", "._*: nenhum fora de data/; nenhum versionado nem entre os novos", not lixo and not [p for p in adic if Path(p).name.startswith("._")], lixo[:3])

# ======================= P. pacote v13 × v14 =======================
J13l = json.load(open(A13 / f"numeros_chave_{V13}.json"))
J14l = json.load(open(MS / f"numeros_chave_{V14}.json"))
J13, J14 = {i["id"]: i for i in J13l}, {i["id"]: i for i in J14l}
E8 = [i["id"] for i in J13l[228:]]                          # os 21 da Etapa 8
NOVOS = [f"Wald6_{s_}_{y_}" for s_ in EXP.values() for y_ in OUTC]
dif = {k: [c for c in J13[k] if c != "commit_pacote" and J13[k][c] != J14[k].get(c)
           and not (k in E8 and c in ("commit_registro", "commit_analise") and J14[k][c] == BASE and J13[k][c] == "")] for k in J13}
ok("P1.01", "números-chave: 255 = os 249 da v13 (mesma ordem) + os 6 Wald de 6 gl no fim; todos os campos iguais, fora o commit_pacote e, "
   "nos 21 da Etapa 8, commit_registro e commit_analise (vazios na v13, cdddf8f agora); commit_pacote = cdddf8f em todos",
   len(J14l) == 255 and [i["id"] for i in J14l[:249]] == [i["id"] for i in J13l] and [i["id"] for i in J14l[249:]] == NOVOS and len(E8) == 21
   and not any(dif.values()) and all(J14[k]["commit_registro"] == J14[k]["commit_analise"] == BASE for k in E8)
   and {i["commit_pacote"] for i in J14l} == {BASE}, f"com diferença {[k for k, v in dif.items() if v][:3]}")
wd = pd.read_csv(TB / f"tab_e8_04_wald_v1_{S}.csv").set_index(["exposicao", "desfecho"])
esp = {f"Wald6_{s_}_{y_}": (wd.p_6gl[(e_, y_)], pv(wd.p_6gl[(e_, y_)]), f"Wald p (6 race\u00d7tertile terms), {TXT[e_]}, births 2015\u20132021, {OUTC[y_]}",
                            f"exposicao={e_}, desfecho={y_}") for e_, s_ in EXP.items() for y_ in OUTC}
ruim = [k for k, (v_, f_, d_, fi_) in esp.items() if not (abs(J14[k]["valor_bruto"] - v_) <= 1e-15 * max(1, abs(v_)) and J14[k]["valor_formatado"] == f_
        and J14[k]["descricao"] == d_ and J14[k]["filtro"] == fi_ and J14[k]["arquivo"] == f"outputs/tables/tab_e8_04_wald_v1_{S}.csv"
        and J14[k]["script"] == "scripts/etapa8_04_modelos.py" and J14[k]["commit_registro"] == J14[k]["commit_analise"] == "")]
ok("P1.02", "os 6 Wald de 6 gl = p_6gl de tab_e8_04_wald (formatação própria), descrição, filtro e origem; campos de commit vazios",
   not ruim, {k: v[1] for k, v in esp.items()})
pares = [(A13 / d_ / f.name, MS / d_ / f.name.replace(V13, V14)) for d_ in ("tabelas", "suplementar") for f in sorted((A13 / d_).glob(f"*_{V13}.csv"))]
ig = [b.name for a, b in pares if a.read_bytes() == b.read_bytes()]
s13 = pd.read_csv(A13 / "suplementar" / f"S2b_access_specifications_{V13}.csv", dtype=str)
s14 = pd.read_csv(MS / "suplementar" / f"S2b_access_specifications_{V14}.csv", dtype=str)
C6 = {e_: f"{COLN[e_]}: Wald p, 6 race\u00d7tertile terms (6 df)" for e_ in EXP}
ordem = []
for c_ in s13.columns:
    ordem.append(c_)
    ordem += [C6[e_] for e_ in EXP if c_ == f"{COLN[e_]}: Wald p, Indigenous terms (2 df)"]
cel = [s14.loc[i, C6[e_]] == esp[f"Wald6_{s_}_{y_}"][1] for i, y_ in enumerate(OUTC) for e_, s_ in EXP.items()]
ok("P2.01", "CSVs: 19 dos 20 idênticos byte a byte aos da v13; na S2b, as colunas da v13 iguais e 2 novas (Wald de 6 gl de (d) e de (e), "
   "cada uma depois do Wald indígena de 2 gl), com os valores recalculados aqui",
   len(pares) == 20 and len(ig) == 19 and s14[list(s13.columns)].equals(s13) and list(s14.columns) == ordem and all(cel), f"{len(ig)}/20; S2b {sum(cel)}/6")


def celulas(f):
    wb = openpyxl.load_workbook(f)
    return {(ws.title, c.coordinate): c.value for ws in wb.worksheets for row in ws.iter_rows() for c in row if c.value is not None}


x13, x14 = celulas(A13 / "tabelas" / f"tabelas_principais_{V13}.xlsx"), celulas(MS / "tabelas" / f"tabelas_principais_{V14}.xlsx")
ok("P2.02", "xlsx das tabelas principais: todas as células iguais às da v13", x13 == x14, f"{len(x14)} células")
e13, e14, es = celulas(A13 / "suplementar" / f"ESM_1_tables_S1_S6_{V13}.xlsx"), celulas(MS / "suplementar" / f"ESM_1_tables_S1_S6_{V14}.xlsx"), celulas(SUB / "ESM_1.xlsx")
de = sorted(k for k in set(e13) | set(e14) if e13.get(k) != e14.get(k))
W2 = ("in (d) and (e), it jointly tests the Indigenous \u00d7 T1 and Indigenous \u00d7 T2 terms (2 df), with the same cluster-robust covariance.",
      "in (d) and (e), it jointly tests the Indigenous \u00d7 T1 and Indigenous \u00d7 T2 terms (2 df) and, separately, the 6 race \u00d7 "
      "tertile terms of its own tertiles (6 df), with the same cluster-robust covariance.")
k_rod = [k for k in de if isinstance(e13.get(k), str) and "Sources:" in e13[k]]
outras = [k for k in de if k not in k_rod]
novas_esp = sorted(list(C6.values()) + [esp[k][1] for k in esp])
novas_got = sorted(str(e14[k]) for k in outras if k in e14)
ok("P2.03", "ESM_1 (pacote e Submissao/): só a aba S2b muda — rodapé = o da v13 com o Wald de 6 gl em (d) e (e), e as 2 colunas novas "
   "(cabeçalhos e 6 valores); as células das colunas seguintes deslocadas sem mudar de conteúdo",
   e14 == es and all(k[0].startswith("S2b_") for k in de) and len(k_rod) == 1 and e13[k_rod[0]].count(W2[0]) == 1
   and e14[k_rod[0]] == e13[k_rod[0]].replace(*W2)
   and sorted(str(v) for k, v in e14.items() if k[0].startswith("S2b_") and k not in k_rod) ==
   sorted([str(v) for k, v in e13.items() if k[0].startswith("S2b_") and k not in k_rod] + novas_esp),
   f"{len(de)} células diferentes")
d13, d14 = docx.Document(A13 / "tabelas" / f"tabelas_principais_{V13}.docx"), docx.Document(MS / "tabelas" / f"tabelas_principais_{V14}.docx")
ok("P3.01", "docx: células iguais; parágrafos iguais, fora o rótulo de versão",
   [c.text for t in d13.tables for r in t.rows for c in r.cells] == [c.text for t in d14.tables for r in t.rows for c in r.cells]
   and [p.text.replace(V13, V14) for p in d13.paragraphs] == [p.text for p in d14.paragraphs])
txt = lambda f: "\n".join(pg.get_text() for pg in pymupdf.open(f))
pix = lambda f: (lambda im: (im.size, im.mode, im.info.get("dpi"), md5(im.tobytes())))(Image.open(f))
ims = [f for d_ in ("figuras", "suplementar") for f in sorted((A13 / d_).glob(f"*_{V13}.*")) if f.suffix in (".png", ".tif")]
ok("P3.02", "PDFs (S7, S8, ESM_2–4) com o mesmo texto da v13; ESM_2/3 = S7/S8 da v14; figuras 1–4 e S9 e Fig1–4 de Submissao/ com os mesmos pixels",
   all(txt(A13 / "suplementar" / n.format(V13)) == txt(MS / "suplementar" / n.format(V14)) for n in ("S7_variables_codes_{}.pdf", "S8_strobe_record_checklist_{}.pdf"))
   and all(txt(SUB / f"ESM_{k}.pdf") == txt(A13 / "Submissao" / f"ESM_{k}.pdf") for k in (2, 3, 4))
   and md5((SUB / "ESM_2.pdf").read_bytes()) == md5((MS / "suplementar" / f"S7_variables_codes_{V14}.pdf").read_bytes())
   and len(ims) == 10 and all(pix(f) == pix(MS / f.parent.name / f.name.replace(V13, V14)) for f in ims)
   and all(pix(SUB / f"Fig{k}.tif") == pix(A13 / "Submissao" / f"Fig{k}.tif") for k in range(1, 5)))
norm = lambda t, v: [re.sub(r"\| [0-9a-f]{12} \|$", "| MD5 |", l.replace(v, "VX")) for l in t.splitlines()]
m13, m14 = norm((A13 / f"MANIFEST_{V13}.md").read_text(), V13), norm((MS / "MANIFEST.md").read_text(), V14)
dm = [(a, b) for a, b in zip(m13, m14) if a != b]
ok("P4.01", "MANIFEST (versão e MD5 normalizados): mudam só o título (Etapas 7b–8b) e o parágrafo de abertura (data, commit cdddf8f, etapa, v14)",
   len(m13) == len(m14) and len(dm) == 2 and dm[0][1] == dm[0][0].replace("Etapas 7b–8,", "Etapas 7b–8b,")
   and "v14 = v13 com o Wald de 6 gl" in dm[1][1] and "Commit do repositório ao gerar o pacote: cdddf8f" in dm[1][1] and f"'{TITULO}')" in dm[1][1],
   [b[:70] for a, b in dm])
lm = (MS / "MANIFEST.md").read_text().splitlines()
lin = [re.match(r"^\| ((?:manuscrito|Submissao)/\S+) \| .* \| ([0-9a-f]{12}) \|$", l) for l in lm if re.match(r"^\| (manuscrito|Submissao)/", l)]
lugar = lambda c: (MS / c[len("manuscrito/"):]) if c.startswith("manuscrito/") else PROJ / c
espm = [f"{rot}/{f.name}" for pasta, rot in [(MS / "tabelas", "manuscrito/tabelas"), (MS / "figuras", "manuscrito/figuras"), (MS / "suplementar", "manuscrito/suplementar"),
                                             (MS, "manuscrito"), (SUB, "Submissao")]
        for f in sorted(pasta.iterdir()) if f.is_file() and not f.name.startswith(("._", "_", "audita_")) and f.name != "MANIFEST.md"]
ok("P4.02", "MANIFEST: MD5 de cada arquivo confere; lista completa, sem repetição; toda linha de tabela bem formada",
   bool(lin) and all(m and md5(lugar(m.group(1)).read_bytes())[:12] == m.group(2) for m in lin) and sorted(m.group(1) for m in lin) == sorted(espm)
   and all(len(re.findall(r"(?<!\\)\|", l)) in (4, 5) for l in lm if l.startswith("|")), f"{len(lin)} arquivos")
dc13 = " ".join((A13 / f"data_code_availability_{V13}.md").read_text().split())
dc14 = " ".join((MS / "data_code_availability.md").read_text().split())
volta = dc14.replace(V14, V13).replace(TITULO, T8).replace('`git log --grep "^Etapa 8b:"`', '`git log --grep "^Etapa 8:"`').replace("Etapa 8b)", "Etapa 8)")
ok("P5.01", "disponibilidade igual à v13, fora versão, etapa e commit de referência (grep '^Etapa 8b:'); legendas iguais, fora o rótulo de versão",
   volta == dc13 and dc14.count('`git log --grep "^Etapa 8b:"`') == 1
   and (MS / "legendas_figuras.md").read_text().replace(V14, V13) == (A13 / f"legendas_figuras_{V13}.md").read_text())

# ======================= C. scripts =======================
TROCAS = {
    "scripts/etapa7b_lib.py": [
        ('V = "v13_20261013"               # versão/data do pacote (v13 = Etapa 8: cobertura da Atenção Básica na S2b e nota "n.a." da Tabela 4; v1–v12 em outputs/manuscrito/_arquivo_v1.._v12)',
         'V = "v14_20261026"               # versão/data do pacote (v14 = Etapa 8b: Wald de 6 gl da cobertura na S2b; v1–v13 em outputs/manuscrito/_arquivo_v1.._v13)'),
        ('md = ["# Key numbers (Etapas 7b–8)"', 'md = ["# Key numbers (Etapas 7b–8b)"')],
    "scripts/etapa7b_01_tabelas.py": [
        ('''B.grava_xlsx(XL, B.TABD / f"tabelas_principais_{B.V}.xlsx")''',
         '''# Etapa 8b: Wald de 6 gl (todos os termos raça × tercil) das duas exposições da Etapa 8, mostrado na S2b (pacote v14)
for ex_, (sf_, txt_) in ROT8.items():
    for d_ in ["ptb", "pig", "ptb_ind"]:
        w = e8w.loc[(ex_, d_)]
        R.add(f"Wald6_{sf_}_{d_}", float(w.p_6gl), B.pval(w.p_6gl), "tab_e8_04_wald",
              f"Wald p (6 race\\u00d7tertile terms), {txt_}, births 2015\\u20132021, {B.OUTC[d_]}", f"exposicao={ex_}, desfecho={d_}")
B.grava_xlsx(XL, B.TABD / f"tabelas_principais_{B.V}.xlsx")''')],
    "scripts/etapa7b_02_suplementar.py": [
        ('''        rows[-1][f"{col_}: Wald p, Indigenous terms (2 df)"] = B.pval(w.p_ind_2gl)''',
         '''        rows[-1][f"{col_}: Wald p, Indigenous terms (2 df)"] = B.pval(w.p_ind_2gl)
        rows[-1][f"{col_}: Wald p, 6 race\\u00d7tertile terms (6 df)"] = B.pval(w.p_6gl)     # Etapa 8b (v14)'''),
        ('''"Indigenous \\u00d7 T1 and T2; 6 df); in (d) and (e), it jointly tests the Indigenous \\u00d7 T1 and Indigenous \\u00d7 T2 terms (2 df), "
       "with the same cluster-robust covariance.''',
         '''"Indigenous \\u00d7 T1 and T2; 6 df); in (d) and (e), it jointly tests the Indigenous \\u00d7 T1 and Indigenous \\u00d7 T2 terms (2 df) "
       "and, separately, the 6 race \\u00d7 tertile terms of its own tertiles (6 df), with the same cluster-robust covariance.'''),
        ('ETAPA = "Etapa 8: sensibilidade com a cobertura da Atenção Básica (pacote v13)"', 'ETAPA = "Etapa 8b: Wald de 6 gl da cobertura na S2b (pacote v14)"'),
        ('(draft, package {B.V}, Etapa 8)', '(draft, package {B.V}, Etapa 8b)'),
        ('`git log --grep "^Etapa 8:"`', '`git log --grep "^Etapa 8b:"`')],
    "scripts/etapa7b_04_submissao.py": [
        ('''  8: S2b com a cobertura da Atenção Básica (colunas d e e); MANIFEST com a v13 no histórico
"""''', '''  8: S2b com a cobertura da Atenção Básica (colunas d e e); MANIFEST com a v13 no histórico
  8b: Wald de 6 gl das colunas d e e na S2b; MANIFEST com a v14 no histórico
"""'''),
        ('(Etapas 7b–8, {V})', '(Etapas 7b–8b, {V})'),
        ("'Etapa 8: sensibilidade com a cobertura da Atenção Básica (pacote v13)'). Nenhuma", "'Etapa 8b: Wald de 6 gl da cobertura na S2b (pacote v14)'). Nenhuma"),
        ('''"Tabela 4. Scripts em scripts/.''', '''"Tabela 4; v14 = v13 com o Wald de 6 gl (termos raça × tercil) nas colunas d e e da Tabela S2b e seus 6 números-chave (Etapa 8b). "
          "Scripts em scripts/.''')],
}
rui = {}
for a, trocas in TROCAS.items():
    v_, n_ = git("show", f"{BASE}:{a}"), (PROJ / a).read_text()
    cont = [v_.count(x) for x, _ in trocas]
    for x, y in trocas:
        v_ = v_.replace(x, y)
    if cont != [1] * len(trocas) or v_ != n_:
        rui[a] = f"ocorrências {cont}; reproduz {v_ == n_}"
ok("C1.01", "lib, 01, 02 e 04: o arquivo atual = o de cdddf8f com exatamente estas trocas (cada trecho velho ocorre uma vez): versão, 6 "
   "números-chave, colunas e rodapé da S2b, etapa e grep '^Etapa 8b:', MANIFEST", not rui, rui or {a: len(t) for a, t in TROCAS.items()})
c14, c13 = pd.read_csv(MS / f"checa_7b_{V14}.csv"), pd.read_csv(A13 / f"checa_7b_{V13}.csv")
r13, r14 = set(c13.verificacao.str.replace(V13, "VX")), set(c14.verificacao.str.replace(V14, "VX"))
ok("C2.01", "checa da v14: 140/140; as 128 da v13 continuam com os mesmos rótulos; as 12 novas são da Etapa 8b ('8b ')",
   len(c14) == 140 and c14.ok.astype(bool).all() and len(c13) == 128 and r13 <= r14 and len(r14 - r13) == 12 and all(x.startswith("8b ") for x in r14 - r13),
   f"sumiram {sorted(r13 - r14)[:2]}")
ck, ck0 = (PROJ / "scripts/etapa7b_checa.py").read_text(), git("show", f"{BASE}:scripts/etapa7b_checa.py")
cab = git("diff", "-U0", BASE, "--", "scripts/etapa7b_checa.py")
rem_l, add_l = set(), set()
for m in re.finditer(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", cab, re.M):
    a, b, c, d_ = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1), int(m.group(3)), int(m.group(4) if m.group(4) is not None else 1)
    rem_l |= set(range(a, a + b))
    add_l |= set(range(c, c + d_))
L0, L1 = ck0.splitlines(), ck.splitlines()
lin_de = lambda L, s: [i + 1 for i, l in enumerate(L) if l.startswith(s)]
i0 = (lin_de(L0, "# ---- 9i.")[0], lin_de(L0, "# sem 'ICR'")[0] - 1)
doc0 = lin_de(L0, "  9i. Etapa 8")
p0 = [i + 1 for i, l in enumerate(L0) if '"173fecd", "Etapa 7b.2", "Etapa 8",' in l]
rem_fora = sorted(i for i in rem_l if not (i0[0] <= i <= i0[1]) and i not in doc0 + p0)
reg = [(lin_de(L1, "  9i. Etapa 8")[0], lin_de(L1, "  9j. Etapa 8b")[0]), (lin_de(L1, 'A13, V13 = B.MS / "_arquivo_v13"')[0],) * 2,
       (lin_de(L1, "J13l = json.load")[0], lin_de(L1, "J13 = {")[0]), (lin_de(L1, "# ---- 9i.")[0], lin_de(L1, "# sem 'ICR'")[0] - 1),
       ([i + 1 for i, l in enumerate(L1) if '"173fecd", "Etapa 7b.2", "Etapa 8b",' in l][0],) * 2]
add_fora = sorted(i for i in add_l if not any(a <= i <= b for a, b in reg))
g9i = ck[ck.index("# ---- 9i."):ck.index("# ---- 9j.")]
ok("C2.02", "checa: linhas removidas só na docstring, no bloco 9i e na lista da disponibilidade; acrescentadas só na docstring, em A13/J13, "
   "nos blocos 9i/9j e na lista ('Etapa 8b'); o 9i compara v12 × v13 arquivadas (sem Jcur, B.TABD, B.SUPD, B.SUB, B.FIGD, B.V, B.MS)",
   rem_l and not rem_fora and not add_fora and not any(x in g9i for x in ("Jcur", "B.TABD", "B.SUPD", "B.SUB", "B.FIGD", "B.V", "B.MS"))
   and "pacote_esperado(V13)" in g9i, f"{len(rem_l)} removidas, {len(add_l)} acrescentadas; fora: {rem_fora[:3]} / {add_fora[:3]}")

# ---- sandbox: checa com mutações, commit simulado, LEIAME
class GuardaFalhou(Exception):
    pass


TMP = Path(tempfile.mkdtemp(prefix="audita8b_"))
BASE_SBX = TMP / "base"
tab_antes = {f.name: (f.stat().st_size, f.stat().st_mtime) for f in TB.iterdir()}
SEM_ASSERT = ("import sys; sys.path.insert(0, 'scripts'); src = open('scripts/etapa7b_checa.py').read(); "
              "assert src.count('    assert cond, nome\\n') == 1; "
              "exec(compile(src.replace('    assert cond, nome\\n', '    pass\\n'), 'scripts/etapa7b_checa.py', 'exec'), {'__name__': '__main__'})")
GUARDA = TMP / "guarda"
GUARDA_PY = """import os, sys
_F = "/Volumes/Forja"
_W = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC
_dentro = [False]
def _forja(p):
    if isinstance(p, int) or p is None:
        return False
    r = os.path.realpath(os.fsdecode(p))
    return r == _F or r.startswith(_F + "/")
def _guarda(ev, a):
    if _dentro[0]:
        return
    _dentro[0] = True
    try:
        alvo = []
        if ev == "open" and ((isinstance(a[1], str) and any(c in a[1] for c in "wax+")) or (isinstance(a[2], int) and a[2] & _W)):
            alvo = [a[0]]
        elif ev in ("os.remove", "os.rmdir", "os.mkdir", "os.truncate", "os.chmod", "os.utime", "shutil.rmtree"):
            alvo = [a[0]]
        elif ev in ("os.rename", "shutil.move"):
            alvo = [a[0], a[1]]
        elif ev in ("os.symlink", "os.link", "shutil.copyfile", "shutil.copytree"):
            alvo = [a[1]]
        if any(_forja(x) for x in alvo):
            raise PermissionError(f"guarda 8b: {ev} no Forja bloqueado: {alvo}")
    finally:
        _dentro[0] = False
sys.addaudithook(_guarda)
"""


def monta():
    GUARDA.mkdir()
    (GUARDA / "sitecustomize.py").write_text(GUARDA_PY)
    subprocess.run(["git", "clone", "-q", "-s", str(PROJ), str(BASE_SBX)], check=True, env=ENV)
    for s_, p in ns:                                       # as mudanças rastreadas da Etapa 8 (inclusive as renomeações)
        if s_ == "D":
            (BASE_SBX / p).unlink()
        else:
            (BASE_SBX / p).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PROJ / p, BASE_SBX / p)
    for p in naor:                                         # novos não ignorados; de docs/referencias, só o mapa e o ACESSO da cobertura
        if not p.startswith("docs/referencias/") or p.endswith(("territorio_dez24/rl_municip_regsaud.csv", "aps_cobertura_ab/ACESSO.txt")):
            (BASE_SBX / p).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PROJ / p, BASE_SBX / p)
    (BASE_SBX / "outputs/tables").mkdir(parents=True, exist_ok=True)
    for f in TB.iterdir():                                 # ignorados: só links simbólicos (leitura), nenhuma cópia
        (BASE_SBX / "outputs/tables" / f.name).symlink_to(f)
    for f in (PROJ / "audit_independente").rglob("comparacao_*.csv"):
        if not f.name.startswith("._") and not (BASE_SBX / f.relative_to(PROJ)).exists():
            (BASE_SBX / f.relative_to(PROJ)).parent.mkdir(parents=True, exist_ok=True)
            (BASE_SBX / f.relative_to(PROJ)).symlink_to(f)
    (BASE_SBX / "data/raw/aps_cobertura_ab").mkdir(parents=True)
    for f in RAW.glob("cobertura_ab_uf*_201401_202012.json"):     # dado público agregado por município (o checa confere o MD5)
        (BASE_SBX / "data/raw/aps_cobertura_ab" / f.name).symlink_to(f)
    (BASE_SBX / "outputs/logs").mkdir(parents=True, exist_ok=True)


def roda(dirr, codigo=None, script=None, env=None):
    """Todo Python do sandbox carrega a guarda (sitecustomize com audit hook): nada de escrita, remoção ou renomeação no Forja."""
    cmd = [sys.executable, "-c", codigo] if codigo else [sys.executable, script]
    e = {**ENV, **(env or {})}
    e["PYTHONPATH"] = os.pathsep.join([str(GUARDA)] + ([e["PYTHONPATH"]] if e.get("PYTHONPATH") else []))
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(cmd, cwd=dirr, capture_output=True, text=True, env=e, timeout=1800)


def falhas(dirr, r, pai=""):
    f = dirr / f"outputs/manuscrito/checa_7b_{V14}.csv"
    if r.returncode or not f.exists():
        return dict(rc=r.returncode, n=0, fl=[r.stderr.strip()[-300:]], rot=set(), pai=pai)
    c = pd.read_csv(f)
    return dict(rc=0, n=len(c), fl=sorted(c.verificacao[~c.ok.astype(bool)]), rot=set(c.verificacao), pai=pai)


def jmuda(fun, rel=f"outputs/manuscrito/numeros_chave_{V14}.json"):
    def f(d):
        p = d / rel
        J = json.load(open(p))
        fun(J)
        p.write_text(json.dumps(J, ensure_ascii=False, indent=1))
    return f


def troca_txt(rel, a, b):
    def f(d):
        t = (d / rel).read_text()
        assert t.count(a) >= 1, (rel, a)
        (d / rel).write_text(t.replace(a, b, 1))
    return f


def xl_troca(rel, aba, a, b):
    def f(d):
        wb = openpyxl.load_workbook(d / rel)
        ws = [w for w in wb.worksheets if w.title.startswith(aba)][0]
        c = [c for row in ws.iter_rows() for c in row if c.value and a in str(c.value)][0]
        c.value = str(c.value).replace(a, b)
        wb.save(d / rel)
    return f


def dx_muda(d):
    p = d / f"outputs/manuscrito/tabelas/tabelas_principais_{V14}.docx"
    D_ = docx.Document(p)
    par = [q for q in D_.paragraphs if NOTA_NA.strip() in q.text][0]
    par.text = par.text.replace(NOTA_NA, "")
    D_.save(p)


def px_muda(d, rel=f"outputs/manuscrito/figuras/fig02_pr_race_m1m3_{V14}.png"):
    p = d / rel
    im = Image.open(p)
    dpi = im.info.get("dpi")
    im = im.convert("RGB")
    im.putpixel((5, 5), (1, 2, 3))
    im.save(p, dpi=dpi)


def xl_digito(rel):
    """Soma 1 ao 1º dígito da 1ª célula com dígito da 2ª aba (nem a 1ª nem a última célula da aba, que o 9i/9j antigos já comparavam)."""
    def f(d):
        wb = openpyxl.load_workbook(d / rel)
        cs = [c for row in wb.worksheets[1].iter_rows() for c in row if c.value is not None]
        c = [c for c in cs[1:-1] if re.search(r"\d", str(c.value))][0]
        s = str(c.value); i = re.search(r"\d", s).start()
        c.value = s[:i] + str((int(s[i]) + 1) % 10) + s[i + 1:]
        wb.save(d / rel)
    return f


def csv_muda(rel):
    def f(d):
        p = d / rel
        L_ = p.read_text().split("\n")
        k = [j for j, l in enumerate(L_) if j and re.search(r"\d", l)][0]
        i = re.search(r"\d", L_[k]).start()
        L_[k] = L_[k][:i] + str((int(L_[k][i]) + 1) % 10) + L_[k][i + 1:]
        p.write_text("\n".join(L_))
    return f


def md5_muda(d):
    p = d / "docs/referencias/aps_cobertura_ab/ACESSO.txt"
    t = p.read_text()
    m = re.search(r"\) = ([0-9a-f])", t)
    p.write_text(t[:m.start(1)] + ("0" if m.group(1) != "0" else "1") + t[m.start(1) + 1:])



GIT_ID = ["-c", "user.name=audita8b", "-c", "user.email=audita8b@local"]


def caso(k, mut=None, commit=None):
    d = TMP / f"m{k:02d}"
    subprocess.run(["cp", "-cR", str(BASE_SBX), str(d)], check=True)
    try:
        if commit == "unico":
            git(*GIT_ID, "add", "-A", cwd=d)
            git(*GIT_ID, "commit", "-q", "-m", TITULO, cwd=d)
            (d / f"outputs/manuscrito/checa_7b_{V14}.csv").unlink()
            r = roda(d, script="scripts/etapa7b_checa.py")   # o checa de verdade, com assert
            return falhas(d, r, git("rev-parse", "--short", "HEAD^", cwd=d).strip())
        if commit == "meio":
            git(*GIT_ID, "add", "scripts/etapa7b_lib.py", cwd=d)
            git(*GIT_ID, "commit", "-q", "-m", "lib antes", cwd=d)
            git(*GIT_ID, "add", "-A", cwd=d)
            git(*GIT_ID, "commit", "-q", "-m", TITULO, cwd=d)
        if mut:
            mut(d)
        (d / f"outputs/manuscrito/checa_7b_{V14}.csv").unlink()
        r = roda(d, codigo=SEM_ASSERT)
        return falhas(d, r)
    finally:
        shutil.rmtree(d, ignore_errors=True)



S2B = f"outputs/manuscrito/suplementar/S2b_access_specifications_{V14}.csv"
MUT = [   # (nome, mutação, rótulo que tem de falhar, mexe só na v14?)
    ("um Wald de 6 gl da S2b (CSV)", troca_txt(S2B, ",0.00369,", ",0.00370,"), "8b S2b: colunas novas", True),
    ("frase do Wald de 6 gl tirada do rodapé da S2b (ESM_1 do pacote)", xl_troca(f"outputs/manuscrito/suplementar/ESM_1_tables_S1_S6_{V14}.xlsx", "S2b_",
     " and, separately, the 6 race \u00d7 tertile terms of its own tertiles (6 df),", ","), "8b ESM_1", True),
    ("rodapé da S2b no ESM_1 de Submissao/", xl_troca("Submissao/ESM_1.xlsx", "S2b_", "(b) to (e) belong", "(b) and (c) belong"), "8b ESM_1", True),
    ("valor formatado de Wald6_aps_ptb", jmuda(lambda J: [i.update(valor_formatado="0.0037") for i in J if i["id"] == "Wald6_aps_ptb"]),
     "8b commit_registro recalculado", True),
    ("commit_analise de um número da Etapa 8", jmuda(lambda J: [i.update(commit_analise="") for i in J if i["id"] == "IC_Ind_T1_aps_pig"]),
     "8b números-chave", True),
    ("grep da disponibilidade", troca_txt("outputs/manuscrito/data_code_availability.md", '"^Etapa 8b:"', '"^Etapa 8:"'), "8b data_code_availability", True),
    ("um pixel da figura 2 (png) da v14", px_muda, "8b figuras", True),
    # rodada 1 do auditor independente da 8b: mutações que passavam pelo 9j
    ("título do commit da Etapa 8 na disponibilidade", troca_txt("outputs/manuscrito/data_code_availability.md",
     '"Etapa 8b: Wald de 6 gl da cobertura na S2b (pacote v14)"', '"Etapa 8: sensibilidade com a cobertura da Atenção Básica (pacote v13)"'),
     "8b data_code_availability", True),
    ("p de 6 gl de (d) trocado pelo de (e) só na célula da S2b do ESM_1", xl_troca(f"outputs/manuscrito/suplementar/ESM_1_tables_S1_S6_{V14}.xlsx",
     "S2b_", "0.00369", "0.00284"), "8b xlsx célula a célula", True),
    ("uma célula de outra aba do ESM_1", xl_digito(f"outputs/manuscrito/suplementar/ESM_1_tables_S1_S6_{V14}.xlsx"), "8b xlsx célula a célula", True),
    ("uma célula das tabelas principais (xlsx)", xl_digito(f"outputs/manuscrito/tabelas/tabelas_principais_{V14}.xlsx"), "8b xlsx célula a célula", True),
    ("um pixel da S9 (png) da v14", lambda d: px_muda(d, f"outputs/manuscrito/suplementar/S9_maihda_caterpillar_{V14}.png"), "8b S9", True),
    ("MANIFEST arquivado da v13", troca_txt(f"outputs/manuscrito/_arquivo_v13/MANIFEST_{V13}.md", "MANIFEST", "MANIFESTO"), "8b _arquivo_v13", False),
    ("um dígito de um CSV da v13 arquivada", csv_muda(f"outputs/manuscrito/_arquivo_v13/tabelas/tab02_models_m1m3_{V13}.csv"), "8 v12 × v13 célula a célula", False),
]
try:
    monta()
    alvo_t = sorted(f.name for f in (BASE_SBX / "outputs/tables").iterdir())[0]
    g1 = roda(BASE_SBX, codigo=f"open('outputs/tables/{alvo_t}', 'a')")
    g2 = roda(BASE_SBX, codigo="import os; os.remove('outputs/tables/" + alvo_t + "')")
    g4 = roda(BASE_SBX, codigo="open('outputs/logs/teste_guarda.txt', 'w').write('x')")
    ok("C6.00a", "guarda do sandbox: escrever ou remover pelo link de outputs/tables é bloqueado; escrever dentro do sandbox funciona",
       all(r.returncode != 0 and "guarda 8b" in r.stderr for r in (g1, g2)) and g4.returncode == 0, [r.returncode for r in (g1, g2, g4)])
    (BASE_SBX / "outputs/logs/teste_guarda.txt").unlink(missing_ok=True)
    if not R[-1]["ok"]:
        raise GuardaFalhou("a guarda do sandbox não funcionou")
    with cf.ThreadPoolExecutor(4) as ex:
        fb = ex.submit(caso, 0)
        fm = [ex.submit(caso, k + 1, m) for k, (_, m, _, _) in enumerate(MUT)]
        fu = ex.submit(caso, 90, commit="unico")
        fi = ex.submit(caso, 91, commit="meio")
        rb, fm, ru, ri = fb.result(), [f.result() for f in fm], fu.result(), fi.result()
    ok("C6.00", "sandbox: o checa (sem o assert) dá 140/140, com os mesmos rótulos do checa da v14",
       rb["rc"] == 0 and rb["n"] == 140 and not rb["fl"] and rb["rot"] == set(c14.verificacao), f"{rb['n']}; falhas {rb['fl'][:2]}")
    for k, ((nome, _, alvo, so14), r_) in enumerate(zip(MUT, fm)):
        ok(f"C6.{k + 1:02d}", f"mutação ({nome}): o checa acusa '{alvo}'" + ("; os blocos que comparam versões arquivadas (7c.x, 8 ) não se mexem" if so14 else ""),
           r_["rc"] == 0 and any(x.startswith(alvo) for x in r_["fl"]) and (not so14 or not any(x.startswith(("7c.", "8 ")) for x in r_["fl"])),
           f"falhas {[x[:45] for x in r_['fl']][:4]}")
    ok("C6.20", "commit único simulado: o checa de verdade (com assert) dá 140/140; commit_pacote = pai do commit (cdddf8f)",
       ru["rc"] == 0 and ru["n"] == 140 and not ru["fl"] and ru["pai"] == BASE, f"{ru['n']}; falhas {ru['fl'][:2]}; pai {ru['pai']}")
    ok("C6.21", "com um commit no meio, o checa acusa o commit_pacote", ri["rc"] == 0 and any(x.startswith("8b commit_pacote") for x in ri["fl"]), ri["fl"][:3])
except GuardaFalhou as e:
    ok("C6.99", "sandbox interrompido", False, e)
finally:
    shutil.rmtree(TMP, ignore_errors=True)
ok("C6.23", "outputs/tables intacta depois do sandbox; sandbox apagado",
   tab_antes == {f.name: (f.stat().st_size, f.stat().st_mtime) for f in TB.iterdir()} and not TMP.exists())

# ======================= D. logs × mtimes =======================
ev = []
for l in (PROJ / "outputs/logs/etapa7b_20261008.log").read_text(errors="ignore").splitlines():
    m = re.match(r"^\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\] \[([^\]]+)\] (.*)", l)
    if not m:
        continue
    t = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").timestamp()
    if t <= T_BASE:
        continue
    s_, msg = m.group(2), m.group(3)
    e = {"7b_01_tabelas": "01", "7b_02_suplementar": "02", "7b_03_figuras": "03", "7b_04_submissao": "04"}.get(s_)
    if s_ == "7b_checa":
        e = "checa_ini" if msg.startswith("OK  números-chave = arquivo de origem") else "checa_fim" if msg.startswith("autoauditoria 7b:") else "checa_falha" if msg.startswith("FALHA") else None
    if e:
        ev.append((t, e))
ev.sort()
seq = [e for _, e in ev]
ok("D1.01", "execuções desde cdddf8f: três rodadas de 01, 02, 03, 04, checa, 04 (a 2ª depois de reforçar o 9j: grep da disponibilidade; "
   "a 3ª depois da rodada 1 do auditor independente: rodapé e cabeçalho da S2b e 9j reforçado)",
   seq == ["01", "02", "03", "04", "checa_ini", "checa_fim", "04"] * 3,
   [f"{datetime.fromtimestamp(t):%H:%M:%S} {e}" for t, e in ev])
if len(ev) == 21:
    t01, t02, t03, t04a, tci, tcf, t04 = [t for t, _ in ev[14:]]
    T_BASE2 = ev[13][0]
    dentro = lambda f, a, b: a - 2 <= f.stat().st_mtime <= b + 2
    jan = ([(f, T_BASE2, t01) for f in (MS / "tabelas").glob(f"*_{V14}.*")] + [(MS / f"numeros_chave_{V14}.{x}", T_BASE2, t01) for x in ("json", "md")]
           + [(f, t01, t02) for f in (MS / "suplementar").glob(f"*_{V14}.*") if not f.name.startswith("S9_")] + [(MS / "data_code_availability.md", t01, t02)]
           + [(f, t02, t03) for f in list((MS / "figuras").glob(f"*_{V14}.*")) + list((MS / "suplementar").glob(f"S9_*_{V14}.*"))]
           + [(MS / "legendas_figuras.md", t02, t03), (MS / f"checa_7b_{V14}.csv", tci, tcf), (MS / "MANIFEST.md", tcf, t04), (SUB / "ESM_4.pdf", tcf, t04)])
    fora = [f.name for f, a, b in jan if not dentro(f, a, b)]
    lim = {"scripts/etapa7b_lib.py": t01, "scripts/etapa7b_01_tabelas.py": t01, "scripts/etapa7b_02_suplementar.py": t01,
           "scripts/etapa7b_04_submissao.py": t01, "scripts/etapa7b_checa.py": tci}
    tarde = [s_ for s_, l_ in lim.items() if (PROJ / s_).stat().st_mtime > l_]
    ok("D1.02", "cada saída com mtime na janela do script que a grava; nenhum script editado depois da execução", not fora and not tarde and len(jan) >= 40,
       f"{len(jan)} arquivos; fora {fora[:3]}; editados depois {tarde}")
else:
    ok("D1.02", "janelas de mtime (não conferidas: a sequência do D1.01 não bate)", False)

# ======================= E. microdados e git no que vai para o commit =======================
vai = sorted(set(p for s_, p in ns if s_ != "D") | {p for p in naor if not p.startswith("docs/referencias/")})
EXT = (".parquet", ".dbc", ".dbf", ".rds", ".rda", ".rdata", ".sav", ".dta", ".feather", ".sqlite", ".db", ".gz", ".zip", ".7z")
ruim_e = [p for p in vai if p.startswith("data/") or p.lower().endswith(EXT) or Path(p).name.startswith("._") or Path(p).name == ".DS_Store"
          or (p.startswith("audit_independente/") and p.endswith(".csv")) or (PROJ / p).stat().st_size > 20e6]
IDS = re.compile(r"(?i)^(NUMERODN|NUMERODV|DTNASC|DTNASCMAE|CODMUNRES|CODMUNNASC|CODESTAB|CONTADOR|coMunicipioIbge)$")
lin_max = {p: len(pd.read_csv(PROJ / p, dtype=str)) for p in vai if p.endswith(".csv")}
col_id = [f"{p}:{c}" for p in vai if p.endswith(".csv") for c in pd.read_csv(PROJ / p, nrows=0).columns if IDS.match(str(c))]
ok("E1.01", "o que vai para o commit: nada em data/, nenhum parquet/rds/zip, nenhum ._*, nenhum CSV do auditor, nada > 20 MB; CSVs só agregados "
   "(≤ 1.000 linhas, sem coluna identificadora); .gitignore igual ao de cdddf8f",
   vai and not ruim_e and max(lin_max.values()) <= 1000 and not col_id and (PROJ / ".gitignore").read_text() == git("show", f"{BASE}:.gitignore"),
   f"{len(vai)} arquivos; problemas {ruim_e[:3]}; maior CSV {max(lin_max.values())}")

out = pd.DataFrame(R)
out.to_csv(SAIDA, index=False)
print(out.to_string(max_colwidth=160))
print(f"\n{int(out.ok.sum())}/{len(out)} OK")
